"""Strand D: the recommended project schedule, re-checked under the Monte Carlo simulator's uncertainty."""
import copy
import time

from labforge.contracts import errors, load_example
from labforge.sim.portfolio import confirm_schedule, prioritise


def _project(pid, units, dispense_s, read_s, confidence=None):
    wf = copy.deepcopy(load_example("workflow"))
    wf["id"] = pid
    for s in wf["steps"]:
        if s["id"] in ("dispense", "read"):
            s["duration_s"] = dispense_s if s["id"] == "dispense" else read_s
            if confidence:
                s["duration_uncertainty"] = {"value": s["duration_s"], "confidence": confidence}
    return {"id": pid, "workflow": wf, "units": units}


def test_recommended_schedule_is_confirmed_with_p10_p90_makespans():
    projects = [_project("dispense_heavy", 10, 1800, 60), _project("read_heavy", 10, 60, 1800)]
    t = time.time()
    out = prioritise(projects)
    assert time.time() - t < 10
    assert errors(out, "project_schedule") == []
    assert "Monte Carlo" in out["caveat"] and "P10-P90" in out["caveat"]
    assert "NOT reliably better" not in out["caveat"]

    best = out["candidates"][0]
    mc = confirm_schedule(projects, {"recommended": (best["policy"].split(":")[0], best.get("order")),
                                     "order_given": ("sequential", ["dispense_heavy", "read_heavy"])}, replicates=30)
    rec, naive = mc["makespan_h"]["recommended"], mc["makespan_h"]["order_given"]
    assert rec["p10"] <= rec["p50"] <= rec["p90"] and rec["p90"] > rec["p10"]  # uncertainty shows up as a band
    assert rec["p90"] < naive["p10"]  # bands do not overlap: the saving is real, not noise
    assert mc["prob_faster"]["recommended"]["order_given"] >= 0.95


def test_placeholder_durations_widen_the_makespan_band():
    def width(conf):
        projects = [_project("a", 6, 1800, 60, conf), _project("b", 6, 60, 1800, conf)]
        m = confirm_schedule(projects, {"s": ("sequential", ["a", "b"])}, replicates=30)["makespan_h"]["s"]
        return m["p90"] - m["p10"]

    assert width("placeholder") > 2 * width("datasheet")


def test_monte_carlo_can_be_switched_off():
    projects = [_project("a", 3, 1800, 60), _project("b", 3, 60, 1800)]
    assert "Monte Carlo" not in prioritise(projects, mc_replicates=0)["caveat"]
