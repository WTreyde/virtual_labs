"""Strand D: check the agent's claims against independent evidence. Owner: Maxim.

A claim's `metric` names a value the verifier computes itself, e.g. "throughput.p50",
"bom.total_usd", "layout.violations" or "bottleneck.lcms_1". The verifier never trusts numbers the
agent reports: given the lab spec, it re-derives the layout's transfers and violations from the
placements and re-runs the Monte Carlo itself. Without a spec it can only check against the
supplied sim result, and says so in each claim's `verifier_note`.

Comparators: >=, <=, == (1% tolerance), exists (value is non-zero), none (value is zero).
"""
import operator
import statistics

from labforge.catalog.store import load_catalog
from labforge.contracts import validate
from labforge.layout.placer import generate_layout, rederive
from labforge.sim.simulate import simulate
from labforge.verify.tamper import restore_protected

OPS = {">=": operator.ge, "<=": operator.le, "==": lambda a, b: abs(a - b) <= max(1e-6, 0.01 * abs(b)),
       "exists": lambda a, _: bool(a), "none": lambda a, _: not a}
SAFETY_KINDS = {"safety", "zone_mismatch", "egress_blocked", "keep_out", "clearance"}
VERIFY_REPLICATES = 20


def recompute(spec: dict, workflow: dict, layout: dict | None = None, replicates: int = VERIFY_REPLICATES,
              seed: int = 12345) -> dict:
    """Our own layout and sim for this design, with protected catalog durations restored.

    A different seed from the agent's runs on purpose; `restored` lists durations we put back."""
    honest, restored = restore_protected(workflow)
    lay = rederive(spec, honest, layout) if layout and layout.get("placements") else generate_layout(spec, honest)
    sim = simulate(spec, honest, lay, replicates=replicates, seed=seed, sensitivity=False)
    return {"layout": lay, "sim": sim, "restored": restored}


def observed_metrics(workflow: dict, layout: dict, sim: dict) -> dict[str, float]:
    catalog = load_catalog()
    t = sim["throughput"]
    out = {
        "throughput.value": t["value"],
        "throughput.p50": t.get("p50", t["value"]),
        "throughput.p10": t.get("p10", t["value"]),
        "throughput.p90": t.get("p90", t["value"]),
        "throughput.prob_meets_target": t.get("prob_meets_target", float(t.get("meets_target", False))),
        "throughput.meets_target": float(t.get("meets_target", False)),
        "cycle_time_s": sim.get("cycle_time_s", 0.0),
        "bom.total_usd": sum((catalog.get(e["catalog_id"]) or {}).get("price_usd_estimate", 0) for e in workflow["equipment"]),
        "bom.items": len(workflow["equipment"]),
        "layout.violations": len(layout.get("violations", [])),
        "layout.safety_violations": sum(v["kind"] in SAFETY_KINDS for v in layout.get("violations", [])),
        "layout.total_weighted_distance_m": (layout.get("score") or {}).get("total_weighted_distance_m", 0.0),
    }
    for v in layout.get("violations", []):
        out[f"layout.{v['kind']}"] = out.get(f"layout.{v['kind']}", 0) + 1
    for u in sim.get("utilisation", []):
        out[f"utilisation.{u['instance_id']}"] = u["busy_fraction"]
        out[f"bottleneck.{u['instance_id']}"] = 0.0
    for b in sim.get("bottlenecks", []):
        if b["severity"] in ("high", "medium") and b["kind"] in ("instrument_capacity", "operator_capacity", "transporter_capacity"):
            for i in b.get("instances", []):
                out[f"bottleneck.{i}"] = 1.0
    return out


def verify_claims(claims: list[dict], workflow: dict, layout: dict | None, sim: dict | None,
                  spec: dict | None = None, recomputed: dict | None = None) -> list[dict]:
    """Return the claims with status, verified_value and a note. Pass `spec` so nothing is taken on trust."""
    if recomputed is None and spec is not None:
        recomputed = recompute(spec, workflow, layout)
    if recomputed:
        layout, sim, source = recomputed["layout"], recomputed["sim"], "recomputed by the verifier"
        if recomputed.get("restored"):
            source += " with catalog durations restored for " + ", ".join(r.split(":")[0] for r in recomputed["restored"])
    else:
        source = "checked against the supplied sim result (not recomputed: no lab spec given)"
    seen = observed_metrics(workflow, layout or {"violations": []}, sim) if sim else {}
    out = []
    for c in claims:
        c = dict(c)
        metric, op = c.get("metric"), c.get("comparator")
        needs_value = op in (">=", "<=", "==")
        if metric not in seen and metric and metric.startswith(("layout.", "bottleneck.")) and op in ("exists", "none"):
            seen[metric] = 0.0  # a violation kind or bottleneck that did not occur counts as zero
        if metric not in seen or op not in OPS or (needs_value and "predicted_value" not in c):
            c["status"] = "unverifiable"
            c["verifier_note"] = f"No independent check for metric '{metric}' with '{op}'." if metric else \
                "No machine-checkable metric given."
        else:
            c["verified_value"] = round(float(seen[metric]), 4)
            c["status"] = "supported" if OPS[op](seen[metric], c.get("predicted_value", 0)) else "refuted"
            c["verifier_note"] = f"{metric} = {c['verified_value']:g}, {source}."
        out.append(validate(c, "claim"))
    return out


def brier_score(claims: list[dict]) -> float | None:
    """Mean squared error between stated confidence and outcome; lower is better calibrated."""
    scored = [(c["confidence"], c["status"] == "supported") for c in claims if c["status"] in ("supported", "refuted")]
    return sum((p - y) ** 2 for p, y in scored) / len(scored) if scored else None


def calibration(claims: list[dict], bins: int = 5) -> dict:
    """Brier score plus a reliability table (stated confidence vs how often claims held), across sessions."""
    scored = [(c["confidence"], c["status"] == "supported") for c in claims if c["status"] in ("supported", "refuted")]
    table = []
    for k in range(bins):
        lo, hi = k / bins, (k + 1) / bins
        group = [(p, y) for p, y in scored if lo <= p < hi or (k == bins - 1 and p == 1.0)]
        if group:
            table.append({"confidence_low": lo, "confidence_high": hi, "n": len(group),
                          "mean_confidence": round(statistics.mean(p for p, _ in group), 3),
                          "fraction_supported": round(sum(y for _, y in group) / len(group), 3)})
    return {"brier": brier_score(claims), "n_scored": len(scored),
            "n_unverifiable": sum(c["status"] == "unverifiable" for c in claims), "reliability": table}
