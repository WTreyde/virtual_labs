import type { Design } from "./types";

/** Strand A: the side panel (metrics with uncertainty band, BOM). Owner: Roshan. */
export function renderPanel(d: Design) {
  const t = d.sim_result.throughput;
  const lo = t.p10 ?? t.value, hi = t.p90 ?? t.value, target = t.target ?? t.value;
  const max = Math.max(hi, target) * 1.25;
  const pct = (v: number) => `${(100 * v) / max}%`;
  document.querySelector("#metrics")!.innerHTML = `
    <b>Throughput</b> ${t.p50 ?? t.value} ${t.unit}<br/>
    P10–P90: ${lo}–${hi} · target ${target} · P(meet) ${t.prob_meets_target ?? "?"}
    <div class="band"><div class="range" style="left:${pct(lo)};width:calc(${pct(hi)} - ${pct(lo)})"></div>
    <div class="target" style="left:${pct(target)}"></div></div>`;
  const esc = (v: unknown) => String(v ?? "").replace(/[&<>"]/g, (c) => `&#${c.charCodeAt(0)};`);
  const label: Record<string, string> = { datasheet: "DATASHEET", literature: "LITERATURE", estimated: "ESTIMATE", placeholder: "PLACEHOLDER" };
  const rows = d.workflow.equipment.map((e) => {
    const it = d.catalog[e.catalog_id], c = it?.data_confidence;
    const badge = c ? `<span class="badge badge-${esc(c)}">${label[c] ?? esc(c)}</span>` : `<span class="badge badge-unknown">UNSOURCED</span>`;
    return `<tr><td><b>${esc(it?.model ?? e.catalog_id)}</b><div class="vendor">${esc(it?.vendor ?? "?")} · ${esc(e.instance_id)}</div></td>
      <td class="num">${it?.price_usd_estimate != null ? `$${it.price_usd_estimate.toLocaleString()}` : "?"}<div>${badge}</div></td></tr>`;
  });
  const total = d.workflow.equipment.reduce((s, e) => s + (d.catalog[e.catalog_id]?.price_usd_estimate ?? 0), 0);
  const unpriced = d.workflow.equipment.filter((e) => d.catalog[e.catalog_id]?.price_usd_estimate == null).length;
  const firm = d.workflow.equipment.filter((e) => ["datasheet", "literature"].includes(d.catalog[e.catalog_id]?.data_confidence ?? "")).length;
  document.querySelector("#bom")!.innerHTML = `<b>Bill of materials</b><table>${rows.join("")}
    <tr class="total"><td><b>Total${unpriced ? ` (${unpriced} unpriced)` : ""}</b></td><td class="num"><b>$${total.toLocaleString()}</b></td></tr></table>
    <div class="note">${firm} of ${d.workflow.equipment.length} items have sourced specs; the rest are estimates.</div>`;
}
