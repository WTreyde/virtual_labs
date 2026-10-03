"""Contract tests: every strand's output must validate against /schemas. Keep these green before pushing."""
from fastapi.testclient import TestClient

from labforge.agent.report import render_report
from labforge.bench.runner import load_tasks
from labforge.catalog.store import load_catalog
from labforge.contracts import errors, load_example
from labforge.gateway import app
from labforge.layout.placer import generate_layout
from labforge.sim.simulate import simulate
from labforge.verify.verifier import verify_claims

SPEC, WORKFLOW = load_example("lab_spec"), load_example("workflow")


def test_examples_match_schemas():
    for name in ("lab_spec", "workflow", "layout", "sim_result"):
        assert errors(load_example(name), name) == []


def test_catalog_loads():
    assert set(load_catalog()) >= {e["catalog_id"] for e in WORKFLOW["equipment"]}


def test_layout_then_simulate():
    layout = generate_layout(SPEC, WORKFLOW)
    assert not [v for v in layout["violations"] if v["kind"] == "unreachable_transfer"]
    sim = simulate(SPEC, WORKFLOW, layout, hours=24, replicates=3)
    assert sim["throughput"]["p10"] <= sim["throughput"]["p50"] <= sim["throughput"]["p90"]
    assert "lh_1" in sim["bottlenecks"][0]["instances"]


def test_verifier_refutes_inflated_claim():
    layout = generate_layout(SPEC, WORKFLOW)
    sim = simulate(SPEC, WORKFLOW, layout, hours=24, replicates=3)
    claim = {"id": "fast", "statement": "Does 100 plates/day", "metric": "throughput.p50", "comparator": ">=",
             "predicted_value": 100, "confidence": 0.9, "status": "unverified"}
    assert verify_claims([claim], WORKFLOW, layout, sim)[0]["status"] == "refuted"


def test_report_and_bench():
    assert "Bill of materials" in render_report(SPEC, WORKFLOW, load_example("layout"), load_example("sim_result"))
    assert load_tasks()


def test_gateway_offline_chat():
    client = TestClient(app)
    out = client.post("/chat", json={"messages": [{"role": "user", "content": "hi"}]}).json()
    assert errors(out["layout"], "layout") == []
