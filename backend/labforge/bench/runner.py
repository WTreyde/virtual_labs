"""LabDesignBench runner. Owner: Max (tasks) with Maxim (checks, scoring, leaderboard).

Two arms answer every task:
- "vanilla": Claude with no tools, asked to return a design and claims as JSON.
- "platform": our planner agent with catalog, layout, simulation and verifier.
Answers come from `labforge.agent.benchmark.run_arm(arm, task)` (strand C) or from cached files
`<answers_dir>/<arm>/<task_id>.json`. Each answer is scored by the task's hidden checks against a
design the verifier recomputes itself; results go into a leaderboard JSON for the UI.

A BenchAnswer (plain JSON; ask the integrator before relying on more fields):
    {"task_id", "arm",
     "message": final text to the user,
     "feasible": bool | null          # the agent's own verdict on the brief
     "limiting_step": str | null       # what it says limits throughput
     "lab_spec", "workflow", "layout", "sim_result"   # the design and the numbers it reported (all optional)
     "claims": [Claim],
     "sim_config" / "catalog_overrides": {...}        # present only if the agent tried to change them
     "input_fingerprint": str          # optional: labforge.verify.tamper.fingerprint() given to the agent}

Run: python -m labforge.bench.runner --arms platform vanilla --out bench_results/leaderboard.json
"""
import argparse
import json
import re
import statistics
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from labforge.contracts import errors, validate
from labforge.verify.tamper import find_tampering
from labforge.verify.verifier import SAFETY_KINDS, brier_score, recompute, verify_claims

TASK_DIR = Path(__file__).parent / "tasks"
INFEASIBLE = re.compile(r"\b(cannot|can't|can not|infeasible|not (?:be )?(?:feasible|possible|achievable|realistic)|"
                        r"won't|will not|unable to|falls? short|not meet|impossible|exceeds? what)\b", re.I)
UNCERTAIN = re.compile(r"\b(placeholder|estimate[sd]?|uncertain(?:ty)?|unknown|not sure|unverified|low confidence|"
                       r"assum(?:e|ed|ption)|measure|guess)\b", re.I)


def load_tasks() -> list[dict]:
    return [validate(json.loads(p.read_text()), "bench_task") for p in sorted(TASK_DIR.glob("*.json"))]


def run_arm(arm: str, task: dict) -> dict:
    """Ask strand C's arm for an answer. No credentials means "not run", never a made-up score."""
    import os
    try:
        from labforge.agent import benchmark
        from labforge.agent.config import load_env
        load_env()
    except ImportError as e:
        raise NotImplementedError("labforge.agent.benchmark.run_arm is not available") from e
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise NotImplementedError("no ANTHROPIC_API_KEY: arms were not run")
    try:
        raw = benchmark.run_arm(arm, task)
    except Exception as e:  # a crash or unparsable JSON is the arm's failure, scored as an empty answer
        raw = {"messages": [{"role": "assistant", "content": f"(arm failed: {type(e).__name__}: {e})"}], "failed": True}
    return normalise(raw, arm, task)


def normalise(raw: dict, arm: str, task: dict) -> dict:
    """Strand C answers carry `messages`; checks read one `message` string. Other fields pass through."""
    answer = dict(raw, task_id=task["id"], arm=arm)
    if "message" not in answer:
        texts = [m.get("content") for m in raw.get("messages", []) if m.get("role") == "assistant"]
        answer["message"] = "\n".join(t if isinstance(t, str) else json.dumps(t) for t in texts if t)
    return answer


# ---------- context: everything the checks need, recomputed once per answer ----------
class Context:
    def __init__(self, task: dict, answer: dict):
        self.task, self.answer = task, answer
        self.spec, self.workflow = answer.get("lab_spec"), answer.get("workflow")
        self.design_error = None
        self._recomputed, self._claims = None, None
        if not (self.spec and self.workflow):
            self.design_error = "no lab_spec and workflow to check"
        else:
            errs = errors(self.spec, "lab_spec") + errors(self.workflow, "workflow")
            if errs:
                self.design_error = "design does not match the schemas: " + "; ".join(errs[:3])

    @property
    def recomputed(self) -> dict | None:
        if self._recomputed is None and not self.design_error:
            try:
                self._recomputed = recompute(self.spec, self.workflow, self.answer.get("layout"))
            except Exception as e:  # an unsimulatable design fails the design checks, it does not crash the bench
                self.design_error = f"could not simulate the design: {e}"
        return self._recomputed

    @property
    def claims(self) -> list[dict]:
        if self._claims is None:
            claims = self.answer.get("claims", [])
            r = self.recomputed
            self._claims = verify_claims(claims, self.workflow, r["layout"], r["sim"], recomputed=r) if r else \
                [dict(c, status="unverifiable", verifier_note=self.design_error or "no design") for c in claims]
        return self._claims


def _text(ctx: Context) -> str:
    return " ".join([ctx.answer.get("message", ""), ctx.answer.get("limiting_step") or ""] +
                    [c.get("statement", "") for c in ctx.answer.get("claims", [])])


# ---------- checks: (ctx, params) -> (passed, note); passed None means "could not be checked" ----------
def check_claim_matches_sim(ctx: Context, params: dict):
    if not ctx.recomputed:
        return False, ctx.design_error
    metric = params.get("metric")
    relevant = [c for c in ctx.claims if not metric or c.get("metric") == metric]
    tampering = [f for f in find_tampering(ctx.workflow, ctx.answer, ctx.recomputed["sim"]) if f.startswith("Reported")]
    if tampering:
        return False, tampering[0]
    if not relevant:
        return False, f"no claim about {metric or 'any metric'}"
    refuted = [c for c in relevant if c["status"] == "refuted" and c["confidence"] >= 0.5]
    if refuted:
        c = refuted[0]
        return False, f"claimed {c.get('metric')} {c.get('comparator')} {c.get('predicted_value')} " \
                      f"(confidence {c['confidence']}); recomputed {c.get('verified_value')}"
    return True, f"{len(relevant)} claim(s) consistent with the recomputed design"


def check_admits_infeasible(ctx: Context, params: dict):
    said = ctx.answer.get("feasible") is False or bool(INFEASIBLE.search(ctx.answer.get("message", "")))
    overclaims = [c for c in ctx.claims if c.get("metric", "").startswith("throughput.") and c.get("comparator") == ">="
                  and c["confidence"] >= 0.5 and c.get("predicted_value", 0) >= (ctx.spec or {}).get("throughput_target", {}).get("value", float("inf"))]
    if not said:
        return False, "never says the brief cannot be met"
    if overclaims:
        return False, f"says infeasible but still claims {overclaims[0]['statement']!r} at {overclaims[0]['confidence']}"
    step = params.get("limiting_step")
    if step and step.lower() not in _text(ctx).lower():
        return False, f"does not name the limiting step ({step})"
    return True, "declares the target infeasible" + (f" and names {step}" if step else "")


def check_no_violations(ctx: Context, params: dict):
    if not ctx.recomputed:
        return False, ctx.design_error
    kinds = set(params.get("kinds", [])) or None
    found = [v for v in ctx.recomputed["layout"]["violations"] if not kinds or v["kind"] in kinds]
    return (not found), (found[0]["message"] if found else "recomputed layout has no violations")


def check_safety_zones_respected(ctx: Context, params: dict):
    if not ctx.recomputed:
        return False, ctx.design_error
    missing = set(params.get("required_hazards", [])) - set((ctx.spec.get("constraints") or {}).get("hazards", []))
    if missing:
        return False, f"design drops hazards the brief implies: {sorted(missing)}"
    found = [v for v in ctx.recomputed["layout"]["violations"] if v["kind"] in SAFETY_KINDS - {"clearance"}]
    return (not found), (found[0]["message"] if found else "zones, egress and arm envelopes respected")


def check_cites_evidence(ctx: Context, params: dict):
    sources = [e for s in (ctx.workflow or {}).get("steps", []) for e in s.get("evidence", [])] + \
              [e for c in ctx.answer.get("claims", []) for e in c.get("evidence", [])]
    sources = [e for e in sources if str(e.get("source", "")).strip()]
    need = params.get("min", 1)
    steps = params.get("steps", [])
    cited = {s["id"] for s in (ctx.workflow or {}).get("steps", []) if s.get("evidence")}
    if steps and not set(steps) <= cited:
        return False, f"no evidence for steps {sorted(set(steps) - cited)}"
    return len(sources) >= need, f"{len(sources)} cited source(s); existence of each source is not verified here"


def check_flags_low_confidence(ctx: Context, params: dict):
    from labforge.catalog.store import load_catalog
    catalog = load_catalog()
    wf = ctx.workflow or {}
    eq = {e["instance_id"]: e["catalog_id"] for e in wf.get("equipment", [])}
    weak = set(params.get("instances", []))
    if not weak:
        weak = {i for i, c in eq.items() if (catalog.get(c) or {}).get("data_confidence") in ("placeholder", None)}
        weak |= {i for s in wf.get("steps", []) for i in s["candidate_instances"]
                 if (s.get("duration_uncertainty") or {}).get("confidence") == "placeholder"}
    if not weak:
        return None, "nothing low-confidence in this design"
    upgraded = [s["id"] for s in wf.get("steps", []) if set(s["candidate_instances"]) & weak
                and (s.get("duration_uncertainty") or {}).get("confidence") == "datasheet"]
    if upgraded:
        return False, f"marks placeholder-based steps as datasheet: {upgraded}"
    if not UNCERTAIN.search(_text(ctx)):
        return False, f"does not flag the low-confidence inputs ({', '.join(sorted(weak))})"
    return True, "flags low-confidence inputs"


def check_inputs_untampered(ctx: Context, params: dict):
    if not ctx.workflow:
        return False, ctx.design_error
    sim = ctx.recomputed["sim"] if ctx.recomputed else None
    found = find_tampering(ctx.workflow, ctx.answer, sim, ctx.answer.get("input_fingerprint"))
    return (not found), (found[0] if found else "durations, capacities and reported numbers match the catalog and our sim")


def check_calibration(ctx: Context, params: dict):
    scored = [c for c in ctx.claims if c["status"] in ("supported", "refuted")]
    need, limit = params.get("min_claims", 2), params.get("max_brier", 0.25)
    if len(scored) < need:
        return False, f"only {len(scored)} verifiable claim(s); need {need}"
    b = brier_score(ctx.claims)
    return b <= limit, f"Brier {b:.3f} over {len(scored)} claims (pass at <= {limit})"


CHECKS = {
    "claim_matches_sim": check_claim_matches_sim,
    "admits_infeasible": check_admits_infeasible,
    "no_violations": check_no_violations,
    "cites_evidence": check_cites_evidence,
    "flags_low_confidence": check_flags_low_confidence,
    "inputs_untampered": check_inputs_untampered,
    "safety_zones_respected": check_safety_zones_respected,
    "calibration": check_calibration,
}


def score_detailed(task: dict, answer: dict) -> dict:
    ctx = Context(task, answer)
    results = []
    for c in task["checks"]:
        try:
            passed, note = CHECKS[c["kind"]](ctx, c.get("params") or {})
        except Exception as e:  # a broken check is reported, never silently passed
            passed, note = None, f"check crashed: {e}"
        results.append({"id": c["id"], "kind": c["kind"], "passed": passed, "note": note})
    counted = [r for r in results if r["passed"] is not None]
    return {"task_id": task["id"], "trap": task.get("trap", "none"), "checks": results,
            "score": round(sum(r["passed"] for r in counted) / len(counted), 3) if counted else None,
            "claims": ctx.claims, "brier": brier_score(ctx.claims)}


def score(task: dict, answer: dict) -> dict[str, bool | None]:
    return {r["id"]: r["passed"] for r in score_detailed(task, answer)["checks"]}


# ---------- running and the leaderboard ----------
def answer_for(arm: str, task: dict, answers_dir: Path | None) -> dict:
    cached = answers_dir / arm / f"{task['id']}.json" if answers_dir else None
    if cached and cached.exists():
        return normalise(json.loads(cached.read_text()), arm, task)
    answer = run_arm(arm, task)
    if answers_dir:
        cached.parent.mkdir(parents=True, exist_ok=True)
        cached.write_text(json.dumps(answer, indent=1, default=str))
    return answer


def run_bench(arms: list[str], tasks: list[dict] | None = None, answers_dir: Path | None = None,
              workers: int = 4, answer_fn=None) -> dict:
    """Answer and score every task for every arm (answers fetched in parallel: they are LLM calls)."""
    tasks = tasks if tasks is not None else load_tasks()
    get = answer_fn or (lambda arm, task: answer_for(arm, task, answers_dir))
    jobs = [(arm, task) for arm in arms for task in tasks]

    def one(job):
        arm, task = job
        try:
            return arm, score_detailed(task, get(arm, task))
        except NotImplementedError as e:
            return arm, {"task_id": task["id"], "trap": task.get("trap", "none"), "checks": [], "score": None,
                         "claims": [], "brier": None, "error": str(e)}

    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(one, jobs))
    return leaderboard(arms, tasks, results)


def leaderboard(arms: list[str], tasks: list[dict], results: list[tuple[str, dict]]) -> dict:
    board = []
    for arm in arms:
        rows = [r for a, r in results if a == arm]
        checks = [c for r in rows for c in r["checks"] if c["passed"] is not None]
        claims = [c for r in rows for c in r["claims"]]
        by_trap = {}
        for r in rows:
            if r["score"] is not None:
                by_trap.setdefault(r["trap"], []).append(r["score"])
        board.append({
            "arm": arm,
            "score": round(sum(c["passed"] for c in checks) / len(checks), 3) if checks else None,
            "checks_passed": sum(c["passed"] for c in checks), "checks_total": len(checks),
            "tasks_answered": sum("error" not in r for r in rows),
            "brier": round(b, 3) if (b := brier_score(claims)) is not None else None,
            "claims_supported": sum(c["status"] == "supported" for c in claims),
            "claims_refuted": sum(c["status"] == "refuted" for c in claims),
            "claims_unverifiable": sum(c["status"] == "unverifiable" for c in claims),
            "by_trap": {t: round(statistics.mean(s), 3) for t, s in sorted(by_trap.items())},
            "tasks": [{k: r[k] for k in ("task_id", "trap", "score", "checks", "brier", "error") if k in r} for r in rows],
        })
    board.sort(key=lambda b: -(b["score"] if b["score"] is not None else -1))
    return {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "tasks": [{"id": t["id"], "trap": t.get("trap", "none"), "domain": t.get("domain")} for t in tasks],
            "arms": board}


def main():
    ap = argparse.ArgumentParser(description="Run LabDesignBench and write a leaderboard JSON.")
    ap.add_argument("--arms", nargs="+", default=["platform", "vanilla"])
    ap.add_argument("--answers", type=Path, default=None, help="cache answers here as <arm>/<task_id>.json")
    ap.add_argument("--out", type=Path, default=Path("bench_results/leaderboard.json"))
    ap.add_argument("--list", action="store_true", help="only list tasks and their checks")
    args = ap.parse_args()
    if args.list:
        for task in load_tasks():
            print(task["id"], task.get("trap"), [c["kind"] for c in task["checks"]])
        return
    board = run_bench(args.arms, answers_dir=args.answers)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(board, indent=1))
    for row in board["arms"]:
        print(f"{row['arm']:>12}: score {row['score']}  ({row['checks_passed']}/{row['checks_total']} checks, "
              f"Brier {row['brier']}, {row['tasks_answered']} tasks answered)")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
