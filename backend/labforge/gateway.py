"""Integrator: the one HTTP API the game client talks to. Owner: the integrator.

Run: uvicorn labforge.gateway:app --reload --port 8000
`make demo` also serves the built game (frontend/dist) from this app, so everything is on one URL.
"""
import json
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from labforge.agent.config import load_env
from labforge.agent.planner import run_turn
from labforge.agent.errors import safe_error
from labforge.agent.streaming import stream_turn
from labforge.agent.report import render_report
from labforge.bench.runner import load_tasks
from labforge.catalog.store import search
from labforge.contracts import load_example
from labforge.layout.placer import generate_layout
from labforge.sim.portfolio import prioritise
from labforge.sim.simulate import simulate
from labforge.sim.whatif import optimise_instrument
from labforge.validation.runner import load_cases, run_case
from labforge.verify.verifier import brier_score, verify_claims

app = FastAPI(title="LabForge")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class ChatRequest(BaseModel):
    messages: list[dict]


class DesignRequest(BaseModel):
    lab_spec: dict
    workflow: dict
    layout: dict | None = None
    sim_result: dict | None = None
    claims: list[dict] = []
    instance_id: str | None = None


# LABFORGE_REPLAY_ONLY=1 (the public Hugging Face Space) turns off live agent runs, so no one spends our API credits.
REPLAY_ONLY = os.getenv("LABFORGE_REPLAY_ONLY", "").strip().lower() in {"1", "true", "yes"}
REPLAY_ONLY_MESSAGE = "Live design is off on this public demo. Open the chemistry or XChem case study to watch a recorded agent run."


@app.get("/health")
def health():
    """`live_chat`: the chat routes are on. `api_key_loaded`: the backend process sees an Anthropic key, so the chat
    runs the real agent; without one it serves the offline worked example. `live_agent_note` says why the agent is off."""
    load_env()
    key_loaded = bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())
    note = None
    if REPLAY_ONLY:
        note = REPLAY_ONLY_MESSAGE
    elif not key_loaded:
        note = ("Live agent off: no API key loaded. Put ANTHROPIC_API_KEY in the repo-root .env (not backend/.env), "
                "make sure your shell does not export an empty ANTHROPIC_API_KEY, then restart the backend.")
    return {"ok": True, "live_chat": not REPLAY_ONLY, "api_key_loaded": key_loaded,
            "live_agent": key_loaded and not REPLAY_ONLY, "live_agent_note": note}


@app.get("/example/{name}")
def example(name: str):
    return load_example(name)


@app.get("/catalog")
def catalog(capability: str | None = None, labware: str | None = None, max_price_usd: float | None = None):
    return search(capability, labware, max_price_usd)


@app.post("/chat")
def chat(req: ChatRequest):
    if REPLAY_ONLY:
        raise HTTPException(status_code=503, detail=REPLAY_ONLY_MESSAGE)
    try:
        return run_turn(req.messages)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=safe_error(exc)) from exc


@app.post("/chat/stream")
def chat_stream(req: ChatRequest):
    if REPLAY_ONLY:
        raise HTTPException(status_code=503, detail=REPLAY_ONLY_MESSAGE)
    return StreamingResponse(stream_turn(req.messages), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache"})


@app.post("/layout")
def layout(req: DesignRequest):
    return generate_layout(req.lab_spec, req.workflow)


@app.post("/simulate")
def simulate_design(req: DesignRequest):
    lay = req.layout or generate_layout(req.lab_spec, req.workflow)
    return simulate(req.lab_spec, req.workflow, lay)


@app.post("/verify")
def verify(req: DesignRequest):
    claims = verify_claims(req.claims, req.workflow, req.layout, req.sim_result, spec=req.lab_spec)
    return {"claims": claims, "brier": brier_score(claims)}


@app.post("/report", response_class=PlainTextResponse)
def report(req: DesignRequest):
    lay = req.layout or generate_layout(req.lab_spec, req.workflow)
    sim = req.sim_result or simulate(req.lab_spec, req.workflow, lay)
    return render_report(req.lab_spec, req.workflow, lay, sim)


@app.get("/bench/tasks")
def bench_tasks():
    return load_tasks()


LEADERBOARD = Path(__file__).parent / "bench" / "results" / "leaderboard.json"


@app.get("/bench/leaderboard")
def bench_leaderboard():
    """The committed LabDesignBench leaderboard (written by labforge.bench.runner --out)."""
    if not LEADERBOARD.is_file():
        raise HTTPException(404, "No leaderboard yet: run python -m labforge.bench.runner --out " + str(LEADERBOARD))
    return json.loads(LEADERBOARD.read_text())


@app.post("/optimise")
def optimise(req: DesignRequest):
    lay = req.layout or generate_layout(req.lab_spec, req.workflow)
    return optimise_instrument(req.lab_spec, req.workflow, lay, req.instance_id)


# Agent-designed workflows for cases that only have a brief, produced offline once (never on a page view).
VALIDATION_DESIGN_DIR = Path(__file__).resolve().parent / "validation" / "designs"


def _stored_design(case_id: str) -> dict | None:
    path = VALIDATION_DESIGN_DIR / f"{case_id}.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text()).get("workflow")


@app.get("/validation")
def validation():
    """Cost every published lab from a stored design. This route never calls the agent: a case without a hand-written
    or pre-generated workflow comes back as `no_design_yet`, and a case that fails comes back as one `error` row."""
    rows = []
    for case in load_cases():
        try:
            workflow = case.get("workflow") or _stored_design(case["id"])
            if workflow is None:
                rows.append({"id": case["id"], "name": case["name"], "verified": case["verified"],
                             "includes": case["reported"]["cost"]["includes"], "status": "no_design_yet",
                             "reason": "No stored design yet; it is generated offline, not on page load."})
                continue
            rows.append(run_case({**case, "workflow": workflow}))
        except Exception as exc:  # one bad case must not blank the whole tab
            rows.append({"id": case.get("id"), "name": case.get("name"), "verified": case.get("verified"),
                         "status": "error", "reason": f"{type(exc).__name__}: {exc}"[:300]})
    return rows


class PortfolioRequest(BaseModel):
    projects: list[dict]  # [{id, workflow, units, weight?, deadline_h?}]
    lab_id: str = "lab"


@app.post("/prioritise")
def prioritise_projects(req: PortfolioRequest):
    return prioritise(req.projects, req.lab_id)


# Keep this last: the built game client is served at / for `make demo`, behind every API route above.
STATIC_DIR = Path(os.getenv("LABFORGE_STATIC_DIR", str(Path(__file__).resolve().parents[2] / "frontend" / "dist")))
if STATIC_DIR.is_dir():
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="game")
