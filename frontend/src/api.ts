import catalogList from "../../examples/catalog.json";
import labSpec from "../../examples/lab_spec.json";
import layout from "../../examples/layout.json";
import simResult from "../../examples/sim_result.json";
import workflow from "../../examples/workflow.json";
import cachedOptimise from "./fixtures/example_optimise.json";
import cachedSchedule from "./fixtures/example_schedule.json";
import cachedTimeline from "./fixtures/example_timeline.json";
import type { CatalogItem, Design, InstrumentOptimisation, ProjectRequest, ProjectSchedule } from "./types";

export const API = (import.meta as any).env?.VITE_API ?? "http://localhost:8000";

const byId = (items: CatalogItem[]) => Object.fromEntries(items.map((i) => [i.id, i]));

/** The worked example, bundled so the client renders with no backend running. */
export function exampleDesign(): Design {
  const d = { lab_spec: labSpec, workflow, layout, sim_result: simResult, catalog: byId(catalogList as CatalogItem[]) } as Design;
  // examples/sim_result.json carries a two-event stub timeline; use a cached run of the real simulator instead.
  if ((d.sim_result.timeline?.length ?? 0) < 20)
    return { ...d, sim_result: { ...d.sim_result, timeline: cachedTimeline.timeline as Design["sim_result"]["timeline"] }, timeline_note: "cached sim run" };
  return d;
}

export async function chat(messages: { role: string; content: string }[], current: Design): Promise<{ reply: string; design: Design }> {
  const res = await fetch(`${API}/chat`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ messages }) });
  const out = await res.json();
  const catalog = byId(await (await fetch(`${API}/catalog`)).json());
  const design = out.layout ? { lab_spec: out.lab_spec, workflow: out.workflow, layout: out.layout, sim_result: out.sim_result, catalog } : current;
  return { reply: out.messages?.at(-1)?.content ?? "", design };
}

/** Live catalog entries for the design's items, so the BOM matches the backend report. Throws when offline. */
export async function liveCatalog(d: Design): Promise<Design["catalog"]> {
  const live = byId(await (await fetch(`${API}/catalog`, { signal: AbortSignal.timeout(3000) })).json());
  const ids = d.workflow.equipment.map((e) => e.catalog_id);
  if (!ids.every((id) => live[id])) throw new Error("live catalog lacks some items");
  return { ...d.catalog, ...live };
}

export async function report(d: Design): Promise<string> {
  const body = { lab_spec: d.lab_spec, workflow: d.workflow, layout: d.layout, sim_result: d.sim_result };
  const res = await fetch(`${API}/report`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  return res.text();
}

const post = async <T>(path: string, body: unknown): Promise<T> => {
  const res = await fetch(`${API}${path}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body), signal: AbortSignal.timeout(30000) });
  if (!res.ok) throw new Error(`${path}: HTTP ${res.status}`);
  return res.json();
};

/** Vendor what-if for one instance. Offline, falls back to a cached run for the bundled example only. */
export async function optimise(d: Design, instance_id: string): Promise<{ result: InstrumentOptimisation; cached: boolean }> {
  try {
    return { result: await post<InstrumentOptimisation>("/optimise", { lab_spec: d.lab_spec, workflow: d.workflow, layout: d.layout, instance_id }), cached: false };
  } catch (e) {
    const hit = d.layout.id === layout.id ? (cachedOptimise.by_instance as Record<string, InstrumentOptimisation>)[instance_id] : undefined;
    if (!hit) throw e;
    return { result: hit, cached: true };
  }
}

/** Best order or mix for several projects. Offline, falls back to a cached run of the bundled fixture projects. */
export async function prioritise(projects: ProjectRequest[], lab_id: string): Promise<{ result: ProjectSchedule; cached: boolean }> {
  try {
    return { result: await post<ProjectSchedule>("/prioritise", { projects, lab_id }), cached: false };
  } catch {
    return { result: cachedSchedule.schedule as ProjectSchedule, cached: true };
  }
}
