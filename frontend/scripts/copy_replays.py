"""Copy recorded agent runs into frontend/public/replays/ for ?replay=<name>. Strand A (Roshan).

Run from the repo root with the backend installed:
    python frontend/scripts/copy_replays.py <scenarios_dir> <name>...      e.g. ... scenarios_20261003_combined_main fbdd
Names: chem (chemistry.json), fbdd (xchem.json). Adds the catalog entries the run's workflow uses, so the replay
needs no backend. Recorded runs store sim_result without its timeline; if so, the timeline (only) is recomputed by
running the simulator on the recorded design, and the file says so in `timeline_source`.
"""
import json
import sys
from pathlib import Path

from labforge.catalog.store import load_catalog
from labforge.sim.simulate import simulate

ROOT = Path(__file__).resolve().parents[2]
FILES = {"chem": "chemistry.json", "fbdd": "xchem.json"}

src, names = Path(sys.argv[1]), sys.argv[2:] or list(FILES)
catalog = load_catalog()
for name in names:
    path = src / FILES[name]
    run = json.loads(path.read_text())
    out = run["output"]
    equipment = (out.get("workflow") or {}).get("equipment", [])
    run["catalog"] = {e["catalog_id"]: catalog[e["catalog_id"]] for e in equipment if e["catalog_id"] in catalog}
    run["source"] = str(path.resolve().relative_to(ROOT))
    if out.get("layout") and out.get("sim_result") and not out["sim_result"].get("timeline"):
        out["sim_result"]["timeline"] = simulate(out["lab_spec"], out["workflow"], out["layout"])["timeline"]
        run["timeline_source"] = "recomputed by labforge.sim.simulate from the recorded design; all other numbers are as recorded"
    (ROOT / "frontend/public/replays" / f"{name}.json").write_text(json.dumps(run, indent=1))
    print(f"{name}: {run['source']} ({len(run.get('events', []))} events, design={'layout' in out}, "
          f"timeline={len((out.get('sim_result') or {}).get('timeline') or [])})")
