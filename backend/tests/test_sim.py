"""Strand D simulator behaviour: batches, fan-out, operators with shifts, external and in-silico steps."""
import pytest

from labforge.contracts import errors
from labforge.layout.placer import transfer_edges
from labforge.sim.simulate import simulate


def spec(unit="plates_per_day", target=10, operators=None):
    s = {"id": "t", "name": "t", "domain": "chemistry", "description": "t",
         "throughput_target": {"value": target, "unit": unit}, "room": {"width_m": 6, "depth_m": 4}}
    if operators:
        s["operators"] = operators
    return s


def step(sid, cands, dur, after=(), exact=True, **kw):
    s = {"id": sid, "name": sid, "capability": "manual_bench", "candidate_instances": list(cands),
         "duration_s": dur, "after": list(after), **kw}
    if exact:
        s["duration_uncertainty"] = {"value": dur, "low": dur, "high": dur}
    return s


def wf(steps, equipment):
    return {"id": "wf", "lab_spec_id": "t", "steps": steps,
            "equipment": [{"instance_id": i, "catalog_id": c} for i, c in equipment.items()]}


def layout(operators=(), transfers=()):
    return {"id": "lay", "workflow_id": "wf", "room": {"width_m": 6, "depth_m": 4}, "placements": [],
            "transfers": list(transfers), "operators": [{"id": o, "role": r, "home": {"x": 0, "y": 0}} for o, r in operators]}


def run(s, w, lay, hours=48, reps=2):
    out = simulate(s, w, lay, hours=hours, replicates=reps)
    assert errors(out, "sim_result") == []
    return out


SOURCE = {"src_1": "generic_plate_hotel"}  # no catalog capacity: one slot, zero-time steps


def test_batch_size_multiplies_batch_device_throughput():
    def evaporator(batch):
        w = wf([step("load", ["src_1"], 0), step("evap", ["evap_1"], 3600, ["load"], batch_size=batch)],
               {**SOURCE, "evap_1": "generic_plate_hotel"})
        return run(spec(), w, layout())["throughput"]["p50"]

    assert evaporator(1) == pytest.approx(24, rel=0.05)
    assert evaporator(6) == pytest.approx(144, rel=0.05)


def test_batch_cannot_exceed_catalog_capacity():
    # The Clariostar has catalog capacity 1, so asking for batches of 6 must not run 6 plates at once.
    w = wf([step("load", ["src_1"], 0), step("read", ["reader_1"], 3600, ["load"], batch_size=6)],
           {**SOURCE, "reader_1": "bmg_clariostar"})
    assert run(spec(), w, layout())["throughput"]["p50"] == pytest.approx(24, rel=0.05)


def test_fan_out_splits_and_merges_plates():
    w = wf([step("load", ["src_1"], 0), step("split", ["lh_1"], 3600, ["load"], fan_out=8),
            step("read", ["reader_1"], 60, ["split"])],
           {**SOURCE, "lh_1": "opentrons_flex", "reader_1": "bmg_clariostar"})
    assert run(spec(), w, layout())["throughput"]["p50"] == pytest.approx(24 * 8, rel=0.05)

    w["steps"][1]["fan_out"] = 0.25  # four 96-well plates into one 384-well plate
    w["steps"][1]["duration_s"] = w["steps"][1]["duration_uncertainty"]["value"] = 600
    w["steps"][1]["duration_uncertainty"].update(low=600, high=600)
    assert run(spec(), w, layout())["throughput"]["p50"] == pytest.approx(144 / 4, rel=0.05)


def test_units_per_labware_converts_plates_to_compounds():
    w = wf([step("load", ["src_1"], 0), step("qc", ["lh_1"], 3600, ["load"], params={"units_per_labware": 96})],
           {**SOURCE, "lh_1": "opentrons_flex"})
    assert run(spec("compounds_per_day", 768), w, layout())["throughput"]["p50"] == pytest.approx(24 * 96, rel=0.05)


@pytest.mark.parametrize("shift_hours,count,expected", [(8, 1, 8), (8, 2, 16), (24, 1, 24)])
def test_manual_steps_only_run_on_shift(shift_hours, count, expected):
    w = wf([step("load", ["src_1"], 0), step("fish", [], 3600, ["load"], mode="manual", operator_role="crystallographer")],
           SOURCE)
    ops = [{"role": "crystallographer", "count": count, "shift_hours": shift_hours}]
    lay = layout([(f"crystallographer_{n + 1}", "crystallographer") for n in range(count)])
    out = run(spec(operators=ops), w, lay, hours=72)
    assert out["throughput"]["p50"] == pytest.approx(expected, rel=0.08)
    op_util = next(u for u in out["utilisation"] if u["instance_id"] == "crystallographer_1")
    assert op_util["busy_fraction"] > 0.9  # busy for their whole shift, not 1/3 of the day
    assert out["bottlenecks"][0]["kind"] == "operator_capacity"


def test_unstaffed_manual_step_produces_nothing_and_says_why():
    w = wf([step("load", ["src_1"], 0), step("purify", [], 3600, ["load"], mode="manual")], SOURCE)
    out = run(spec(), w, layout())
    assert out["throughput"]["p50"] == 0
    assert out["bottlenecks"][0]["kind"] == "operator_capacity" and out["bottlenecks"][0]["severity"] == "high"


def test_semi_automated_step_only_needs_operator_to_load():
    # The operator loads for 5 min per 1 h run, so an 8 h shift does not cap the instrument at 8 runs a day.
    w = wf([step("load", ["src_1"], 0), step("express", ["inc_1"], 3600, ["load"], mode="semi_automated")],
           {**SOURCE, "inc_1": "bmg_clariostar"})
    lay = layout([("tech_1", "tech")])
    out = run(spec(operators=[{"role": "tech", "count": 1, "shift_hours": 8}]), w, lay, hours=72)
    assert 8 < out["throughput"]["p50"] < 24


def test_external_step_adds_latency_not_capacity_limit():
    steps = [step("load", ["src_1"], 0), step("prep", ["lh_1"], 3600, ["load"]),
             step("synchrotron", [], 2 * 86400, ["prep"], mode="external", params={"queue_time_s": 86400}),
             step("hits", [], 600, ["synchrotron"], mode="in_silico")]
    w = wf(steps, {**SOURCE, "lh_1": "opentrons_flex"})
    out = run(spec(), w, layout(), hours=48)
    assert out["throughput"]["p50"] == pytest.approx(24, rel=0.05)
    assert out["cycle_time_s"] > 3 * 86400
    assert any(b["kind"] == "external_queue" for b in out["bottlenecks"])

    w["steps"][2]["params"]["max_concurrent"] = 6  # beamtime slots: 6 in flight over ~3 days = 2/day
    # Shipments return in bunches of 6 every ~3 days, so measure over several turnarounds.
    assert run(spec(), w, layout(), hours=24 * 12)["throughput"]["p50"] == pytest.approx(2, rel=0.2)


def test_in_silico_step_keeps_labware_in_place_for_transfers():
    steps = [step("image", ["imager_1"], 60), step("score", [], 60, ["image"], mode="in_silico"),
             step("soak", ["echo_1"], 60, ["score"]),
             step("ship", [], 60, ["soak"], mode="external"), step("process", ["lh_1"], 60, ["ship"])]
    w = wf(steps, {"imager_1": "liconic_stx44", "echo_1": "bmg_clariostar", "lh_1": "opentrons_flex"})
    assert transfer_edges(w) == [("imager_1", "echo_1")]


def test_operator_transfer_waits_for_shift():
    w = wf([step("load", ["src_1"], 0), step("read", ["reader_1"], 60, ["load"])], {**SOURCE, "reader_1": "bmg_clariostar"})
    carry = {"from_instance": "src_1", "to_instance": "reader_1", "transporter_instance": "tech_1", "distance_m": 10,
             "est_time_s": 600}
    lay = layout([("tech_1", "tech")], [carry])
    out = run(spec(operators=[{"role": "tech", "count": 1, "shift_hours": 8}]), w, lay, hours=72)
    # 10-minute carries by hand, one per plate, 8 h a day: about 48 plates/day (walking time is uncertain).
    assert 25 < out["throughput"]["p50"] < 50


def test_uncertainty_band_reflects_confidence():
    def band(confidence):
        s = step("work", ["lh_1"], 3600, ["load"], exact=False)
        s["duration_uncertainty"] = {"value": 3600, "confidence": confidence}
        w = wf([step("load", ["src_1"], 0), s], {**SOURCE, "lh_1": "opentrons_flex"})
        t = simulate(spec(), w, layout(), hours=24, replicates=30)["throughput"]
        return t["p90"] - t["p10"]

    assert band("placeholder") > 2 * band("datasheet")


def test_window_extends_until_enough_labware_finishes():
    # One 384-compound plate every 8 h: a 24 h window would see only 3 plates, so the sim keeps going.
    w = wf([step("load", ["src_1"], 0), step("lcms", ["lh_1"], 8 * 3600, ["load"], params={"units_per_labware": 384})],
           {**SOURCE, "lh_1": "opentrons_flex"})
    out = run(spec("compounds_per_day", 768), w, layout(), hours=24)
    assert out["simulated_hours"] >= 20 * 8
    assert out["throughput"]["p50"] == pytest.approx(3 * 384, rel=0.05)


def test_sensitivity_ranks_the_bottleneck_first_and_skips_idle_steps():
    from labforge.contracts import load_example
    from labforge.layout.placer import generate_layout
    s, w = load_example("lab_spec"), load_example("workflow")
    out = simulate(s, w, generate_layout(s, w), hours=48, replicates=6)
    assert errors(out, "sim_result") == []
    top = out["sensitivity"][0]
    assert top["parameter"] == "dispense.duration_s" and top["effect"] < -5  # slower liquid handling, fewer plates
    assert "seal.duration_s" not in {e["parameter"] for e in out["sensitivity"]}  # sealer idles: not worth measuring


def test_parallel_backends_match_serial():
    w = wf([step("load", ["src_1"], 0), step("work", ["lh_1"], 3600, ["load"], exact=False)], {**SOURCE, "lh_1": "opentrons_flex"})
    serial = simulate(spec(), w, layout(), hours=24, replicates=30, backend="serial")
    pooled = simulate(spec(), w, layout(), hours=24, replicates=30, backend="process")
    remote = simulate(spec(), w, layout(), hours=24, replicates=30, backend="modal")  # no token in CI: falls back locally
    assert serial["throughput"] == pooled["throughput"] == remote["throughput"]
    assert serial["sensitivity"] == pooled["sensitivity"]
