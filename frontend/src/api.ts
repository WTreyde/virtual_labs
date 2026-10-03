import catalogList from "../../examples/catalog.json";
import labSpec from "../../examples/lab_spec.json";
import layout from "../../examples/layout.json";
import simResult from "../../examples/sim_result.json";
import workflow from "../../examples/workflow.json";
import cachedOptimise from "./fixtures/example_optimise.json";
import cachedTimeline from "./fixtures/example_timeline.json";
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

export async function chat(messages: ChatMessage[], current: Design): Promise<{ reply: string; design: Design; history: ChatMessage[] }> {
  const res = await apiFetch("/chat", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ messages }) });
  const out = await res.json();
  if (!res.ok || out.type === "error") throw new Error(out.detail ?? out.message ?? `Chat failed: HTTP ${res.status}`);
  const catalog = byId(await (await apiFetch("/catalog")).json());
  const design = out.layout ? { lab_spec: out.lab_spec, workflow: out.workflow, layout: out.layout, sim_result: out.sim_result, catalog, report_markdown: out.report_markdown } : current;
  const reply = out.messages?.at(-1)?.content ?? "";
  return { reply, design, history: out.history ?? [...messages, { role: "assistant", content: reply }] };
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
