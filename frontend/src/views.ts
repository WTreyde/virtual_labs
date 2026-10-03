import type { InstrumentOptimisation, Leaderboard, ProjectRequest, ProjectSchedule, ValidationRow } from "./types";

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

function openModal(title: string, html: string, wide = false) {
  modal.classList.toggle("wide", wide);
  modal.innerHTML = `<button class="close" aria-label="Close">✕</button><h2>${esc(title)}</h2>${html}`;
  modal.classList.remove("hidden");
}

export function showLoading(title: string, what = "Simulating…") { openModal(title, `<p class="muted">${esc(what)}</p>`); }
export function showHtml(title: string, html: string) { openModal(title, `<div class="answer">${html}</div>`); }
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

// ---- validation: predicted vs reported lab cost ------------------------------------------------

const usd = (v: number) => (v >= 1e6 ? `$${+(v / 1e6).toFixed(1)}M` : v >= 1e3 ? `$${Math.round(v / 1e3)}k` : `$${Math.round(v)}`);
const shortName = (n: string) => { const s = n.split(/[(:,]/)[0].trim(); return s.length > 26 ? `${s.slice(0, 24)}…` : s; };

/** Log-log scatter: reported cost (x) against LabForge's P50 with a P10-P90 bar (y), y = x line, hollow = unverified. */
export function showValidation(rows: ValidationRow[]) {
  const pts = rows.filter((r) => r.status === "compared" && r.reported_usd && r.predicted);
  const rest = rows.filter((r) => !pts.includes(r));
  const inBand = pts.filter((r) => r.within_p10_p90).length;
  let chart = `<p class="muted">No case has a LabForge design to compare yet.</p>`;
  if (pts.length) {
    const vals = pts.flatMap((r) => [r.reported_usd!, r.predicted!.p10, r.predicted!.p90]);
    const lo = Math.log10(Math.min(...vals) / 1.6), hi = Math.log10(Math.max(...vals) * 1.6);
    const W = 640, H = 420, L = 64, R = 20, T = 16, B = 46;
    const X = (v: number) => L + ((Math.log10(v) - lo) / (hi - lo)) * (W - L - R);
    const Y = (v: number) => H - B - ((Math.log10(v) - lo) / (hi - lo)) * (H - T - B);
    const ticks: number[] = [];
    for (let k = Math.floor(lo); k <= Math.ceil(hi); k++) for (const m of [1, 2, 5]) { const v = m * 10 ** k; if (Math.log10(v) >= lo && Math.log10(v) <= hi) ticks.push(v); }
    const grid = ticks.map((v) => `<line x1="${L}" x2="${W - R}" y1="${Y(v)}" y2="${Y(v)}" stroke="${C.grid}"/><text x="${L - 6}" y="${Y(v) + 3}" text-anchor="end" class="tick">${usd(v)}</text>
      <line x1="${X(v)}" x2="${X(v)}" y1="${T}" y2="${H - B}" stroke="${C.grid}"/><text x="${X(v)}" y="${H - B + 14}" text-anchor="middle" class="tick">${usd(v)}</text>`).join("");
    const a = 10 ** lo, b = 10 ** hi;
    const diag = `<line x1="${X(a)}" y1="${Y(a)}" x2="${X(b)}" y2="${Y(b)}" stroke="${C.ink2}" stroke-dasharray="5 4"/>
      <text x="${X(b) - 4}" y="${Y(b) + 14}" text-anchor="end" class="ref">predicted = reported</text>`;
    // Direct labels: each goes to the first of right/left/above/below that clears earlier labels and the markers.
    type Box = { x0: number; y0: number; x1: number; y1: number };
    const hit = (a: Box, b: Box) => a.x0 < b.x1 && b.x0 < a.x1 && a.y0 < b.y1 && b.y0 < a.y1;
    const taken: Box[] = pts.map((r) => ({ x0: X(r.reported_usd!) - 6, x1: X(r.reported_usd!) + 6, y0: Y(r.predicted!.p90), y1: Y(r.predicted!.p10) }));
    const marks = [...pts].sort((a, b) => a.reported_usd! - b.reported_usd!).map((r) => {
      const p = r.predicted!, x = X(r.reported_usd!), y = Y(p.p50), hollow = !r.verified, name = shortName(r.name), w = name.length * 5.6 + 4;
      const spots = [
        { x: x + 10, y: y + 4, a: "start", box: { x0: x + 10, x1: x + 10 + w, y0: y - 7, y1: y + 6 } },
        { x: x - 10, y: y + 4, a: "end", box: { x0: x - 10 - w, x1: x - 10, y0: y - 7, y1: y + 6 } },
        { x, y: Y(p.p90) - 8, a: "middle", box: { x0: x - w / 2, x1: x + w / 2, y0: Y(p.p90) - 19, y1: Y(p.p90) - 5 } },
        { x, y: Y(p.p10) + 16, a: "middle", box: { x0: x - w / 2, x1: x + w / 2, y0: Y(p.p10) + 5, y1: Y(p.p10) + 19 } },
      ];
      const spot = spots.find((s) => s.box.x0 >= 0 && s.box.x1 <= W && !taken.some((t) => hit(t, s.box))) ?? spots[2];
      taken.push(spot.box);
      const tip = `<b>${esc(r.name)}</b><br>Reported ${usd(r.reported_usd!)} · predicted ${usd(p.p50)} (P10–P90 ${usd(p.p10)}–${usd(p.p90)})<br>` +
        `${r.within_p10_p90 ? "Inside" : "Outside"} the band · log10 error ${r.log10_error ?? "?"}${hollow ? "<br><i>Reported cost not verified</i>" : ""}`;
      return `<g data-tip="${esc(tip)}">
        <line x1="${x}" x2="${x}" y1="${Y(p.p10)}" y2="${Y(p.p90)}" stroke="${C.s1}" stroke-width="2"/>
        <line x1="${x - 5}" x2="${x + 5}" y1="${Y(p.p10)}" y2="${Y(p.p10)}" stroke="${C.s1}" stroke-width="2"/>
        <line x1="${x - 5}" x2="${x + 5}" y1="${Y(p.p90)}" y2="${Y(p.p90)}" stroke="${C.s1}" stroke-width="2"/>
        <circle cx="${x}" cy="${y}" r="14" fill="transparent"/>
        <circle cx="${x}" cy="${y}" r="5" fill="${hollow ? C.surface : C.s1}" stroke="${hollow ? C.s1 : C.surface}" stroke-width="2"/>
        <text x="${spot.x}" y="${spot.y}" text-anchor="${spot.a}" class="lane">${esc(name)}</text></g>`;
    }).join("");
    chart = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Predicted against reported lab cost, log scales">${grid}${diag}${marks}
      <text x="${(L + W - R) / 2}" y="${H - 8}" text-anchor="middle" class="axis">reported cost (USD, log scale)</text>
      <text x="14" y="${(T + H - B) / 2}" text-anchor="middle" class="axis" transform="rotate(-90 14 ${(T + H - B) / 2})">LabForge predicted cost, P50 with P10–P90 (USD, log)</text></svg>
      <div class="legend"><span><i style="background:${C.s1};border-radius:50%"></i>reported cost verified</span><span><i style="background:${C.surface};border:2px solid ${C.s1};border-radius:50%;width:7px;height:7px"></i>reported cost not verified</span></div>`;
  }
  const table = `<details${pts.length ? "" : " open"}><summary>Table view: all ${rows.length} cases</summary><table>
    <tr><th>Case</th><th>Reported</th><th>Predicted P10–P50–P90</th><th>In band</th><th>Source verified</th></tr>
    ${rows.map((r) => `<tr><td>${esc(r.name)}</td><td>${r.reported_usd ? usd(r.reported_usd) : "–"}</td>
      <td>${r.predicted ? `${usd(r.predicted.p10)} – ${usd(r.predicted.p50)} – ${usd(r.predicted.p90)}` : esc(r.status.replace(/_/g, " "))}</td>
      <td>${r.within_p10_p90 == null ? "–" : r.within_p10_p90 ? "yes" : "no"}</td><td>${r.verified ? "yes" : "no"}</td></tr>`).join("")}
    </table></details>`;
  openModal("Does LabForge price real labs right?", `
    <p class="muted">Predicted equipment cost against the cost reported for published labs. <b>${pts.length} of ${rows.length}</b> cases have a LabForge design to compare;
      <b>${inBand} of ${pts.length}</b> reported costs fall inside our P10–P90 band. Points on the dashed line would be exact.</p>
    ${chart}
    ${rest.length ? `<p class="muted">No prediction yet: ${rest.map((r) => esc(shortName(r.name))).join(" · ")}.</p>` : ""}
    ${table}`, true);
}

// ---- LabDesignBench leaderboard ------------------------------------------------------------------

/** A failed check that means the agent tampered with inputs or reported numbers the simulator did not produce. */
const isTamper = (c: { kind: string; passed: boolean | null; note?: string }) =>
  c.passed === false && (c.kind === "inputs_untampered" || /tamper|reported .* but/i.test(c.note ?? ""));

export function showLeaderboard(board: Leaderboard | null) {
  if (!board) {
    openModal("LabDesignBench", `<p class="muted">No results yet. The leaderboard appears once the bench has been run and committed
      (<code>python -m labforge.bench.runner --out backend/labforge/bench/results/leaderboard.json</code>).</p>`, true);
    return;
  }
  const armName = (a: string) => (a === "platform" ? "LabForge platform" : a === "vanilla" ? "Vanilla Claude (no tools)" : a);
  const pct = (v: number | null | undefined) => (v == null ? "–" : `${Math.round(v * 100)}%`);
  const cards = board.arms.map((a, i) => {
    const caught = a.tasks.flatMap((t) => t.checks).filter(isTamper).length;
    return `<div class="tile${i === 0 ? " lead" : ""}"><div class="tile-label">${esc(armName(a.arm))}</div>
      <div class="tile-val"><b>${pct(a.score)}</b> <span class="was">of checks</span></div>
      <div class="muted">${a.checks_passed}/${a.checks_total} checks · ${a.tasks_answered}/${a.tasks.length} tasks answered · Brier ${a.brier ?? "–"}
        ${a.claims_refuted != null ? ` · ${a.claims_refuted} claims refuted` : ""}${caught ? ` · <span class="tamper">${caught} tamper attempt${caught > 1 ? "s" : ""} caught</span>` : ""}</div></div>`;
  }).join("");
  const byArm = new Map(board.arms.map((a) => [a.arm, new Map(a.tasks.map((t) => [t.task_id, t]))]));
  const cell = (arm: string, taskId: string) => {
    const t = byArm.get(arm)?.get(taskId);
    if (!t) return `<td class="muted">–</td>`;
    if (t.error) return `<td class="muted" title="${esc(t.error)}">not run</td>`;
    const tamper = t.checks.some(isTamper);
    const chips = t.checks.map((c) => {
      const cls = c.passed === true ? "ok" : c.passed === false ? (isTamper(c) ? "bad tamper" : "bad") : "na";
      const sym = c.passed === true ? "✓" : c.passed === false ? "✗" : "–";
      return `<span class="chip ${cls}" data-tip="${esc(`<b>${c.id}</b> (${c.kind.replace(/_/g, " ")}): ${c.passed === true ? "passed" : c.passed === false ? "failed" : "not applicable"}${c.note ? `<br>${esc(c.note)}` : ""}`)}">${sym}</span>`;
    }).join("");
    return `<td${tamper ? ' class="tamper-cell"' : ""}><b>${pct(t.score)}</b> ${chips}${tamper ? `<div class="tamper">⚠ tamper attempt caught</div>` : ""}</td>`;
  };
  const arms = board.arms.map((a) => a.arm);
  const table = `<table class="bench"><tr><th>Task</th><th>Trap</th>${arms.map((a) => `<th>${esc(armName(a))}</th>`).join("")}</tr>
    ${board.tasks.map((t) => `<tr><td>${esc(t.id)}${t.domain ? `<div class="muted">${esc(t.domain)}</div>` : ""}</td><td>${esc((t.trap ?? "none").replace(/_/g, " "))}</td>
      ${arms.map((a) => cell(a, t.id)).join("")}</tr>`).join("")}</table>`;
  openModal("LabDesignBench: do design agents know when they're wrong?", `
    <p class="muted">Each task hides checks, including traps: impossible targets, placeholder specs, a simulator config the agent could edit.
      ✓ passed · ✗ failed · – not applicable; hover a mark for the verifier's note.${board.generated_at ? ` Run ${esc(new Date(board.generated_at).toLocaleString())}.` : ""}</p>
    <div class="tiles">${cards}</div>${table}`, true);
}
