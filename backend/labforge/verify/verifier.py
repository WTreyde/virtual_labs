"""Strand D: check the agent's claims against independent evidence. Owner: Maxim.

A claim's `metric` names a value the verifier can compute itself, e.g. "throughput.p50",
"bom.total_usd" or "layout.violations". The verifier never trusts numbers the agent reports.
TODO(Maxim): tamper detection (hash simulator inputs), more metrics, Brier score across sessions.
"""
import operator

from labforge.catalog.store import get as get_item

OPS = {">=": operator.ge, "<=": operator.le, "==": lambda a, b: abs(a - b) < 1e-6}


def observed_metrics(workflow: dict, layout: dict, sim: dict) -> dict[str, float]:
    t = sim["throughput"]
    return {
        "throughput.p50": t.get("p50", t["value"]),
        "throughput.p10": t.get("p10", t["value"]),
        "throughput.prob_meets_target": t.get("prob_meets_target", float(t.get("meets_target", False))),
        "bom.total_usd": sum(get_item(e["catalog_id"]).get("price_usd_estimate", 0) for e in workflow["equipment"]),
        "layout.violations": len(layout.get("violations", [])),
    }


def verify_claims(claims: list[dict], workflow: dict, layout: dict, sim: dict) -> list[dict]:
    seen = observed_metrics(workflow, layout, sim)
    out = []
    for c in claims:
        c = dict(c)
        metric, op = c.get("metric"), c.get("comparator")
        if metric not in seen or op not in OPS or "predicted_value" not in c:
            c["status"], c["verifier_note"] = "unverifiable", "No independent check for this metric yet."
        else:
            c["verified_value"] = seen[metric]
            c["status"] = "supported" if OPS[op](seen[metric], c["predicted_value"]) else "refuted"
        out.append(c)
    return out


def brier_score(claims: list[dict]) -> float | None:
    """Mean squared error between stated confidence and outcome; lower is better calibrated."""
    scored = [(c["confidence"], c["status"] == "supported") for c in claims if c["status"] in ("supported", "refuted")]
    return sum((p - y) ** 2 for p, y in scored) / len(scored) if scored else None
