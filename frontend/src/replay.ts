import { marked } from "marked";
import type { CaseSummary, CatalogItem, Design, InstrumentOptimisation } from "./types";

/**
 * Strand A: ?replay=<name> plays a recorded agent run from /replays/<name>.json at demo speed with no backend
 * calls: the brief, the agent's tool calls in order, then (if the run produced one) the layout, the timeline
 * animation and the BOM/report; otherwise the agent's own explanation of why it stopped.
 * Files come from backend/labforge/agent/demo (python -m labforge.agent.demo_scenarios), copied by
 * frontend/scripts/copy_replays.py, which also attaches the catalog entries the run uses.
 */

export interface RecordedRun {
  brief: string; model?: string; source?: string;
  /** Set by copy_replays.py when the recorded sim_result had no timeline and it was recomputed from the design. */
  timeline_source?: string;
  output: {
    messages?: { role: string; content: unknown }[];
    lab_spec?: any; workflow?: Design["workflow"]; layout?: Design["layout"]; sim_result?: Design["sim_result"];
    claims?: import("./verdicts").CheckedClaim[]; report_markdown?: string;
  };
  events?: { type: string; name?: string; input?: Record<string, unknown>; step?: number; text?: string; error?: string }[];
  gate?: { passed?: boolean; missing_capabilities?: string[] };
  catalog?: Record<string, CatalogItem>;
}

/** One agent event, as recorded in a run's `events` or streamed live by POST /chat/stream. */
export type AgentEvent = { type: string; name?: string; input?: Record<string, unknown>; step?: number; text?: string; error?: string; message?: string; output?: any };

export interface ReplayHooks {
  say: (lines: string[], speaker?: string) => void;
  /** A plain log entry: the brief, or the agent's answer. */
  log: (line: string, kind: "user" | "agent") => void;
  /** Every recorded agent event, for the structured agent log. */
  event: (e: AgentEvent) => void;
  showDesign: (d: Design) => void;
  showAnswer: (title: string, html: string) => void;
}

const runs = new Map<string, Promise<RecordedRun>>();
const base = () => (import.meta as any).env?.BASE_URL ?? "/";

/** Load (once) a recorded run from public/replays/<name>.json. */
export function loadReplay(name: string): Promise<RecordedRun> {
  if (!runs.has(name)) {
    const p = (async () => {
      const res = await fetch(`${base()}replays/${encodeURIComponent(name)}.json`);
      // Dev servers and static hosts often answer a missing file with index.html and status 200, so check the body too.
      const text = res.ok ? await res.text() : "";
      if (!text.trimStart().startsWith("{"))
        throw new Error(`There is no recorded run called "${name}" yet, so there is nothing to replay. (Looked for public/replays/${name}.json.)`);
      return JSON.parse(text) as RecordedRun;
    })();
    p.catch(() => runs.delete(name)); // let a later visit retry
    runs.set(name, p);
  }
  return runs.get(name)!;
}

/** Optional public/replays/<name>.summary.json: headline, independent check, gate and limits for a recording. */
export async function loadSummary(name: string): Promise<CaseSummary | undefined> {
  try {
    const res = await fetch(`${base()}replays/${encodeURIComponent(name)}.summary.json`);
    const text = res.ok ? await res.text() : "";
    return text.trimStart().startsWith("{") ? JSON.parse(text) : undefined;
  } catch {
    return undefined;
  }
}

/**
 * Optional cached what-if sweeps for a case (public/replays/<name>.whatif.json, written by
 * frontend/scripts/cache_whatif.py), so the case's what-if also works without the backend.
 */
export async function loadWhatIfCache(name: string): Promise<Record<string, InstrumentOptimisation> | undefined> {
  try {
    const res = await fetch(`${base()}replays/${encodeURIComponent(name)}.whatif.json`);
    const text = res.ok ? await res.text() : "";
    return text.trimStart().startsWith("{") ? JSON.parse(text).by_instance : undefined;
  } catch {
    return undefined;
  }
}

/** A room with nothing in it, shown while the recorded agent is still "working". */
export function emptyDesign(lab_spec?: any): Design {
  const room = lab_spec?.room ?? {};
  return {
    lab_spec: lab_spec ?? {}, catalog: {},
    workflow: { id: "pending", equipment: [] },
    layout: { id: "pending", room: { width_m: room.width_m ?? 10, depth_m: room.depth_m ?? 8 }, placements: [], transfers: [] },
    sim_result: { throughput: { value: 0, unit: "" }, utilisation: [], bottlenecks: [] },
  };
}

const humanise = (s: unknown) => String(s).replace(/_/g, " ");

/** One line per recorded event, in the agent's voice. */
export function describe(e: AgentEvent): string | undefined {
  const i = e.input ?? {};
  switch (e.type) {
    case "model_call": return `Thinking (step ${e.step ?? "?"})…`;
    case "tool_error": return `${humanise(e.name)} failed: ${e.error ?? "error"}`;
    case "tool_start":
      switch (e.name) {
        case "search_catalog":
          return i.capability ? `Searching the catalog for ${humanise(i.capability)}…` : i.labware ? `Searching the catalog for ${humanise(i.labware)} labware…` : "Listing the whole catalog…";
        case "search_evidence": return `Looking for evidence: “${i.query ?? ""}”`;
        case "layout_and_simulate": return "Laying out the room and simulating it…";
        case "verify_claims": return "Checking my claims against the simulator…";
        case "create_report": return "Writing the report…";
        case "optimise_instrument": return `Trying what-ifs on ${humanise(i.instance_id ?? "an instrument")}…`;
        case "plan_projects": return "Planning the project order…";
        default: return `${humanise(e.name)}…`;
      }
    default: return undefined; // text deltas, tool_end and assistant_text are summarised by the final message
  }
}

const textOf = (c: unknown): string =>
  typeof c === "string" ? c : Array.isArray(c) ? c.map((b: any) => (typeof b === "string" ? b : b?.text ?? "")).join("\n") : "";

/** First heading or sentence of a Markdown answer, for the dialogue box. */
function headline(md: string): string {
  const h = md.match(/^#+\s*(.+)$/m)?.[1];
  return (h ?? md.split(/(?<=[.!?])\s/)[0] ?? "").replace(/[*`_]/g, "").trim();
}

/** Resolves after ms, or as soon as skip.now is set. Timer-based so it also runs while the tab renders slowly. */
const wait = (ms: number, skip: { now: boolean }) =>
  new Promise<void>((resolve) => {
    if (skip.now) return resolve(); // after Skip, run straight through to the final state
    let left = ms;
    const id = setInterval(() => { left -= 100; if (skip.now || left <= 0) { clearInterval(id); resolve(); } }, 100);
  });

/** Play the run. `skip.now = true` fast-forwards to the end state. */
export async function playReplay(run: RecordedRun, hooks: ReplayHooks, skip: { now: boolean }) {
  hooks.log(`You: ${run.brief}`, "user");
  hooks.say([run.brief], "YOU");
  await wait(4500, skip);

  for (const e of run.events ?? []) {
    hooks.event(e);
    const line = describe(e);
    if (!line) continue; // ends and results update the log but don't pace the replay
    if (!skip.now) hooks.say([line]);
    await wait(e.type === "model_call" ? 1400 : 700, skip);
  }

  const o = run.output;
  const answer = textOf([...(o.messages ?? [])].reverse().find((m) => m.role === "assistant")?.content ?? "");
  if (o.layout && o.workflow && o.sim_result && o.lab_spec) {
    const design: Design = {
      lab_spec: o.lab_spec, workflow: o.workflow, layout: o.layout, sim_result: o.sim_result,
      catalog: run.catalog ?? {}, report_markdown: o.report_markdown,
      timeline_note: run.timeline_source ? "timeline recomputed from recorded design" : "recorded run",
    };
    hooks.showDesign(design);
    if (answer) hooks.log(`Agent: ${answer}`, "agent");
    return;
  }
  // No design: the agent stopped. Show its own explanation; that refusal is the honest result.
  const missing = run.gate?.missing_capabilities ?? [];
  hooks.log(`Agent: ${answer}`, "agent");
  hooks.say([headline(answer) || "I stopped before producing a design.",
    ...(missing.length ? [`The catalog has nothing for: ${missing.map(humanise).join(", ")}.`] : [])]);
  if (answer) hooks.showAnswer("The agent's answer", await marked.parse(answer.replace(/</g, "&lt;")));
}
