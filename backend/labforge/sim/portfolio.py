"""Project prioritisation: which order should several projects run through one lab? Owner: Maxim.

Each project is a Workflow (using the lab's equipment instance ids) plus how many labware units it
needs, an optional priority weight and an optional deadline. We simulate the lab running all
projects under several release policies and recommend the one that finishes soonest (or with the
least weighted lateness when deadlines are given):

- sequential: all units of one project, then the next; every project order is tried (up to 6 projects).
- interleave: release units round-robin across projects.
- bottleneck_mix: release the next unit from the project whose heaviest instrument is least loaded,
  so projects that stress different instruments overlap.

Policies are compared on mean durations (fast enough to try every order). `confirm_schedule` then
re-runs the recommended and the naive schedule under the Monte Carlo simulator's uncertainty: one
epistemic draw per step per replicate from the same ranges sim/simulate.py uses, plus run jitter,
with the same draws for both schedules. Still ignored: transfer times and operator shifts.
"""
import copy
import itertools
import random
import statistics
from collections import defaultdict

import simpy

from labforge.catalog.store import get as get_item
from labforge.catalog.store import load_catalog
from labforge.contracts import validate
from labforge.sim.simulate import JITTER, duration_range

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
               record: bool = False, rng: random.Random | None = None) -> dict:
    """Run one release policy. With `rng`, each step run is jittered (Monte Carlo); without, mean durations."""
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
                dt = step["duration_s"] * (rng.uniform(1 - JITTER, 1 + JITTER) if rng else 1.0)
                yield env.timeout(dt)
                busy[inst] += dt
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


def _draw_durations(projects: list[dict], rng: random.Random) -> list[dict]:
    """Copy of the projects with each step's mean duration drawn from its uncertainty range."""
    catalog = load_catalog()
    drawn = copy.deepcopy(projects)
    for p in drawn:
        eq = {e["instance_id"]: e["catalog_id"] for e in p["workflow"]["equipment"]}
        for s in p["workflow"]["steps"]:
            item = catalog.get(eq.get(s["candidate_instances"][0], "")) if s["candidate_instances"] else None
            low, mode, high = duration_range(s, item)
            s["duration_s"] = rng.triangular(low, high, mode) if high > low else mode
    return drawn


def _quantiles(xs: list[float]) -> dict:
    q = statistics.quantiles(xs, n=10, method="inclusive") if len(xs) > 1 else xs * 9
    return {"p10": round(q[0], 2), "p50": round(statistics.median(xs), 2), "p90": round(q[-1], 2)}


def confirm_schedule(projects: list[dict], schedules: dict[str, tuple[str, list[str] | None]],
                     replicates: int = 30, seed: int = 0) -> dict:
    """Makespan P10/P50/P90 (hours) for each named schedule {label: (policy, order)} under duration uncertainty.

    Every schedule sees the same drawn durations in a replicate (common random numbers), so
    `prob_faster[a][b]` is the share of plausible worlds in which schedule a finishes before b."""
    master = random.Random(seed)
    seeds = [master.randrange(2**31) for _ in range(replicates)]
    spans = {label: [] for label in schedules}
    for sd in seeds:
        drawn = _draw_durations(projects, random.Random(sd))
        for label, (policy, order) in schedules.items():
            spans[label].append(run_policy(drawn, policy, order, rng=random.Random(sd + 1))["makespan_h"])
    labels = list(schedules)
    return {
        "replicates": replicates,
        "makespan_h": {label: _quantiles(v) for label, v in spans.items()},
        "prob_faster": {a: {b: round(sum(x < y for x, y in zip(spans[a], spans[b])) / replicates, 2)
                            for b in labels if b != a} for a in labels},
    }


def prioritise(projects: list[dict], lab_id: str = "lab", mc_replicates: int = 30) -> dict:
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
        "caveat": "Policies compared on mean step durations; transfer times and operator shifts are not modelled.",
    }
    if mc_replicates:
        sched = {"recommended": (best["policy"].split(":")[0], best.get("order"))}
        if best is not naive:
            sched["order_given"] = ("sequential", ids)
        mc = confirm_schedule(projects, sched, replicates=mc_replicates)
        rec = mc["makespan_h"]["recommended"]
        text = f" Monte Carlo over duration uncertainty ({mc_replicates} replicates): recommended {rec['p50']} h " \
               f"(P10-P90 {rec['p10']}-{rec['p90']} h)"
        if "order_given" in mc["makespan_h"]:
            nv = mc["makespan_h"]["order_given"]
            win = mc["prob_faster"]["recommended"]["order_given"]
            text += f" vs order given {nv['p50']} h ({nv['p10']}-{nv['p90']} h); recommended finishes first in {win:.0%} of replicates."
        else:
            text += "; the order given is already the best."
        result["caveat"] += text
        if objective == "makespan" and "order_given" in mc["makespan_h"] \
                and mc["prob_faster"]["recommended"]["order_given"] < 0.5:
            result["caveat"] += " Under uncertainty the recommendation is NOT reliably better; do not quote the saving."
    return validate(result, "project_schedule")
