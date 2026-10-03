"""Integrator: the one HTTP API the game client talks to. Owner: the integrator.

Run: uvicorn labforge.gateway:app --reload --port 8000
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from labforge.agent.planner import run_turn
from labforge.agent.report import render_report
from labforge.bench.runner import load_tasks
from labforge.catalog.store import search
from labforge.contracts import load_example
from labforge.layout.placer import generate_layout
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


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/example/{name}")
def example(name: str):
    return load_example(name)


@app.get("/catalog")
def catalog(capability: str | None = None, labware: str | None = None, max_price_usd: float | None = None):
    return search(capability, labware, max_price_usd)


@app.post("/chat")
def chat(req: ChatRequest):
    return run_turn(req.messages)


@app.post("/layout")
def layout(req: DesignRequest):
    return generate_layout(req.lab_spec, req.workflow)


@app.post("/simulate")
def simulate_design(req: DesignRequest):
    lay = req.layout or generate_layout(req.lab_spec, req.workflow)
    return simulate(req.lab_spec, req.workflow, lay)


@app.post("/verify")
def verify(req: DesignRequest):
    claims = verify_claims(req.claims, req.workflow, req.layout, req.sim_result)
    return {"claims": claims, "brier": brier_score(claims)}


@app.post("/report", response_class=PlainTextResponse)
def report(req: DesignRequest):
    lay = req.layout or generate_layout(req.lab_spec, req.workflow)
    sim = req.sim_result or simulate(req.lab_spec, req.workflow, lay)
    return render_report(req.lab_spec, req.workflow, lay, sim)


@app.get("/bench/tasks")
def bench_tasks():
    return load_tasks()


@app.post("/optimise")
def optimise(req: DesignRequest):
    lay = req.layout or generate_layout(req.lab_spec, req.workflow)
    return optimise_instrument(req.lab_spec, req.workflow, lay, req.instance_id)


@app.get("/validation")
def validation():
    return [run_case(c) for c in load_cases()]
