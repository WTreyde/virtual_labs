import type { TimelineEvent } from "./types";

/**
 * Turns SimResult.timeline into things the scene can draw at any sim time t:
 * steps (labware inside an instrument) and moves (labware being carried).
 * The simulator logs `transfer_start` with only the transporter, so a move's origin is the labware's
 * previous instrument and its destination comes from its next `step_start`. That step can start long after
 * the transfer began when the destination is busy, so a move lasts only the travel time and the rest is
 * counted as queueing at the destination.
 */

/** Shared sim clock: the scene advances it, the HTML controls read and set it. */
export const clock = { t: 0, end: 0, speed: 300, playing: true };

export interface Step { labware: string; instance: string; step?: string; t0: number; t1: number }
export interface Move { labware: string; by: string; from?: string; to: string; t0: number; t1: number }

export class Timeline {
  readonly steps: Step[] = [];
  readonly moves: Move[] = [];
  readonly queues: Step[] = [];
  readonly end: number;

  /** `travel` gives the transfer time in seconds between two instances (e.g. from layout est_time_s). */
  constructor(events: TimelineEvent[], travel: (from: string | undefined, to: string) => number = () => 15) {
    const byLab = new Map<string, TimelineEvent[]>();
    for (const e of [...events].sort((a, b) => a.t_s - b.t_s)) {
      if (!byLab.has(e.labware_id)) byLab.set(e.labware_id, []);
      byLab.get(e.labware_id)!.push(e);
    }
    this.end = Math.max(0, ...events.map((e) => e.t_s));
    for (const [labware, evs] of byLab) {
      let at: string | undefined;
      evs.forEach((e, i) => {
        if (e.event === "step_start" && e.instance_id) {
          const close = evs.slice(i + 1).find((f) => f.event === "step_end" && f.instance_id === e.instance_id);
          this.steps.push({ labware, instance: e.instance_id, step: e.step_id, t0: e.t_s, t1: close?.t_s ?? this.end });
          at = e.instance_id;
        } else if (e.event === "transfer_start" && e.instance_id) {
          const arrive = evs.slice(i + 1).find((f) => f.event === "step_start" && f.instance_id);
          if (!arrive) return;
          const to = arrive.instance_id!, t1 = Math.min(arrive.t_s, e.t_s + travel(at, to));
          this.moves.push({ labware, by: e.instance_id, from: at, to, t0: e.t_s, t1 });
          if (arrive.t_s > t1) this.queues.push({ labware, instance: to, t0: t1, t1: arrive.t_s });
        }
      });
    }
  }

  /** Enough events to be worth animating (the bundled examples/sim_result.json has only two). */
  get usable() { return this.moves.length >= 3; }

  /** Steps running at time t, grouped by instance. Zero-length steps (e.g. hotel `load`) are skipped. */
  activeSteps(t: number) { return Timeline.at(this.steps, t); }

  /** Labware waiting at time t for a busy instance, grouped by that instance. */
  queuedAt(t: number) { return Timeline.at(this.queues, t); }

  private static at(list: Step[], t: number): Map<string, Step[]> {
    const out = new Map<string, Step[]>();
    for (const s of list)
      if (s.t1 > s.t0 && s.t0 <= t && t < s.t1) {
        if (!out.has(s.instance)) out.set(s.instance, []);
        out.get(s.instance)!.push(s);
      }
    return out;
  }

  /**
   * Moves in flight at t, with progress f in [0, 1]. Transfers take seconds while steps take an hour,
   * so at fast-forward a move is stretched to at least `minDur` sim seconds to stay visible.
   */
  movesAt(t: number, minDur: number): { move: Move; f: number }[] {
    const out: { move: Move; f: number }[] = [];
    for (const m of this.moves) {
      const dur = Math.max(m.t1 - m.t0, minDur);
      if (m.t0 <= t && t < m.t0 + dur) out.push({ move: m, f: (t - m.t0) / dur });
    }
    return out;
  }

  /** Labware that has finished the workflow's final step by time t. */
  finishedBy(t: number, lastStep?: string): number {
    return this.steps.filter((s) => s.step === lastStep && s.t1 <= t && s.t1 < this.end).length;
  }
}
