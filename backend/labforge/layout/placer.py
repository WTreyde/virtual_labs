"""Strand D: place equipment in the room. Owner: Maxim.

1. Transfer edges come from the workflow graph, weighted by labware flow (fan-out multiplies it).
2. Greedy start: each arm's ring is filled in workflow order, so a cluster is one stretch of the
   process; arms sit in a row away from the door; the rest line the walls near the door.
3. Simulated annealing on flow-weighted transfer time plus penalties (overlap, clearance, out of
   room, keep-out, blocked door, no floor to stand on where people work) and a pull that keeps
   each hazard group together. Rotations snap to 90 degrees: instruments face the arm that serves
   them, or the room. `locked` placements from a previous layout never move.
4. Zones (fume hood / ventilated enclosure, BSL2, cryogen) are drawn around the instruments that
   need them (catalog safety fields, safety_rules.json, or the spec's hazards).
5. Each transfer goes to the fastest transporter that reaches both access points: arm or rail,
   then mobile robot, then a human operator walking an A* path around the equipment.
"""
import math
import random

from labforge.catalog.store import load_catalog
from labforge.contracts import validate
from labforge.layout.geometry import (Grid, aabb, area, arm_bases, human_spot, outside_area, overlap_area,
                                      polyline_length, world_point)
from labforge.layout.safety import choose_kind, derive_zones, door_box, load_rules, zone_needs
from labforge.layout.validate import find_violations

BENCH_HEIGHT_M = 0.9
HUMAN_SPEED_M_S = 1.0
HUMAN_PICK_PLACE_S = 15.0
UNASSIGNED_PENALTY_S = 900.0
PLACEHOLDER_ITEM = {  # geometry for catalog ids the catalog does not have (yet); flagged as placeholder
    "id": "placeholder", "vendor": "unknown", "model": "unknown", "category": "instrument", "capabilities": ["manual_bench"],
    "footprint": {"width_m": 0.8, "depth_m": 0.7, "height_m": 0.8, "clearance_m": 0.3, "mount": "bench"},
    "access_points": [{"id": "front", "position": {"x": 0.0, "y": -0.35, "z": 0.1}}], "data_confidence": "placeholder",
}
W_OVERLAP, W_ROOM, W_KEEP_OUT, W_DOOR, W_CLEARANCE, W_ACCESS, W_COHESION = 2e4, 2e4, 2e4, 1e4, 300, 500, 30


def transfer_edges(workflow: dict) -> list[tuple[str, str]]:
    """Pairs of equipment instances that hand labware to each other, from step dependencies.

    Labware waits in place during an instrument-less in-silico step (e.g. crystal scoring), so the
    edge skips over it; after an external step (synchrotron) nothing comes back to move.
    """
    return list(edge_weights(workflow))


def edge_weights(workflow: dict) -> dict[tuple[str, str], float]:
    """Labware units moved along each instance pair per unit released at the start, split over parallel units."""
    steps = {s["id"]: s for s in workflow["steps"]}
    order = _topo(workflow["steps"])
    flow_in = {}
    for s in order:
        preds = s.get("after", [])
        flow_in[s["id"]] = max([flow_in[p] * steps[p].get("fan_out", 1) for p in preds], default=1.0)

    def sources(step_id: str, flow: float) -> list[tuple[str, float]]:
        s = steps[step_id]
        if s["candidate_instances"]:
            return [(c, flow / len(s["candidate_instances"])) for c in s["candidate_instances"]]
        if s.get("mode") == "external":
            return []
        return [x for p in s.get("after", []) for x in sources(p, flow)]

    weights = {}
    for s in order:
        for p in s.get("after", []):
            moved = flow_in[p] * steps[p].get("fan_out", 1)
            for a, wa in sources(p, moved):
                for b in s["candidate_instances"]:
                    if a != b:
                        weights[(a, b)] = weights.get((a, b), 0.0) + wa / len(s["candidate_instances"])
    return weights


def _topo(steps: list[dict]) -> list[dict]:
    done, order, pending = set(), [], list(steps)
    while pending:
        ready = [s for s in pending if set(s.get("after", [])) <= done]
        if not ready:
            raise ValueError("Workflow has a dependency cycle or depends on a missing step.")
        for s in ready:
            order.append(s)
            done.add(s["id"])
            pending.remove(s)
    return order


def resolve_items(workflow: dict) -> dict[str, dict]:
    catalog = load_catalog()
    return {e["instance_id"]: catalog.get(e["catalog_id"], PLACEHOLDER_ITEM) for e in workflow["equipment"]}


def _kind(item: dict) -> str | None:
    return (item.get("transport") or {}).get("kind")


class Placer:
    def __init__(self, spec: dict, workflow: dict, previous: dict | None, seed: int):
        self.spec, self.workflow, self.rng = spec, workflow, random.Random(seed)
        room = spec["room"]
        self.W, self.D = room["width_m"], room["depth_m"]
        self.room_box = (0.0, 0.0, self.W, self.D)
        self.doors = room.get("doors") or [{"x": 0.0, "y": self.D / 2}]
        self.door_boxes = [door_box(d, self.W, self.D) for d in self.doors]
        self.keep_out = [(z["min"]["x"], z["min"]["y"], z["max"]["x"], z["max"]["y"]) for z in room.get("keep_out_zones", [])]
        self.items = resolve_items(workflow)
        self.weights = edge_weights(workflow)
        self.rules = load_rules()
        needs = zone_needs(spec, workflow, self.items, self.rules)
        self.zone_kind = {i: choose_kind([ok for ok, _ in sets]) for i, sets in needs.items()}
        self.zone_groups = {}
        for i, kind in self.zone_kind.items():
            self.zone_groups.setdefault(kind, []).append(i)
        self.arms = [i for i, it in self.items.items() if _kind(it) in ("arm", "rail")]
        self.mobiles = [i for i, it in self.items.items() if _kind(it) == "mobile"]
        self.humans = [i for i, it in self.items.items() if _kind(it) == "human"]
        self.placeable = [i for i in self.items if i not in self.humans]
        self.locked = {p["instance_id"]: p for p in (previous or {}).get("placements", [])
                       if p.get("locked") and p["instance_id"] in self.items}
        self.movable = [i for i in self.placeable if i not in self.locked]
        self.operators = self._operators()
        self.links = {i: {} for i in self.items}
        for (a, b), w in self.weights.items():
            self.links[a][b] = self.links[a].get(b, 0) + w
            self.links[b][a] = self.links[b].get(a, 0) + w
        steps_of = {i: [s for s in workflow["steps"] if i in s["candidate_instances"]] for i in self.items}
        self.hands_on = {i for i, ss in steps_of.items() if any(s.get("mode") in ("manual", "semi_automated") for s in ss)}
        self.manual_only = {i for i, ss in steps_of.items() if ss and all(s.get("mode") == "manual" for s in ss)}
        self.walkway = self.rules.get("min_walkway_width_m", 1.0)

    # ---------- people ----------
    def _operators(self) -> list[dict]:
        home = {"x": self.doors[0]["x"], "y": self.doors[0]["y"]}
        ops = [{"id": f"{op['role']}_{n + 1}", "role": op["role"], "home": dict(home)}
               for op in self.spec.get("operators", []) for n in range(op["count"])]
        if not ops:  # human operators chosen as catalog equipment instead of spec.operators
            ops = [{"id": h, "role": h, "home": dict(home)} for h in self.humans]
        return ops

    def _operator_for(self, b: str) -> str | None:
        if not self.operators:
            return None
        roles = [s.get("operator_role") for s in self.workflow["steps"] if b in s["candidate_instances"] and s.get("operator_role")]
        for role in roles:
            for op in self.operators:
                if op["role"] == role:
                    return op["id"]
        return self.operators[0]["id"]

    # ---------- geometry ----------
    def _z(self, inst: str) -> float:
        return 0.0 if self.items[inst]["footprint"].get("mount") == "floor" else BENCH_HEIGHT_M

    def _placement(self, inst: str, x: float, y: float, rot: float) -> dict:
        return {"instance_id": inst, "position": {"x": x, "y": y, "z": self._z(inst)}, "rotation_deg": rot}

    def _facing(self, inst: str, x: float, y: float, arm_xy: dict) -> float:
        """Rotation (multiple of 90) that points the item's access point at its nearest arm, else into the room."""
        item = self.items[inst]
        if inst in self.arms or _kind(item):
            return 0.0
        ap = item["access_points"][0]["position"]
        alpha = math.atan2(ap["y"], ap["x"]) if (ap["x"] or ap["y"]) else -math.pi / 2
        best, target = None, None
        for arm, (ax, ay) in (arm_xy.items() if inst not in self.manual_only and self.links[inst] else ()):
            d = math.hypot(ax - x, ay - y)
            if d <= self.items[arm]["transport"].get("reach_m", 1.0) + 0.6 and (best is None or d < best):
                best, target = d, (ax, ay)
        if target is None:
            walls = [(x, (1, 0)), (self.W - x, (-1, 0)), (y, (0, 1)), (self.D - y, (0, -1))]
            normal = min(walls)[1]
            target = (x + normal[0], y + normal[1])
        theta = math.atan2(target[1] - y, target[0] - x) - alpha
        return float(round(math.degrees(theta) / 90) * 90 % 360)

    def placements(self, state: dict[str, tuple[float, float]]) -> dict[str, dict]:
        arm_xy = {a: (self.locked[a]["position"]["x"], self.locked[a]["position"]["y"]) if a in self.locked else state[a]
                  for a in self.arms}
        out = {}
        for inst in self.placeable:
            if inst in self.locked:
                out[inst] = self.locked[inst]
            else:
                x, y = state[inst]
                out[inst] = self._placement(inst, x, y, self._facing(inst, x, y, arm_xy))
        return out

    # ---------- transport ----------
    def serve(self, a: str, b: str, pl: dict[str, dict]) -> tuple[str, float, float, str]:
        """(transporter, distance_m, time_s, how) for one transfer edge on placements `pl`."""
        pa = world_point(pl[a], self.items[a]["access_points"][0]["position"])
        pb = world_point(pl[b], self.items[b]["access_points"][0]["position"])
        best = None
        for arm in self.arms:
            t = self.items[arm]["transport"]
            base = pl[arm]["position"]
            reach = t.get("reach_m", 1.0)
            if _kind(self.items[arm]) == "rail":
                half = self.items[arm]["footprint"]["width_m"] / 2
                da, db = _seg_dist(pa, pl[arm], half), _seg_dist(pb, pl[arm], half)
                if da[0] <= reach and db[0] <= reach:
                    dist = da[0] + db[0] + abs(da[1] - db[1])
                    cand = (arm, dist, t.get("pick_place_s", 10) + dist / t.get("speed_m_s", 0.5), "rail")
                    best = min(best, cand, key=lambda c: c[2]) if best else cand
                continue
            if math.dist(pa[:2], (base["x"], base["y"])) <= reach and math.dist(pb[:2], (base["x"], base["y"])) <= reach:
                lift = (base["x"], base["y"], base["z"] + 0.3)
                dist = math.dist(pa, lift) + math.dist(lift, pb)
                cand = (arm, dist, t.get("pick_place_s", 8) + dist / t.get("speed_m_s", 0.5), "arm")
                best = min(best, cand, key=lambda c: c[2]) if best else cand
        if best:
            return best
        manhattan = abs(pa[0] - pb[0]) + abs(pa[1] - pb[1])
        if self.mobiles:
            t = self.items[self.mobiles[0]]["transport"]
            return self.mobiles[0], manhattan, 2 * t.get("pick_place_s", 20) + manhattan / t.get("speed_m_s", 1.0), "walk"
        op = self._operator_for(b)
        if op:
            return op, manhattan, HUMAN_PICK_PLACE_S + manhattan / HUMAN_SPEED_M_S, "walk"
        return "unassigned", math.dist(pa, pb), UNASSIGNED_PENALTY_S, "none"

    # ---------- cost ----------
    def cost(self, state: dict[str, tuple[float, float]]) -> float:
        pl = self.placements(state)
        boxes = {i: aabb(pl[i], self.items[i]) for i in self.placeable}
        pads = {i: aabb(pl[i], self.items[i], clearance=True) for i in self.placeable}
        c = 0.0
        ids = self.placeable
        for k, a in enumerate(ids):
            ba = boxes[a]
            c += W_ROOM * outside_area(ba, self.room_box)
            for z in self.keep_out:
                c += W_KEEP_OUT * overlap_area(ba, z)
            if a not in self.arms:
                for d in self.door_boxes:
                    c += W_DOOR * overlap_area(ba, d)
            for b in ids[k + 1:]:
                c += W_OVERLAP * overlap_area(ba, boxes[b])
                if a not in self.arms and b not in self.arms:
                    c += W_CLEARANCE * (overlap_area(pads[a], boxes[b]) + overlap_area(ba, pads[b]))
        for kind, group in self.zone_groups.items():  # keep each hazard group together so one enclosure covers it
            pts = [(pl[i]["position"]["x"], pl[i]["position"]["y"]) for i in group]
            cx, cy = sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)
            c += W_COHESION * sum(math.hypot(x - cx, y - cy) for x, y in pts)
        touched = set(self.hands_on)
        for (a, b), w in self.weights.items():
            via, _, time_s, how = self.serve(a, b, pl)
            c += w * time_s
            if how == "walk":
                touched |= {a, b}
        arms = arm_bases(pl, self.items)
        for a in touched & set(ids):  # a person needs a walkway-sized patch of floor where they stand
            sx, sy = human_spot(pl[a], self.items[a], arms, self.walkway / 2)
            h = self.walkway / 2
            patch = (sx - h, sy - h, sx + h, sy + h)
            c += W_ACCESS * outside_area(patch, self.room_box)
            for b in ids:
                if b != a and b not in self.arms:
                    c += W_ACCESS * overlap_area(patch, boxes[b])
        return c

    # ---------- search ----------
    def _first_use(self) -> list[str]:
        order = []
        for st in _topo(self.workflow["steps"]):
            order += [c for c in st["candidate_instances"] if c not in order]
        return order + [i for i in self.items if i not in order]

    def _ring_radius(self, arm: str, inst: str) -> float:
        ap = self.items[inst]["access_points"][0]["position"]
        return 0.75 * self.items[arm]["transport"].get("reach_m", 1.0) + math.hypot(ap["x"], ap["y"])

    def _fits(self, arm: str, members: list[str]) -> bool:
        """Do these instruments fit side by side on a ring around the arm?"""
        angle = 0.0
        for m in members:  # measured at the inner edge, where neighbours collide first
            fp = self.items[m]["footprint"]
            angle += (fp["width_m"] + 0.15) / max(0.3, self._ring_radius(arm, m) - fp["depth_m"] / 2)
        return angle <= 2 * math.pi * 0.9

    def _cluster_radius(self, arm: str, members: list[str]) -> float:
        fp = [self.items[m]["footprint"] for m in members]
        return max([self._ring_radius(arm, m) + max(f["width_m"], f["depth_m"]) / 2 for m, f in zip(members, fp)] + [0.5]) \
            + self.walkway / 2

    def initial(self) -> dict[str, tuple[float, float]]:
        """Fill each arm's ring in workflow order (so a cluster is a stretch of the process), then line the walls."""
        state = {}
        loose = [i for i in self._first_use() if i in self.movable and i not in self.arms and not _kind(self.items[i])]
        members, k = {a: [] for a in self.arms}, 0
        for inst in loose:
            if inst in self.manual_only or not self.links[inst] or not self.arms:
                continue
            while k < len(self.arms) and not self._fits(self.arms[k], members[self.arms[k]] + [inst]):
                k += 1
            if k == len(self.arms):
                break
            members[self.arms[k]].append(inst)

        # Clusters in a row along the long wall, starting from the end away from the door.
        door = self.doors[0]
        along_x = self.W >= self.D
        length, across = (self.W, self.D) if along_x else (self.D, self.W)
        from_far = (door["x"] if along_x else door["y"]) < length / 2
        cursor, row = 0.2, 0
        for arm in self.arms:
            if arm in self.locked:
                continue
            r = self._cluster_radius(arm, members[arm])
            if cursor + 2 * r > length and cursor > 0.2:
                cursor, row = 0.2, row + 1
            pos = cursor + r
            pos = length - pos if from_far else pos
            off = across / 2 if row == 0 else (across / 4 if row % 2 else 3 * across / 4)
            state[arm] = (pos, off) if along_x else (off, pos)
            cursor += 2 * r
        for arm, ms in members.items():
            ax, ay = state[arm] if arm in state else (self.locked[arm]["position"]["x"], self.locked[arm]["position"]["y"])
            theta = 0.0
            for inst in ms:
                r = self._ring_radius(arm, inst)
                half = (self.items[inst]["footprint"]["width_m"] + 0.15) / r / 2
                theta += half
                state[inst] = (ax + r * math.cos(theta), ay + r * math.sin(theta))
                theta += half

        # Everything else lines the walls near the door, zone groups kept together.
        arm_r = {a: self._cluster_radius(a, members[a]) for a in self.arms}
        arm_xy = {a: state.get(a) or (self.locked[a]["position"]["x"], self.locked[a]["position"]["y"]) for a in self.arms}
        slots = [p for p in self._wall_slots() if all(math.dist(p, arm_xy[a]) > arm_r[a] for a in self.arms)]
        rest = sorted((i for i in loose if i not in state), key=lambda i: (self.zone_kind.get(i, "~"), loose.index(i)))
        for inst in rest:
            state[inst] = slots.pop(0) if slots else (self.rng.uniform(0.5, self.W - 0.5), self.rng.uniform(0.5, self.D - 0.5))
        for inst in self.movable:  # transporters other than arms (mobile robot docks) and anything left
            if inst not in state:
                state[inst] = slots.pop(0) if slots else (self.W / 2, self.D / 2)
        return state

    def _wall_slots(self) -> list[tuple[float, float]]:
        step, inset, slots = 1.1, 0.6, []
        perimeter = [(inset, y) for y in _frange(inset, self.D - inset, step)] + \
                    [(x, self.D - inset) for x in _frange(inset, self.W - inset, step)] + \
                    [(self.W - inset, y) for y in _frange(self.D - inset, inset, -step)] + \
                    [(x, inset) for x in _frange(self.W - inset, inset, -step)]
        door = (self.doors[0]["x"], self.doors[0]["y"])
        return [p for p in sorted(dict.fromkeys(perimeter), key=lambda p: math.dist(p, door)) if math.dist(p, door) > 1.3]

    def anneal(self, state: dict, iterations: int) -> dict:
        """Refine the greedy start: temperature from small local moves, so structure survives."""
        if not self.movable:
            return state
        cur, cur_cost = dict(state), self.cost(state)
        best, best_cost = dict(cur), cur_cost
        deltas = sorted(abs(self.cost(self._neighbour(cur, 0.1, local=True)) - cur_cost) for _ in range(30))
        t0 = max(1e-3, deltas[len(deltas) // 2])
        for k in range(iterations):
            frac = 1 - k / iterations
            temp = t0 * (1e-3 ** (k / iterations))
            cand = self._neighbour(cur, frac)
            c = self.cost(cand)
            if c <= cur_cost or self.rng.random() < math.exp(-(c - cur_cost) / temp):
                cur, cur_cost = cand, c
                if c < best_cost:
                    best, best_cost = dict(cand), c
        return best

    def _neighbour(self, state: dict, frac: float, local: bool = False) -> dict:
        s = dict(state)
        r = 0.0 if local else self.rng.random()
        inst = self.rng.choice(self.movable)
        if r < 0.55:
            sigma = 0.05 + 0.6 * frac
            x, y = s[inst]
            s[inst] = (x + self.rng.gauss(0, sigma), y + self.rng.gauss(0, sigma))
        elif r < 0.7 and len(self.movable) > 1:
            other = self.rng.choice(self.movable)
            s[inst], s[other] = s[other], s[inst]
        elif r < 0.85 and self.arms and inst not in self.arms and inst not in self.manual_only and self.links[inst]:
            arm = self.rng.choice(self.arms)
            ax, ay = s[arm] if arm in s else (self.locked[arm]["position"]["x"], self.locked[arm]["position"]["y"])
            ap = self.items[inst]["access_points"][0]["position"]
            r_ring = self._ring_radius(arm, inst)
            theta = self.rng.uniform(0, 2 * math.pi)
            s[inst] = (ax + r_ring * math.cos(theta), ay + r_ring * math.sin(theta))
        elif r < 0.95 and self.arms:
            arm = self.rng.choice(self.arms)
            if arm in self.locked:
                return s
            ax, ay = s[arm]
            reach = self.items[arm]["transport"].get("reach_m", 1.0) + 0.6
            dx, dy = self.rng.gauss(0, 0.1 + 0.8 * frac), self.rng.gauss(0, 0.1 + 0.8 * frac)
            for m in self.movable:
                if m == arm or math.dist(s[m], (ax, ay)) <= reach:
                    s[m] = (s[m][0] + dx, s[m][1] + dy)
        else:
            s[inst] = (self.rng.uniform(0.3, self.W - 0.3), self.rng.uniform(0.3, self.D - 0.3))
        x, y = s[inst]
        s[inst] = (min(max(x, 0.1), self.W - 0.1), min(max(y, 0.1), self.D - 0.1))
        return s

    # ---------- output ----------
    def build(self, state: dict) -> dict:
        pl = self.placements(state)
        for p in pl.values():
            p["position"] = {k: round(v, 3) for k, v in p["position"].items()}
        for h in self.humans:  # people chosen as equipment wait at the door
            pl[h] = self._placement(h, self.doors[0]["x"], self.doors[0]["y"], 0.0)
            pl[h]["position"]["z"] = 0.0
        if any(p.get("locked") for p in self.locked.values()):
            for i in self.locked:
                pl[i]["locked"] = True
        boxes = [aabb(pl[i], self.items[i]) for i in self.placeable]
        grid = Grid(self.W, self.D, boxes, inflate_m=0.15)
        transfers, weighted = [], 0.0
        for (a, b), w in self.weights.items():
            via, dist, time_s, how = self.serve(a, b, pl)
            pa = world_point(pl[a], self.items[a]["access_points"][0]["position"])
            pb = world_point(pl[b], self.items[b]["access_points"][0]["position"])
            if how == "arm":
                base = pl[via]["position"]
                path = [pa, (base["x"], base["y"], base["z"] + 0.3), pb]
            elif how == "rail":
                path = [pa, pb]
            elif how == "walk":
                arms = arm_bases(pl, self.items)
                sa, sb = human_spot(pl[a], self.items[a], arms), human_spot(pl[b], self.items[b], arms)
                walk = grid.path(sa, sb)
                carry = 1.0
                pts = [(x, y, carry) for x, y in walk] if walk else [(sa[0], sa[1], carry), (sb[0], sb[1], carry)]
                path = [pa] + pts + [pb]
                dist = polyline_length(path)
                if via in self.mobiles:
                    t = self.items[via]["transport"]
                    time_s = 2 * t.get("pick_place_s", 20) + dist / t.get("speed_m_s", 1.0)
                else:
                    time_s = HUMAN_PICK_PLACE_S + dist / HUMAN_SPEED_M_S
            else:
                path = [pa, pb]
            t = {"from_instance": a, "to_instance": b, "transporter_instance": via, "distance_m": round(dist, 2),
                 "path": [{"x": round(p[0], 3), "y": round(p[1], 3), "z": round(p[2], 3)} for p in path]}
            if via != "unassigned":
                t["est_time_s"] = round(time_s, 1)
            transfers.append(t)
            weighted += w * dist
        layout = {
            "id": f"{self.workflow['id']}_layout",
            "workflow_id": self.workflow["id"],
            "room": {k: self.spec["room"][k] for k in ("width_m", "depth_m", "height_m") if k in self.spec["room"]},
            "placements": [pl[i] for i in self.items],
            "operators": self.operators,
            "transfers": transfers,
            "zones": derive_zones(pl, self.items, self.zone_kind, self.W, self.D),
            "score": {"total_weighted_distance_m": round(weighted, 2),
                      "floor_area_used_m2": round(sum(area(b) for b in boxes), 2)},
        }
        return layout


def _seg_dist(p: tuple, placement: dict, half: float) -> tuple[float, float]:
    """(distance from p to a rail of half-length `half`, position along the rail)."""
    phi = math.radians(placement["rotation_deg"])
    cx, cy = placement["position"]["x"], placement["position"]["y"]
    ux, uy = math.cos(phi), math.sin(phi)
    s = max(-half, min(half, (p[0] - cx) * ux + (p[1] - cy) * uy))
    return math.dist(p[:2], (cx + s * ux, cy + s * uy)), s


def _frange(a: float, b: float, step: float) -> list[float]:
    n = int(abs(b - a) / abs(step)) + 1
    return [a + k * step for k in range(n)]


def generate_layout(spec: dict, workflow: dict, previous: dict | None = None, seed: int = 0,
                    iterations: int | None = None) -> dict:
    """Place the workflow's equipment in the spec's room. `previous` keeps its `locked` placements."""
    placer = Placer(spec, workflow, previous, seed)
    state = placer.initial()
    n = len(placer.movable)
    state = placer.anneal(state, iterations if iterations is not None else min(6000, 1500 + 200 * n))
    layout = placer.build(state)
    layout["violations"] = find_violations(layout, placer.items, spec, placer.rules, workflow=workflow)
    return validate(layout, "layout")
