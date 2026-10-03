"""Bake offline fallbacks for the demo so case pages and #/schedule work without the backend. Strand A (Roshan).

Run from the repo root with the backend installed (re-run after replays or the demo queue change):
    python frontend/scripts/cache_offline.py [--force]
Writes:
  frontend/public/replays/<name>.whatif.json  what-if sweeps for each case's capacity-bottleneck instances, only
      when missing or stale (the cache's design hash differs, or without a hash, the cache was last committed
      before its recording). Others' committed caches are left alone unless --force.
  frontend/src/fixtures/demo_schedule.json    POST /prioritise on backend/labforge/catalog/data/demo_prioritise_queue.json,
      only when missing or the queue changed
Each file records its source; the UI labels these results "cached".
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from labforge.contracts import validate
from labforge.sim.portfolio import prioritise
from labforge.sim.whatif import optimise_instrument

ROOT = Path(__file__).resolve().parents[2]
rev = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT).decode().strip()
FORCE = "--force" in sys.argv[1:]


def committed_at(path: Path) -> int:
    """Unix time of the last commit touching path (0 if uncommitted)."""
    out = subprocess.check_output(["git", "log", "-1", "--format=%ct", "--", str(path)], cwd=ROOT).decode().strip()
    return int(out or 0)


for path in sorted((ROOT / "frontend/public/replays").glob("*.json")):
    run = json.loads(path.read_text())
    if not isinstance(run, dict) or "output" not in run:
        continue  # <name>.summary.json, <name>.whatif.json and anything else that isn't a recording
    out = run["output"]
    if not out.get("layout"):
        continue
    design_sha = hashlib.sha256(json.dumps([out["lab_spec"], out["workflow"], out["layout"]], sort_keys=True).encode()).hexdigest()[:16]
    dest = path.with_name(path.stem + ".whatif.json")
    if dest.exists() and not FORCE:
        old = json.loads(dest.read_text())
        fresh = old.get("design_sha") == design_sha if "design_sha" in old else committed_at(dest) >= committed_at(path)
        if fresh:
            print(f"{dest.name}: up to date, kept")
            continue
    ids = {e["instance_id"] for e in out["workflow"]["equipment"]}
    targets = [b["instances"][0] for b in out["sim_result"]["bottlenecks"]
               if b["kind"] != "long_transfer" and b.get("instances") and b["instances"][0] in ids]
    by_instance = {}
    for iid in dict.fromkeys(targets):
        r = optimise_instrument(out["lab_spec"], out["workflow"], out["layout"], iid)
        validate(r, "instrument_optimisation")
        by_instance[iid] = r
    dest.write_text(json.dumps({"source": f"labforge.sim.whatif.optimise_instrument on the design in {path.name}, repo@{rev}",
                                "design_sha": design_sha, "by_instance": by_instance}))
    print(f"{dest.name}: {list(by_instance)}")

queue_path = ROOT / "backend/labforge/catalog/data/demo_prioritise_queue.json"
queue = json.loads(queue_path.read_text())
queue_sha = hashlib.sha256(json.dumps(queue, sort_keys=True).encode()).hexdigest()[:16]
dest = ROOT / "frontend/src/fixtures/demo_schedule.json"
old = json.loads(dest.read_text()) if dest.exists() else {}
fresh = old.get("queue_sha") == queue_sha if "queue_sha" in old else bool(old) and committed_at(dest) >= committed_at(queue_path)
if fresh and not FORCE:
    print("demo_schedule.json: up to date, kept")
else:
    schedule = prioritise(queue["projects"], queue["lab_id"])
    validate(schedule, "project_schedule")
    dest.write_text(json.dumps({"source": f"labforge.sim.portfolio.prioritise on {queue_path.relative_to(ROOT)}, repo@{rev}",
                                "queue_sha": queue_sha, "schedule": schedule}))
    print("demo_schedule.json:", schedule["recommended"], f"gain {schedule.get('gain_vs_naive')}")
