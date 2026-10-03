"""Strand D: which equipment needs which safety zone, and the zones drawn around it. Owner: Maxim.

Rules come from catalog/data/safety_rules.json (strand B). Hazards per instrument come from the
catalog's `safety` fields and, when the catalog is silent, are inferred from the spec's hazards
and the capabilities the instrument runs in this workflow (marked "inferred" in messages).
"""
import json
import math
from pathlib import Path

RULES_PATH = Path(__file__).resolve().parents[1] / "catalog" / "data" / "safety_rules.json"
DEFAULT_RULES = {
    "zone_requirements": {"flammable_solvents": ["fume_hood", "ventilated"], "toxic_reagents": ["fume_hood"],
                          "cryogens": ["cryogen"], "biohazard": ["bsl2"]},
    "min_walkway_width_m": 1.0,
    "min_egress_width_m": 1.2,
    "human_robot_separation_m": 0.5,
}
# Used only if safety_rules.json has no "capability_hazards": which capabilities handle a spec hazard.
FALLBACK_CAPABILITY_HAZARDS = {
    "flammable_solvents": ["reaction", "heating_stirring", "evaporation", "liquid_dosing", "powder_dosing", "filtration",
                           "solid_phase_extraction", "inert_atmosphere", "ventilated_enclosure"],
    "toxic_reagents": ["reaction", "powder_dosing", "liquid_dosing"],
    "cryogens": ["cryo_cooling"],
    "biohazard": ["cell_culture", "bioreactor", "cell_lysis", "colony_picking", "centrifugation"],
}
INHERENT = {"cryo_cooling": "cryogens"}  # hazards a capability always brings, whatever the spec says
# Catalog hazards that depend on what is being handled: a liquid handler is only a biohazard in a lab that
# handles biohazards. Others (cryogens, high-g, lasers) belong to the equipment and always apply.
USAGE_HAZARDS = {"biohazard", "toxic_reagents", "flammable_solvents"}
# Equipment that is itself the containment does not need to sit inside one. The catalog's
# safety.provides_zone says what an item provides; this capability map is only a fallback.
PROVIDES = {"ventilated_enclosure": {"fume_hood", "ventilated"}}
# A sealed inert enclosure (glovebox) contains toxic or flammable work at least as well as a fume hood.
CONTAINS = {"inert": {"fume_hood", "ventilated"}}


def provided_zones(item: dict) -> tuple[set[str], set[str]]:
    """(zones the item provides, zones its contents are contained as if in) for its own work."""
    stated = (item.get("safety") or {}).get("provides_zone")
    direct = set(stated) if stated is not None else set().union(*[PROVIDES.get(c, set()) for c in item.get("capabilities", [])])
    return direct, direct.union(*[CONTAINS.get(z, set()) for z in direct])


def load_rules() -> dict:
    rules = dict(DEFAULT_RULES)
    try:
        rules.update({k: v for k, v in json.loads(RULES_PATH.read_text()).items() if not k.startswith("_")})
    except (OSError, ValueError):
        pass
    return rules


def instance_capabilities(workflow: dict) -> dict[str, set[str]]:
    caps = {e["instance_id"]: set() for e in workflow["equipment"]}
    for s in workflow["steps"]:
        for c in s["candidate_instances"]:
            caps.setdefault(c, set()).add(s["capability"])
    return caps


def zone_needs(spec: dict, workflow: dict, items: dict[str, dict], rules: dict) -> dict[str, list[tuple[set[str], str]]]:
    """inst -> [(acceptable zone kinds, reason)]; every entry must be met by a zone the item sits in."""
    constraints = spec.get("constraints") or {}
    spec_hazards = set(constraints.get("hazards", []))
    if (constraints.get("biosafety_level") or 1) >= 2:
        spec_hazards.add("biohazard")
    cap_hazards = rules.get("capability_hazards", FALLBACK_CAPABILITY_HAZARDS)
    req = rules["zone_requirements"]
    used = instance_capabilities(workflow)
    needs = {}
    for inst, item in items.items():
        if (item.get("transport") or {}).get("kind"):
            continue
        safety = item.get("safety") or {}
        direct, contained = provided_zones(item)
        out = []
        if safety.get("requires_zone") and not set(safety["requires_zone"]) & direct:
            out.append((set(safety["requires_zone"]), f"catalog: {item['id']} requires {'/'.join(safety['requires_zone'])}"))
        hazards = {h: "catalog" for h in safety.get("hazards", []) if h not in USAGE_HAZARDS or h in spec_hazards}
        for cap in used.get(inst, ()):
            if cap in INHERENT:
                hazards.setdefault(INHERENT[cap], f"inferred: {cap} uses {INHERENT[cap].replace('_', ' ')}")
            for hz in spec_hazards:
                if cap in cap_hazards.get(hz, []):
                    hazards.setdefault(hz, f"inferred: {cap} with {hz.replace('_', ' ')} in the brief")
        for hz, why in hazards.items():
            if hz in req:
                out.append((set(req[hz]), why if why != "catalog" else f"catalog: {item['id']} has {hz.replace('_', ' ')}"))
        out = [(ok, why) for ok, why in out if why.startswith("catalog: " + item["id"] + " requires") or not ok & contained]
        if out:
            needs[inst] = out
    return needs


def door_box(door: dict, width: float, depth: float, size: float = 1.2) -> tuple[float, float, float, float]:
    """Square of floor inside the door that must stay clear for egress."""
    x, y, h = door["x"], door["y"], size / 2
    wall = min((x, "w"), (width - x, "e"), (y, "s"), (depth - y, "n"))[1]
    if wall == "w":
        return 0.0, y - h, size, y + h
    if wall == "e":
        return width - size, y - h, width, y + h
    if wall == "s":
        return x - h, 0.0, x + h, size
    return x - h, depth - size, x + h, depth


def choose_kinds(sets: list[set[str]]) -> list[str]:
    """Fewest zone kinds that meet every need (greedy hitting set); zones of different kinds may overlap."""
    open_sets, kinds = [set(x) for x in sets], []
    while open_sets:
        kind = choose_kind(open_sets)
        kinds.append(kind)
        open_sets = [x for x in open_sets if kind not in x]
    return kinds


def choose_kind(sets: list[set[str]]) -> str:
    counts = {}
    for s in sets:
        for k in s:
            counts[k] = counts.get(k, 0) + 1
    first = [k for s in sets for k in sorted(s)]
    return max(first, key=lambda k: (counts[k], -first.index(k)))


def derive_zones(placements: dict[str, dict], items: dict[str, dict], zone_kinds: dict[str, list[str]],
                 width: float, depth: float, margin: float = 0.3) -> list[dict]:
    """One enclosure per hazard group: the members' footprints plus a margin, merged when they touch."""
    from labforge.layout.geometry import aabb
    boxes = {}
    for inst, kinds in zone_kinds.items():
        if inst not in placements:
            continue
        x0, y0, x1, y1 = aabb(placements[inst], items[inst])
        for kind in ([kinds] if isinstance(kinds, str) else kinds):
            boxes.setdefault(kind, []).append([max(0.0, x0 - margin), max(0.0, y0 - margin),
                                               min(width, x1 + margin), min(depth, y1 + margin)])
    zones = []
    for kind in sorted(boxes):
        merged = boxes[kind]
        changed = True
        while changed:
            changed = False
            for i in range(len(merged)):
                for j in range(i + 1, len(merged)):
                    if _overlaps(merged[i], merged[j]):
                        a, b = merged[i], merged.pop(j)
                        merged[i] = [min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])]
                        changed = True
                        break
                if changed:
                    break
        for n, z in enumerate(merged, 1):
            zones.append({"id": f"{kind}_{n}", "kind": kind, "min": {"x": round(z[0], 3), "y": round(z[1], 3)},
                          "max": {"x": round(z[2], 3), "y": round(z[3], 3)}})
    return zones


def _overlaps(a: tuple, b: tuple) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]
