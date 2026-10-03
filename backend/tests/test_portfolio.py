"""Project prioritisation should overlap projects that stress different instruments."""
import copy

from labforge.contracts import load_example
from labforge.sim.portfolio import prioritise


def _project(pid: str, units: int, dispense_s: float, read_s: float, **extra) -> dict:
    wf = copy.deepcopy(load_example("workflow"))
    wf["id"] = pid
    for s in wf["steps"]:
        if s["id"] == "dispense":
            s["duration_s"] = dispense_s
        if s["id"] == "read":
            s["duration_s"] = read_s
    return {"id": pid, "workflow": wf, "units": units, **extra}


def test_mixing_dispense_heavy_and_read_heavy_projects_beats_running_them_in_turn():
    projects = [_project("dispense_heavy", 10, 1800, 60), _project("read_heavy", 10, 60, 1800)]
    out = prioritise(projects)
    assert out["recommended"] != "sequential:dispense_heavy>read_heavy"  # the naive order given
    assert out["gain_vs_naive"] > 0.2
    assert out["gantt"]


def test_deadlines_switch_the_objective_and_put_the_urgent_project_first():
    projects = [_project("big", 12, 1800, 60), _project("urgent", 2, 1800, 60, deadline_h=3, weight=5)]
    out = prioritise(projects)
    assert out["objective"] == "weighted_tardiness"
    assert out["candidates"][0]["deadline_misses"] == []
    naive = next(c for c in out["candidates"] if c.get("order") == ["big", "urgent"])
    assert naive["deadline_misses"] == ["urgent"]
