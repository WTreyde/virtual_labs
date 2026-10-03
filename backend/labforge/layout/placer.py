"""Strand D: place equipment in the room. Owner: Maxim.

v0 baseline: put the first arm in the middle of the room and arrange instruments in a ring
around it with their access points facing the arm. Anything the arm cannot serve falls back
to a human operator. TODO(Maxim): greedy clustering per transporter + simulated annealing on
weighted transfer distance, zones from safety_rules.json, locked placements from the UI.
"""
import math

from labforge.catalog.store import get as get_item
from labforge.contracts import validate
from labforge.layout.geometry import world_point
from labforge.layout.validate import find_violations

BENCH_HEIGHT_M = 0.9
HUMAN_SPEED_M_S = 1.0
HUMAN_PICK_PLACE_S = 15.0


def transfer_edges(workflow: dict) -> list[tuple[str, str]]:
    """Pairs of equipment instances that hand labware to each other, from step dependencies.

    Labware waits in place during an instrument-less in-silico step (e.g. crystal scoring), so the
    edge skips over it; after an external step (synchrotron) nothing comes back to move.
    """
    steps = {s["id"]: s for s in workflow["steps"]}

    def sources(step_id: str) -> list[str]:
        s = steps[step_id]
        if s["candidate_instances"]:
            return s["candidate_instances"]
        if s.get("mode") == "external":
            return []
        return [i for p in s.get("after", []) for i in sources(p)]

    edges = []
    for step in workflow["steps"]:
        for prev_id in step.get("after", []):
            for a in sources(prev_id):
                for b in step["candidate_instances"]:
                    if a != b and (a, b) not in edges:
                        edges.append((a, b))
    return edges


def generate_layout(spec: dict, workflow: dict) -> dict:
    room = spec["room"]
    items = {e["instance_id"]: get_item(e["catalog_id"]) for e in workflow["equipment"]}
    arms = [i for i, it in items.items() if it.get("transport", {}).get("kind") == "arm"]
    others = [i for i in items if i not in arms]

    centre = {"x": room["width_m"] / 2, "y": room["depth_m"] / 2}
    placements = {}
    for k, arm in enumerate(arms):
        placements[arm] = {"instance_id": arm, "rotation_deg": 0,
                           "position": {"x": centre["x"] + 2.5 * k, "y": centre["y"], "z": BENCH_HEIGHT_M}}

    reach = items[arms[0]]["transport"]["reach_m"] if arms else 1.5
    for k, inst in enumerate(others):
        theta = 2 * math.pi * k / max(len(others), 1)
        ap = items[inst]["access_points"][0]["position"]
        ap_r = math.hypot(ap["x"], ap["y"])
        alpha = math.atan2(ap["y"], ap["x"]) if ap_r else 0.0
        r = 0.8 * reach + ap_r
        z = 0.0 if items[inst]["footprint"].get("mount") == "floor" else BENCH_HEIGHT_M
        placements[inst] = {"instance_id": inst, "rotation_deg": round(math.degrees(theta + math.pi - alpha) % 360, 1),
                            "position": {"x": round(centre["x"] + r * math.cos(theta), 3),
                                         "y": round(centre["y"] + r * math.sin(theta), 3), "z": z}}

    operators = [{"id": f"{op['role']}_{n + 1}", "role": op["role"], "home": (room.get("doors") or [{"x": 0.5, "y": 0.5}])[0]}
                 for op in spec.get("operators", []) for n in range(op["count"])]

    transfers = []
    for a, b in transfer_edges(workflow):
        pa = world_point(placements[a], items[a]["access_points"][0]["position"])
        pb = world_point(placements[b], items[b]["access_points"][0]["position"])
        arm = next((m for m in arms if all(math.dist(p[:2], _xy(placements[m])) <= items[m]["transport"]["reach_m"] for p in (pa, pb))), None)
        if arm:
            base = (*_xy(placements[arm]), placements[arm]["position"]["z"] + 0.3)
            dist = math.dist(pa, base) + math.dist(base, pb)
            t = items[arm]["transport"]
            transfers.append(_transfer(a, b, arm, dist, t["pick_place_s"] + dist / t["speed_m_s"], [pa, base, pb]))
        elif operators:
            dist = abs(pa[0] - pb[0]) + abs(pa[1] - pb[1])
            corner = (pb[0], pa[1], pa[2])
            transfers.append(_transfer(a, b, operators[0]["id"], dist, HUMAN_PICK_PLACE_S + dist / HUMAN_SPEED_M_S, [pa, corner, pb]))
        else:
            transfers.append(_transfer(a, b, "unassigned", math.dist(pa, pb), None, [pa, pb]))

    layout = {
        "id": f"{workflow['id']}_layout",
        "workflow_id": workflow["id"],
        "room": {k: room[k] for k in ("width_m", "depth_m", "height_m") if k in room},
        "placements": list(placements.values()),
        "operators": operators,
        "transfers": transfers,
        "score": {"total_weighted_distance_m": round(sum(t["distance_m"] for t in transfers), 2)},
    }
    layout["violations"] = find_violations(layout, items)
    return validate(layout, "layout")


def _xy(placement: dict) -> tuple[float, float]:
    return placement["position"]["x"], placement["position"]["y"]


def _transfer(a, b, via, dist, time_s, path) -> dict:
    t = {"from_instance": a, "to_instance": b, "transporter_instance": via, "distance_m": round(dist, 2),
         "path": [{"x": round(p[0], 3), "y": round(p[1], 3), "z": round(p[2], 3)} for p in path]}
    if time_s is not None:
        t["est_time_s"] = round(time_s, 1)
    return t
