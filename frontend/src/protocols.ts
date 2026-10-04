import type { CatalogItem } from "./types";

/**
 * Strand A: the Protocols tab (#/protocols, #/protocols/<id>). Published lab protocols for the two demo pipelines,
 * paraphrased by Strand B and exported statically to public/protocols/ (cd backend && python -m labforge.protocols
 * ../frontend/public/protocols), so it works offline like the replays.
 * Honesty rules from the library README: never present a paraphrase as the official protocol, always show the source
 * link and licence, and show "time not stated by source" where a step has no duration.
 */

export interface ProtocolRow {
  id: string; title: string; domain?: string; pipeline: string; automation_level?: string; capabilities?: string[];
  n_steps?: number; catalog_ids?: string[]; license?: string; access?: string; confidence?: string;
  source: { url: string; publisher?: string; authors?: string; year?: number; doi?: string };
}
type Duration = { value: number; low?: number; high?: number; confidence: string; note?: string };
export interface Protocol extends ProtocolRow {
  summary: string; pipeline_steps?: string[]; notes?: string; retrieved?: string;
  steps: { order: number; text: string; capability?: string; catalog_ids?: string[]; duration_s?: Duration }[];
  equipment?: { name: string; catalog_id?: string }[]; materials?: string[]; safety?: string[];
}

const base = () => (import.meta as any).env?.BASE_URL ?? "/";
const esc = (s: unknown) => String(s ?? "").replace(/[&<>"]/g, (c) => `&#${c.charCodeAt(0)};`);
const human = (s?: string) => String(s ?? "").replace(/_/g, " ");

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${base()}${path}`);
  const text = res.ok ? await res.text() : "";
  if (!/^\s*[[{]/.test(text)) throw new Error(`Not found: ${path}`); // dev servers answer misses with index.html
  return JSON.parse(text);
}
let indexCache: Promise<ProtocolRow[]> | undefined;
export const protocolIndex = () => (indexCache ??= getJSON<ProtocolRow[]>("protocols/index.json"));
export const loadProtocol = (id: string) => getJSON<Protocol>(`protocols/${encodeURIComponent(id)}.json`);

/** Pipeline stages in order (docs/pipelines.md), to order protocols within a pipeline. */
const STAGES: Record<string, string[]> = {
  chem_library: ["powder_dosing", "liquid_dosing", "reaction", "heating_stirring", "inert_atmosphere", "filtration", "solid_phase_extraction",
    "evaporation", "lcms", "hplc", "liquid_handling", "compound_storage", "acoustic_dispensing", "reagent_dispensing", "incubation",
    "fluorescence_read", "absorbance_read", "luminescence_read", "in_silico"],
  xchem: ["cell_culture", "shaking", "bioreactor", "centrifugation", "cell_lysis", "protein_purification", "protein_qc", "concentration_measurement",
    "crystallization_setup", "crystal_imaging", "crystal_soaking", "acoustic_dispensing", "crystal_harvesting", "cryo_cooling", "cold_storage",
    "external_service", "xray_diffraction", "in_silico"],
};
const PIPELINE_NAME: Record<string, string> = { chem_library: "Chemistry library", xchem: "XChem" };
const pipelineName = (p: string) => PIPELINE_NAME[p] ?? "General";
const stageOf = (r: ProtocolRow) => {
  const order = STAGES[r.pipeline] ?? [];
  const idx = (r.capabilities ?? []).map((c) => order.indexOf(c)).filter((i) => i >= 0);
  return idx.length ? Math.min(...idx) : 99;
};

const AUTOMATION: Record<string, string> = { automated: "Automated", semi_automated: "Semi-automated", manual: "Manual" };
const CONF_LABEL: Record<string, string> = { datasheet: "DATASHEET", literature: "LITERATURE", estimated: "ESTIMATE", placeholder: "PLACEHOLDER" };
const badge = (c?: string) => (c ? `<span class="badge badge-${esc(c)}">${CONF_LABEL[c] ?? esc(c).toUpperCase()}</span>` : "");
const licenceBadge = (r: ProtocolRow) =>
  `<span class="lic ${r.access === "open" ? "open" : "restricted"}" title="${esc(r.license)}">${r.access === "open" ? "Open access" : esc(human(r.access) || "Access unknown")} · ${esc(r.license ?? "licence unknown")}</span>`;
const sourceLine = (s: ProtocolRow["source"]) => [s.authors, s.year, s.publisher].filter(Boolean).map(esc).join(" · ");

function duration(d?: Duration): string {
  if (!d) return `<span class="no-time">time not stated by source</span>`;
  const f = (s: number) => (s < 120 ? `${Math.round(s)} s` : s < 7200 ? `${+(s / 60).toFixed(1)} min` : `${+(s / 3600).toFixed(1)} h`);
  const range = d.low != null && d.high != null ? ` (${f(d.low)}–${f(d.high)})` : "";
  return `<span class="dur" title="${esc(d.note ?? "")}">${f(d.value)}${range}</span> ${badge(d.confidence)}`;
}

// ---- list view ----------------------------------------------------------------------------------

export interface Filters { pipeline: string; capability: string; automation: string; openOnly: boolean }
const filters: Filters = { pipeline: "", capability: "", automation: "", openOnly: false };

export async function renderProtocolList(el: HTMLElement) {
  let rows: ProtocolRow[];
  try { rows = await protocolIndex(); } catch {
    el.innerHTML = `<p class="muted">The protocol library is not available in this build (public/protocols/index.json is missing).</p>`;
    return;
  }
  const caps = [...new Set(rows.flatMap((r) => r.capabilities ?? []))].sort();
  const pipelines = [...new Set(rows.map((r) => r.pipeline))];
  const opt = (v: string, label: string, cur: string) => `<option value="${esc(v)}"${v === cur ? " selected" : ""}>${esc(label)}</option>`;
  const draw = () => {
    const shown = rows.filter((r) => (!filters.pipeline || r.pipeline === filters.pipeline) && (!filters.capability || r.capabilities?.includes(filters.capability))
      && (!filters.automation || r.automation_level === filters.automation) && (!filters.openOnly || r.access === "open"));
    const groups = [...new Set(shown.map((r) => pipelineName(r.pipeline)))].sort((a, b) => (a === "General" ? 1 : b === "General" ? -1 : a.localeCompare(b)));
    el.querySelector(".proto-groups")!.innerHTML = groups.length ? groups.map((g) => `<section class="proto-group"><h3>${esc(g)}</h3><div class="proto-cards">${
      shown.filter((r) => pipelineName(r.pipeline) === g).sort((a, b) => stageOf(a) - stageOf(b) || a.title.localeCompare(b.title)).map((r) => `
        <a class="proto-card" href="#/protocols/${encodeURIComponent(r.id)}">
          <div class="proto-title">${esc(r.title)}</div>
          <div class="proto-meta"><span class="auto">${esc(AUTOMATION[r.automation_level ?? ""] ?? human(r.automation_level))}</span> · ${r.n_steps ?? "?"} steps · ${badge(r.confidence)}</div>
          <div class="proto-caps">${(r.capabilities ?? []).map((c) => `<span class="cap">${esc(human(c))}</span>`).join("")}</div>
          <div class="proto-src">${sourceLine(r.source)}</div>${licenceBadge(r)}
        </a>`).join("")}</div></section>`).join("") : `<p class="muted">No protocols match these filters.</p>`;
    el.querySelector(".proto-count")!.textContent = `${shown.length} of ${rows.length} protocols`;
  };
  el.innerHTML = `
    <p class="lead-text">Published lab protocols for the two demo pipelines, <b>paraphrased in our own words</b> with a link to each original and its licence.
      Steps are mapped to LabForge capabilities and catalog equipment; the instruments are our suggested equivalents, not necessarily those the authors used.</p>
    <div class="proto-filters">
      <label>Pipeline <select data-f="pipeline">${opt("", "All", filters.pipeline)}${pipelines.map((p) => opt(p, pipelineName(p), filters.pipeline)).join("")}</select></label>
      <label>Capability <select data-f="capability">${opt("", "All", filters.capability)}${caps.map((c) => opt(c, human(c), filters.capability)).join("")}</select></label>
      <label>Automation <select data-f="automation">${opt("", "All", filters.automation)}${Object.entries(AUTOMATION).map(([k, v]) => opt(k, v, filters.automation)).join("")}</select></label>
      <label class="chk"><input type="checkbox" data-f="openOnly"${filters.openOnly ? " checked" : ""}/> Open access only</label>
      <span class="proto-count muted"></span>
    </div>
    <div class="proto-groups"></div>`;
  for (const c of el.querySelectorAll<HTMLSelectElement | HTMLInputElement>("[data-f]"))
    c.addEventListener("change", () => {
      const k = c.dataset.f as keyof Filters;
      (filters as any)[k] = c instanceof HTMLInputElement && c.type === "checkbox" ? c.checked : c.value;
      draw();
    });
  draw();
}

// ---- detail view --------------------------------------------------------------------------------

export async function renderProtocol(el: HTMLElement, id: string, catalog: Record<string, CatalogItem>) {
  let p: Protocol;
  try { p = await loadProtocol(id); } catch {
    el.innerHTML = `<p class="muted">No protocol called "${esc(id)}". <a href="#/protocols">All protocols</a></p>`;
    return;
  }
  const chip = (cid: string) => catalog[cid]
    ? `<button class="equip" data-cid="${esc(cid)}" title="Open the catalog card">${esc(`${catalog[cid].vendor} ${catalog[cid].model}`)}</button>`
    : `<span class="equip off" title="Not in the catalog">${esc(human(cid))}</span>`;
  el.innerHTML = `
    <p><a href="#/protocols">← All protocols</a></p>
    <div class="proto-head" data-title="${esc(p.title)}">
      <div class="proto-kicker">${esc(pipelineName(p.pipeline))} · ${esc(AUTOMATION[p.automation_level ?? ""] ?? human(p.automation_level))} · ${p.steps.length} steps</div>
      <a class="read-original" href="${esc(p.source.url)}" target="_blank" rel="noopener">Read the original protocol ↗</a>
    </div>
    <p class="licence-line"><b>Paraphrased summary; see the source for the full protocol.</b> ${sourceLine(p.source)}${
      p.source.doi ? ` · doi:${esc(p.source.doi)}` : ""} · ${licenceBadge(p)}${p.retrieved ? ` <span class="muted">· retrieved ${esc(p.retrieved)}</span>` : ""}</p>
    <p class="proto-summary">${esc(p.summary)}</p>
    ${p.safety?.length ? `<div class="safety"><b>⚠ Safety</b><ul>${p.safety.map((s) => `<li>${esc(s)}</li>`).join("")}</ul></div>` : ""}
    <h3>Steps</h3>
    <ol class="proto-steps">${[...p.steps].sort((a, b) => a.order - b.order).map((s) => `<li id="step-${s.order}">
      <div class="step-text">${esc(s.text)}</div>
      <div class="step-meta">${s.capability ? `<span class="cap">${esc(human(s.capability))}</span>` : ""}${(s.catalog_ids ?? []).map(chip).join("")}
        <span class="step-dur">${duration(s.duration_s)}</span></div></li>`).join("")}</ol>
    ${p.equipment?.length ? `<h3>Equipment</h3><div class="step-meta">${p.equipment.map((e) => e.catalog_id ? chip(e.catalog_id) : `<span class="equip off">${esc(e.name)}</span>`).join("")}</div>` : ""}
    ${p.materials?.length ? `<h3>Materials</h3><ul class="materials">${p.materials.map((m) => `<li>${esc(m)}</li>`).join("")}</ul>` : ""}
    ${p.notes ? `<h3>Notes</h3><p class="proto-notes">${esc(p.notes)}</p>` : ""}`;
}

/** Protocols relevant to a design, ranked by how many of its capabilities they cover (client-side for_workflow). */
export async function protocolsFor(capabilities: string[], limit = 5): Promise<{ row: ProtocolRow; matched: string[] }[]> {
  const rows = await protocolIndex().catch(() => [] as ProtocolRow[]);
  const want = new Set(capabilities);
  return rows.map((row) => ({ row, matched: (row.capabilities ?? []).filter((c) => want.has(c)) }))
    .filter((x) => x.matched.length).sort((a, b) => b.matched.length - a.matched.length || stageOf(a.row) - stageOf(b.row)).slice(0, limit);
}
