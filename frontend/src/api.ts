import catalogList from "../../examples/catalog.json";
import labSpec from "../../examples/lab_spec.json";
import layout from "../../examples/layout.json";
import simResult from "../../examples/sim_result.json";
import workflow from "../../examples/workflow.json";
import cachedOptimise from "./fixtures/example_optimise.json";
import cachedTimeline from "./fixtures/example_timeline.json";
import type { AgentEvent } from "./replay";
import type { CatalogItem, ChatMessage, Design, InstrumentOptimisation, Leaderboard, ProjectRequest, ProjectSchedule, ValidationRow } from "./types";

export const API = (import.meta as any).env?.VITE_API ?? "http://localhost:8000";

/** Replay mode sets this so nothing talks to the backend; every call then fails fast into its offline fallback. */
let offline = false;
export function setOffline(on: boolean) { offline = on; }
const apiFetch = (path: string, init?: RequestInit): Promise<Response> =>
  offline ? Promise.reject(new Error("offline (replay mode)")) : fetch(`${API}${path}`, init);

const byId = (items: CatalogItem[]) => Object.fromEntries(items.map((i) => [i.id, i]));

/** The worked example, bundled so the client renders with no backend running. */
export function exampleDesign(): Design {
  const d = { lab_spec: labSpec, workflow, layout, sim_result: simResult, catalog: byId(catalogList as CatalogItem[]) } as Design;
  // examples/sim_result.json carries a two-event stub timeline; use a cached run of the real simulator instead.
  if ((d.sim_result.timeline?.length ?? 0) < 20)
    return { ...d, sim_result: { ...d.sim_result, timeline: cachedTimeline.timeline as Design["sim_result"]["timeline"] }, timeline_note: "cached sim run" };
  return d;
}

type ChatOut = { reply: string; design: Design; history: ChatMessage[] };

/** Turn a /chat result (or the stream's final `result.output`) into the client's design and history. */
async function chatResult(out: any, messages: ChatMessage[], current: Design): Promise<ChatOut> {
  const catalog = byId(await (await apiFetch("/catalog")).json());
  const design = out.layout ? { lab_spec: out.lab_spec, workflow: out.workflow, layout: out.layout, sim_result: out.sim_result, catalog, report_markdown: out.report_markdown } : current;
  const reply = out.messages?.at(-1)?.content ?? "";
  return { reply, design, history: out.history ?? [...messages, { role: "assistant", content: reply }] };
}

export async function chat(messages: ChatMessage[], current: Design): Promise<ChatOut> {
  const res = await apiFetch("/chat", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ messages }) });
  const out = await res.json();
  if (!res.ok || out.type === "error") throw new Error(out.detail ?? out.message ?? `Chat failed: HTTP ${res.status}`);
  return chatResult(out, messages, current);
}

/**
 * POST /chat/stream (SSE): calls `onEvent` for every agent event as it happens (model calls, tool calls, text),
 * then resolves with the final result like chat(). Falls back to POST /chat if the backend has no stream route.
 */
export async function chatStream(messages: ChatMessage[], current: Design, onEvent: (e: AgentEvent) => void): Promise<ChatOut> {
  const res = await apiFetch("/chat/stream", { method: "POST", headers: { "Content-Type": "application/json", Accept: "text/event-stream" }, body: JSON.stringify({ messages }) });
  if (res.status === 404 || res.status === 405) return chat(messages, current);
  if (!res.ok || !res.body) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? body.message ?? `Chat failed: HTTP ${res.status}`);
  }
  const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
  let buf = "", result: any;
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += value;
    let cut: number;
    while ((cut = buf.indexOf("\n\n")) >= 0) {
      const frame = buf.slice(0, cut);
      buf = buf.slice(cut + 2);
      const data = frame.split("\n").filter((l) => l.startsWith("data:")).map((l) => l.slice(5).trimStart()).join("\n");
      if (!data) continue; // ": keepalive" comments
      const e = JSON.parse(data) as AgentEvent;
      if (e.type === "error") throw new Error(e.message ?? "The agent failed");
      if (e.type === "result") result = e.output;
      else onEvent(e);
    }
  }
  if (!result) throw new Error("The agent stream ended without a result");
  return chatResult(result, messages, current);
}

/** Live catalog entries for the design's items, so the BOM matches the backend report. Throws when offline. */
export async function liveCatalog(d: Design): Promise<Design["catalog"]> {
  const live = byId(await (await apiFetch("/catalog", { signal: AbortSignal.timeout(3000) })).json());
  const ids = d.workflow.equipment.map((e) => e.catalog_id);
  if (!ids.every((id) => live[id])) throw new Error("live catalog lacks some items");
  return { ...d.catalog, ...live };
}

export async function report(d: Design): Promise<string> {
  if (d.report_markdown) return d.report_markdown; // recorded runs carry the agent's report
  const body = { lab_spec: d.lab_spec, workflow: d.workflow, layout: d.layout, sim_result: d.sim_result };
  const res = await apiFetch("/report", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  return res.text();
}

const post = async <T>(path: string, body: unknown): Promise<T> => {
  const res = await apiFetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body), signal: AbortSignal.timeout(30000) });
  if (!res.ok) throw new Error(`${path}: HTTP ${res.status}`);
  return res.json();
};

/** Vendor what-if for one instance. Offline, falls back to cached sweeps: the design's own, or the bundled example's. */
export async function optimise(d: Design, instance_id: string): Promise<{ result: InstrumentOptimisation; cached: boolean }> {
  try {
    return { result: await post<InstrumentOptimisation>("/optimise", { lab_spec: d.lab_spec, workflow: d.workflow, layout: d.layout, instance_id }), cached: false };
  } catch (e) {
    const hit = d.whatif_cache?.[instance_id]
      ?? (d.layout.id === layout.id ? (cachedOptimise.by_instance as Record<string, InstrumentOptimisation>)[instance_id] : undefined);
    if (!hit) throw e;
    return { result: hit, cached: true };
  }
}

/** Best order or mix for several projects. Offline, falls back to `cached` (a saved run of the same projects). */
export async function prioritise(projects: ProjectRequest[], lab_id: string, cached: ProjectSchedule): Promise<{ result: ProjectSchedule; cached: boolean }> {
  try {
    return { result: await post<ProjectSchedule>("/prioritise", { projects, lab_id }), cached: false };
  } catch {
    return { result: cached, cached: true };
  }
}

/** GET /validation: one row per published lab case, with LabForge's predicted cost band where a design exists. */
export async function validation(): Promise<ValidationRow[]> {
  const res = await apiFetch("/validation", { signal: AbortSignal.timeout(60000) });
  if (!res.ok) throw new Error(`/validation: HTTP ${res.status}`);
  return res.json();
}

/** GET /bench/leaderboard; null when no results have been committed yet (404). */
export async function leaderboard(): Promise<Leaderboard | null> {
  const res = await apiFetch("/bench/leaderboard", { signal: AbortSignal.timeout(10000) });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`/bench/leaderboard: HTTP ${res.status}`);
  return res.json();
}

export interface Health { state: "on" | "off" | "unreachable"; liveAgent: boolean; note?: string }

/**
 * GET /health, once per page load. state: "off" when live_chat is false (the public replay-only demo),
 * "unreachable" without a backend, else "on". liveAgent: the backend has an API key and runs the real agent;
 * when false, note says why (the chat then serves the offline worked example).
 */
let healthState: Promise<Health> | undefined;
export function health(): Promise<Health> {
  healthState ??= apiFetch("/health", { signal: AbortSignal.timeout(3000) })
    .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
    .then((h: { live_chat?: boolean; live_agent?: boolean; live_agent_note?: string | null }): Health => ({
      state: h.live_chat === false ? "off" : "on",
      liveAgent: h.live_agent ?? h.live_chat !== false, // older backends don't report it
      note: h.live_agent_note ?? undefined,
    }))
    .catch((): Health => ({ state: "unreachable", liveAgent: false }));
  return healthState;
}
export const liveChat = () => health().then((h) => h.state);
export const LIVE_CHAT_MESSAGE = {
  off: "Live design is off in this public demo. Watch the two recorded cases instead.",
  unreachable: "Live design needs the backend (make backend or make demo), which isn't reachable right now.",
};
