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
  const rows = d.workflow.equipment.map((e) => {
    const it = d.catalog[e.catalog_id];
    return `<tr><td>${it?.vendor ?? "?"} ${it?.model ?? e.catalog_id}</td><td>$${(it?.price_usd_estimate ?? 0).toLocaleString()}</td>
      <td class="conf-${it?.data_confidence}">${it?.data_confidence ?? ""}</td></tr>`;
  });
  const total = d.workflow.equipment.reduce((s, e) => s + (d.catalog[e.catalog_id]?.price_usd_estimate ?? 0), 0);
  document.querySelector("#bom")!.innerHTML = `<b>Bill of materials</b><table>${rows.join("")}
    <tr><td><b>Total</b></td><td><b>$${total.toLocaleString()}</b></td><td></td></tr></table>`;
}
