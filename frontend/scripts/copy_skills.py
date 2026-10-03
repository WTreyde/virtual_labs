"""Copy each case's generated agent skill into frontend/public/skills/<case>/ for offline download. Strand A (Roshan).

Run from the repo root after the orchestrator samples change:
    python frontend/scripts/copy_skills.py
Source: backend/labforge/orchestrator/samples/<case>/{SKILL.md,tools.json} (read only).
"""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC, DEST = ROOT / "backend/labforge/orchestrator/samples", ROOT / "frontend/public/skills"

for case in sorted(p for p in SRC.iterdir() if p.is_dir()):
    out = DEST / case.name
    out.mkdir(parents=True, exist_ok=True)
    for name in ("SKILL.md", "tools.json"):
        if (case / name).exists():
            shutil.copyfile(case / name, out / name)
    print(f"{case.name}: {sorted(f.name for f in out.iterdir())}")
