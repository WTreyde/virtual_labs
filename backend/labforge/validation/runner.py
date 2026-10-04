"""Validation runner: design each published lab from its brief and compare with its real cost. Owner: Max.

Run: python -m labforge.validation.runner                    (costs every case; writes validation_report.json)
     python -m labforge.validation.runner --design-missing   (first runs the agent ONCE per case with no design)

A case with a hand-written `workflow` is costed directly (tests catalog + cost model). A case with only a `brief`
is costed from its stored agent design in designs/<case_id>.json, the same file GET /validation reads, so the CLI
and the tab agree. Costing never calls the agent; only --design-missing does, once per case, never retrying, and it
records a {"status": "no_design", "reason": ...} file when no design comes out. Needs ANTHROPIC_API_KEY.
Unverified cases are reported but kept out of the headline numbers.
"""
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from labforge.contracts import validate
from labforge.validation.cost import CONFIDENCE_TOLERANCE, MODELLED_CATEGORIES, compare, predicted_cost

CASE_DIR = Path(__file__).parent / "cases"
DESIGN_DIR = Path(__file__).parent / "designs"


def load_cases() -> list[dict]:
    return [validate(json.loads(p.read_text()), "validation_case") for p in sorted(CASE_DIR.glob("*.json"))]


def design_from_brief(case: dict) -> dict | None:
    """Delegate to Strand C; reported costs are withheld from the model."""
    from labforge.agent.validation_cases import design_from_brief as plan
    return plan(case)


def stored_design(case_id: str) -> dict:
    """designs/<case_id>.json: {"workflow", "provenance"} or {"status": "no_design", "reason"}; {} if never generated."""
    path = DESIGN_DIR / f"{case_id}.json"
    return json.loads(path.read_text()) if path.is_file() else {}


def generate_missing(cases: list[dict], workers: int = 9) -> list[str]:
    """Run the agent once for every case with neither a workflow nor a stored design file. Never retries."""
    from labforge.agent.planner import MODEL
    todo = [c for c in cases if not c.get("workflow") and not (DESIGN_DIR / f"{c['id']}.json").exists()]
    DESIGN_DIR.mkdir(exist_ok=True)
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()

    def one(case: dict) -> str:
        provenance = {"model": MODEL, "date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                      "commit": commit, "cost_withheld": True}
        try:
            workflow = design_from_brief(case)
            out = {"workflow": workflow, "provenance": provenance} if workflow else \
                {"status": "no_design", "reason": "the agent did not complete a valid design in one run "
                                                  "(incomplete turn or missing lab_spec/workflow)", "provenance": provenance}
        except Exception as e:  # recorded, not retried
            out = {"status": "no_design", "reason": f"{type(e).__name__}: {e}"[:300], "provenance": provenance}
        (DESIGN_DIR / f"{case['id']}.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
        return f"{case['id']}: {'design' if out.get('workflow') else 'no_design'}"

    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(one, todo))


def run_case(case: dict) -> dict:
    stored = {} if case.get("workflow") else stored_design(case["id"])
    workflow = case.get("workflow") or stored.get("workflow")
    cost = case["reported"]["cost"]
    row = {"id": case["id"], "name": case["name"], "verified": case["verified"], "includes": cost["includes"],
           "unmodelled_categories": sorted(set(cost["includes"]) - MODELLED_CATEGORIES)}
    if workflow is None:
        return {**row, "status": "no_design_yet", "reason": stored.get("reason") or "no stored design yet"}
    if stored.get("provenance"):
        row["design_provenance"] = stored["provenance"]
    predicted = predicted_cost(workflow, cost["includes"], build=case.get("build", "turnkey"),
                               year=cost.get("year"), basis=case.get("price_basis"),
                               figure_type=case.get("figure_type"))
    if predicted.get("not_costable"):
        return {**row, "status": "not_costable", "predicted": predicted, "reason": predicted["not_costable"]}
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
    cases = load_cases()
    if "--design-missing" in sys.argv[1:]:
        for line in generate_missing(cases):
            print(line)
    rows = [run_case(c) for c in cases]
    Path("validation_report.json").write_text(json.dumps(rows, indent=2))
    for r in rows:
        print(r["id"], r["status"], r.get("within_p10_p90"), r.get("log10_error"))
    print("calibration:", calibration(rows))
    return rows


if __name__ == "__main__":
    main()
