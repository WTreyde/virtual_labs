"""Strand D helpers shared by placer and validator. Owner: Maxim."""
import heapq
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


def overlap_area(a: tuple, b: tuple) -> float:
    return max(0.0, min(a[2], b[2]) - max(a[0], b[0])) * max(0.0, min(a[3], b[3]) - max(a[1], b[1]))


def area(a: tuple) -> float:
    return max(0.0, a[2] - a[0]) * max(0.0, a[3] - a[1])


def outside_area(box: tuple, region: tuple) -> float:
    """Area of `box` that lies outside `region` (both AABBs)."""
    return area(box) - overlap_area(box, region)


def standing_spot(placement: dict, item: dict, offset_m: float = 0.4) -> tuple[float, float]:
    """Where a person stands to use an item: in front of its first access point, away from the item centre."""
    ax, ay, _ = world_point(placement, item["access_points"][0]["position"])
    cx, cy = placement["position"]["x"], placement["position"]["y"]
    dx, dy = ax - cx, ay - cy
    n = math.hypot(dx, dy) or 1.0
    return ax + offset_m * dx / n, ay + offset_m * dy / n


def human_spot(placement: dict, item: dict, arms: list[tuple[float, float, float]], offset_m: float = 0.4) -> tuple[float, float]:
    """Where a person stands to load an item. Inside an arm's cell they work from the outer side, away from the arm.

    `arms` holds (x, y, reach_m) for each arm."""
    cx, cy = placement["position"]["x"], placement["position"]["y"]
    near = [(math.hypot(cx - x, cy - y), x, y) for x, y, reach in arms if math.hypot(cx - x, cy - y) <= reach + 0.6]
    if not near:
        return standing_spot(placement, item, offset_m)
    d, x, y = min(near)
    fp = item["footprint"]
    out = math.hypot(fp["width_m"], fp["depth_m"]) / 2 + offset_m
    ux, uy = ((cx - x) / d, (cy - y) / d) if d > 1e-6 else (0.0, -1.0)
    return cx + out * ux, cy + out * uy


def arm_bases(placements: dict[str, dict], items: dict[str, dict]) -> list[tuple[float, float, float]]:
    return [(p["position"]["x"], p["position"]["y"], items[i]["transport"].get("reach_m", 1.0))
            for i, p in placements.items() if i in items and (items[i].get("transport") or {}).get("kind") == "arm"]


class Grid:
    """Occupancy grid of the room floor for walking paths, walkway widths and egress."""

    def __init__(self, width_m: float, depth_m: float, boxes: list[tuple], cell_m: float = 0.1, inflate_m: float = 0.0):
        self.cell, self.nx, self.ny = cell_m, max(1, math.ceil(width_m / cell_m)), max(1, math.ceil(depth_m / cell_m))
        self.blocked = [[False] * self.ny for _ in range(self.nx)]
        for x0, y0, x1, y1 in boxes:
            i0, j0 = self.index(x0 - inflate_m, y0 - inflate_m)
            i1, j1 = self.index(x1 + inflate_m, y1 + inflate_m)
            for i in range(i0, i1 + 1):
                for j in range(j0, j1 + 1):
                    self.blocked[i][j] = True
        self._clear = None

    def index(self, x: float, y: float) -> tuple[int, int]:
        return min(self.nx - 1, max(0, int(x / self.cell))), min(self.ny - 1, max(0, int(y / self.cell)))

    def centre(self, i: int, j: int) -> tuple[float, float]:
        return (i + 0.5) * self.cell, (j + 0.5) * self.cell

    def clearance(self) -> list[list[float]]:
        """Distance (m) from each cell to the nearest blocked cell or wall (two-pass chamfer transform)."""
        if self._clear is not None:
            return self._clear
        inf, a, b = float("inf"), 1.0, math.sqrt(2)
        d = [[0.0 if self.blocked[i][j] else inf for j in range(self.ny)] for i in range(self.nx)]
        for i in range(self.nx):
            for j in range(self.ny):
                wall = min(i, j, self.nx - 1 - i, self.ny - 1 - j) + 0.5
                d[i][j] = min(d[i][j], wall)
        for i in range(self.nx):
            for j in range(self.ny):
                for di, dj, w in ((-1, 0, a), (0, -1, a), (-1, -1, b), (-1, 1, b)):
                    ii, jj = i + di, j + dj
                    if 0 <= ii < self.nx and 0 <= jj < self.ny:
                        d[i][j] = min(d[i][j], d[ii][jj] + w)
        for i in range(self.nx - 1, -1, -1):
            for j in range(self.ny - 1, -1, -1):
                for di, dj, w in ((1, 0, a), (0, 1, a), (1, 1, b), (1, -1, b)):
                    ii, jj = i + di, j + dj
                    if 0 <= ii < self.nx and 0 <= jj < self.ny:
                        d[i][j] = min(d[i][j], d[ii][jj] + w)
        self._clear = [[v * self.cell for v in col] for col in d]
        return self._clear

    def nearest_free(self, i: int, j: int, min_clear: float = 0.0) -> tuple[int, int] | None:
        clear = self.clearance() if min_clear else None
        best, best_d = None, float("inf")
        for ii in range(self.nx):
            for jj in range(self.ny):
                if self.blocked[ii][jj] or (clear and clear[ii][jj] < min_clear):
                    continue
                dd = (ii - i) ** 2 + (jj - j) ** 2
                if dd < best_d:
                    best, best_d = (ii, jj), dd
        return best

    def reachable(self, start: tuple[float, float], min_clear: float) -> set[tuple[int, int]]:
        """Cells reachable from `start` while keeping `min_clear` metres from obstacles (a walkway that wide)."""
        clear = self.clearance()
        s = self.nearest_free(*self.index(*start), min_clear=min_clear)
        if s is None:
            return set()
        seen, stack = {s}, [s]
        while stack:
            i, j = stack.pop()
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                c = (i + di, j + dj)
                if 0 <= c[0] < self.nx and 0 <= c[1] < self.ny and c not in seen \
                        and not self.blocked[c[0]][c[1]] and clear[c[0]][c[1]] >= min_clear:
                    seen.add(c)
                    stack.append(c)
        return seen

    def path(self, a: tuple[float, float], b: tuple[float, float]) -> list[tuple[float, float]] | None:
        """Shortest 8-connected walking path around obstacles, simplified to its corners. None if cut off."""
        start = self.index(*a)
        goal = self.index(*b)
        if self.blocked[start[0]][start[1]]:
            start = self.nearest_free(*start)
        if self.blocked[goal[0]][goal[1]]:
            goal = self.nearest_free(*goal)
        if start is None or goal is None:
            return None
        steps = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
                 (1, 1, math.sqrt(2)), (1, -1, math.sqrt(2)), (-1, 1, math.sqrt(2)), (-1, -1, math.sqrt(2))]
        g, came, frontier = {start: 0.0}, {}, [(0.0, start)]
        while frontier:
            _, cur = heapq.heappop(frontier)
            if cur == goal:
                break
            for di, dj, w in steps:
                nxt = (cur[0] + di, cur[1] + dj)
                if not (0 <= nxt[0] < self.nx and 0 <= nxt[1] < self.ny) or self.blocked[nxt[0]][nxt[1]]:
                    continue
                if di and dj and (self.blocked[cur[0] + di][cur[1]] or self.blocked[cur[0]][cur[1] + dj]):
                    continue  # no corner cutting
                cost = g[cur] + w
                if cost < g.get(nxt, float("inf")):
                    g[nxt], came[nxt] = cost, cur
                    heapq.heappush(frontier, (cost + math.dist(nxt, goal), nxt))
        if goal not in g:
            return None
        cells = [goal]
        while cells[-1] != start:
            cells.append(came[cells[-1]])
        cells.reverse()
        corners = [cells[0]] + [c for k, c in enumerate(cells[1:-1], 1)
                                if (c[0] - cells[k - 1][0], c[1] - cells[k - 1][1]) != (cells[k + 1][0] - c[0], cells[k + 1][1] - c[1])]
        corners.append(cells[-1])
        pts = [self.centre(*c) for c in corners]
        return [a] + pts[1:-1] + [b] if len(pts) > 1 else [a, b]


def polyline_length(pts: list) -> float:
    return sum(math.dist(p[:2], q[:2]) for p, q in zip(pts, pts[1:]))
