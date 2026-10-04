import demoQueue from "../../backend/labforge/catalog/data/demo_prioritise_queue.json";
import { catalogItems, prioritise } from "./api";
import cachedDemoSchedule from "./fixtures/demo_schedule.json";
import { loadReplay } from "./replay";
import type { ProjectRequest, ProjectSchedule } from "./types";

/**
 * Strand A: the scheduling case study (#/case/schedule). Max's demo queue (three projects sharing one existing
 * screening cell) run through POST /prioritise, or its cached result offline. Shared by the case card and the page so
 * both show the same numbers.
 */
export interface ScheduleCase {
  projects: ProjectRequest[]; result: ProjectSchedule; cached: boolean;
  deviceNames: Record<string, { short: string; full: string }>;
}

let pending: Promise<ScheduleCase> | undefined;
export function loadScheduleCase(): Promise<ScheduleCase> {
  return (pending ??= (async () => {
    const projects = demoQueue.projects as unknown as ProjectRequest[];
    const extra = await Promise.all(["chem", "fbdd"].map((n) => loadReplay(n).then((x) => x.catalog ?? {}).catch(() => ({}))));
    const [{ result, cached }, catalog] = await Promise.all([
      prioritise(projects, demoQueue.lab_id, cachedDemoSchedule.schedule as ProjectSchedule), catalogItems(extra)]);
    // Instruments by vendor and model, not instance id; a readable catalog id when the catalog doesn't have it.
    const deviceNames: ScheduleCase["deviceNames"] = {};
    for (const p of projects) for (const e of p.workflow.equipment) {
      const it = catalog[e.catalog_id], fallback = e.catalog_id.replace(/_/g, " ");
      deviceNames[e.instance_id] = it ? { short: it.model, full: `${it.vendor} ${it.model}` } : { short: fallback, full: fallback };
    }
    return { projects, result, cached, deviceNames };
  })().catch((e) => { pending = undefined; throw e; }));
}

/**
 * The Monte Carlo check the backend reports in the schedule's caveat (median and P10-P90 over N runs with random step
 * times). The case card and page lead with these medians, the same pair as the README and the pitch; the Gantt and the
 * table stay on average step times. Undefined when the caveat doesn't have the usual shape.
 */
export interface ScheduleMC { reps: number; rec: number; recLo: number; recHi: number; naive: number; naiveLo: number; naiveHi: number; firstPct: number }
export function scheduleMC(caveat?: string): ScheduleMC | undefined {
  const m = caveat?.match(/\((\d+) replicates\):\s*recommended ([\d.]+) h \(P10-P90 ([\d.]+)-([\d.]+) h\) vs order given ([\d.]+) h \(([\d.]+)-([\d.]+) h\); recommended finishes first in (\d+)% of replicates/);
  if (!m) return undefined;
  const [reps, rec, recLo, recHi, naive, naiveLo, naiveHi, firstPct] = m.slice(1).map(Number);
  return { reps, rec, recLo, recHi, naive, naiveLo, naiveHi, firstPct };
}
