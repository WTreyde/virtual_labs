import type { CaseSummary, CatalogItem, Design } from "./types";

/**
 * Strand A: storage capacity facts read from a design, for the stat card and the idle-capacity card. Nothing is
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

/**
 * The idle-capacity card for a case page, or "" when the design has no such pair. It is never called "the fix": the
 * what-if result (summary.imager_growth_whatif) is compared verified-with-verified against the case's own checked
 * baseline, a change within NOISE counts as no gain, and the planning number is only a footnote.
 */
const NOISE = 0.05; // ±5% between two independent checks is within simulation noise (assumption, estimated)

export function fixCard(d: Design, summary?: CaseSummary): string {
  const fix = idleCapacityFix(d);
  if (!fix) return "";
  const { busiest: b, alt: a } = fix;
  const w = summary?.imager_growth_whatif as Record<string, any> | undefined;
  const unit = String(w?.unit ?? summary?.headline_throughput.unit ?? "").replace(/_/g, " ");
  const perDay = unit.endsWith("per day") ? "/day" : ` ${unit}`;
  const n = (v: number) => (Math.abs(v) >= 100 ? Math.round(v).toLocaleString() : String(+(+v).toFixed(1)));
  const base = summary?.headline_throughput.verified_p50, after = w?.verified_p50, planned = w?.planned_p50 ?? w?.p50;
  let result: string;
  if (w && base != null && after != null) {
    const change = (after - base) / base;
    const verdict = Math.abs(change) < NOISE ? "No throughput gain" : change > 0 ? `${Math.round(change * 100)}% more throughput` : `${Math.round(-change * 100)}% less throughput`;
    const nb = w.bottleneck;
    const next = nb ? `${nb.kind === "operator" ? "operators" : esc(nb.instance_id)}${nb.busy_fraction != null ? `, ${Math.round(nb.busy_fraction * 100)}% busy` : ""}` : "";
    result = `<div class="check-row"><span>Simulated</span><span><b>${verdict}</b> (${esc(n(base))} → ${esc(n(after))}${perDay} checked)</span></div>
      ${next ? `<div class="check-row"><span>Next limit</span><span>${next}${nb?.instance_id ? ` <span class="muted">(${esc(nb.instance_id)})</span>` : ""}</span></div>` : ""}
      ${planned != null ? `<p class="footnote">The planning simulation alone said ${esc(n(planned))}${perDay}; the independent check does not confirm it.</p>` : ""}`;
  } else {
    result = `<div class="check-row"><span>Simulated</span><span class="muted">not yet simulated</span></div>`;
  }
  return `<b>Idle capacity: what if?</b>
    <p>The planner grows plates in the <b>${esc(b.model)}</b> (${esc(b.id)}): ${pct(b.busy)} busy, ${esc(slotsText(b.slots))}.
      The <b>${esc(a.model)}</b> (${esc(a.id)}) is already in the lab at ${pct(a.busy)} busy with ${esc(slotsText(a.slots))}.
      Growing plates there instead needs no extra equipment.</p>
    <div class="check-row"><span>Extra equipment</span><span>$0 (already in the design)</span></div>
    ${result}
    <button class="fix-show" data-id="${esc(a.id)}">Show the ${esc(a.model)}</button>`;
}
