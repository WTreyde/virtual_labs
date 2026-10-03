"""Vendor optimisation: how would this lab's throughput change if one instrument were better? Owner: Maxim.

For one equipment instance, sweep a spec (cycle time, parallel capacity) through the Monte Carlo
simulator with the same random seed at every point (common random numbers, so differences are
the spec change and not noise). Reports elasticity near baseline and which instrument becomes the
bottleneck next, i.e. how much headroom an improvement actually buys in this setup.

TODO(Maxim): transfer_time and uptime sweeps; run points in parallel on Modal.
"""
import copy

from labforge.contracts import validate
from labforge.sim.simulate import simulate

CYCLE_FACTORS = (0.5, 0.7, 0.85, 1.0, 1.2)


def _scaled(workflow: dict, instance_id: str, factor: float) -> dict:
    wf = copy.deepcopy(workflow)
    for step in wf["steps"]:
        if instance_id in step["candidate_instances"]:
            step["duration_s"] *= factor
            u = step.get("duration_uncertainty")
            if u:
                for k in ("value", "low", "high"):
                    if k in u:
                        u[k] *= factor
    return wf


def _point(value: float, sim: dict) -> dict:
    t = sim["throughput"]
    return {"value": value, "throughput_p50": t["p50"], "throughput_p10": t["p10"], "throughput_p90": t["p90"]}


def _busiest_other(sim: dict, instance_id: str) -> str | None:
    others = [u for u in sim["utilisation"] if u["instance_id"] != instance_id]
    return max(others, key=lambda u: u["busy_fraction"])["instance_id"] if others else None


def optimise_instrument(spec: dict, workflow: dict, layout: dict, instance_id: str,
                        hours: float = 48, replicates: int = 8, seed: int = 0) -> dict:
    catalog_id = next(e["catalog_id"] for e in workflow["equipment"] if e["instance_id"] == instance_id)
    run = lambda wf, caps=None: simulate(spec, wf, layout, hours=hours, replicates=replicates, seed=seed,
                                         sensitivity=False, capacity_overrides=caps)

    base = run(workflow)
    base_tp = base["throughput"]["p50"]
    base_util = next((u["busy_fraction"] for u in base["utilisation"] if u["instance_id"] == instance_id), None)

    cycle_sims = {f: (base if f == 1.0 else run(_scaled(workflow, instance_id, f))) for f in CYCLE_FACTORS}
    cycle_points = [_point(f, s) for f, s in cycle_sims.items()]
    tp_085 = cycle_sims[0.85]["throughput"]["p50"]
    elasticity = round(((tp_085 - base_tp) / base_tp) / 0.15, 2) if base_tp else 0.0

    from labforge.catalog.store import get as get_item
    slots = get_item(catalog_id).get("process", {}).get("capacity", 1)
    cap_points = [_point(slots + extra, base if extra == 0 else run(workflow, {instance_id: slots + extra})) for extra in (0, 1, 2)]

    fastest = cycle_sims[min(CYCLE_FACTORS)]
    gain = fastest["throughput"]["p50"] / base_tp - 1 if base_tp else 0.0
    nxt = _busiest_other(fastest, instance_id)
    if elasticity < 0.1:
        note = f"Making {instance_id} faster barely helps here (elasticity {elasticity}); it is not the limiting instrument in this lab."
    else:
        util = {u["instance_id"]: u["busy_fraction"] for u in fastest["utilisation"]}
        still_limit = util.get(instance_id, 0) >= util.get(nxt, 0)
        after = f"{instance_id} is still the bottleneck, so further gains are possible" if still_limit else f"after that {nxt} becomes the limit"
        note = f"Halving {instance_id}'s cycle time raises throughput {gain:.0%}; {after}."
        if still_limit:
            nxt = None

    result = {
        "instance_id": instance_id, "catalog_id": catalog_id, "layout_id": layout["id"],
        "baseline": {"throughput_p50": base_tp, "unit": base["throughput"]["unit"], "utilisation": base_util},
        "sweeps": [
            {"parameter": "cycle_time", "points": cycle_points, "elasticity": elasticity},
            {"parameter": "capacity", "points": cap_points},
        ],
        "headroom_note": note,
    }
    if nxt:
        result["next_bottleneck"] = nxt
    return validate(result, "instrument_optimisation")
