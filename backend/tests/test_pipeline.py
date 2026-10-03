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


def test_validation_cost_band(monkeypatch):
    monkeypatch.setenv('ANTHROPIC_API_KEY', '')
    from labforge.validation.cost import compare, predicted_cost
    from labforge.validation.runner import load_cases, run_case
    pred = predicted_cost(WORKFLOW, ["instruments", "robots", "analytics"])
    assert pred["p10"] < pred["p50"] < pred["p90"]
    assert compare(pred["p50"], pred)["within_p10_p90"]
    assert all(run_case(c)["status"] in ("compared", "no_design_yet") for c in load_cases())


def test_bench_leaderboard_route(tmp_path, monkeypatch):
    import labforge.gateway as gw
    client = TestClient(app)
    monkeypatch.setattr(gw, "LEADERBOARD", tmp_path / "missing.json")
    assert client.get("/bench/leaderboard").status_code == 404
    board = tmp_path / "leaderboard.json"
    board.write_text('{"arms": []}')
    monkeypatch.setattr(gw, "LEADERBOARD", board)
    assert client.get("/bench/leaderboard").json() == {"arms": []}


def test_demo_serves_built_game_behind_api_routes(tmp_path, monkeypatch):
    """`make demo`: the built client is served at / and its replays statically, while API routes still win."""
    import importlib
    import labforge.gateway as gw
    (tmp_path / "replays").mkdir()
    (tmp_path / "index.html").write_text("<html>LabForge</html>")
    (tmp_path / "replays" / "chem.json").write_text('{"brief": "x"}')
    monkeypatch.setenv("LABFORGE_STATIC_DIR", str(tmp_path))
    try:
        client = TestClient(importlib.reload(gw).app)
        assert "LabForge" in client.get("/").text
        assert client.get("/replays/chem.json").json() == {"brief": "x"}
        assert client.get("/health").status_code == 200
        assert client.get("/example/lab_spec").status_code == 200
    finally:
        monkeypatch.delenv("LABFORGE_STATIC_DIR")
        importlib.reload(gw)


def test_replay_only_mode_refuses_live_chat(monkeypatch):
    """The public demo (LABFORGE_REPLAY_ONLY=1) never runs the agent, so it cannot spend API credits."""
    import labforge.gateway as gw
    client = TestClient(gw.app)
    assert client.get("/health").json()["live_chat"] is True
    monkeypatch.setattr(gw, "REPLAY_ONLY", True)
    monkeypatch.setattr(gw, "run_turn", lambda *_: (_ for _ in ()).throw(AssertionError("agent must not run")))
    health = client.get("/health").json()
    assert health["live_chat"] is False and health["live_agent"] is False and "recorded agent run" in health["live_agent_note"]
    for path in ("/chat", "/chat/stream"):
        response = client.post(path, json={"messages": [{"role": "user", "content": "design a lab"}]})
        assert response.status_code == 503 and "recorded agent run" in response.json()["detail"]



def test_health_says_when_no_api_key_is_loaded(monkeypatch):
    """The UI shows "live agent off: no API key loaded" instead of silently serving the offline example."""
    import labforge.gateway as gw
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    health = TestClient(gw.app).get("/health").json()
    assert health["live_chat"] is True and health["api_key_loaded"] is False and health["live_agent"] is False
    assert "no API key loaded" in health["live_agent_note"]
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    health = TestClient(gw.app).get("/health").json()
    assert health["api_key_loaded"] is True and health["live_agent"] is True and health["live_agent_note"] is None


def _no_agent(*_args, **_kwargs):
    raise AssertionError("GET /validation must never run the agent")


def test_validation_route_never_calls_the_agent(monkeypatch):
    """With a key loaded, /validation still costs only stored designs: zero agent calls, every case gets a row."""
    import labforge.agent.planner as planner
    import labforge.gateway as gw
    import labforge.validation.runner as vr
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setattr(planner, "run_turn", _no_agent)
    monkeypatch.setattr(gw, "run_turn", _no_agent)
    monkeypatch.setattr(vr, "design_from_brief", _no_agent)
    rows = TestClient(gw.app).get("/validation").json()
    assert len(rows) == len(vr.load_cases())
    assert {r["status"] for r in rows} <= {"compared", "not_costable", "no_design_yet"}
    assert any(r["status"] == "compared" for r in rows)


def test_validation_route_turns_one_failing_case_into_one_error_row(monkeypatch):
    import labforge.gateway as gw
    real = gw.run_case
    cases = gw.load_cases()
    broken = next(c["id"] for c in cases if c.get("workflow"))

    def flaky(case):
        if case["id"] == broken:
            raise RuntimeError("cost model blew up")
        return real(case)

    monkeypatch.setattr(gw, "run_case", flaky)
    rows = TestClient(gw.app).get("/validation").json()
    assert len(rows) == len(cases)
    errors = [r for r in rows if r["status"] == "error"]
    assert [r["id"] for r in errors] == [broken] and "blew up" in errors[0]["reason"]


def test_replay_only_validation_makes_no_agent_calls(monkeypatch):
    import labforge.agent.planner as planner
    import labforge.gateway as gw
    import labforge.validation.runner as vr
    monkeypatch.setattr(gw, "REPLAY_ONLY", True)
    monkeypatch.setattr(planner, "run_turn", _no_agent)
    monkeypatch.setattr(vr, "design_from_brief", _no_agent)
    response = TestClient(gw.app).get("/validation")
    assert response.status_code == 200 and all(r["status"] != "error" for r in response.json())
