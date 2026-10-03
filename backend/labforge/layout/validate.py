"""Strand D: layout checks. Owner: Maxim. TODO: zones, clearances, egress (safety_rules.json)."""
from labforge.layout.geometry import aabb, overlap


def find_violations(layout: dict, items: dict[str, dict]) -> list[dict]:
    out = []
    room = layout["room"]
    boxes = {p["instance_id"]: aabb(p, items[p["instance_id"]]) for p in layout["placements"]}
    for inst, (x0, y0, x1, y1) in boxes.items():
        if x0 < 0 or y0 < 0 or x1 > room["width_m"] or y1 > room["depth_m"]:
            out.append({"kind": "out_of_room", "instances": [inst], "message": f"{inst} sticks out of the room."})
    ids = list(boxes)
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            if overlap(boxes[a], boxes[b]):
                out.append({"kind": "overlap", "instances": [a, b], "message": f"{a} and {b} overlap."})
    for t in layout["transfers"]:
        if t["transporter_instance"] == "unassigned":
            out.append({"kind": "unreachable_transfer", "instances": [t["from_instance"], t["to_instance"]],
                        "message": f"No robot or operator can move labware from {t['from_instance']} to {t['to_instance']}."})
    return out
