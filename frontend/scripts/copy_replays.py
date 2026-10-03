"""Copy recorded agent runs into frontend/public/replays/ for ?replay=<name>. Strand A (Roshan).

Run from the repo root with the backend installed:
    python frontend/scripts/copy_replays.py [scenarios_dir]
Defaults to the newest backend/labforge/agent/demo/scenarios_* directory. Adds the catalog entries the run's
workflow uses (so the replay needs no backend) and records where the run came from.
"""
import json
import sys
from pathlib import Path

from labforge.catalog.store import load_catalog

ROOT = Path(__file__).resolve().parents[2]
NAMES = {"chem": "chemistry.json", "fbdd": "xchem.json"}

src = Path(sys.argv[1]) if len(sys.argv) > 1 else sorted((ROOT / "backend/labforge/agent/demo").glob("scenarios_*"))[-1]
catalog = load_catalog()
for name, file in NAMES.items():
    run = json.loads((src / file).read_text())
    equipment = (run["output"].get("workflow") or {}).get("equipment", [])
    run["catalog"] = {e["catalog_id"]: catalog[e["catalog_id"]] for e in equipment if e["catalog_id"] in catalog}
    run["source"] = str((src / file).relative_to(ROOT))
    (ROOT / "frontend/public/replays" / f"{name}.json").write_text(json.dumps(run, indent=1))
    print(f"{name}: {run['source']} ({len(run.get('events', []))} events, design={'layout' in run['output']})")
