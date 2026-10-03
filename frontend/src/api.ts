import catalogList from "../../examples/catalog.json";
import labSpec from "../../examples/lab_spec.json";
import layout from "../../examples/layout.json";
import simResult from "../../examples/sim_result.json";
import workflow from "../../examples/workflow.json";
import type { CatalogItem, Design } from "./types";

export const API = (import.meta as any).env?.VITE_API ?? "http://localhost:8000";

const byId = (items: CatalogItem[]) => Object.fromEntries(items.map((i) => [i.id, i]));

/** The worked example, bundled so the client renders with no backend running. */
export function exampleDesign(): Design {
  return { lab_spec: labSpec, workflow, layout, sim_result: simResult, catalog: byId(catalogList as CatalogItem[]) } as Design;
}

export async function chat(messages: { role: string; content: string }[], current: Design): Promise<{ reply: string; design: Design }> {
  const res = await fetch(`${API}/chat`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ messages }) });
  const out = await res.json();
  const catalog = byId(await (await fetch(`${API}/catalog`)).json());
  const design = out.layout ? { lab_spec: out.lab_spec, workflow: out.workflow, layout: out.layout, sim_result: out.sim_result, catalog } : current;
  return { reply: out.messages?.at(-1)?.content ?? "", design };
}

export async function report(d: Design): Promise<string> {
  const body = { lab_spec: d.lab_spec, workflow: d.workflow, layout: d.layout, sim_result: d.sim_result };
  const res = await fetch(`${API}/report`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  return res.text();
}
