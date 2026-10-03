"""Vendor optimisation: how would this lab's throughput change if one instrument were better? Owner: Maxim.

For one equipment instance, sweep a spec through the Monte Carlo simulator with the same random
seeds at every point (common random numbers, so differences are the spec change and not noise):
- cycle_time: the instrument's step durations x 0.5 ... 1.2
- capacity: 1, 2, 3 identical units' worth of slots (absolute slots)
- transfer_time: transfers into and out of it x 0.5 ... 2 (faster plate handling, better placement)
- uptime: availability A; effective process time is duration / A (a standard approximation that
  ignores how failures cluster, so it understates the pain of long outages)
All points of all sweeps run as one batch (local processes or Modal via `backend`).
Elasticity is a log-log least-squares slope over the points near baseline, not a single noisy difference.
"""
import copy
import math

from labforge.catalog.store import load_catalog
from labforge.contracts import validate
from labforge.sim.simulate import simulate_many

CYCLE_FACTORS = (0.5, 0.7, 0.85, 1.0, 1.2)
TRANSFER_FACTORS = (0.5, 0.75, 1.0, 1.5, 2.0)
UPTIMES = (0.8, 0.9, 0.95, 1.0)
UNITS = (1, 2, 3)
NEAR_BASELINE = (0.7, 1.2)  # factor range used for the elasticity fit
NOISE_FLOOR = 0.05  # |elasticity| below this is reported as 0: indistinguishable from "not the limit"


def _scaled(workflow: dict, instance_id: str, factor: float) -> dict:
    wf = copy.deepcopy(workflow)
    for step in wf["steps"]:
        if instance_id in step["candidate_instances"]:
            step["duration_s"] *= factor
            u = step.get("duration_uncertainty")
            if u:
                for k in ("value", "low", "high"):
                    if k in u:
                        u[k] *= factor
    return wf


def _faster_transfers(layout: dict, instance_id: str, factor: float) -> dict:
    lay = copy.deepcopy(layout)
    for t in lay.get("transfers", []):
        if instance_id in (t["from_instance"], t["to_instance"], t["transporter_instance"]) and "est_time_s" in t:
            t["est_time_s"] *= factor
    return lay


def _point(value: float, sim: dict) -> dict:
    t = sim["throughput"]
    return {"value": value, "throughput_p50": t["p50"], "throughput_p10": t["p10"], "throughput_p90": t["p90"]}


def elasticity(points: list[dict], lower_is_better: bool = True) -> float:
    """% throughput change per % improvement, from a log-log fit over points near baseline."""
    xs, ys = [], []
    for p in points:
        if NEAR_BASELINE[0] <= p["value"] <= NEAR_BASELINE[1] and p["throughput_p50"] > 0:
            xs.append(math.log(p["value"]))
            ys.append(math.log(p["throughput_p50"]))
    if len(xs) < 2:
        return 0.0
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx if sxx else 0.0
    e = -slope if lower_is_better else slope
    return 0.0 if abs(e) < NOISE_FLOOR else round(e, 2)


def _busiest_other(sim: dict, instance_id: str) -> str | None:
    others = [u for u in sim["utilisation"] if u["instance_id"] != instance_id]
    return max(others, key=lambda u: u["busy_fraction"])["instance_id"] if others else None


def _base_slots(workflow: dict, instance_id: str, catalog_id: str) -> int:
    stated = ((load_catalog().get(catalog_id) or {}).get("process") or {}).get("capacity")
    batches = [s.get("batch_size", 1) for s in workflow["steps"] if instance_id in s["candidate_instances"]]
    return int(stated or max(batches + [1]))


def optimise_instrument(spec: dict, workflow: dict, layout: dict, instance_id: str,
                        hours: float = 48, replicates: int = 8, seed: int = 0, backend: str | None = None) -> dict:
    catalog_id = next(e["catalog_id"] for e in workflow["equipment"] if e["instance_id"] == instance_id)
    slots = _base_slots(workflow, instance_id, catalog_id)
    uses_steps = any(instance_id in s["candidate_instances"] for s in workflow["steps"])

    variants, keys = [], []

    def add(key, wf=workflow, lay=layout, caps=None):
        keys.append(key)
        variants.append({"workflow": wf, "layout": lay, "capacity_overrides": caps})

    add(("base", 1.0))
    for f in CYCLE_FACTORS:
        if f != 1.0 and uses_steps:
            add(("cycle_time", f), wf=_scaled(workflow, instance_id, f))
    for n in UNITS[1:]:
        add(("capacity", slots * n), caps={instance_id: slots * n})
    for f in TRANSFER_FACTORS:
        if f != 1.0:
            add(("transfer_time", f), lay=_faster_transfers(layout, instance_id, f))
    for u in UPTIMES:
        if u != 1.0 and uses_steps:
            add(("uptime", u), wf=_scaled(workflow, instance_id, 1 / u))
    sims = dict(zip(keys, simulate_many(spec, variants, hours=hours, replicates=replicates, seed=seed, backend=backend)))
    base = sims[("base", 1.0)]
    base_tp = base["throughput"]["p50"]
    base_util = next((u["busy_fraction"] for u in base["utilisation"] if u["instance_id"] == instance_id), None)

    def sweep(param, values, base_value):
        return [_point(v, base if v == base_value else sims[(param, v)]) for v in values if v == base_value or (param, v) in sims]

    cycle = sweep("cycle_time", CYCLE_FACTORS, 1.0)
    capacity = sweep("capacity", [slots * n for n in UNITS], slots)
    transfer = sweep("transfer_time", TRANSFER_FACTORS, 1.0)
    uptime = sweep("uptime", UPTIMES, 1.0)
    e_cycle = elasticity(cycle)
    sweeps = [{"parameter": "cycle_time", "points": cycle, "elasticity": e_cycle},
              {"parameter": "capacity", "points": capacity},
              {"parameter": "transfer_time", "points": transfer, "elasticity": elasticity(transfer)},
              {"parameter": "uptime", "points": uptime}]

    fastest = sims.get(("cycle_time", min(CYCLE_FACTORS)), base)
    gain = fastest["throughput"]["p50"] / base_tp - 1 if base_tp else 0.0
    nxt = _busiest_other(fastest, instance_id)
    if not uses_steps:  # a transporter: what matters is how fast it moves labware
        e_move = sweeps[2]["elasticity"]
        note = (f"Faster plate moves by {instance_id} would lift throughput (elasticity {e_move})." if e_move >= 0.1 else
                f"{instance_id}'s transfer speed is not what limits this lab (elasticity {e_move}).")
    elif e_cycle < 0.1:
        note = f"Making {instance_id} faster barely helps here (elasticity {e_cycle}); it is not the limiting instrument in this lab."
    else:
        util = {u["instance_id"]: u["busy_fraction"] for u in fastest["utilisation"]}
        still_limit = util.get(instance_id, 0) >= util.get(nxt, 0)
        after = f"{instance_id} is still the bottleneck, so further gains are possible" if still_limit \
            else f"after that {nxt} becomes the limit"
        note = f"Halving {instance_id}'s cycle time raises throughput {gain:.0%}; {after}."
        if still_limit:
            nxt = None
    worst_uptime = uptime[0] if uptime and uptime[0]["value"] < 1.0 else None
    if worst_uptime and base_tp:
        note += f" At {worst_uptime['value']:.0%} uptime throughput would be {worst_uptime['throughput_p50'] / base_tp - 1:+.0%}."

    result = {
        "instance_id": instance_id, "catalog_id": catalog_id, "layout_id": layout["id"],
        "baseline": {"throughput_p50": base_tp, "unit": base["throughput"]["unit"], "utilisation": base_util},
        "sweeps": sweeps,
        "headroom_note": note,
    }
    if nxt:
        result["next_bottleneck"] = nxt
    return validate(result, "instrument_optimisation")
