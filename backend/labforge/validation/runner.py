"""Validation runner: design each published lab from its brief and compare with its real cost. Owner: Max.

Run: python -m labforge.validation.runner   (writes validation_report.json)

A case with a hand-written `workflow` is costed directly (tests catalog + cost model).
A case with only a `brief` goes through the planner agent (tests the whole platform; needs ANTHROPIC_API_KEY).
Unverified cases are reported but kept out of the headline numbers.
"""
import json
from pathlib import Path

from labforge.contracts import validate
from labforge.validation.cost import compare, predicted_cost

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
    row = {"id": case["id"], "name": case["name"], "verified": case["verified"], "includes": cost["includes"]}
    if workflow is None:
        return {**row, "status": "no_design_yet"}
    return {**row, "status": "compared", **compare(cost["value_usd"], predicted_cost(workflow, cost["includes"]))}


def main() -> list[dict]:
    rows = [run_case(c) for c in load_cases()]
    Path("validation_report.json").write_text(json.dumps(rows, indent=2))
    for r in rows:
        print(r["id"], r["status"], r.get("within_p10_p90"), r.get("log10_error"))
    return rows


if __name__ == "__main__":
    main()
