"""Strand D helpers shared by placer and validator. Owner: Maxim."""
import math


def world_point(placement: dict, local: dict) -> tuple[float, float, float]:
    """Transform an item-local point (e.g. an access point) into room coordinates."""
    phi = math.radians(placement["rotation_deg"])
    x, y = local["x"], local["y"]
    p = placement["position"]
    return (
        p["x"] + x * math.cos(phi) - y * math.sin(phi),
        p["y"] + x * math.sin(phi) + y * math.cos(phi),
        p["z"] + local.get("z", 0.0),
    )


def aabb(placement: dict, item: dict, clearance: bool = False) -> tuple[float, float, float, float]:
    """Axis-aligned bounding box (xmin, ymin, xmax, ymax) of a rotated footprint."""
    fp = item["footprint"]
    pad = fp.get("clearance_m", 0.3) if clearance else 0.0
    w, d = fp["width_m"] / 2 + pad, fp["depth_m"] / 2 + pad
    corners = [world_point(placement, {"x": sx * w, "y": sy * d}) for sx in (-1, 1) for sy in (-1, 1)]
    xs, ys = [c[0] for c in corners], [c[1] for c in corners]
    return min(xs), min(ys), max(xs), max(ys)


def overlap(a: tuple, b: tuple) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]
