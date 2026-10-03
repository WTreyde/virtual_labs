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


def test_gateway_offline_chat(monkeypatch):
    monkeypatch.setenv('ANTHROPIC_API_KEY', '')
    client = TestClient(app)
    out = client.post("/chat", json={"messages": [{"role": "user", "content": "hi"}]}).json()
    assert errors(out["layout"], "layout") == []


def test_instrument_optimisation_finds_the_limit():
    from labforge.sim.whatif import optimise_instrument
    layout = generate_layout(SPEC, WORKFLOW)
    lh = optimise_instrument(SPEC, WORKFLOW, layout, "lh_1", hours=24, replicates=3)
    reader = optimise_instrument(SPEC, WORKFLOW, layout, "reader_1", hours=24, replicates=3)
    assert lh["sweeps"][0]["elasticity"] > 0.5  # the liquid handler is the bottleneck
    assert reader["sweeps"][0]["elasticity"] < 0.1  # a faster reader changes nothing


def test_validation_cost_band():
    from labforge.validation.cost import compare, predicted_cost
    from labforge.validation.runner import load_cases, run_case
    pred = predicted_cost(WORKFLOW, ["instruments", "robots", "analytics"])
    assert pred["p10"] < pred["p50"] < pred["p90"]
    assert compare(pred["p50"], pred)["within_p10_p90"]
    assert all(run_case(c)["status"] in ("compared", "no_design_yet") for c in load_cases())
