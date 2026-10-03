"""Bake offline fallbacks for the demo so case pages and #/schedule work without the backend. Strand A (Roshan).

Run from the repo root with the backend installed (re-run after replays or the demo queue change):
    python frontend/scripts/cache_offline.py
Writes:
  frontend/public/replays/<name>.whatif.json  what-if sweeps for each case's capacity-bottleneck instances
  frontend/src/fixtures/demo_schedule.json    POST /prioritise on backend/labforge/catalog/data/demo_prioritise_queue.json
Each file records its source; the UI labels these results "cached".
"""
import json
import subprocess
from pathlib import Path

from labforge.contracts import validate
from labforge.sim.portfolio import prioritise
from labforge.sim.whatif import optimise_instrument

ROOT = Path(__file__).resolve().parents[2]
rev = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT).decode().strip()

for path in sorted((ROOT / "frontend/public/replays").glob("*.json")):
    if path.name.endswith(".whatif.json"):
        continue
    out = json.loads(path.read_text())["output"]
    if not out.get("layout"):
        continue
    ids = {e["instance_id"] for e in out["workflow"]["equipment"]}
    targets = [b["instances"][0] for b in out["sim_result"]["bottlenecks"]
               if b["kind"] != "long_transfer" and b.get("instances") and b["instances"][0] in ids]
    by_instance = {}
    for iid in dict.fromkeys(targets):
        r = optimise_instrument(out["lab_spec"], out["workflow"], out["layout"], iid)
        validate(r, "instrument_optimisation")
        by_instance[iid] = r
    dest = path.with_name(path.stem + ".whatif.json")
    dest.write_text(json.dumps({"source": f"labforge.sim.whatif.optimise_instrument on the design in {path.name}, repo@{rev}",
                                "by_instance": by_instance}))
    print(f"{dest.name}: {list(by_instance)}")

queue = json.loads((ROOT / "backend/labforge/catalog/data/demo_prioritise_queue.json").read_text())
schedule = prioritise(queue["projects"], queue["lab_id"])
validate(schedule, "project_schedule")
(ROOT / "frontend/src/fixtures/demo_schedule.json").write_text(json.dumps(
    {"source": f"labforge.sim.portfolio.prioritise on backend/labforge/catalog/data/demo_prioritise_queue.json, repo@{rev}", "schedule": schedule}))
print("demo_schedule.json:", schedule["recommended"], f"gain {schedule.get('gain_vs_naive')}")
