"""Validation runner: design each published lab from its brief and compare with its real cost. Owner: Max.

Run: python -m labforge.validation.runner   (writes validation_report.json)

A case with a hand-written `workflow` is costed directly (tests catalog + cost model).
A case with only a `brief` goes through the planner agent (tests the whole platform; needs ANTHROPIC_API_KEY).
Unverified cases are reported but kept out of the headline numbers.
"""
import json
from pathlib import Path

from labforge.contracts import validate
from labforge.validation.cost import CONFIDENCE_TOLERANCE, MODELLED_CATEGORIES, compare, predicted_cost

CASE_DIR = Path(__file__).parent / "cases"


def load_cases() -> list[dict]:
    return [validate(json.loads(p.read_text()), "validation_case") for p in sorted(CASE_DIR.glob("*.json"))]


def design_from_brief(case: dict) -> dict | None:
    """Delegate to Strand C; reported costs are withheld from the model."""
    from labforge.agent.validation_cases import design_from_brief as plan
    return plan(case)


def run_case(case: dict) -> dict:
    workflow = case.get("workflow") or design_from_brief(case)
    cost = case["reported"]["cost"]
    row = {"id": case["id"], "name": case["name"], "verified": case["verified"], "includes": cost["includes"],
           "unmodelled_categories": sorted(set(cost["includes"]) - MODELLED_CATEGORIES)}
    if workflow is None:
        return {**row, "status": "no_design_yet"}
    predicted = predicted_cost(workflow, cost["includes"], build=case.get("build", "turnkey"),
                               year=cost.get("year"), basis=case.get("price_basis"))
    out = {**row, "status": "compared", **compare(cost["value_usd"], predicted)}
    out["within_25pct"] = predicted["p50"] / CONFIDENCE_TOLERANCE <= cost["value_usd"] <= predicted["p50"] * CONFIDENCE_TOLERANCE
    # Used equipment cannot be matched: the catalog only prices new purchases.
    out["like_for_like"] = case.get("condition", "new") == "new"
    return out


def calibration(rows: list[dict]) -> dict:
    """How well the confidence numbers match reality on verified, like-for-like comparisons: the mean stated chance
    of landing within x/÷ 1.25 versus how often that happened, and the Brier score of those stated chances
    (lower is better; compare with always stating the observed hit rate)."""
    used = [r for r in rows if r.get("status") == "compared" and r["verified"] and r.get("like_for_like")]
    if not used:
        return {"n": 0}
    p = [r["predicted"]["confidence"]["within_25pct"] for r in used]
    hit = [1.0 if r["within_25pct"] else 0.0 for r in used]
    rate = sum(hit) / len(hit)
    return {"n": len(used), "stated_within_25pct": round(sum(p) / len(p), 2), "observed_within_25pct": round(rate, 2),
            "brier": round(sum((a - b) ** 2 for a, b in zip(p, hit)) / len(p), 3),
            "brier_constant_baseline": round(sum((rate - b) ** 2 for b in hit) / len(hit), 3),
            "in_p10_p90": sum(r["within_p10_p90"] for r in used),
            "excluded_not_like_for_like": [r["id"] for r in rows if r.get("status") == "compared" and not r.get("like_for_like")]}


def main() -> list[dict]:
    rows = [run_case(c) for c in load_cases()]
    Path("validation_report.json").write_text(json.dumps(rows, indent=2))
    for r in rows:
        print(r["id"], r["status"], r.get("within_p10_p90"), r.get("log10_error"))
    print("calibration:", calibration(rows))
    return rows


if __name__ == "__main__":
    main()
