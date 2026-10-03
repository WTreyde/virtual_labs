import type { CaseSummary, CatalogItem, Design } from "./types";

/**
 * Strand A: storage capacity facts read from a design, for the stat card and "The fix" card. Nothing is
 * hard-coded: an instrument "stores plates" if it lists a storage capability, its slots come from the catalog
 * (storage_slots, else process.capacity), and busy fractions come from the simulation's utilisation.
 */

const STORAGE = ["plate_storage", "compound_storage", "incubation", "cold_storage"];

export interface StorageFact { id: string; model: string; slots?: number; busy?: number; caps: string[] }

export function storageFacts(d: Design): StorageFact[] {
  return d.workflow.equipment.flatMap((e) => {
    const it: CatalogItem | undefined = d.catalog[e.catalog_id];
    const caps = (it?.capabilities ?? []).filter((c) => STORAGE.includes(c));
    if (!it || !caps.length) return [];
    const slots = (it as CatalogItem & { storage_slots?: number }).storage_slots ?? it.process?.capacity;
    const busy = d.sim_result.utilisation.find((u) => u.instance_id === e.instance_id)?.busy_fraction;
    return [{ id: e.instance_id, model: it.model, slots, busy, caps }];
  });
}

export const pct = (f?: number) => (f == null ? "?" : `${Math.round(f * 100)}%`);
export const slotsText = (n?: number) => (n == null ? "" : `${n.toLocaleString()} plate slot${n === 1 ? "" : "s"}`);

/**
 * The idle-capacity fix: the busiest storage instrument versus one that shares a storage capability, has more
 * slots and is mostly idle. Returns undefined when the design has no such pair (e.g. the chemistry case).
 */
export function idleCapacityFix(d: Design) {
  const facts = storageFacts(d).filter((f) => f.busy != null);
  const busiest = [...facts].sort((a, b) => b.busy! - a.busy!)[0];
  if (!busiest || busiest.busy! < 0.6) return undefined;
  const alt = facts
    .filter((f) => f.id !== busiest.id && f.busy! < 0.25 && f.caps.some((c) => busiest.caps.includes(c)) && (f.slots ?? 0) > (busiest.slots ?? 0))
    .sort((a, b) => (b.slots ?? 0) - (a.slots ?? 0))[0];
  return alt ? { busiest, alt } : undefined;
}

const esc = (s: unknown) => String(s ?? "").replace(/[&<>"]/g, (c) => `&#${c.charCodeAt(0)};`);

/** "The fix" card for a case page, or "" when the design has no idle-capacity fix. */
export function fixCard(d: Design, summary?: CaseSummary): string {
  const fix = idleCapacityFix(d);
  if (!fix) return "";
  const { busiest: b, alt: a } = fix;
  const w = summary?.imager_growth_whatif as Record<string, any> | undefined;
  const unit = String(w?.unit ?? summary?.headline_throughput.unit ?? "").replace(/_/g, " ");
  const planned = w?.planned_p50 ?? w?.p50 ?? w?.headline_throughput?.p50;
  const verified = w?.verified_p50 ?? w?.headline_throughput?.verified_p50;
  const n = (v: number) => (Math.abs(v) >= 100 ? Math.round(v).toLocaleString() : String(+(+v).toFixed(1)));
  const result = planned != null || verified != null
    ? `<div class="check-row"><span>Simulated</span><span>${planned != null ? `${esc(n(planned))} planned` : ""}${planned != null && verified != null ? " · " : ""}${verified != null ? `${esc(n(verified))} checked` : ""}${unit ? ` ${esc(unit)}` : ""}</span></div>`
    : `<div class="check-row"><span>Simulated</span><span class="muted">not yet simulated</span></div>`;
  return `<b>The fix</b>
    <p>The planner grows plates in the <b>${esc(b.model)}</b> (${esc(b.id)}): ${pct(b.busy)} busy, ${esc(slotsText(b.slots))}.
      The <b>${esc(a.model)}</b> (${esc(a.id)}) is already in the lab at ${pct(a.busy)} busy with ${esc(slotsText(a.slots))}.
      Grow the plates there instead.</p>
    <div class="check-row"><span>Extra equipment</span><span>$0 (already in the design)</span></div>
    ${result}
    <button class="fix-show" data-id="${esc(a.id)}">Show the ${esc(a.model)}</button>`;
}
