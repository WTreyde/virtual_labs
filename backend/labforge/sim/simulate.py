"""Strand D: Monte Carlo discrete-event simulation of a workflow on a layout. Owner: Maxim.

Model (SimPy, one process per workflow step):
- Labware tokens flow along the `after` graph through bounded buffers. A step reserves space in
  every downstream buffer *before* it grabs an instrument, so it never blocks while holding one
  (no deadlock with shared instruments such as a hotel used at start and end).
- `batch_size`: a step waits for that many units (per predecessor), then runs them together for
  one `duration_s` on one instrument, using `batch_size` of its capacity slots (an evaporator with
  6 slots and batch 6 runs one batch at a time; an incubator with 44 slots and batch 1 runs 44).
  `params.batch_timeout_s` lets a partial batch go after waiting that long.
- Storage hotels: a residence step (incubation, plate/cold/compound storage that the catalog does not time as an
  operation) on an instrument with `storage_slots` above its process capacity holds labware in a separate pool of
  that many slots (`<instance>__storage` in utilisation). The Rock Imager 1000 grows 970 plates but images one at a
  time; a timed storage operation (the compound store's 120 s pick) keeps the process capacity.
- `fan_out`: outputs per input (8 = split into 8 plates, 0.25 = four 96-well into one 384-well).
- Operators (layout.operators, shift hours from spec.operators) run `manual` steps for their
  whole duration and load `semi_automated` ones (`params.operator_s`, default 300 s, estimated);
  they also carry labware on transfers assigned to them. They only work during their shift
  (t=0 is the start of the first shift; optional `shift_start_h` per spec operator role).
- `external` steps (synchrotron): no instrument, unlimited concurrency unless
  `params.max_concurrent`; `params.queue_time_s` (number or uncertain_number) is added to the
  turnaround. Labware that leaves for an external service is not transferred back in the room.
  Optional `params.beamtime_h_per_day` (number or uncertain_number, e.g. confidence "estimated") caps the beam an
  external step gets per day: each run uses its `duration_s` of beam, topped up daily (`<step>__beamtime` in
  utilisation). Off unless set.
- `in_silico` steps (or steps without instruments): a pure delay; labware stays where it was.

Downtime (optional, `simulate(..., downtime=...)`): per-instance random failures (MTBF/MTTR) or a
charging duty cycle; work pauses while the unit is down. Off by default.

Uncertainty: each Monte Carlo replicate draws one "true" mean duration per step from its range
(epistemic: we do not know the LC-MS run time exactly), then every run jitters ±5% around it
(aleatoric). Ranges come from `duration_uncertainty`, else the catalog's provenance for that
capability, else a band set by the confidence level. Throughput is the steady-state rate,
measured after a warm-up that covers the pipeline's fill time.

Sensitivity: the busiest wide-range inputs are pinned low and high (same seeds); see sensitivity_analysis.
Parallel runs: sim/parallel.py (local processes or Modal).
"""
import bisect
import math
import random
import statistics
from collections import defaultdict
from dataclasses import dataclass

import simpy

from labforge.catalog.store import load_catalog
from labforge.contracts import validate
from labforge.sim.parallel import map_replicates

# Range multipliers (low, high) around a stated duration when no explicit range is given.
BANDS = {"datasheet": (0.95, 1.10), "literature": (0.85, 1.25), "estimated": (0.8, 1.4), "placeholder": (0.5, 2.0)}
JITTER = 0.05  # run-to-run variation around a replicate's mean duration
SEMI_AUTO_OPERATOR_S = 300.0  # estimated: operator time to load and start a semi-automated instrument
DAY_S = 86400.0
RESIDENCE_CAPABILITIES = {"incubation", "plate_storage", "cold_storage", "compound_storage"}  # may use storage_slots
HUMAN_WALK_BAND = (0.8, 1.5)  # estimated: real walking/handling vs the layout's straight-line estimate
UNASSIGNED_CARRY_S = 120.0  # placeholder: someone carries labware no transporter can reach
DEFAULT_TRANSFER_S = 30.0
MIN_RUN_S = 1.0  # keeps zero-time steps (e.g. "pick plate from hotel") from looping forever at one instant
TIMELINE_LIMIT = 500
MIN_SINK_LABWARE = 20  # extend the measurement window until this many units finish...
MAX_WINDOW_H = 60 * 24  # ...but never beyond 60 days
UNBOUNDED = 10_000
SENSITIVITY_TOP = 6  # inputs swung per sensitivity analysis
SENSITIVITY_REPS = 6  # replicates per swing end
SENSITIVITY_MIN_SCORE = 0.03  # skip inputs that are narrow or sit on idle resources


def topo_order(steps: list[dict]) -> list[dict]:
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


def step_mode(step: dict) -> str:
    mode = step.get("mode", "automated")
    if mode == "automated" and not step["candidate_instances"]:
        return "in_silico"
    return mode


def duration_range(step: dict, item: dict | None = None) -> tuple[float, float, float]:
    """(low, mode, high) for a step's duration: explicit range, else catalog provenance, else a confidence band."""
    v = step["duration_s"]
    u = step.get("duration_uncertainty")
    if not u and item:
        u = (item.get("provenance") or {}).get(f"process.durations_s.{step['capability']}")
        if u and u.get("value"):  # rescale the catalog's range to this step's stated value
            u = {k: (u[k] / u["value"] * v if k in ("low", "high") else u[k]) for k in u}
        elif item.get("data_confidence"):
            u = {"confidence": item["data_confidence"]}
    return _range(v, u)


def _range(v: float, u: dict | None) -> tuple[float, float, float]:
    band = BANDS.get((u or {}).get("confidence", "estimated"), BANDS["estimated"])
    low = (u or {}).get("low", v * band[0])
    high = (u or {}).get("high", v * band[1])
    return min(low, v), v, max(high, v)


def _uncertain(x) -> tuple[float, float, float]:
    if x is None:
        return 0.0, 0.0, 0.0
    if isinstance(x, (int, float)):
        return _range(float(x), None)
    return _range(x["value"], x)


@dataclass
class Token:
    id: str
    birth: float
    at: str | None  # instance holding the labware; None before entering the room or once shipped out


@dataclass
class Operator:
    id: str
    role: str
    skills: tuple
    shift_h: float
    start_h: float

    def phase_h(self, t: float) -> float:
        return (t / 3600 - self.start_h) % 24

    def on_shift(self, t: float) -> bool:
        return self.shift_h >= 24 or self.phase_h(t) < self.shift_h - 1e-9

    def until_change(self, t: float) -> float | None:
        """Seconds until this operator's next shift start or end."""
        if self.shift_h >= 24:
            return None
        ph = self.phase_h(t)
        return ((self.shift_h - ph) if ph < self.shift_h - 1e-9 else (24 - ph)) * 3600

    def shift_seconds(self, t0: float, t1: float) -> float:
        if self.shift_h >= 24:
            return t1 - t0
        total, day = 0.0, math.floor((t0 / 3600 - self.start_h) / 24) - 1
        while (self.start_h + 24 * day) * 3600 < t1:
            s = (self.start_h + 24 * day) * 3600
            total += max(0.0, min(t1, s + self.shift_h * 3600) - max(t0, s))
            day += 1
        return total


class Buffer:
    """Labware waiting between two steps. `space` is reserved by the upstream step before it starts."""

    def __init__(self, env: simpy.Environment, capacity: int):
        self.items = simpy.Store(env)
        self.space = simpy.Container(env, capacity=capacity, init=capacity)


class Model:
    def __init__(self, spec: dict, workflow: dict, layout: dict, t0: float, t1: float, rng: random.Random,
                 pins: dict[str, str] | None = None, record: bool = False, capacity_overrides: dict[str, int] | None = None,
                 downtime: dict[str, dict] | None = None):
        self.env, self.rng, self.t0, self.t1, self.record = simpy.Environment(), rng, t0, t1, record
        self.steps = topo_order(workflow["steps"])
        self.by_id = {s["id"]: s for s in self.steps}
        self.succ = defaultdict(list)
        for s in self.steps:
            for p in s.get("after", []):
                self.succ[p].append(s["id"])

        catalog = load_catalog()
        self.items = {e["instance_id"]: catalog.get(e["catalog_id"]) for e in workflow["equipment"]}
        for s in self.steps:
            missing = [c for c in s["candidate_instances"] if c not in self.items]
            if missing:
                raise ValueError(f"Step {s['id']} uses instances not in workflow.equipment: {missing}")

        # Capacity slots: the catalog's number if it states one, else enough for the largest batch run on it.
        caps = {}
        for inst, item in self.items.items():
            stated = ((item or {}).get("process") or {}).get("capacity")
            batches = [s.get("batch_size", 1) for s in self.steps if inst in s["candidate_instances"]]
            caps[inst] = stated or max(batches + [1])
        # Storage hotels: a residence step (storage or incubation the catalog does not time as an operation) holds
        # labware in the instrument's storage_slots, a pool separate from its process capacity. The Rock Imager 1000
        # grows 970 plates but images one at a time. Pool key "<instance>__storage".
        self.pool = {}
        for s in self.steps:
            for c in s["candidate_instances"]:
                item = self.items.get(c) or {}
                slots = int(item.get("storage_slots") or 0)
                timed = s["capability"] in ((item.get("process") or {}).get("durations_s") or {})
                if s["capability"] in RESIDENCE_CAPABILITIES and not timed and slots > caps[c]:
                    caps[f"{c}__storage"] = slots
                    self.pool[(s["id"], c)] = f"{c}__storage"
        caps.update({i: int(c) for i, c in (capacity_overrides or {}).items() if i in caps})  # what-if: more slots
        self.caps = caps
        self.slots = {s["id"]: max(1, min([s.get("batch_size", 1)] + [caps[self.key(s["id"], c)] for c in s["candidate_instances"]]))
                      for s in self.steps}
        self.res = {i: simpy.Container(self.env, capacity=c, init=c) for i, c in caps.items()}
        self.ext = {s["id"]: simpy.Container(self.env, capacity=int(s["params"]["max_concurrent"]),
                                             init=int(s["params"]["max_concurrent"]))
                    for s in self.steps if step_mode(s) == "external" and (s.get("params") or {}).get("max_concurrent")}

        # Operators: ids and roles from the layout, shift hours from the spec.
        roles = {o["role"]: o for o in spec.get("operators", [])}
        self.ops = {o["id"]: Operator(o["id"], o["role"], tuple(roles.get(o["role"], {}).get("skills", [])),
                                      float(roles.get(o["role"], {}).get("shift_hours", 8)),
                                      float(roles.get(o["role"], {}).get("shift_start_h", 0)))
                    for o in layout.get("operators", [])}
        self.op_pool = simpy.FilterStore(self.env)
        self.op_pool.items.extend(self.ops.values())
        self.eligible, self.staffing_issues = {}, []
        for s in self.steps:
            if step_mode(s) in ("manual", "semi_automated"):
                self.eligible[s["id"]] = self._eligible_ops(s)

        self.moves = {(t["from_instance"], t["to_instance"]): t for t in layout.get("transfers", [])}

        # Epistemic draws: one mean per step for this replicate; `pins` forces "low"/"high" (sensitivity).
        pins = pins or {}
        self.mean, self.queue = {}, {}
        for s in self.steps:
            item = self.items.get(s["candidate_instances"][0]) if s["candidate_instances"] else None
            self.mean[s["id"]] = self._draw(duration_range(s, item), pins.get(s["id"]))
            self.queue[s["id"]] = self._draw(_uncertain((s.get("params") or {}).get("queue_time_s")),
                                             pins.get(f"{s['id']}.queue"))
        # Optional beamtime cap on an external step (params.beamtime_h_per_day, number or uncertain_number): that many
        # beam-seconds a day, topped up at each day boundary (unused beam does not carry over); each run uses its
        # duration_s of beam after its queue. Off unless set, so designs without it simulate exactly as before.
        self.beam, self.beam_queue, self.beam_used = {}, {}, defaultdict(list)
        for s in self.steps:
            bt = (s.get("params") or {}).get("beamtime_h_per_day")
            if step_mode(s) == "external" and bt is not None:
                band = (float(bt),) * 3 if isinstance(bt, (int, float)) else _uncertain(bt)  # a plain number is exact
                cap = max(1.0, self._draw(band, pins.get(f"{s['id']}.beamtime")) * 3600)
                self.beam[s["id"]] = simpy.Container(self.env, capacity=cap, init=cap)
                self.beam_queue[s["id"]] = simpy.Resource(self.env, capacity=1)
                self.env.process(self._top_up_beam(s["id"]))
        self.walk = self._draw((HUMAN_WALK_BAND[0], 1.0, HUMAN_WALK_BAND[1]), pins.get("operator_walking"))
        self.down = self._down_intervals(downtime or {}, t0 + MAX_WINDOW_H * 3600)

        # Buffers between steps, sized so a step's own parallel runs are never throttled by reservation.
        self.buffers, self.acc = {}, defaultdict(float)
        for s in self.steps:
            for nxt in self.succ[s["id"]]:
                self.buffers[(s["id"], nxt)] = Buffer(self.env, self._buffer_capacity(s, self.by_id[nxt]))

        sinks = [s for s in self.steps if not self.succ[s["id"]]]
        flagged = [s for s in sinks if (s.get("params") or {}).get("count_throughput")]
        self.sink = (flagged or sinks)[-1]["id"]
        self.units_per_labware = float((self.by_id[self.sink].get("params") or {}).get("units_per_labware", 1))

        self.busy, self.open = defaultdict(float), {}
        self.waits = defaultdict(list)
        self.completed, self.cycle, self.timeline = 0, [], []
        self.n_tokens, self.unassigned_used = 0, set()

    # ---------- helpers ----------
    def _top_up_beam(self, sid: str):
        beam = self.beam[sid]
        while True:
            yield self.env.timeout(DAY_S - self.env.now % DAY_S)
            if beam.level < beam.capacity:
                yield beam.put(beam.capacity - beam.level)

    def _use_beam(self, sid: str, seconds: float):
        """Take `seconds` of beam, first come first served (a beamline collects one shipment at a time): what is left
        today, then the rest from the next days' allocations."""
        beam, left = self.beam[sid], seconds
        with self.beam_queue[sid].request() as turn:
            yield turn
            while left > 1e-9:
                take = min(left, beam.level if beam.level > 1e-9 else beam.capacity)
                yield beam.get(take)
                self.beam_used[sid].append((self.env.now, take))
                left -= take

    def _draw(self, rng3: tuple[float, float, float], pin: str | None) -> float:
        low, mode, high = rng3
        if pin == "low":
            return low
        if pin == "high":
            return high
        return self.rng.triangular(low, high, mode) if high > low else mode

    def _down_intervals(self, downtime: dict[str, dict], horizon: float) -> dict[str, tuple[list, list]]:
        """Pre-drawn (starts, ends) of down periods per instance for this replicate.

        Spec per instance: {"mtbf_h", "mttr_h"} random failures (exponential), {"up_h", "down_h"} a periodic
        duty cycle such as charging (random phase), or {"availability", "cycle_h"} as shorthand for one."""
        out = {}
        for inst, d in downtime.items():
            if inst not in self.res:
                raise ValueError(f"downtime given for {inst}, which is not in workflow.equipment")
            rng = random.Random(self.rng.randrange(2**31))
            if "availability" in d:
                a, cycle = float(d["availability"]), float(d.get("cycle_h", 8))
                if not 0 < a <= 1:
                    raise ValueError(f"availability for {inst} must be in (0, 1]")
                d = {"up_h": a * cycle, "down_h": (1 - a) * cycle}
            starts, ends = [], []
            if "mtbf_h" in d:
                t = rng.expovariate(1 / (d["mtbf_h"] * 3600))
                while t < horizon:
                    rep_s = rng.expovariate(1 / (d["mttr_h"] * 3600))
                    starts.append(t)
                    ends.append(t + rep_s)
                    t += rep_s + rng.expovariate(1 / (d["mtbf_h"] * 3600))
            elif d.get("down_h", 0) > 0:
                up, dn = d["up_h"] * 3600, d["down_h"] * 3600
                t = -rng.uniform(0, up + dn)  # random phase
                while t < horizon:
                    if t + up + dn > 0:
                        starts.append(max(0.0, t + up))
                        ends.append(t + up + dn)
                    t += up + dn
            else:
                raise ValueError(f"downtime for {inst} needs mtbf_h+mttr_h, up_h+down_h or availability")
            out[inst] = (starts, ends)
        return out

    def machine_work(self, inst: str, seconds: float, slots: int = 1):
        """Run an instrument or robot for `seconds` of working time, pausing while it is down (failed, charging)."""
        starts, ends = self.down[inst]
        remaining = seconds
        while remaining > 1e-9:
            now = self.env.now
            k = bisect.bisect_right(starts, now) - 1
            if k >= 0 and now < ends[k] - 1e-9:  # down right now: wait for it to come back
                yield self.env.timeout(ends[k] - now)
                continue
            nxt = starts[k + 1] if k + 1 < len(starts) else float("inf")
            chunk = min(remaining, nxt - now)
            h = self._start_busy(inst, slots)
            yield self.env.timeout(chunk)
            self._end_busy(h)
            remaining -= chunk

    def _eligible_ops(self, step: dict) -> set[str]:
        role = step.get("operator_role")
        if role:
            ids = {o.id for o in self.ops.values() if o.role == role}
            if ids:
                return ids
            if self.ops:
                self.staffing_issues.append((step["id"], "medium", f"No operator has role '{role}' for {step['id']}; "
                                                                   "assumed any operator can do it."))
                return set(self.ops)
        else:
            skilled = {o.id for o in self.ops.values() if step["capability"] in o.skills}
            if skilled or self.ops:
                return skilled or set(self.ops)
        self.staffing_issues.append((step["id"], "high", f"{step['id']} needs a human operator but none is staffed, "
                                                         "so nothing gets past it."))
        return set()

    def _buffer_capacity(self, step: dict, nxt: dict) -> int:
        downstream = 2 * self.slots[nxt["id"]] + 2
        if step_mode(step) in ("in_silico", "external"):
            # Fed at a finite rate from upstream, so no need to throttle; a source of this kind gets a small buffer.
            return UNBOUNDED if step.get("after") else 64 + downstream
        if step["candidate_instances"]:
            parallel = sum(self.caps[self.key(step["id"], c)] // self.slots[step["id"]] for c in step["candidate_instances"]) or 1
        else:
            parallel = max(1, len(self.eligible.get(step["id"], ())))
        out_max = math.ceil(self.slots[step["id"]] * step.get("fan_out", 1)) + 1
        return max(4, parallel * out_max + downstream)

    def _jitter(self, mean: float) -> float:
        return mean * self.rng.uniform(1 - JITTER, 1 + JITTER)

    def _log(self, lw: str, event: str, inst: str | None = None, step: str | None = None):
        if self.record and len(self.timeline) < TIMELINE_LIMIT:
            e = {"t_s": round(self.env.now, 1), "labware_id": lw, "event": event}
            if inst:
                e["instance_id"] = inst
            if step:
                e["step_id"] = step
            self.timeline.append(e)

    def _start_busy(self, key: str, slots: float = 1) -> object:
        handle = object()
        self.open[handle] = (key, self.env.now, slots)
        return handle

    def _end_busy(self, handle: object):
        key, start, slots = self.open.pop(handle)
        a, b = max(start, self.t0), min(self.env.now, self.t1)
        if b > a:
            self.busy[key] += (b - a) * slots

    def _new_token(self, birth: float, at: str | None) -> Token:
        self.n_tokens += 1
        return Token(f"plate_{self.n_tokens:05d}", birth, at)

    # ---------- operators ----------
    def acquire_operator(self, eligible: set[str]):
        while True:
            get = self.op_pool.get(lambda o: o.id in eligible and o.on_shift(self.env.now))
            changes = [d for o in eligible if (d := self.ops[o].until_change(self.env.now)) is not None]
            if not changes:
                return (yield get)
            yield get | self.env.timeout(max(min(changes), 1e-3))
            if get.triggered:
                return get.value
            get.cancel()

    def operator_work(self, op: Operator, seconds: float, inst: str | None = None, slots: int = 1):
        """Spend `seconds` of an operator's time, pausing outside their shift. `inst` is busy only while they work."""
        remaining = seconds
        while remaining > 1e-9:
            if not op.on_shift(self.env.now):
                yield self.env.timeout(op.until_change(self.env.now))
                continue
            chunk = min(remaining, op.until_change(self.env.now) or remaining)
            handles = [self._start_busy(op.id)] + ([self._start_busy(inst, slots)] if inst else [])
            yield self.env.timeout(chunk)
            for h in handles:
                self._end_busy(h)
            remaining -= chunk

    # ---------- transport ----------
    def move(self, tokens: list[Token], dest: str):
        for origin in dict.fromkeys(t.at for t in tokens):
            if origin is None or origin == dest:
                continue
            group = [t for t in tokens if t.at == origin]
            mv = self.moves.get((origin, dest))
            if mv is None:
                continue  # no physical edge in the layout (e.g. labware passes through an in-silico step)
            via = mv["transporter_instance"]
            base = mv.get("est_time_s", DEFAULT_TRANSFER_S)
            if via in self.ops:  # one trip carries the whole group
                op = yield from self.acquire_operator({o.id for o in self.ops.values() if o.role == self.ops[via].role})
                for t in group:
                    self._log(t.id, "transfer_start", op.id)
                yield from self.operator_work(op, self._jitter(base * self.walk))
                yield self.op_pool.put(op)
                for t in group:
                    self._log(t.id, "transfer_end", op.id)
            elif via in self.res:
                for t in group:
                    yield self.res[via].get(1)
                    self._log(t.id, "transfer_start", via)
                    if via in self.down:
                        yield from self.machine_work(via, self._jitter(base))
                    else:
                        h = self._start_busy(via)
                        yield self.env.timeout(self._jitter(base))
                        self._end_busy(h)
                    yield self.res[via].put(1)
                    self._log(t.id, "transfer_end", via)
            else:
                self.unassigned_used.add((origin, dest))
                yield self.env.timeout(UNASSIGNED_CARRY_S)
            for t in group:
                t.at = dest

    # ---------- steps ----------
    def take_inputs(self, step: dict):
        sid, preds = step["id"], step.get("after", [])
        n = self.slots[sid]
        timeout = (step.get("params") or {}).get("batch_timeout_s")
        taken = []
        for k, p in enumerate(preds):
            buf, got = self.buffers[(p, sid)], []
            want = n if k == 0 else len(taken[0])
            deadline = None
            while len(got) < want:
                get = buf.items.get()
                if k == 0 and got and timeout is not None:
                    deadline = deadline or self.env.now + float(timeout)
                    yield get | self.env.timeout(max(deadline - self.env.now, 0))
                    if not get.triggered:
                        get.cancel()
                        break
                    tok = get.value
                else:
                    tok = yield get
                got.append(tok)
                yield buf.space.put(1)
            taken.append(got)
        return [t for group in taken for t in group], (len(taken[0]) if taken else n)

    def key(self, sid: str, inst: str) -> str:
        """The slot pool a step uses on an instance: its storage pool for residence, else the instance itself."""
        return self.pool.get((sid, inst), inst)

    def acquire_instance(self, step: dict):
        sid, cands, need = step["id"], step["candidate_instances"], self.slots[step["id"]]
        res = {c: self.res[self.key(sid, c)] for c in cands}
        free = [c for c in cands if res[c].level >= need]
        if free:
            pick = max(free, key=lambda c: res[c].level / self.caps[self.key(sid, c)])
            yield res[pick].get(need)
            return pick
        gets = {c: res[c].get(need) for c in cands}
        yield simpy.AnyOf(self.env, list(gets.values()))
        pick = next(c for c, g in gets.items() if g.triggered)
        for c, g in gets.items():
            if c == pick:
                continue
            if g.triggered:
                yield res[c].put(need)
            else:
                g.cancel()
        return pick

    def dispatcher(self, step: dict):
        sid, fan = step["id"], float(step.get("fan_out", 1))
        mode = step_mode(step)
        while True:
            if step.get("after"):
                tokens, n_in = yield from self.take_inputs(step)
            else:
                tokens, n_in = None, self.slots[sid]
            self.acc[sid] += n_in * fan
            n_out = int(self.acc[sid] + 1e-9)
            self.acc[sid] -= n_out
            for nxt in self.succ[sid]:
                if n_out:
                    yield self.buffers[(sid, nxt)].space.get(n_out)
            t_req, inst = self.env.now, None
            if step["candidate_instances"]:
                inst = yield from self.acquire_instance(step)
                self.waits[inst].append(self.env.now - t_req)
            elif sid in self.ext:
                yield self.ext[sid].get(1)
            if tokens is None:
                tokens = [self._new_token(self.env.now, None) for _ in range(n_in)]
            started = self.env.event()
            self.env.process(self.run(step, mode, inst, tokens, n_out, started))
            if not inst and mode in ("manual", "semi_automated"):
                yield started  # operators are the capacity limit: dispatch the next unit only once one is working

    def run(self, step: dict, mode: str, inst: str | None, tokens: list[Token], n_out: int, started: simpy.Event):
        sid = step["id"]
        if inst:
            yield from self.move(tokens, inst)
        item = self.items.get(inst) if inst else None
        dur = max(MIN_RUN_S, self._jitter(self.mean[sid]) + float(((item or {}).get("process") or {}).get("setup_s", 0)))
        if mode in ("manual", "semi_automated"):
            # The instrument waits for a person; that idle time is the operator's bottleneck, not the instrument's.
            op = yield from self.acquire_operator(self.eligible[sid])
            started.succeed()
        for t in tokens:
            self._log(t.id, "step_start", inst, sid)
        timed = inst in self.down  # downtime-aware instruments account their own busy time
        pool = self.key(sid, inst) if inst else None
        h = self._start_busy(pool, self.slots[sid]) if inst and mode != "manual" and not timed else None
        if mode == "manual":
            yield from self.operator_work(op, dur, inst, self.slots[sid])
            yield self.op_pool.put(op)
        elif mode == "semi_automated":
            handling = float((step.get("params") or {}).get("operator_s", SEMI_AUTO_OPERATOR_S))
            yield from self.operator_work(op, min(handling, dur) if dur else handling)
            yield self.op_pool.put(op)
            if timed:
                yield from self.machine_work(inst, max(dur - handling, 0), self.slots[sid])
            else:
                yield self.env.timeout(max(dur - handling, 0))
        else:
            if mode == "external":
                yield self.env.timeout(self._jitter(self.queue[sid]))
                if sid in self.beam:
                    yield from self._use_beam(sid, dur)
            if timed:
                yield from self.machine_work(inst, dur, self.slots[sid])
            else:
                yield self.env.timeout(dur)
        if h:
            self._end_busy(h)
        if inst:
            yield self.res[pool].put(self.slots[sid])
        elif sid in self.ext:
            yield self.ext[sid].put(1)
        for t in tokens:
            self._log(t.id, "step_end", inst, sid)

        where = inst or (None if mode == "external" else tokens[0].at)
        birth = min(t.birth for t in tokens)
        if n_out == len(tokens) and len(set(t.at for t in tokens)) <= 1 and step.get("fan_out", 1) == 1 \
                and len(step.get("after", [])) <= 1:
            outs = [Token(t.id, t.birth, where) for t in tokens]
        else:
            outs = [self._new_token(birth, where) for _ in range(n_out)]
        if not self.succ[sid]:
            if sid == self.sink and self.t0 <= self.env.now <= self.t1:
                self.completed += len(outs)
                self.cycle.extend(self.env.now - t.birth for t in outs)
            return
        for k, nxt in enumerate(self.succ[sid]):
            for t in outs:
                copy = t if k == 0 else Token(f"{t.id}_{k}", t.birth, t.at)
                yield self.buffers[(sid, nxt)].items.put(copy)

    def run_until_end(self) -> dict:
        for s in self.steps:
            if s["id"] in self.eligible and not self.eligible[s["id"]]:
                continue  # unstaffed manual step: it never runs
            if not s.get("after") and not self.succ[s["id"]] and not s["candidate_instances"]:
                continue  # isolated instrument-less step: nothing to throttle it, nothing depends on it
            self.env.process(self.dispatcher(s))
        self.env.run(until=self.t1)
        # Few, large labware units (one 384-compound plate every 16 h) make a short window lumpy:
        # keep simulating until enough units finish, up to MAX_WINDOW_H.
        while self.completed < MIN_SINK_LABWARE and self.t1 - self.t0 < MAX_WINDOW_H * 3600:
            self.t1 = min(self.t0 + 2 * (self.t1 - self.t0), self.t0 + MAX_WINDOW_H * 3600)
            self.env.run(until=self.t1)
        for h in list(self.open):
            self._end_busy(h)
        window = self.t1 - self.t0
        util = {i: self.busy[i] / (window * self.caps[i]) for i in self.res}
        for sid, beam in self.beam.items():  # share of the beamtime on offer in the window that was used
            used = sum(x for t, x in self.beam_used[sid] if self.t0 <= t < self.t1)
            util[f"{sid}__beamtime"] = min(1.0, used / (beam.capacity * window / DAY_S))
        for op in self.ops.values():
            shift = op.shift_seconds(self.t0, self.t1)
            util[op.id] = self.busy[op.id] / shift if shift else 0.0
        return {"units": self.completed * self.units_per_labware, "window_h": window / 3600,
                "horizon_h": self.t1 / 3600, "cycle": self.cycle, "util": util,
                "waits": {i: statistics.mean(w) for i, w in self.waits.items() if w}, "timeline": self.timeline,
                "staffing": self.staffing_issues, "unassigned": sorted(self.unassigned_used)}


def warmup_hours(spec: dict, workflow: dict) -> float:
    """Time to fill the pipeline before throughput is measured: 1.5x the longest mean path, plus a day with humans."""
    longest = {}
    for s in topo_order(workflow["steps"]):
        own = s["duration_s"] + _uncertain((s.get("params") or {}).get("queue_time_s"))[1]
        longest[s["id"]] = own + max([longest[p] for p in s.get("after", [])] + [0])
    hours = 1.5 * max(longest.values(), default=0) / 3600
    if any(step_mode(s) in ("manual", "semi_automated") for s in workflow["steps"]) or spec.get("operators"):
        hours += 24
    return float(max(1, math.ceil(hours)))


def run_replicate(spec: dict, workflow: dict, layout: dict, hours: float, seed: int, pins: dict[str, str] | None = None,
                  record: bool = False, capacity_overrides: dict[str, int] | None = None,
                  downtime: dict[str, dict] | None = None) -> dict:
    """One Monte Carlo replicate; JSON in, JSON out so it can run remotely (Modal)."""
    warm = warmup_hours(spec, workflow)
    model = Model(spec, workflow, layout, warm * 3600, (warm + hours) * 3600, random.Random(seed), pins, record,
                  capacity_overrides, downtime)
    out = model.run_until_end()
    out["per_day"] = out["units"] / out["window_h"] * spec["throughput_target"].get("operating_hours_per_day", 24)
    return out


def simulate(spec: dict, workflow: dict, layout: dict, hours: float = 72, replicates: int = 20, seed: int = 0,
             sensitivity: bool = True, backend: str | None = None, capacity_overrides: dict[str, int] | None = None,
             downtime: dict[str, dict] | None = None) -> dict:
    """Monte Carlo over duration uncertainty. `hours` is the minimum measurement window after warm-up.

    `backend` picks where replicates run: "serial", "process" (local cores) or "modal"; default from
    LABFORGE_SIM_BACKEND, else serial. Sensitivity re-runs the top uncertain inputs pinned low and high.
    `capacity_overrides` ({instance: slots}) is for what-if sweeps. `downtime` ({instance: spec}, default off)
    makes instruments or robots unavailable for failures or charging; see Model._down_intervals."""
    rng = random.Random(seed)
    seeds = [rng.randrange(2**31) for _ in range(replicates)]
    base = dict(spec=spec, workflow=workflow, layout=layout, hours=hours, capacity_overrides=capacity_overrides,
                downtime=downtime)
    runs = map_replicates([dict(base, seed=s, record=(k == 0)) for k, s in enumerate(seeds)], backend)
    result = summarise(spec, workflow, layout, hours, runs)
    if sensitivity:
        result["sensitivity"] = sensitivity_analysis(base, seeds, runs, backend)
    return result


def simulate_many(spec: dict, variants: list[dict], hours: float = 48, replicates: int = 8, seed: int = 0,
                  backend: str | None = None) -> list[dict]:
    """Several design variants ({workflow, layout, capacity_overrides?}) with the same seeds, as one batch of jobs.

    Common random numbers make differences between variants the change itself, not noise; one batch lets
    local processes or Modal run every point of a sweep at once."""
    rng = random.Random(seed)
    seeds = [rng.randrange(2**31) for _ in range(replicates)]
    jobs = [dict(spec=spec, workflow=v["workflow"], layout=v["layout"], hours=hours, seed=s,
                 capacity_overrides=v.get("capacity_overrides")) for v in variants for s in seeds]
    runs = map_replicates(jobs, backend)
    n = len(seeds)
    return [summarise(spec, v["workflow"], v["layout"], hours, runs[k * n:(k + 1) * n]) for k, v in enumerate(variants)]


def sensitivity_candidates(workflow: dict, layout: dict, util: dict[str, float]) -> list[tuple[str, str, float]]:
    """(parameter, pin key, screening score) for inputs that could move throughput: wide ranges on busy resources."""
    catalog = load_catalog()
    items = {e["instance_id"]: catalog.get(e["catalog_id"]) for e in workflow["equipment"]}
    ops_util = [u for i, u in util.items() if i in {o["id"] for o in layout.get("operators", [])}]
    out = []
    for s in workflow["steps"]:
        mode = step_mode(s)
        item = items.get(s["candidate_instances"][0]) if s["candidate_instances"] else None
        low, mid, high = duration_range(s, item)
        if mid <= 0 or high - low <= 0.02 * mid:
            continue
        if s["candidate_instances"]:
            busy = max(util.get(c, 0.0) for c in s["candidate_instances"])
            if mode in ("manual", "semi_automated"):
                busy = max([busy] + ops_util)
        elif mode == "manual":
            busy = max(ops_util, default=0.0)
        elif mode == "external" and (s.get("params") or {}).get("max_concurrent"):
            busy = 1.0
        else:
            continue  # pure delays (in silico, unlimited external) add latency, not a throughput limit
        out.append((f"{s['id']}.duration_s", s["id"], busy * (high - low) / mid))
        q = _uncertain((s.get("params") or {}).get("queue_time_s"))
        if mode == "external" and (s.get("params") or {}).get("max_concurrent") and q[2] > q[0]:
            out.append((f"{s['id']}.queue_time_s", f"{s['id']}.queue", (q[2] - q[0]) / max(q[1] + mid, 1)))
    operators = {o["id"] for o in layout.get("operators", [])}
    if any(t["transporter_instance"] in operators for t in layout.get("transfers", [])):
        busy = max(ops_util, default=0.0)
        out.append(("operator_walking_time", "operator_walking", busy * (HUMAN_WALK_BAND[1] - HUMAN_WALK_BAND[0])))
    return sorted((c for c in out if c[2] >= SENSITIVITY_MIN_SCORE), key=lambda c: -c[2])[:SENSITIVITY_TOP]


def sensitivity_analysis(base: dict, seeds: list[int], runs: list[dict], backend: str | None) -> list[dict]:
    """One-at-a-time swings with common random numbers: p50 with the input at its high end minus at its low end."""
    util = {i: statistics.mean(r["util"][i] for r in runs) for i in runs[0]["util"]}
    cands = sensitivity_candidates(base["workflow"], base["layout"], util)
    seeds = seeds[:SENSITIVITY_REPS]
    jobs = [dict(base, seed=s, pins={pin: end}) for _, pin, _ in cands for end in ("low", "high") for s in seeds]
    results = map_replicates(jobs, backend)
    out, n = [], len(seeds)
    for k, (param, _, _) in enumerate(cands):
        lo = results[2 * k * n:(2 * k + 1) * n]
        hi = results[(2 * k + 1) * n:(2 * k + 2) * n]
        effect = statistics.median(r["per_day"] for r in hi) - statistics.median(r["per_day"] for r in lo)
        out.append({"parameter": param, "effect": round(effect, 1)})
    return sorted(out, key=lambda e: -abs(e["effect"]))


def summarise(spec: dict, workflow: dict, layout: dict, hours: float, runs: list[dict]) -> dict:
    target = spec["throughput_target"]["value"]
    unit = spec["throughput_target"]["unit"]
    tputs = sorted(r["per_day"] for r in runs)
    q = statistics.quantiles(tputs, n=10, method="inclusive") if len(tputs) > 1 else tputs * 9
    p50 = statistics.median(tputs)
    util = {i: statistics.mean(r["util"][i] for r in runs) for i in runs[0]["util"]}
    waits = runs[0]["waits"]
    cycle = [c for r in runs for c in r["cycle"]]
    cycle_mean = statistics.mean(cycle) if cycle else 0.0

    bottlenecks = _bottlenecks(workflow, layout, runs[0], util, p50, unit, cycle_mean)
    result = {
        "id": f"{layout['id']}_sim",
        "layout_id": layout["id"],
        "simulated_hours": round(max(r["horizon_h"] for r in runs), 1),
        "replicates": len(runs),
        "throughput": {"value": round(p50, 1), "unit": unit, "target": target, "meets_target": p50 >= target,
                       "p10": round(q[0], 1), "p50": round(p50, 1), "p90": round(q[-1], 1),
                       "prob_meets_target": round(sum(t >= target for t in tputs) / len(tputs), 2)},
        "cycle_time_s": round(cycle_mean, 1),
        "utilisation": [{"instance_id": i, "busy_fraction": round(min(u, 1.0), 3), "mean_queue_wait_s": round(waits.get(i, 0.0), 1)}
                        for i, u in util.items()],
        "bottlenecks": bottlenecks,
        "sensitivity": [],
        "timeline": runs[0]["timeline"],
    }
    return validate(result, "sim_result")


def _bottlenecks(workflow: dict, layout: dict, run: dict, util: dict, p50: float, unit: str, cycle_mean: float) -> list[dict]:
    out = []
    movers = {t["transporter_instance"] for t in layout.get("transfers", [])}
    operators = {o["id"] for o in layout.get("operators", [])}
    for step_id, severity, message in run["staffing"]:
        out.append({"kind": "operator_capacity", "instances": [], "severity": severity, "message": message,
                    "suggestion": "Staff an operator with the right role and shift, or automate the step."})
    for a, b in run["unassigned"]:
        out.append({"kind": "transporter_capacity", "instances": [a, b], "severity": "high",
                    "message": f"Nothing can move labware from {a} to {b}; the simulation assumed a "
                               f"{UNASSIGNED_CARRY_S:.0f} s carry (placeholder).",
                    "suggestion": "Add an arm or operator that reaches both."})
    for inst, u in sorted(util.items(), key=lambda kv: -kv[1]):
        if u <= 0.7:
            continue
        if inst.endswith("__beamtime"):
            step_id = inst[: -len("__beamtime")]
            cap = f"; it caps throughput near {p50 / u:.0f} {unit.replace('_', ' ')}" if u > 0.85 and p50 > 0 else ""
            out.append({"kind": "external_queue", "instances": [], "severity": "high" if u > 0.85 else "medium",
                        "message": f"Step {step_id} uses {u:.0%} of the beamtime on offer (params.beamtime_h_per_day){cap}.",
                        "suggestion": "Book more beamtime, collect fewer datasets per crystal, or shorten exposures."})
            continue
        kind = "operator_capacity" if inst in operators else "transporter_capacity" if inst in movers else "instrument_capacity"
        what = f"busy {u:.0%} of their shift" if inst in operators else f"busy {u:.0%} of the time"
        cap = f"; it caps throughput near {p50 / u:.0f} {unit.replace('_', ' ')}" if u > 0.85 and p50 > 0 else ""
        out.append({"kind": kind, "instances": [inst], "severity": "high" if u > 0.85 else "medium",
                    "message": f"{inst} is {what}{cap}.",
                    "suggestion": "Add a second operator or stagger shifts." if inst in operators
                    else "Add a parallel unit or move slow steps elsewhere."})
    for s in workflow["steps"]:
        if step_mode(s) != "external":
            continue
        latency = s["duration_s"] + _uncertain((s.get("params") or {}).get("queue_time_s"))[1]
        if cycle_mean and latency > 0.2 * cycle_mean:
            out.append({"kind": "external_queue", "instances": [], "severity": "medium" if latency > 0.5 * cycle_mean else "low",
                        "message": f"External step '{s['name']}' takes about {latency / 3600:.0f} h of the "
                                   f"{cycle_mean / 3600:.0f} h cycle; the layout cannot shorten it.",
                        "suggestion": "Batch shipments and book access early; report turnaround as a range."})
    for t in layout.get("transfers", []):
        if t["distance_m"] > 5:
            out.append({"kind": "long_transfer", "instances": [t["from_instance"], t["to_instance"]], "severity": "medium",
                        "message": f"Labware travels {t['distance_m']} m from {t['from_instance']} to {t['to_instance']}."})
    rank = {"high": 0, "medium": 1, "low": 2}
    return sorted(out, key=lambda b: rank[b["severity"]])
