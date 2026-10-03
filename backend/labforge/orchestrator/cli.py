"""Write the orchestrating-agent bundle for a recorded run.

    cd backend && python3 -m labforge.orchestrator.cli ../frontend/public/replays/fbdd.json --out /tmp/fbdd-agent

Writes <out>/SKILL.md and <out>/tools.json.
"""
import argparse
import json
from pathlib import Path

from labforge.orchestrator.skills import from_replay


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("replay", help="path to a replay JSON (frontend/public/replays/<name>.json)")
    ap.add_argument("--out", required=True, help="output directory")
    ap.add_argument("--schedule", help="optional ProjectSchedule JSON from POST /prioritise")
    a = ap.parse_args(argv)
    schedule = json.loads(Path(a.schedule).read_text()) if a.schedule else None
    bundle = from_replay(a.replay, schedule)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "SKILL.md").write_text(bundle["skill_md"])
    (out / "tools.json").write_text(json.dumps(bundle["manifest"], indent=2) + "\n")
    print(f"wrote {out / 'SKILL.md'} and {out / 'tools.json'}")


if __name__ == "__main__":
    main()
