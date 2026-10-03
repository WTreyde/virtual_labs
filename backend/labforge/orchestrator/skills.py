"""Generate an orchestrating agent for a designed lab: a SKILL.md plus a device and tool manifest.

The digital twin already knows what an orchestrator needs: the workflow graph, which transporter
serves which handoff, each instrument's limits and confidence, the safety zones, the bottleneck and
how long each step should take. This module writes that down for an LLM that has the instrument
APIs, so the agent that runs the real lab starts from the twin instead of from scratch.

Inputs are the existing contracts (LabSpec, Workflow, Layout, SimResult, CatalogItems, and
optionally Claims and a ProjectSchedule from /prioritise). Nothing here calls Claude or the
simulator; it is a pure function of a finished design, so it is cheap and deterministic.

Honesty rules carried into the output:
- every limit keeps its confidence; placeholder values become "measure on first run" tasks;
- unresolved layout violations become a pre-flight gate that needs a human sign-off;
- refuted claims cap what the agent may promise; it reports the verified value instead;
- instruments without a confirmed standard control interface are marked, not assumed drivable.

The tool manifest is shaped like MCP tool definitions with a per-device limits and safety block.
That is aligned with the idea of device descriptions carrying capabilities and safety limits
(e.g. Anthropic's Model Hardware Standard, whose spec is not public); it does not implement it.
"""
import json
import re
from pathlib import Path

from labforge.layout.safety import load_rules

GENERATOR = "labforge.orchestrator"
ALIGNMENT_NOTE = ("Each devices[] entry is a device sheet: capabilities used, limits with confidence, safety and "
                  "control interface. Tool definitions follow the MCP tool shape (name, description, input_schema) with a device "
                  "limits/safety block. Aligned with device-description standards such as Anthropic's Model "
                  "Hardware Standard; not an implementation of it (spec not public).")
STANDARD_API = re.compile(r"sila|opc[- ]?ua|rest|python|sdk|api", re.I)
OPEN_STANDARD = re.compile(r"sila|opc[- ]?ua", re.I)
UNCONFIRMED = re.compile(r"not confirmed|unknown|unclear", re.I)
PAUSE_FACTOR = 1.5  # a step running past PAUSE_FACTOR x its P90-style high bound is paused and escalated


# ---------- small helpers ----------

def _fmt_s(s: float | None) -> str:
    if s is None:
        return "?"
    s = float(s)
    if s < 120:
        return f"{s:.0f} s"
    if s < 7200:
        return f"{s / 60:.0f} min"
    if s < 172800:
        return f"{s / 3600:.1f} h"
    return f"{s / 86400:.1f} d"


def _group(ids: list[str]) -> str:
    """Join instance ids, folding numbered siblings: dry_shipper_1..dry_shipper_7 -> dry_shipper_1-7."""
    out, runs = [], {}
    for i in ids:
        stem, _, n = i.rpartition("_")
        if stem and n.isdigit():
            runs.setdefault(stem, []).append(int(n))
        else:
            out.append(i)
    for stem, ns in runs.items():
        ns.sort()
        out.append(f"{stem}_{ns[0]}" if len(ns) == 1 else
                   f"{stem}_{ns[0]}-{ns[-1]}" if ns == list(range(ns[0], ns[-1] + 1)) else ", ".join(f"{stem}_{n}" for n in ns))
    return ", ".join(sorted(out))


def _waves(steps: list[dict]) -> list[list[str]]:
    """Steps grouped into dependency levels: everything in a wave can run once earlier waves are done."""
    done, waves, pending = set(), [], list(steps)
    while pending:
        ready = [s for s in pending if set(s.get("after", [])) <= done]
        if not ready:
            raise ValueError("Workflow has a dependency cycle or depends on a missing step.")
        waves.append([s["id"] for s in ready])
        done |= {s["id"] for s in ready}
        pending = [s for s in pending if s["id"] not in done]
    return waves


def _bounds(step: dict) -> dict:
    u = step.get("duration_uncertainty") or {}
    v = float(step["duration_s"])
    out = {"expected_s": v, "low_s": float(u.get("low", v)), "high_s": float(u.get("high", v)),
           "confidence": u.get("confidence", "unspecified"), "source": u.get("source", "")}
    if not u:
        # No range given: widen so a normal run is not flagged, and say the bound is a guess.
        out.update(low_s=v * 0.5, high_s=v * 1.5, confidence="placeholder", source="no range in workflow; +/-50% assumed")
    return out


def _mode(step: dict) -> str:
    mode = step.get("mode", "automated")
    if mode == "automated" and not step.get("candidate_instances"):
        return "in_silico"
    return mode


def _api_status(item: dict | None) -> tuple[str, list[str]]:
    if not item:
        return "unknown", []
    ifaces = item.get("integration") or []
    text = " ".join(ifaces)
    if not ifaces:
        status = "none_listed"
    elif OPEN_STANDARD.search(text) and not UNCONFIRMED.search(text):
        status = "open_standard"
    elif STANDARD_API.search(text) and not UNCONFIRMED.search(text):
        status = "vendor_api"
    elif UNCONFIRMED.search(text):
        status = "unconfirmed"
    else:
        status = "vendor_software_only"
    return status, ifaces


def _zone_of(pos: dict | None, zones: list[dict]) -> list[str]:
    if not pos:
        return []
    return [z["kind"] for z in zones
            if z["min"]["x"] <= pos["x"] <= z["max"]["x"] and z["min"]["y"] <= pos["y"] <= z["max"]["y"]]


def _placeholders(item: dict | None, used_caps: set[str]) -> list[dict]:
    """Catalog values this lab depends on that are only placeholders: measure them on the first run."""
    out = []
    for key, prov in ((item or {}).get("provenance") or {}).items():
        if prov.get("confidence") != "placeholder":
            continue
        relevant = key.startswith(("process.capacity", "storage_slots", "process.hold_time_s", "transport.")) or \
            any(key == f"process.durations_s.{c}" for c in used_caps)
        if relevant:
            out.append({"field": key, "value": prov.get("value"), "low": prov.get("low"), "high": prov.get("high"),
                        "note": prov.get("note") or prov.get("source", "")})
    return out


# ---------- manifest ----------

def _device(inst: dict, item: dict | None, steps: list[dict], placement: dict | None, zones: list[dict],
            transfers: list[dict]) -> dict:
    iid = inst["instance_id"]
    my_steps = [s for s in steps if iid in s.get("candidate_instances", [])]
    caps = sorted({s["capability"] for s in my_steps})
    process = (item or {}).get("process") or {}
    prov = (item or {}).get("provenance") or {}
    api, ifaces = _api_status(item)
    labware = sorted({lw for ap in (item or {}).get("access_points", []) for lw in ap.get("labware", [])})
    safety = (item or {}).get("safety") or {}
    transport = (item or {}).get("transport")

    durations = {}
    for c in caps:
        p = prov.get(f"process.durations_s.{c}", {})
        if c in process.get("durations_s", {}):
            durations[c] = {"value_s": process["durations_s"][c], "low_s": p.get("low"), "high_s": p.get("high"),
                            "confidence": p.get("confidence", (item or {}).get("data_confidence", "unspecified")),
                            "per": (process.get("duration_basis") or {}).get(c, "labware")}
    limits = {
        "capacity": process.get("capacity", 1),
        "capacity_confidence": prov.get("process.capacity", {}).get("confidence", (item or {}).get("data_confidence")),
        "storage_slots": (item or {}).get("storage_slots"),
        "accepted_labware": labware or None,
        "durations": durations or None,
        "hold_time_s": process.get("hold_time_s"),
    }
    if transport:
        limits["transport"] = {k: transport.get(k) for k in ("kind", "reach_m", "speed_m_s", "payload_kg", "pick_place_s")}
    limits = {k: v for k, v in limits.items() if v is not None}

    tools = []
    for c in caps:
        step_ids = [s["id"] for s in my_steps if s["capability"] == c]
        tools.append({
            "name": f"{iid}__{c}",
            "description": f"Run {c.replace('_', ' ')} on {iid} ({(item or {}).get('model', inst['catalog_id'])}) for one "
                           f"unit of labware. Workflow steps: {', '.join(step_ids)}. Reject the call if the device is at "
                           f"capacity ({limits.get('capacity', 1)}) or the labware type is not accepted.",
            "input_schema": {"type": "object", "required": ["step_id", "labware_id"], "properties": {
                "step_id": {"type": "string", "enum": step_ids},
                "labware_id": {"type": "string", "description": "Barcode of the plate, tube rack, puck or flask."},
                "params": {"type": "object", "description": "Protocol parameters from the workflow step; do not invent new ones."},
            }},
        })
    served = [t for t in transfers if t.get("transporter_instance") == iid]
    if served:
        pairs = sorted({f"{t['from_instance']}->{t['to_instance']}" for t in served})
        tools.append({
            "name": f"{iid}__transfer",
            "description": f"Move one labware unit with {iid}. Only these handoffs are reachable in the layout: {', '.join(pairs)}.",
            "input_schema": {"type": "object", "required": ["route", "labware_id"], "properties": {
                "route": {"type": "string", "enum": pairs},
                "labware_id": {"type": "string"},
            }},
        })
    tools.append({
        "name": f"{iid}__status",
        "description": f"Read {iid}'s state: idle/busy/error, occupied slots, current labware, last error.",
        "input_schema": {"type": "object", "properties": {}},
    })
    return {
        "instance_id": iid, "catalog_id": inst["catalog_id"],
        "vendor": (item or {}).get("vendor"), "model": (item or {}).get("model"),
        "capabilities_used": caps, "control": {"status": api, "interfaces": ifaces},
        "data_confidence": (item or {}).get("data_confidence", "unknown" if not item else "unspecified"),
        "location": {"position": (placement or {}).get("position"), "zones": _zone_of((placement or {}).get("position"), zones)},
        "limits": limits,
        "safety": {"hazards": safety.get("hazards", []), "requires_zone": safety.get("requires_zone", []),
                   "collaborative": safety.get("collaborative"), "needs_light_curtain": safety.get("needs_light_curtain")},
        "measure_on_first_run": _placeholders(item, set(caps)),
        "tools": tools,
    }


GLOBAL_TOOLS = [
    {"name": "request_human", "description": "Page an operator. Use for manual steps, every escalation trigger in the "
     "skill file, and anything outside the manifest. Blocks the affected line until acknowledged.",
     "input_schema": {"type": "object", "required": ["role", "reason", "urgency"], "properties": {
         "role": {"type": "string"}, "reason": {"type": "string"},
         "urgency": {"type": "string", "enum": ["info", "soon", "now", "stop_everything"]},
         "instances": {"type": "array", "items": {"type": "string"}}}}},
    {"name": "record_measurement", "description": "Log a measured value (step duration, capacity, hold time) so the "
     "digital twin can be re-run with real numbers. Always log first-run measurements of placeholder values.",
     "input_schema": {"type": "object", "required": ["parameter", "value"], "properties": {
         "parameter": {"type": "string", "description": "e.g. 'harvest.duration_s' or 'growth_hotel_1.storage_slots'"},
         "value": {"type": "number"}, "unit": {"type": "string"}, "labware_id": {"type": "string"}}}},
    {"name": "pause_line", "description": "Stop releasing new labware into the workflow from a given step onwards; "
     "work already inside instruments finishes.",
     "input_schema": {"type": "object", "required": ["from_step", "reason"], "properties": {
         "from_step": {"type": "string"}, "reason": {"type": "string"}}}},
]


# ---------- run order and policies ----------

def _bottleneck(sim: dict | None, workflow: dict, operator_ids: set[str]) -> dict | None:
    if not sim or not sim.get("utilisation"):
        return None
    inst = [u for u in sim["utilisation"] if u["instance_id"] not in operator_ids]
    if not inst:
        return None
    top = max(inst, key=lambda u: u["busy_fraction"])
    steps = [s["id"] for s in workflow["steps"] if top["instance_id"] in s.get("candidate_instances", [])]
    peers = sorted({i for s in workflow["steps"] if s["id"] in steps for i in s["candidate_instances"]})
    return {"instance_id": top["instance_id"], "busy_fraction": top["busy_fraction"], "steps": steps, "parallel_units": peers}


def _run_order(spec: dict, workflow: dict, sim: dict | None, schedule: dict | None, devices: dict, operator_ids: set[str]) -> dict:
    steps = {s["id"]: s for s in workflow["steps"]}
    waves = _waves(workflow["steps"])
    bn = _bottleneck(sim, workflow, operator_ids)
    hotels = [(d["instance_id"], d["limits"]["storage_slots"]) for d in devices.values() if d["limits"].get("storage_slots")]
    out = {
        "waves": waves,
        "steps": [{"step_id": sid, "name": steps[sid]["name"], "mode": _mode(steps[sid]),
                   "instances": steps[sid].get("candidate_instances", []), "after": steps[sid].get("after", []),
                   "operator_role": steps[sid].get("operator_role"), **_bounds(steps[sid]),
                   "pause_after_s": round(_bounds(steps[sid])["high_s"] * PAUSE_FACTOR, 1)}
                  for wave in waves for sid in wave],
        "bottleneck": bn,
        "dispatch_policy": (
            "Pull-based release paced by the bottleneck (drum-buffer-rope): keep 1-2 units queued in front of "
            f"{bn['instance_id']} ({', '.join(bn['steps'])}) so it never idles, and release a new unit at the first step only "
            "when that buffer drops below 2. Among ready steps, serve the one feeding the bottleneck first, then oldest labware first."
            if bn else "Oldest labware first among ready steps; no simulated bottleneck available."),
        "dispatch_policy_basis": "Heuristic from the twin's utilisation; not an optimised schedule. Confirm in the simulator before relying on it.",
        "wip_limits": [{"instance_id": i, "max_units": n} for i, n in hotels],
    }
    if schedule:
        out["project_order"] = {"recommended": schedule.get("recommended"), "objective": schedule.get("objective"),
                                "gain_vs_naive": schedule.get("gain_vs_naive"), "caveat": schedule.get("caveat")}
    return out


# ---------- safety and escalation ----------

def _safety(spec: dict, layout: dict, devices: dict, rules: dict) -> list[str]:
    out = [
        "Only call tools in the manifest, with step ids and routes from their enums. Never improvise a device action, "
        "parameter or route that is not listed.",
        "Never load a device beyond its capacity or storage slots, and never load labware types it does not accept.",
        "Never start a step before every step in its `after` list has finished for that labware unit.",
        f"Keep walkways of at least {rules.get('min_walkway_width_m', 1.0)} m and egress of at least "
        f"{rules.get('min_egress_width_m', 1.2)} m clear; mobile robots must not park in them.",
    ]
    noncollab = [d["instance_id"] for d in devices.values()
                 if d["limits"].get("transport", {}).get("kind") in ("arm", "rail", "mobile") and d["safety"].get("collaborative") is False]
    if noncollab:
        out.append(f"{_group(noncollab)} {'is' if len(noncollab) == 1 else 'are'} not rated to work beside people: stop them whenever an operator is within "
                   f"{rules.get('human_robot_separation_m', 0.5)} m of their envelope.")
    curtain = [d["instance_id"] for d in devices.values() if d["safety"].get("needs_light_curtain")]
    if curtain:
        out.append(f"{_group(curtain)} need a light curtain: do not run them if the curtain reports a fault.")
    for hazard, zones in (rules.get("zone_requirements") or {}).items():
        hit = [d["instance_id"] for d in devices.values() if hazard in d["safety"]["hazards"]]
        if hit:
            out.append(f"{hazard.replace('_', ' ')}: {_group(hit)} must only run inside a {' or '.join(zones)} zone "
                       "with its extraction or monitoring confirmed on.")
    for hz in (spec.get("constraints") or {}).get("hazards", []):
        if hz == "cryogens":
            out.append("Cryogens: no one handles liquid nitrogen alone; confirm the O2 monitor reads normal before any cryo step.")
        if hz == "high_g_centrifuge":
            out.append("High-g centrifuge: only start a run when the rotor is balanced and the lid interlock reports closed.")
    if (spec.get("constraints") or {}).get("biosafety_level", 1) >= 2:
        out.append(f"BSL{spec['constraints']['biosafety_level']}: biological material stays inside the BSL zone; "
                   "decontaminate labware before it leaves.")
    return out


def _escalations(spec: dict, workflow: dict, sim: dict | None, claims: list[dict], devices: dict, run_order: dict) -> list[str]:
    out = []
    manual = [s for s in run_order["steps"] if s["mode"] in ("manual", "semi_automated")]
    if manual:
        roles = sorted({s["operator_role"] or "operator" for s in manual})
        shifts = {o["role"]: o.get("shift_hours") for o in spec.get("operators", [])}
        shift_txt = "; ".join(f"{r} works {shifts[r]} h shifts" for r in roles if shifts.get(r))
        out.append(f"Manual or semi-automated steps ({', '.join(s['step_id'] for s in manual)}): call `request_human` with the "
                   f"step's operator role before the labware arrives. {shift_txt + '. ' if shift_txt else ''}"
                   "Out of shift, hold the labware in storage rather than skipping the step.")
    ext = [s["step_id"] for s in run_order["steps"] if s["mode"] == "external"]
    if ext:
        out.append(f"External steps ({', '.join(ext)}) leave the lab: a human books, packs and ships them. Never mark them done yourself.")
    out.append(f"A step still running at {PAUSE_FACTOR}x its high bound (`pause_after_s` in the run order) is outside "
               "what the twin expects: check the device status, `pause_line` from that step, and `request_human` (urgency soon).")
    out.append("Any device error, safety interlock, labware mismatch or barcode you cannot read: stop that device, "
               "`request_human` (urgency now). Do not retry a failed physical action more than once.")
    hold = {}
    for d in devices.values():
        if d["limits"].get("hold_time_s"):
            hold.setdefault(d["limits"]["hold_time_s"], []).append(d["instance_id"])
    for h, ids in hold.items():
        out.append(f"{_group(ids)} hold contents for about {_fmt_s(h)} each: track when each was charged, alert a human at 75% "
                   "of that, and ship or unload before it expires.")
    manual_only = {iid for iid in devices
                   if all(s["mode"] == "manual" for s in run_order["steps"] if iid in s["instances"])}
    no_api = [d["instance_id"] for d in devices.values() if d["control"]["status"] in ("none_listed", "unconfirmed", "vendor_software_only", "unknown")
              and d["capabilities_used"] and d["instance_id"] not in manual_only]
    if no_api:
        out.append(f"No confirmed programmable interface for {_group(no_api)}: until a driver is verified, treat their tools as "
                   "'ask a human to do this and confirm', not as direct control.")
    if sim and sim.get("throughput"):
        t = sim["throughput"]
        if t.get("prob_meets_target") is not None and t["prob_meets_target"] < 0.5:
            out.append(f"The twin gives only a {t['prob_meets_target']:.0%} chance of meeting the {t.get('target')} {t['unit']} target. "
                       "Tell the lab manager on day one instead of pushing devices past their limits to catch up.")
    refuted = [c for c in claims if c.get("status") == "refuted"]
    for c in refuted:
        out.append(f"Design claim refuted by the verifier: \"{c['statement']}\" (verified {c.get('metric')} = {c.get('verified_value')}). "
                   "Never report the claimed value as expected performance; use the verified one.")
    return out


# ---------- top level ----------

def build_orchestrator(spec: dict, workflow: dict, layout: dict, catalog: dict[str, dict], sim_result: dict | None = None,
                       claims: list[dict] | None = None, schedule: dict | None = None, source: str = "") -> dict:
    """Return {"skill_md": str, "manifest": dict} for the agent that will run this lab."""
    claims = claims or []
    rules = load_rules()
    placements = {p["instance_id"]: p for p in layout.get("placements", [])}
    zones = layout.get("zones", [])
    transfers = layout.get("transfers", [])
    operator_ids = {o["id"] for o in layout.get("operators", [])}
    devices = {e["instance_id"]: _device(e, catalog.get(e["catalog_id"]), workflow["steps"], placements.get(e["instance_id"]),
                                          zones, transfers) for e in workflow["equipment"]}
    run_order = _run_order(spec, workflow, sim_result, schedule, devices, operator_ids)
    safety = _safety(spec, layout, devices, rules)
    escalate = _escalations(spec, workflow, sim_result, claims, devices, run_order)
    violations = layout.get("violations", [])
    manifest = {
        "lab_id": spec["id"], "lab_name": spec.get("name", spec["id"]), "workflow_id": workflow["id"],
        "layout_id": layout.get("id"), "sim_result_id": (sim_result or {}).get("id"),
        "generated_by": GENERATOR, "source": source, "alignment_note": ALIGNMENT_NOTE,
        "devices": list(devices.values()),
        "operators": [{"id": o["id"], "role": o["role"]} for o in layout.get("operators", [])],
        "transfers": [{k: t.get(k) for k in ("from_instance", "to_instance", "transporter_instance", "distance_m", "est_time_s")}
                      for t in transfers],
        "global_tools": GLOBAL_TOOLS,
        "run_order": run_order,
        "preflight": {"unresolved_layout_violations": violations,
                      "measure_on_first_run": [{"instance_id": d["instance_id"], **m} for d in devices.values() for m in d["measure_on_first_run"]]},
        "safety_rules": safety,
        "escalation_rules": escalate,
        "expected_performance": _expected(sim_result, claims),
    }
    return {"skill_md": render_skill_md(spec, workflow, manifest), "manifest": manifest}


def _expected(sim: dict | None, claims: list[dict]) -> dict | None:
    if not sim:
        return None
    util = sorted(sim.get("utilisation", []), key=lambda u: -u["busy_fraction"])[:5]
    return {"throughput": sim.get("throughput"), "top_utilisation": util,
            "bottlenecks": [b["message"] for b in sim.get("bottlenecks", [])][:6],
            "sensitivity": sim.get("sensitivity", [])[:5],
            "refuted_claims": [{"statement": c["statement"], "metric": c.get("metric", ""), "verified_value": c.get("verified_value"),
                                "note": c.get("verifier_note")} for c in claims if c.get("status") == "refuted"]}


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:56] or "lab"


def render_skill_md(spec: dict, workflow: dict, m: dict) -> str:
    ro = m["run_order"]
    devices = {d["instance_id"]: d for d in m["devices"]}
    by_from = {}
    for t in m["transfers"]:
        by_from.setdefault(t["from_instance"], []).append(t)
    L = []
    L += ["---", f"name: run-{_slug(spec['id'])}",
          f"description: Orchestrate the {spec.get('name', spec['id'])} lab through its instrument APIs. Use when running, "
          "scheduling or troubleshooting this lab's workflow; covers the devices and their limits, run order, safety rules and "
          "when to call a person.", "---", ""]
    L += [f"# Running {spec.get('name', spec['id'])}", ""]
    tgt = spec.get("throughput_target") or {}
    L += [f"You orchestrate this lab. Goal: about {tgt.get('value', '?')} {tgt.get('unit', 'units')} "
          f"({tgt.get('operating_hours_per_day', 24)} h/day), safely. You have the tools in `tools.json`; each device's limits, "
          "zone and confidence are listed there. This file was generated from the lab's digital twin "
          f"(workflow `{workflow['id']}`, layout `{m.get('layout_id')}`, simulation `{m.get('sim_result_id')}`). "
          "Where the twin was unsure, this file says so; trust a measurement over the twin and log it with `record_measurement`.", ""]

    L += ["## Before the first run", ""]
    if m["preflight"]["unresolved_layout_violations"]:
        L += ["The layout check found problems that are not fixed. **Do not start until a person has fixed each one or signed it off** "
              "(`request_human`, urgency soon, listing them):", ""]
        L += [f"- {v['kind']}: {v['message']}" for v in m["preflight"]["unresolved_layout_violations"]] + [""]
    else:
        L += ["The layout check passed with no violations.", ""]
    meas = m["preflight"]["measure_on_first_run"]
    if meas:
        L += ["These values are placeholders in the catalog. Measure each on the first run and log it with `record_measurement`:", ""]
        grouped = {}
        for x in meas:
            grouped.setdefault((x["field"], x["value"], x["low"], x["high"]), []).append(x["instance_id"])
        L += [f"- `{_group(ids)}` {f} = {v} (range {lo}-{hi})" for (f, v, lo, hi), ids in grouped.items()] + [""]

    L += ["## Devices", "", "| Device | Model | Does | Capacity | Control | Data |", "|---|---|---|---|---|---|"]
    rows = {}
    for d in m["devices"]:
        lim = d["limits"]
        cap = lim.get("storage_slots") or lim.get("capacity", 1)
        row = (f"{d.get('model') or d['catalog_id']} | {', '.join(d['capabilities_used']) or 'transport/support'} "
               f"| {cap} ({lim.get('capacity_confidence') or '?'}) | {d['control']['status'].replace('_', ' ')} | {d['data_confidence']} |")
        rows.setdefault(row, []).append(d["instance_id"])
    L += [f"| `{_group(ids)}` | {row}" for row, ids in rows.items()]
    L += [""]

    L += ["## Workflow and handoffs", "", "Steps in run order. Times are the twin's expected value and range per unit of labware.", ""]
    for i, wave in enumerate(ro["waves"], 1):
        for sid in wave:
            s = next(x for x in ro["steps"] if x["step_id"] == sid)
            where = " or ".join(f"`{x}`" for x in s["instances"]) or ("people outside the lab" if s["mode"] == "external" else "compute")
            who = f", operator: {s['operator_role']}" if s.get("operator_role") else ""
            after = f" after {', '.join(s['after'])}" if s["after"] else " (start)"
            L.append(f"{i}. **{s['name']}** (`{sid}`, {s['mode'].replace('_', ' ')}{who}) on {where}{after}. "
                     f"Expect {_fmt_s(s['expected_s'])} ({_fmt_s(s['low_s'])}-{_fmt_s(s['high_s'])}, {s['confidence']}); "
                     f"pause and escalate past {_fmt_s(s['pause_after_s'])}.")
            hand = [t for inst in s["instances"] for t in by_from.get(inst, [])]
            nxt = {x["step_id"] for x in ro["steps"] if sid in x["after"]}
            nxt_inst = {i2 for x in ro["steps"] if x["step_id"] in nxt for i2 in x["instances"]}
            for t in hand:
                if t["to_instance"] in nxt_inst:
                    L.append(f"   - handoff `{t['from_instance']}` to `{t['to_instance']}` by `{t['transporter_instance']}` "
                             f"({t['distance_m']} m, ~{_fmt_s(t['est_time_s'])})")
    L += [""]

    L += ["## Run order and dispatch", ""]
    if ro.get("bottleneck"):
        bn = ro["bottleneck"]
        L += [f"The twin's bottleneck is `{bn['instance_id']}` (busy {bn['busy_fraction']:.0%}; steps {', '.join(bn['steps'])}; "
              f"parallel units {', '.join(bn['parallel_units'])})."]
    L += [ro["dispatch_policy"], f"_{ro['dispatch_policy_basis']}_", ""]
    if ro["wip_limits"]:
        caps = {}
        for w in ro["wip_limits"]:
            caps.setdefault(w["max_units"], []).append(w["instance_id"])
        L += ["Work-in-progress limits (never exceed): " + ", ".join(f"`{_group(ids)}` {n} each" if len(ids) > 1 else f"`{ids[0]}` {n}"
                                                               for n, ids in caps.items()) + ".", ""]
    if ro.get("project_order"):
        po = ro["project_order"]
        L += [f"Several projects share the lab. The scheduler recommends `{po['recommended']}` ({po['objective']}, "
              f"{po['gain_vs_naive']:.0%} better than the order given). {po.get('caveat') or ''}", ""]

    L += ["## Safety rules (hard limits)", ""] + [f"- {r}" for r in m["safety_rules"]] + [""]
    L += ["## When to call a person", ""] + [f"- {r}" for r in m["escalation_rules"]] + [""]

    ex = m.get("expected_performance")
    if ex and ex.get("throughput"):
        t = ex["throughput"]
        L += ["## What the twin expects", "",
              f"Throughput P10/P50/P90: {t.get('p10')} / {t.get('p50')} / {t.get('p90')} {t.get('unit')} "
              f"(target {t.get('target')}, chance of meeting it {t.get('prob_meets_target')}).", ""]
        for c in ex["refuted_claims"]:
            if c.get("metric", "").startswith("throughput"):
                L += [f"**The verifier did not reproduce this.** Its independent recompute gives {c['metric']} = {c['verified_value']}. "
                      "Plan on the verified number until real runs say otherwise.", ""]
        if ex["sensitivity"]:
            L += ["Inputs that move throughput most (measure these first): " +
                  ", ".join(f"{s['parameter']} ({s['effect']:+g})" for s in ex["sensitivity"]) + ".", ""]
        L += ["If real throughput or utilisation drifts outside these bands for a full day, tell the lab manager and log the "
              "measurements so the twin can be re-run. Do not hide a shortfall by skipping QC or overloading devices.", ""]
    return "\n".join(L).rstrip() + "\n"


# ---------- convenience ----------

def from_replay(path: str | Path, schedule: dict | None = None) -> dict:
    """Build from a recorded agent run (frontend/public/replays/<name>.json), which carries its own catalog entries."""
    rec = json.loads(Path(path).read_text())
    o = rec["output"]
    catalog = dict(rec.get("catalog") or {})
    if not catalog:
        from labforge.catalog.store import load_catalog
        catalog = load_catalog()
    return build_orchestrator(o["lab_spec"], o["workflow"], o["layout"], catalog, o.get("sim_result"),
                              o.get("claims"), schedule, source=f"replay:{Path(path).stem}")
