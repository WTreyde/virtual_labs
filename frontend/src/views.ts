import type { InstrumentOptimisation, ProjectRequest, ProjectSchedule } from "./types";

/**
 * Strand A: modal views over the game. Vendor what-if (POST /optimise) and project schedule (POST /prioritise).
 * Charts are plain SVG strings: one axis each, recessive grid, thin marks, legends for 2+ series, and a hover
 * tooltip from `data-tip` on every mark. Project colours are categorical slots 1-3 of the dataviz reference
 * palette (validated all-pairs on the light frame); the third slot is under 3:1 contrast, so the Gantt also
 * has a table view.
 */

const C = { s1: "#2a78d6", s2: "#eb6834", s3: "#1baf7a", before: "#a9a7a1", ink: "#1d2330", ink2: "#52514e", grid: "#e4e3dd", surface: "#fbfbf5" };
const PROJECT_COLOURS = [C.s1, C.s2, C.s3];
const esc = (s: unknown) => String(s ?? "").replace(/[&<>"]/g, (c) => `&#${c.charCodeAt(0)};`);
const num = (n: number, d = 1) => (Math.abs(n) >= 100 ? Math.round(n).toLocaleString() : (+n.toFixed(d)).toString());

// ---- modal + tooltip --------------------------------------------------------------------------

const modal = document.querySelector<HTMLDivElement>("#modal")!;
const tip = document.querySelector<HTMLDivElement>("#viz-tip")!;
modal.addEventListener("click", (e) => { if ((e.target as HTMLElement).closest(".close")) closeModal(); });
window.addEventListener("keydown", (e) => { if (e.key === "Escape") closeModal(); });
modal.addEventListener("mousemove", (e) => {
  const t = (e.target as Element).closest<SVGElement | HTMLElement>("[data-tip]");
  tip.classList.toggle("hidden", !t);
  if (!t) return;
  tip.innerHTML = t.dataset.tip!;
  const host = modal.parentElement!.getBoundingClientRect();
  tip.style.left = `${Math.min(e.clientX - host.left + 14, host.width - tip.offsetWidth - 8)}px`;
  tip.style.top = `${e.clientY - host.top + 14}px`;
});
modal.addEventListener("mouseleave", () => tip.classList.add("hidden"));

export function closeModal() { modal.classList.add("hidden"); tip.classList.add("hidden"); }

function openModal(title: string, html: string) {
  modal.innerHTML = `<button class="close" aria-label="Close">✕</button><h2>${esc(title)}</h2>${html}`;
  modal.classList.remove("hidden");
}

export function showLoading(title: string) { openModal(title, `<p class="muted">Simulating…</p>`); }
export function showError(title: string, msg: string) { openModal(title, `<p class="muted">${esc(msg)}</p>`); }

// ---- vendor what-if ---------------------------------------------------------------------------

const SWEEP_LABEL: Record<string, { title: string; x: string; fmt: (v: number) => string; today: number }> = {
  cycle_time: { title: "If its steps ran faster", x: "cycle time, × today (lower is faster)", fmt: (v) => `×${v}`, today: 1 },
  capacity: { title: "If it held more plates at once", x: "parallel slots", fmt: (v) => `${v}`, today: 1 },
  transfer_time: { title: "If transfers were faster", x: "transfer time, × today", fmt: (v) => `×${v}`, today: 1 },
  uptime: { title: "If it were up more often", x: "uptime, × today", fmt: (v) => `×${v}`, today: 1 },
};

/** Throughput P50 line with a P10-P90 band against one spec, with reference lines for today and the target. */
function sweepChart(sweep: InstrumentOptimisation["sweeps"][number], unit: string, base: number, target?: number) {
  const meta = SWEEP_LABEL[sweep.parameter] ?? { title: sweep.parameter, x: sweep.parameter, fmt: String, today: 1 };
  const pts = [...sweep.points].sort((a, b) => a.value - b.value);
  const W = 330, H = 210, L = 44, R = 12, T = 14, B = 40;
  const xs = pts.map((p) => p.value), x0 = Math.min(...xs), x1 = Math.max(...xs);
  const yMax = Math.max(...pts.map((p) => p.throughput_p90 ?? p.throughput_p50), target ?? 0, base) * 1.12;
  const X = (v: number) => L + ((v - x0) / (x1 - x0 || 1)) * (W - L - R), Y = (v: number) => H - B - (v / yMax) * (H - T - B);
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((f) => f * yMax);
  const grid = ticks.map((v) => `<line x1="${L}" x2="${W - R}" y1="${Y(v)}" y2="${Y(v)}" stroke="${C.grid}"/><text x="${L - 6}" y="${Y(v) + 3}" text-anchor="end" class="tick">${num(v, 0)}</text>`).join("");
  const xt = pts.map((p) => `<text x="${X(p.value)}" y="${H - B + 14}" text-anchor="middle" class="tick">${meta.fmt(p.value)}</text>`).join("");
  const band = pts.every((p) => p.throughput_p10 != null && p.throughput_p90 != null)
    ? `<polygon fill="${C.s1}" fill-opacity="0.16" points="${[...pts.map((p) => `${X(p.value)},${Y(p.throughput_p90!)}`), ...[...pts].reverse().map((p) => `${X(p.value)},${Y(p.throughput_p10!)}`)].join(" ")}"/>` : "";
  const line = `<polyline fill="none" stroke="${C.s1}" stroke-width="2" stroke-linejoin="round" points="${pts.map((p) => `${X(p.value)},${Y(p.throughput_p50)}`).join(" ")}"/>`;
  // Today's label sits above its line at the right, the target's below its line at the left, so they never collide.
  const ref = (v: number, label: string, left: boolean) =>
    `<line x1="${L}" x2="${W - R}" y1="${Y(v)}" y2="${Y(v)}" stroke="${C.ink2}" stroke-dasharray="4 3"/>` +
    `<text x="${left ? L + 4 : W - R}" y="${left ? Y(v) + 12 : Y(v) - 4}" text-anchor="${left ? "start" : "end"}" class="ref">${esc(label)}</text>`;
  const refs = ref(base, `today ${num(base)}`, false) + (target != null ? ref(target, `target ${num(target)}`, true) : "");
  const marks = pts.map((p) => {
    const band = p.throughput_p10 != null ? ` (P10–P90 ${num(p.throughput_p10)}–${num(p.throughput_p90 ?? p.throughput_p10)})` : "";
    const tipText = `<b>${esc(meta.fmt(p.value))}</b>: ${num(p.throughput_p50)} ${esc(unit)}${band}`;
    return `<g data-tip="${esc(tipText)}"><circle cx="${X(p.value)}" cy="${Y(p.throughput_p50)}" r="12" fill="transparent"/>
      <circle cx="${X(p.value)}" cy="${Y(p.throughput_p50)}" r="4" fill="${C.s1}" stroke="${C.surface}" stroke-width="2"/></g>`;
  }).join("");
  const el = sweep.elasticity != null ? `<div class="muted">Elasticity ${num(sweep.elasticity, 2)}${Math.abs(sweep.elasticity) < 0.05 ? ": not the limit here" : ""}</div>` : "";
  return `<figure class="chart"><figcaption>${esc(meta.title)}</figcaption>
    <svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(`${meta.title}: throughput against ${meta.x}`)}">${grid}${band}${refs}${line}${marks}${xt}
      <text x="${(L + W - R) / 2}" y="${H - 6}" text-anchor="middle" class="axis">${esc(meta.x)}</text>
      <text x="12" y="${(T + H - B) / 2}" text-anchor="middle" class="axis" transform="rotate(-90 12 ${(T + H - B) / 2})">${esc(unit.replace(/_/g, " "))}</text></svg>${el}</figure>`;
}

export function showWhatIf(o: InstrumentOptimisation, name: string, target: number | undefined, cached: boolean) {
  const unit = o.baseline.unit ?? "";
  const util = o.baseline.utilisation != null ? ` · busy ${Math.round(o.baseline.utilisation * 100)}%` : "";
  const charts = o.sweeps.map((s) => sweepChart(s, unit, o.baseline.throughput_p50, target)).join("");
  openModal(`How could ${name} be better?`, `
    <p class="muted">Lab throughput today: <b>${num(o.baseline.throughput_p50)} ${esc(unit.replace(/_/g, " "))}</b>${util}. Shaded band: P10–P90 over simulated replicates.
      ${o.next_bottleneck ? `Next bottleneck once improved: <b>${esc(o.next_bottleneck)}</b>.` : ""}${cached ? " <i>(cached simulator run; backend offline)</i>" : ""}</p>
    <div class="charts">${charts}</div>
    ${o.headroom_note ? `<p class="note">${esc(o.headroom_note)}</p>` : ""}`);
}

// ---- project schedule -------------------------------------------------------------------------

function tile(label: string, before: string, after: string, good: boolean) {
  return `<div class="tile"><div class="tile-label">${esc(label)}</div><div class="tile-val"><span class="was">${esc(before)}</span> → <b>${esc(after)}</b> ${good ? "✓" : ""}</div></div>`;
}

export function showSchedule(s: ProjectSchedule, projects: ProjectRequest[], cached: boolean) {
  const given = projects.map((p) => p.id);
  const rec = s.candidates.find((c) => c.policy === s.recommended) ?? s.candidates[0];
  const naive = s.candidates.find((c) => c.order?.join(">") === given.join(">"));
  const colour = Object.fromEntries(given.map((id, i) => [id, PROJECT_COLOURS[i] ?? C.before]));
  const pct = (f: number) => `${Math.round(f * 100)}%`;

  const tiles = naive
    ? tile("Finishes in", `${num(naive.makespan_h)} h`, `${num(rec.makespan_h)} h`, rec.makespan_h < naive.makespan_h) +
      tile("Lab busy", pct(naive.mean_utilisation), pct(rec.mean_utilisation), rec.mean_utilisation > naive.mean_utilisation) +
      tile("Deadlines missed", String(naive.deadline_misses?.length ?? 0), String(rec.deadline_misses?.length ?? 0), (rec.deadline_misses?.length ?? 0) < (naive.deadline_misses?.length ?? 0))
    : "";

  // Gantt: one lane per instrument, bars coloured by project. Zero-length steps (load/unload) are omitted.
  const bars = (s.gantt ?? []).filter((g) => g.end_s > g.start_s);
  const lanes = [...new Set(bars.map((g) => g.instance))];
  const endH = Math.max(rec.makespan_h, ...bars.map((g) => g.end_s / 3600));
  const W = 700, L = 96, R = 14, T = 8, lane = 24, H = T + lanes.length * lane + 34;
  const X = (h: number) => L + (h / endH) * (W - L - R);
  const step = endH > 12 ? 2 : 1, hours = Array.from({ length: Math.floor(endH / step) + 1 }, (_, i) => i * step);
  const gantt = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Gantt chart of the recommended schedule by instrument">
    ${hours.map((h) => `<line x1="${X(h)}" x2="${X(h)}" y1="${T}" y2="${T + lanes.length * lane}" stroke="${C.grid}"/><text x="${X(h)}" y="${T + lanes.length * lane + 14}" text-anchor="middle" class="tick">${h} h</text>`).join("")}
    ${lanes.map((id, i) => `<text x="${L - 8}" y="${T + i * lane + lane / 2 + 4}" text-anchor="end" class="lane">${esc(id)}</text>`).join("")}
    ${bars.map((g) => {
      const y = T + lanes.indexOf(g.instance) * lane + 5, x = X(g.start_s / 3600), w = Math.max(2, X(g.end_s / 3600) - x - 2);
      const t = `<b>${esc(g.project)}</b> #${g.unit} · ${esc(g.step)} on ${esc(g.instance)}<br>${num(g.start_s / 3600, 2)}–${num(g.end_s / 3600, 2)} h`;
      return `<rect data-tip="${esc(t)}" x="${x}" y="${y}" width="${w}" height="14" rx="2" fill="${colour[g.project] ?? C.before}"/>`;
    }).join("")}
    ${projects.filter((p) => p.deadline_h != null).map((p) => `<line x1="${X(p.deadline_h!)}" x2="${X(p.deadline_h!)}" y1="${T - 4}" y2="${T + lanes.length * lane}" stroke="${C.ink}" stroke-width="1.5" stroke-dasharray="5 3"/>
      <text x="${X(p.deadline_h!) + 4}" y="${T + lanes.length * lane + 28}" class="ref">${esc(p.id)} deadline ${p.deadline_h} h</text>`).join("")}
    <text x="${L}" y="${H - 4}" class="axis">hours from start, recommended order</text></svg>`;
  const legend = `<div class="legend">${given.map((id) => `<span><i style="background:${colour[id]}"></i>${esc(id)}</span>`).join("")}</div>`;

  // Busy % per instrument, given order vs recommended.
  let busy = "";
  if (naive?.utilisation && rec.utilisation) {
    const ids = Object.keys(rec.utilisation).filter((k) => (rec.utilisation![k] ?? 0) > 0 || (naive.utilisation![k] ?? 0) > 0);
    const BW = 700, BL = 96, row = 30, BH = ids.length * row + 8, bx = (f: number) => (BW - BL - 60) * f;
    busy = `<h3>Lab busy % by instrument</h3>
      <div class="legend"><span><i style="background:${C.before}"></i>order given (${esc(given.join(" → "))})</span><span><i style="background:${C.s1}"></i>recommended</span></div>
      <svg viewBox="0 0 ${BW} ${BH}" role="img" aria-label="Busy fraction per instrument, order given versus recommended">
      ${ids.map((id, i) => {
        const y = 4 + i * row, a = naive.utilisation![id] ?? 0, b = rec.utilisation![id] ?? 0;
        return `<text x="${BL - 8}" y="${y + 14}" text-anchor="end" class="lane">${esc(id)}</text>
          <rect data-tip="${esc(`<b>${id}</b> busy ${pct(a)} in the order given`)}" x="${BL}" y="${y}" width="${Math.max(2, bx(a))}" height="9" rx="2" fill="${C.before}"/>
          <text x="${BL + bx(a) + 6}" y="${y + 8}" class="tick">${pct(a)}</text>
          <rect data-tip="${esc(`<b>${id}</b> busy ${pct(b)} recommended`)}" x="${BL}" y="${y + 11}" width="${Math.max(2, bx(b))}" height="9" rx="2" fill="${C.s1}"/>
          <text x="${BL + bx(b) + 6}" y="${y + 19}" class="tick">${pct(b)}</text>`;
      }).join("")}</svg>`;
  }

  const table = `<details><summary>Table view: every policy evaluated</summary><table>
    <tr><th>Policy</th><th>Finishes (h)</th><th>Lab busy</th><th>Deadlines missed</th></tr>
    ${s.candidates.map((c) => `<tr${c === rec ? ' class="rec"' : ""}><td>${esc(c.order ? c.order.join(" → ") : c.policy)}${c === rec ? " (recommended)" : c === naive ? " (order given)" : ""}</td>
      <td>${num(c.makespan_h)}</td><td>${pct(c.mean_utilisation)}</td><td>${esc(c.deadline_misses?.join(", ") || "none")}</td></tr>`).join("")}
    </table></details>`;

  const order = rec.order ? rec.order.join(" → ") : rec.policy;
  openModal("What order should these projects run in?", `
    <p class="muted">Recommended: <b>${esc(order)}</b>${s.gain_vs_naive != null ? `, finishing ${Math.round(s.gain_vs_naive * 100)}% sooner than the order given` : ""}.
      Objective: ${s.objective === "weighted_tardiness" ? "meet deadlines first (weighted lateness)" : "finish soonest"}.${cached ? " <i>(cached run; backend offline)</i>" : ""}</p>
    <div class="tiles">${tiles}</div>
    <h3>Recommended schedule</h3>${legend}${gantt}${busy}${table}
    ${s.caveat ? `<p class="note">⚠ ${esc(s.caveat)}</p>` : ""}`);
}
