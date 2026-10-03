"""Project prioritisation: which order should several projects run through one lab? Owner: Maxim.

Each project is a Workflow (using the lab's equipment instance ids) plus how many labware units it
needs, an optional priority weight and an optional deadline. We simulate the lab running all
projects under several release policies and recommend the one that finishes soonest (or with the
least weighted lateness when deadlines are given):

- sequential: all units of one project, then the next; every project order is tried (up to 6 projects).
- interleave: release units round-robin across projects.
- bottleneck_mix: release the next unit from the project whose heaviest instrument is least loaded,
  so projects that stress different instruments overlap.

This is a fast deterministic model on mean durations, separate from the Monte Carlo simulator
(sim/simulate.py) so the two can evolve independently. TODO(Maxim): confirm the recommended
policy's makespan with the Monte Carlo simulator (P10/P90) and include transfer times.
"""
import itertools
from collections import defaultdict

import simpy

from labforge.catalog.store import get as get_item
from labforge.contracts import validate

MAX_PERMUTED_PROJECTS = 6
GANTT_LIMIT = 400


def _steps_in_order(workflow: dict) -> list[dict]:
    done, order, pending = set(), [], list(workflow["steps"])
    while pending:
        ready = [s for s in pending if set(s.get("after", [])) <= done] or pending[:1]
        for s in ready:
            order.append(s)
            done.add(s["id"])
            pending.remove(s)
    return order


def _capacities(projects: list[dict]) -> dict[str, int]:
    caps = {}
    for p in projects:
        for e in p["workflow"]["equipment"]:
            caps[e["instance_id"]] = max(caps.get(e["instance_id"], 1),
                                         get_item(e["catalog_id"]).get("process", {}).get("capacity", 1))
    return caps


def _load(project: dict, caps: dict[str, int]) -> dict[str, float]:
    """Seconds of instrument time one unit of this project needs, per instance (capacity-normalised)."""
    load = defaultdict(float)
    for s in project["workflow"]["steps"]:
        cands = s["candidate_instances"]
        for c in cands:
            load[c] += s["duration_s"] / len(cands) / caps.get(c, 1)
    return load


def run_policy(projects: list[dict], policy: str, order: list[str] | None = None, wip: int | None = None,
               record: bool = False) -> dict:
    env = simpy.Environment()
    caps = _capacities(projects)
    res = {i: simpy.Resource(env, capacity=c) for i, c in caps.items()}
    busy, gantt, finish = defaultdict(float), [], {}
    by_id = {p["id"]: p for p in projects}
    steps = {p["id"]: _steps_in_order(p["workflow"]) for p in projects}
    loads = {p["id"]: _load(p, caps) for p in projects}
    remaining = {p["id"]: p["units"] for p in projects}
    in_lab = defaultdict(float)  # instrument seconds currently committed per instance
    wip_limit = wip or max(2, sum(caps.values()))
    slots = simpy.Container(env, init=wip_limit, capacity=wip_limit)
    left = {p["id"]: p["units"] for p in projects}

    def unit(pid: str, n: int):
        for inst, sec in loads[pid].items():
            in_lab[inst] += sec
        for step in steps[pid]:
            cands = step["candidate_instances"]
            if not cands:
                yield env.timeout(step["duration_s"])
                continue
            inst = min(cands, key=lambda c: len(res[c].queue) + res[c].count / caps[c])
            with res[inst].request() as req:
                yield req
                start = env.now
                yield env.timeout(step["duration_s"])
                busy[inst] += step["duration_s"]
                if record and len(gantt) < GANTT_LIMIT:
                    gantt.append({"project": pid, "unit": n, "step": step["id"], "instance": inst,
                                  "start_s": round(start, 1), "end_s": round(env.now, 1)})
        for inst, sec in loads[pid].items():
            in_lab[inst] -= sec
        left[pid] -= 1
        if left[pid] == 0:
            finish[pid] = env.now
        yield slots.put(1)

    def pick() -> str | None:
        live = [pid for pid in (order or by_id) if remaining[pid] > 0]
        if not live:
            return None
        if policy == "sequential":
            return live[0]
        if policy == "interleave":
            return max(live, key=lambda pid: remaining[pid] / by_id[pid]["units"])
        # bottleneck_mix: the project whose heaviest instrument is least committed right now
        return min(live, key=lambda pid: in_lab[max(loads[pid], key=loads[pid].get)] if loads[pid] else 0)

    def source():
        while True:
            pid = pick()
            if pid is None:
                return
            yield slots.get(1)
            remaining[pid] -= 1
            env.process(unit(pid, by_id[pid]["units"] - remaining[pid]))

    env.process(source())
    env.run()
    makespan = env.now
    used = {i for p in projects for s in p["workflow"]["steps"] for i in s["candidate_instances"]}
    util = {i: round(busy[i] / (makespan * caps[i]), 3) for i in sorted(used)} if makespan else {}
    tard, misses = 0.0, []
    for pid, t in finish.items():
        dl = by_id[pid].get("deadline_h")
        if dl is not None and t / 3600 > dl:
            tard += by_id[pid].get("weight", 1) * (t / 3600 - dl)
            misses.append(pid)
    out = {"policy": policy if not order or policy != "sequential" else "sequential:" + ">".join(order),
           "makespan_h": round(makespan / 3600, 2),
           "mean_utilisation": round(sum(util.values()) / len(util), 3) if util else 0.0,
           "utilisation": util,
           "project_finish_h": {pid: round(t / 3600, 2) for pid, t in finish.items()},
           "weighted_tardiness_h": round(tard, 2), "deadline_misses": misses}
    if order and policy == "sequential":
        out["order"] = list(order)
    if record:
        out["_gantt"] = gantt
    return out


def prioritise(projects: list[dict], lab_id: str = "lab") -> dict:
    """Evaluate release policies for these projects and recommend one. See module docstring."""
    ids = [p["id"] for p in projects]
    objective = "weighted_tardiness" if any("deadline_h" in p for p in projects) else "makespan"
    orders = itertools.permutations(ids) if len(ids) <= MAX_PERMUTED_PROJECTS else [ids]
    cands = [run_policy(projects, "sequential", list(o)) for o in orders]
    cands += [run_policy(projects, "interleave"), run_policy(projects, "bottleneck_mix")]
    key = (lambda c: (c["weighted_tardiness_h"], c["makespan_h"])) if objective == "weighted_tardiness" \
        else (lambda c: (c["makespan_h"], -c["mean_utilisation"]))
    cands.sort(key=key)
    best = cands[0]
    naive = next(c for c in cands if c.get("order") == ids)
    gantt = run_policy(projects, best["policy"].split(":")[0], best.get("order"), record=True)["_gantt"]
    result = {
        "lab_id": lab_id, "objective": objective, "candidates": cands[:10], "recommended": best["policy"],
        "gain_vs_naive": round(1 - best["makespan_h"] / naive["makespan_h"], 3) if naive["makespan_h"] else 0.0,
        "gantt": gantt,
        "caveat": "Deterministic schedule on mean step durations without transfer times; confirm with the Monte Carlo simulator before committing.",
    }
    return validate(result, "project_schedule")
