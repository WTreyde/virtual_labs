"""Strand D: layout checks. Owner: Maxim.

Geometry (overlap, out of room, clearance, keep-out), transport (unreachable transfers), and
safety from catalog/data/safety_rules.json: hazard zones, a walkway from the door to every
place a person works, a clear door, and people kept out of non-collaborative arm envelopes.
"""
import math

from labforge.layout.geometry import Grid, aabb, arm_bases, human_spot, outside_area, overlap, overlap_area, world_point
from labforge.layout.safety import door_box, load_rules, zone_needs

ZONE_TOLERANCE_M2 = 0.01
GRID_SLACK_M = 0.05  # half a 0.1 m grid cell: a true 1.0 m aisle must not fail on rounding
OVERLAP_TOLERANCE_M2 = 1e-4


def find_violations(layout: dict, items: dict[str, dict], spec: dict | None = None, rules: dict | None = None,
                    zone_of: dict | None = None, workflow: dict | None = None) -> list[dict]:
    rules = rules or load_rules()
    out = []
    room = layout["room"]
    W, D = room["width_m"], room["depth_m"]
    pl = {p["instance_id"]: p for p in layout["placements"]}
    solid = [i for i in pl if i in items and (items[i].get("transport") or {}).get("kind") != "human"]
    boxes = {i: aabb(pl[i], items[i]) for i in solid}
    pads = {i: aabb(pl[i], items[i], clearance=True) for i in solid}
    movers = {i for i in solid if (items[i].get("transport") or {}).get("kind")}

    for inst, (x0, y0, x1, y1) in boxes.items():
        if x0 < -1e-6 or y0 < -1e-6 or x1 > W + 1e-6 or y1 > D + 1e-6:
            out.append({"kind": "out_of_room", "instances": [inst], "message": f"{inst} sticks out of the room."})
    for k, a in enumerate(solid):
        for b in solid[k + 1:]:
            if overlap_area(boxes[a], boxes[b]) > OVERLAP_TOLERANCE_M2:  # touching after mm rounding is not a collision
                out.append({"kind": "overlap", "instances": [a, b], "message": f"{a} and {b} overlap."})
            elif a not in movers and b not in movers and \
                    overlap_area(pads[a], boxes[b]) + overlap_area(boxes[a], pads[b]) > ZONE_TOLERANCE_M2:
                out.append({"kind": "clearance", "instances": [a, b],
                            "message": f"{a} and {b} are closer than their service clearance."})
    for z in (spec or {}).get("room", {}).get("keep_out_zones", []):
        zb = (z["min"]["x"], z["min"]["y"], z["max"]["x"], z["max"]["y"])
        for inst in solid:
            if overlap(boxes[inst], zb):
                out.append({"kind": "keep_out", "instances": [inst],
                            "message": f"{inst} is in a keep-out area ({z.get('reason', 'no reason given')})."})
    for t in layout["transfers"]:
        if t["transporter_instance"] == "unassigned":
            out.append({"kind": "unreachable_transfer", "instances": [t["from_instance"], t["to_instance"]],
                        "message": f"No robot or operator can move labware from {t['from_instance']} to {t['to_instance']}."})

    if spec is not None and workflow is not None:
        out += _zone_violations(layout, items, spec, workflow, rules, boxes)
    if spec is not None:
        out += _egress_violations(layout, items, spec, rules, pl, boxes, workflow)
    out += _separation_violations(layout, items, rules, pl, movers)
    return out


def _zone_violations(layout, items, spec, workflow, rules, boxes) -> list[dict]:
    out = []
    zones = [(z["kind"], (z["min"]["x"], z["min"]["y"], z["max"]["x"], z["max"]["y"])) for z in layout.get("zones", [])]
    for inst, sets in zone_needs(spec, workflow, items, rules).items():
        if inst not in boxes:
            continue
        inside = {kind for kind, zb in zones if outside_area(boxes[inst], zb) <= ZONE_TOLERANCE_M2}
        for ok, why in sets:
            if not inside & ok:
                out.append({"kind": "zone_mismatch", "instances": [inst],
                            "message": f"{inst} must sit in a {' or '.join(sorted(ok)).replace('_', ' ')} zone ({why})."})
    return out


def _egress_violations(layout, items, spec, rules, pl, boxes, workflow) -> list[dict]:
    out = []
    W, D = layout["room"]["width_m"], layout["room"]["depth_m"]
    doors = spec["room"].get("doors") or []
    assumed = not doors
    doors = doors or [{"x": 0.0, "y": D / 2}]
    note = " (no door given; assumed one mid-way along the x=0 wall)" if assumed else ""
    egress = rules.get("min_egress_width_m", 1.2)
    for d in doors:
        db = door_box(d, W, D, egress)
        blocking = [i for i, b in boxes.items() if overlap(b, db)]
        if blocking:
            out.append({"kind": "egress_blocked", "instances": blocking,
                        "message": f"{', '.join(blocking)} block the door at ({d['x']}, {d['y']}){note}."})

    # People work at instruments they load, unload, run by hand or carry labware between.
    operators = {o["id"] for o in layout.get("operators", [])}
    touched = set()
    for t in layout["transfers"]:
        if t["transporter_instance"] in operators:
            touched |= {t["from_instance"], t["to_instance"]}
    for s in (workflow or {}).get("steps", []):
        if s.get("mode") in ("manual", "semi_automated"):
            touched |= set(s["candidate_instances"])
    touched &= set(boxes)
    if not touched:
        return out
    walkway = rules.get("min_walkway_width_m", 1.0)
    arms = arm_bases(pl, items)
    spots = {inst: human_spot(pl[inst], items[inst], arms) for inst in touched}
    cut_off, _ = walkway_unreachable(W, D, list(boxes.values()), spots, doors[0], walkway)
    if cut_off is None:
        out.append({"kind": "egress_blocked", "instances": sorted(touched),
                    "message": f"No {walkway} m walkway leads in from the door{note}."})
        return out
    for inst in cut_off:
        out.append({"kind": "egress_blocked", "instances": [inst],
                    "message": f"No {walkway} m walkway from the door to where someone works at {inst}{note}."})
    return out


def walkway_unreachable(width: float, depth: float, boxes: list[tuple], spots: dict[str, tuple[float, float]],
                        door: dict, walkway: float) -> tuple[list[str] | None, list[tuple[float, float]]]:
    """(work spots a `walkway`-wide path from the door cannot reach, pinch points where that path narrows).

    None instead of a list means no such path enters the room at all. Pinch points are where a slightly
    narrower path gets through but the full width does not: moving equipment there opens the route."""
    grid = Grid(width, depth, boxes)
    db = door_box(door, width, depth, 0.6)
    start = ((db[0] + db[2]) / 2, (db[1] + db[3]) / 2)
    need = walkway / 2 - GRID_SLACK_M
    reach = grid.reachable(start, need)
    if not reach:
        return None, [start]
    centres = [grid.centre(*c) for c in reach]
    cut_off = sorted(i for i, (sx, sy) in spots.items()
                     if not any(math.hypot(cx - sx, cy - sy) <= walkway / 2 + 0.5 for cx, cy in centres))
    pinches = []
    if cut_off:
        clear = grid.clearance()
        narrow = grid.reachable(start, max(0.2, need - 0.25)) - reach
        pinches = [grid.centre(*c) for c in narrow if clear[c[0]][c[1]] < need
                   and any((c[0] + di, c[1] + dj) in reach for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)))]
    return cut_off, pinches


def _separation_violations(layout, items, rules, pl, movers) -> list[dict]:
    """People must not reach into a non-collaborative arm's envelope (reach + separation) to hand over labware."""
    out = []
    operators = {o["id"] for o in layout.get("operators", [])}
    sep = rules.get("human_robot_separation_m", 0.5)
    human_spots = {}
    for t in layout["transfers"]:
        if t["transporter_instance"] in operators:
            for inst in (t["from_instance"], t["to_instance"]):
                if inst in pl and inst in items:
                    human_spots[inst] = world_point(pl[inst], items[inst]["access_points"][0]["position"])[:2]
    for arm in sorted(movers):
        item = items[arm]
        if item["transport"].get("kind") != "arm" or (item.get("safety") or {}).get("collaborative"):
            continue
        base = pl[arm]["position"]
        envelope = item["transport"].get("reach_m", 1.0) + sep
        inside = sorted(i for i, (x, y) in human_spots.items() if math.hypot(x - base["x"], y - base["y"]) < envelope)
        if inside:
            rated = "is not rated collaborative" if "collaborative" in (item.get("safety") or {}) else \
                "has no collaborative rating in the catalog"
            out.append({"kind": "safety", "instances": [arm] + inside,
                        "message": f"People hand labware into {arm}'s reach at {', '.join(inside)}, and {arm} {rated}; "
                                   "add a light curtain or a pass-through hotel at the cell edge."})
    return out
