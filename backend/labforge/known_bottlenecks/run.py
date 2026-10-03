"""Does the simulator find the bottleneck the authors of real labs reported?

    cd backend && python -m labforge.known_bottlenecks.run
"""
import copy
import json
import os

from labforge.catalog import store
from labforge.known_bottlenecks.cases import CATALOG, all_cases
from labforge.sim import simulate as sim_mod

_LOCAL = {c["id"]: c for c in CATALOG}


def _use_local_catalog():
    """Point the simulator at this module's catalog without touching Strand B's cache.

    The simulator may import `load_catalog` by name, so patch it there too, and keep replicates in
    this process: worker processes or Modal would not see the patch.
    """
    get = lambda: _LOCAL
    store.load_catalog = get
    if hasattr(sim_mod, "load_catalog"):
        sim_mod.load_catalog = get
    os.environ["LABFORGE_SIM_BACKEND"] = "serial"


def check(case: dict, hours: float = 96, replicates: int = 20) -> dict:
    res = sim_mod.simulate(case["spec"], case["workflow"], case["layout"], hours=hours, replicates=replicates)
    util = sorted(res["utilisation"], key=lambda u: -u["busy_fraction"])
    top = util[0]["instance_id"]
    tp = res["throughput"]
    obs = case["observed"]["value"]
    if "crystals_per_plate" in case:  # report XChem in crystals per shift, like the paper
        k = case["crystals_per_plate"]
        tp = {key: round(tp[key] * k, 0) for key in ("p10", "p50", "p90")}
    out = {
        "case": case["title"],
        "reported_bottleneck": case["reported_bottleneck"],
        "simulated_bottleneck": top,
        "match": top == case["reported_bottleneck"],
        "utilisation": {u["instance_id"]: u["busy_fraction"] for u in util},
        "throughput_sim_p10_p50_p90": [tp["p10"], tp["p50"], tp["p90"]],
        "throughput_observed": round(obs, 2),
        "unit": case["observed"]["unit"],
        "observed_in_band": tp["p10"] <= obs <= tp["p90"],
        "error_pct": round((tp["p50"] - obs) / obs * 100, 1),
        "note": case["observed"]["note"],
    }
    if "low" in case["observed"]:  # observed is itself a range: in band if the two ranges overlap
        out["throughput_observed_range"] = [round(case["observed"]["low"], 2), round(case["observed"]["high"], 2)]
        out["observed_in_band"] = tp["p10"] <= case["observed"]["high"] and case["observed"]["low"] <= tp["p90"]
    if "reported_bottleneck_steps" in case:
        # Which *time component* limits throughput: the step whose uncertainty moves throughput most.
        top = (res.get("sensitivity") or [{}])[0].get("parameter", "")
        out["most_sensitive_input"] = top
        out["match"] = out["match"] and top.split(".")[0] in case["reported_bottleneck_steps"]
        out["whatif"] = {label: _step_whatif(case, ids, hours, replicates) for label, ids in case.get("whatif_steps", {}).items()}
        out["whatif"]["baseline_p50"] = res["throughput"]["p50"]
    return out


def _step_whatif(case: dict, step_ids: list[str], hours: float, replicates: int, factor: float = 0.5) -> float:
    """Throughput P50 with the named steps (and their ranges) scaled by `factor`, same seeds as the baseline."""
    wf = copy.deepcopy(case["workflow"])
    for s in wf["steps"]:
        if s["id"] in step_ids:
            s["duration_s"] *= factor
            for k in ("low", "high"):
                if k in s.get("duration_uncertainty", {}):
                    s["duration_uncertainty"][k] *= factor
    res = sim_mod.simulate(case["spec"], wf, case["layout"], hours=hours, replicates=replicates, sensitivity=False)
    return res["throughput"]["p50"]


def main():
    _use_local_catalog()
    out = [check(c) for c in all_cases()]
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
