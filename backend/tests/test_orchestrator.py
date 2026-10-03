"""Orchestrating-agent export: SKILL.md and tool manifest generated from a finished design."""
import json
from pathlib import Path

import pytest

from labforge.orchestrator import build_orchestrator, from_replay

REPLAYS = Path(__file__).resolve().parents[2] / "frontend" / "public" / "replays"


def design():
    spec = {"id": "mini_lab", "name": "Mini lab", "domain": "chemistry", "description": "t",
            "throughput_target": {"value": 10, "unit": "plates_per_day"}, "room": {"width_m": 6, "depth_m": 4},
            "operators": [{"role": "tech", "count": 1, "shift_hours": 8}]}
    wf = {"id": "wf", "lab_spec_id": "mini_lab", "equipment": [
        {"instance_id": "dispenser_1", "catalog_id": "disp"}, {"instance_id": "reader_1", "catalog_id": "read"},
        {"instance_id": "reader_2", "catalog_id": "read"}, {"instance_id": "arm_1", "catalog_id": "arm"}],
        "steps": [
            {"id": "dispense", "name": "Dispense", "capability": "liquid_handling", "candidate_instances": ["dispenser_1"],
             "duration_s": 600, "after": []},
            {"id": "check", "name": "Visual check", "capability": "manual_bench", "candidate_instances": [],
             "duration_s": 60, "after": ["dispense"], "mode": "manual", "operator_role": "tech"},
            {"id": "read", "name": "Read", "capability": "absorbance_read", "candidate_instances": ["reader_1", "reader_2"],
             "duration_s": 300, "after": ["check"],
             "duration_uncertainty": {"value": 300, "low": 240, "high": 400, "confidence": "datasheet"}}]}
    catalog = {
        "disp": {"id": "disp", "model": "Disp", "integration": ["SiLA 2"], "process": {"capacity": 1, "durations_s": {"liquid_handling": 600}},
                 "provenance": {"process.durations_s.liquid_handling": {"value": 600, "low": 300, "high": 900, "confidence": "placeholder"}},
                 "data_confidence": "estimated"},
        "read": {"id": "read", "model": "Reader", "integration": [], "storage_slots": 20, "data_confidence": "datasheet",
                 "safety": {"hazards": ["toxic_reagents"]}},
        "arm": {"id": "arm", "model": "Arm", "integration": ["Python SDK"], "transport": {"kind": "arm", "reach_m": 0.9},
                "safety": {"collaborative": False}},
    }
    layout = {"id": "lay", "workflow_id": "wf", "room": {"width_m": 6, "depth_m": 4}, "zones": [],
              "placements": [{"instance_id": "reader_1", "position": {"x": 1, "y": 1, "z": 0}}],
              "operators": [{"id": "tech_1", "role": "tech", "home": {"x": 0, "y": 0}}],
              "transfers": [{"from_instance": "dispenser_1", "to_instance": "reader_1", "transporter_instance": "arm_1",
                             "distance_m": 1.2, "est_time_s": 9}],
              "violations": [{"kind": "clearance", "instances": ["reader_1"], "message": "reader_1 too close to the wall."}]}
    sim = {"id": "sim", "throughput": {"value": 8, "unit": "plates_per_day", "target": 10, "p10": 6, "p50": 8, "p90": 11,
                                       "prob_meets_target": 0.3},
           "utilisation": [{"instance_id": "dispenser_1", "busy_fraction": 0.95}, {"instance_id": "reader_1", "busy_fraction": 0.4},
                           {"instance_id": "tech_1", "busy_fraction": 0.99}]}
    claims = [{"id": "c1", "statement": "Meets 10 plates/day.", "metric": "throughput.p50", "status": "refuted", "verified_value": 7.5}]
    return spec, wf, layout, catalog, sim, claims


def test_manifest_has_tools_limits_and_run_order():
    spec, wf, layout, catalog, sim, claims = design()
    out = build_orchestrator(spec, wf, layout, catalog, sim, claims)
    m = out["manifest"]
    dev = {d["instance_id"]: d for d in m["devices"]}
    tools = {t["name"]: t for d in m["devices"] for t in d["tools"]}
    assert "dispenser_1__liquid_handling" in tools and "reader_2__absorbance_read" in tools
    assert tools["arm_1__transfer"]["input_schema"]["properties"]["route"]["enum"] == ["dispenser_1->reader_1"]
    assert dev["dispenser_1"]["control"]["status"] == "open_standard"
    assert dev["reader_1"]["control"]["status"] == "none_listed"
    assert dev["reader_1"]["limits"]["storage_slots"] == 20
    assert m["run_order"]["waves"] == [["dispense"], ["check"], ["read"]]
    # operators are never the bottleneck device, even when busier
    assert m["run_order"]["bottleneck"]["instance_id"] == "dispenser_1"
    assert m["preflight"]["measure_on_first_run"][0]["field"] == "process.durations_s.liquid_handling"
    assert {t["name"] for t in m["global_tools"]} == {"request_human", "record_measurement", "pause_line"}
    json.dumps(m)  # serialisable


def test_skill_md_carries_honesty_and_escalation():
    spec, wf, layout, catalog, sim, claims = design()
    md = build_orchestrator(spec, wf, layout, catalog, sim, claims)["skill_md"]
    assert md.startswith("---\nname: run-mini-lab\n")
    assert "Do not start until a person has fixed each one" in md and "reader_1 too close to the wall." in md
    assert "verified throughput.p50 = 7.5" in md and "The verifier did not reproduce this" in md
    assert "30% chance of meeting" in md
    assert "arm_1 is not rated to work beside people" in md
    assert "No confirmed programmable interface for reader_1-2" in md  # dispenser has SiLA 2, check step is manual
    assert "toxic reagents: reader_1-2 must only run inside a fume_hood zone" in md


def test_without_sim_or_claims():
    spec, wf, layout, catalog, _, _ = design()
    layout["violations"] = []
    out = build_orchestrator(spec, wf, layout, catalog)
    assert out["manifest"]["run_order"]["bottleneck"] is None
    assert "The layout check passed" in out["skill_md"]


@pytest.mark.parametrize("name", ["chem", "fbdd"])
def test_case_study_replays(name):
    path = REPLAYS / f"{name}.json"
    if not path.exists():
        pytest.skip(f"no replay {name}")
    out = from_replay(path)
    assert out["manifest"]["devices"] and out["manifest"]["run_order"]["steps"]
    assert "## When to call a person" in out["skill_md"]
