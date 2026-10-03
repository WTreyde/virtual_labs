"""Strand D: Monte Carlo discrete-event simulation of a workflow on a layout. Owner: Maxim.

v0 model: labware flows through the steps in dependency order; each step grabs the least-busy
candidate instance; moving between instances grabs the transporter for the layout's transfer
time. Durations are sampled per replicate from `duration_uncertainty` (triangular) or a default
-15%/+25% band, so throughput comes out as P10/P50/P90.

TODO(Maxim): batch_size and fan_out, operator shifts, external queues, sensitivity analysis,
run replicates in parallel on Modal.
"""
import random
import statistics
from collections import defaultdict

import simpy

from labforge.catalog.store import get as get_item
from labforge.contracts import validate

DEFAULT_LOW, DEFAULT_HIGH = 0.85, 1.25


def topo_order(steps: list[dict]) -> list[dict]:
    done, order, pending = set(), [], list(steps)
    while pending:
        ready = [s for s in pending if set(s.get("after", [])) <= done]
        if not ready:
            raise ValueError("Workflow has a dependency cycle.")
        for s in ready:
            order.append(s)
            done.add(s["id"])
            pending.remove(s)
    return order


def sample_duration(step: dict, rng: random.Random) -> float:
    v = step["duration_s"]
    u = step.get("duration_uncertainty")
    low, high = (u.get("low", v), u.get("high", v)) if u else (v * DEFAULT_LOW, v * DEFAULT_HIGH)
    return rng.triangular(low, high, v) if high > low else v


def run_once(workflow: dict, layout: dict, hours: float, rng: random.Random, record: bool = False,
             capacity_overrides: dict[str, int] | None = None):
    env = simpy.Environment()
    steps = topo_order(workflow["steps"])
    caps = {e["instance_id"]: get_item(e["catalog_id"]).get("process", {}).get("capacity", 1) for e in workflow["equipment"]}
    caps.update(capacity_overrides or {})
    res = {i: simpy.Resource(env, capacity=c) for i, c in caps.items()}
    for op in layout.get("operators", []):
        res[op["id"]] = simpy.Resource(env, capacity=1)
    moves = {(t["from_instance"], t["to_instance"]): t for t in layout["transfers"]}
    busy, waits, timeline, finished = defaultdict(float), defaultdict(list), [], []
    wip_limit = max(2, sum(caps.values()))
    wip = simpy.Container(env, init=wip_limit, capacity=wip_limit)

    def log(t, lw, event, inst=None, step=None):
        if record and len(timeline) < 500:
            e = {"t_s": round(t, 1), "labware_id": lw, "event": event}
            if inst:
                e["instance_id"] = inst
            if step:
                e["step_id"] = step
            timeline.append(e)

    def labware(n):
        lw, here, start = f"plate_{n:04d}", None, env.now
        for step in steps:
            cands = step["candidate_instances"]
            if not cands:  # in silico or external
                yield env.timeout(sample_duration(step, rng))
                continue
            inst = min(cands, key=lambda c: len(res[c].queue) + res[c].count / caps.get(c, 1))
            if here and here != inst and (here, inst) in moves:
                mv = moves[(here, inst)]
                via = mv["transporter_instance"]
                with res[via].request() as req:
                    yield req
                    log(env.now, lw, "transfer_start", via)
                    dt = mv.get("est_time_s", 30.0)
                    yield env.timeout(dt)
                    busy[via] += dt
            queued = env.now
            with res[inst].request() as req:
                yield req
                waits[inst].append(env.now - queued)
                log(env.now, lw, "step_start", inst, step["id"])
                dt = sample_duration(step, rng)
                yield env.timeout(dt)
                busy[inst] += dt
                log(env.now, lw, "step_end", inst, step["id"])
            here = inst
        finished.append(env.now - start)
        yield wip.put(1)

    def source():
        n = 0
        while True:
            yield wip.get(1)
            env.process(labware(n))
            n += 1

    env.process(source())
    env.run(until=hours * 3600)
    total = hours * 3600
    util = {i: busy[i] / (total * caps.get(i, 1)) for i in res}
    return len(finished), finished, util, waits, timeline


def simulate(spec: dict, workflow: dict, layout: dict, hours: float = 72, replicates: int = 20, seed: int = 0,
             capacity_overrides: dict[str, int] | None = None) -> dict:
    rng = random.Random(seed)
    per_day = spec["throughput_target"].get("operating_hours_per_day", 24)
    target = spec["throughput_target"]["value"]
    runs = [run_once(workflow, layout, hours, rng, record=(k == 0), capacity_overrides=capacity_overrides) for k in range(replicates)]
    tputs = sorted(r[0] / hours * per_day for r in runs)
    q = statistics.quantiles(tputs, n=10, method="inclusive") if len(tputs) > 1 else tputs * 9
    util = {i: statistics.mean(r[2][i] for r in runs) for i in runs[0][2]}
    waits = {i: statistics.mean(w) for i, w in runs[0][3].items() if w}
    cycle = [c for r in runs for c in r[1]]

    bottlenecks = []
    for inst, u in sorted(util.items(), key=lambda kv: -kv[1]):
        if u > 0.7:
            is_mover = any(t["transporter_instance"] == inst for t in layout["transfers"])
            bottlenecks.append({
                "kind": "transporter_capacity" if is_mover else "instrument_capacity",
                "instances": [inst], "severity": "high" if u > 0.85 else "medium",
                "message": f"{inst} is busy {u:.0%} of the time.",
                "suggestion": "Add a parallel unit or move slow steps elsewhere."})
    for t in layout["transfers"]:
        if t["distance_m"] > 5:
            bottlenecks.append({"kind": "long_transfer", "instances": [t["from_instance"], t["to_instance"]], "severity": "medium",
                                "message": f"Labware travels {t['distance_m']} m from {t['from_instance']} to {t['to_instance']}."})

    result = {
        "id": f"{layout['id']}_sim",
        "layout_id": layout["id"],
        "simulated_hours": hours,
        "replicates": replicates,
        "throughput": {"value": round(statistics.median(tputs), 1), "unit": spec["throughput_target"]["unit"],
                       "target": target, "meets_target": statistics.median(tputs) >= target,
                       "p10": round(q[0], 1), "p50": round(statistics.median(tputs), 1), "p90": round(q[-1], 1),
                       "prob_meets_target": round(sum(t >= target for t in tputs) / len(tputs), 2)},
        "cycle_time_s": round(statistics.mean(cycle), 1) if cycle else 0,
        "utilisation": [{"instance_id": i, "busy_fraction": round(min(u, 1.0), 3), "mean_queue_wait_s": round(waits.get(i, 0.0), 1)}
                        for i, u in util.items()],
        "bottlenecks": bottlenecks,
        "sensitivity": [],
        "timeline": runs[0][4],
    }
    return validate(result, "sim_result")
