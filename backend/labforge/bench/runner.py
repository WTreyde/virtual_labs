"""LabDesignBench runner. Owner: Max (tasks) with Maxim (checks).

Two arms answer every task:
- "vanilla": Claude with no tools, asked to return a design and claims as JSON.
- "platform": our planner agent with catalog, layout, simulation and verifier.
Each answer is scored by the task's hidden checks; the output feeds the UI leaderboard.

Run: python -m labforge.bench.runner
TODO: implement each check kind in CHECKS, the vanilla arm, and parallel runs on Modal.
"""
import json
from pathlib import Path

from labforge.contracts import validate

TASK_DIR = Path(__file__).parent / "tasks"
CHECKS = {}  # kind -> fn(task, answer) -> bool. TODO(Maxim)


def load_tasks() -> list[dict]:
    return [validate(json.loads(p.read_text()), "bench_task") for p in sorted(TASK_DIR.glob("*.json"))]


def run_arm(arm: str, task: dict) -> dict:
    raise NotImplementedError(f"TODO: run the {arm} arm on {task['id']}")


def score(task: dict, answer: dict) -> dict[str, bool | None]:
    return {c["id"]: (CHECKS[c["kind"]](task, answer) if c["kind"] in CHECKS else None) for c in task["checks"]}


if __name__ == "__main__":
    for task in load_tasks():
        print(task["id"], task["trap"], [c["kind"] for c in task["checks"]])
