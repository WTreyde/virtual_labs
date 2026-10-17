"""Snapshot the backend's read-only routes as static JSON, for the GitHub Pages build of the replay-only demo.

Run from the repo root with the backend installed, after `vite build`:
    python deploy/pages/export_api.py frontend/dist
Writes <dist>/api/<route>.json for every GET the client makes (health, catalog, bench, validation). A client built
with VITE_STATIC_API=1 reads these files instead of calling a backend; its POST routes (chat, report, optimise,
prioritise) fail fast into the cached fallbacks the replays already use.
"""
import json
import os
import sys
from pathlib import Path

os.environ["LABFORGE_REPLAY_ONLY"] = "1"  # /health then reports live_chat: false, so the client shows replay mode
os.environ["LABFORGE_STATIC_DIR"] = "/nonexistent"  # don't mount a previous build behind the API routes
os.environ.pop("ANTHROPIC_API_KEY", None)

from fastapi.testclient import TestClient  # noqa: E402

from labforge.gateway import app  # noqa: E402

ROUTES = ["/health", "/catalog", "/bench/tasks", "/bench/leaderboard", "/validation"]


def main(dist: Path) -> None:
    client = TestClient(app)
    for route in ROUTES:
        res = client.get(route)
        if res.status_code != 200:
            raise SystemExit(f"GET {route}: HTTP {res.status_code} {res.text[:200]}")
        out = dist / "api" / f"{route.lstrip('/')}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        body = res.json()
        if route == "/health":  # a static site never runs the agent, whatever .env the build machine has
            body.update(api_key_loaded=False, live_agent=False)
        out.write_text(json.dumps(body))
        print(f"{route} -> {out} ({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else "frontend/dist"))
