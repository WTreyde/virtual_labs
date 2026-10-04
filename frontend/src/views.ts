import type { BenchTask, InstrumentOptimisation, Leaderboard, ProjectRequest, ProjectSchedule, ValidationRow } from "./types";

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

export function openModal(title: string, html: string, wide = false) {
  modal.classList.toggle("wide", wide);
  modal.innerHTML = `<button class="close" aria-label="Close" title="Close (Esc)">✕</button><h2>${esc(title)}</h2>${html}`;
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

/** Readable project names for the demo queue; anything else falls back to its humanised id. */
const PROJECT_NAME: Record<string, string> = {
  enzyme_campaign: "Enzyme campaign", chem_library_screen: "Chemistry library screen", urgent_retest: "Urgent hit re-test",
};
export const projectName = (id: string) => PROJECT_NAME[id] ?? id.replace(/_/g, " ");

/**
 * The Schedule tab: which order to run several projects through one existing lab. It states the question and the
 * answer in plain words (built from the queue and the /prioritise result), explains each figure, names instruments
 * by vendor and model rather than instance id, and restates the backend's caveat in plain words.
 */
export function showSchedule(s: ProjectSchedule, projects: ProjectRequest[], cached: boolean, deviceNames: Record<string, { short: string; full: string }> = {}) {
  const given = projects.map((p) => p.id);
  const rec = s.candidates.find((c) => c.policy === s.recommended) ?? s.candidates[0];
  const naive = s.candidates.find((c) => c.order?.join(">") === given.join(">"));
  const colour = Object.fromEntries(given.map((id, i) => [id, PROJECT_COLOURS[i] ?? C.before]));
  const pct = (f: number) => `${Math.round(f * 100)}%`;
  // Lanes show the model (short); hover shows vendor and model (full).
  const dev = (id: string) => deviceNames[id]?.full ?? id, devShort = (id: string) => deviceNames[id]?.short ?? id;
  const short = (t: string) => (t.length > 24 ? `${t.slice(0, 23)}…` : t);
  const instruments = new Set(projects.flatMap((p) => p.workflow.equipment.map((e) => e.instance_id)));
  const plates = (p: ProjectRequest) => `${p.units} ${/^sbs|plate/.test(String((p.workflow as any).labware ?? "")) ? (p.units === 1 ? "plate" : "plates") : "units"}`;
  const list = (xs: string[]) => (xs.length < 2 ? xs.join("") : `${xs.slice(0, -1).join(", ")} and ${xs.at(-1)}`);

  // The question and the answer, in plain words.
  const asked = list(projects.map((p) => `${/^[aeiou]/i.test(projectName(p.id)) ? "an" : "a"} ${projectName(p.id).toLowerCase()} (${plates(p)}${p.deadline_h != null ? `, due within ${num(p.deadline_h)} h` : ""})`));
  const anyDeadline = projects.some((p) => p.deadline_h != null);
  const question = `One existing screening cell, with ${instruments.size} instruments, has ${projects.length} projects waiting: ${asked}.
    In what order should they run so ${anyDeadline ? "deadlines are met and " : ""}everything finishes soonest?`;
  const recOrder = rec.order ?? [];
  const fin = rec.project_finish_h ?? {};
  const firstDue = recOrder.map((id) => projects.find((p) => p.id === id)).find((p) => p?.deadline_h != null);
  const steps = recOrder.map((id, i) => {
    const p = projects.find((q) => q.id === id), name = projectName(id);
    const first = i === 0 ? `Run the ${name.toLowerCase()} first` : i === recOrder.length - 1 ? `then the ${name.toLowerCase()}` : `then the ${name.toLowerCase()}`;
    return p === firstDue && fin[id] != null ? `${first} (done at ${num(fin[id])} h, deadline ${num(p!.deadline_h!)} h)` : first;
  });
  const answer = recOrder.length
    ? `${steps.join(", ")}: everything is done in <b>${num(rec.makespan_h)} h</b>${naive ? ` instead of ${num(naive.makespan_h)} h in the order listed` : ""}${
      (rec.deadline_misses?.length ?? 0) === 0 ? ", with no missed deadline" : `, but ${esc(list((rec.deadline_misses ?? []).map(projectName)))} still miss their deadline`}.`
    : `Recommended: ${esc(rec.policy)}.`;

  const tile2 = (label: string, explain: string, before: string, after: string, good: boolean) =>
    `<div class="tile"><div class="tile-label">${esc(label)}</div><div class="tile-val"><span class="was">${esc(before)}</span> → <b>${esc(after)}</b> ${good ? "✓" : ""}</div><div class="tile-explain">${esc(explain)}</div></div>`;
  const tiles = naive
    ? tile2("Finishes in", "time until all projects are done (order listed → recommended)", `${num(naive.makespan_h)} h`, `${num(rec.makespan_h)} h`, rec.makespan_h < naive.makespan_h) +
      tile2("Lab busy", "average share of time the cell's instruments are working", pct(naive.mean_utilisation), pct(rec.mean_utilisation), rec.mean_utilisation > naive.mean_utilisation) +
      tile2("Deadlines missed", "projects finishing after their deadline", String(naive.deadline_misses?.length ?? 0), String(rec.deadline_misses?.length ?? 0), (rec.deadline_misses?.length ?? 0) < (naive.deadline_misses?.length ?? 0))
    : "";

  // Gantt: one lane per instrument (named by vendor and model), bars coloured by project. Zero-length steps omitted.
  const bars = (s.gantt ?? []).filter((g) => g.end_s > g.start_s);
  const lanes = [...new Set(bars.map((g) => g.instance))];
  const endH = Math.max(rec.makespan_h, ...bars.map((g) => g.end_s / 3600));
  const deadlines = projects.filter((p) => p.deadline_h != null);
  // Deadline labels sit above the chart at the top of their line, clear of the x-axis title below.
  const W = 720, L = 160, R = 14, T = deadlines.length ? 22 : 8, lane = 24, H = T + lanes.length * lane + 34;
  const X = (h: number) => L + (h / endH) * (W - L - R);
  const step = endH > 12 ? 2 : 1, hours = Array.from({ length: Math.floor(endH / step) + 1 }, (_, i) => i * step);
  const gantt = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Gantt chart of the recommended schedule by instrument">
    ${hours.map((h) => `<line x1="${X(h)}" x2="${X(h)}" y1="${T}" y2="${T + lanes.length * lane}" stroke="${C.grid}"/><text x="${X(h)}" y="${T + lanes.length * lane + 14}" text-anchor="middle" class="tick">${h} h</text>`).join("")}
    ${lanes.map((id, i) => `<text x="${L - 8}" y="${T + i * lane + lane / 2 + 4}" text-anchor="end" class="lane" data-tip="${esc(`<b>${esc(dev(id))}</b> (${esc(id)})`)}">${esc(short(devShort(id)))}</text>`).join("")}
    ${bars.map((g) => {
      const y = T + lanes.indexOf(g.instance) * lane + 5, x = X(g.start_s / 3600), w = Math.max(2, X(g.end_s / 3600) - x - 2);
      const t = `<b>${esc(projectName(g.project))}</b>, plate ${g.unit} · ${esc(g.step.replace(/_/g, " "))} on ${esc(dev(g.instance))}<br>${num(g.start_s / 3600, 2)}–${num(g.end_s / 3600, 2)} h`;
      return `<rect data-tip="${esc(t)}" x="${x}" y="${y}" width="${w}" height="14" rx="2" fill="${colour[g.project] ?? C.before}"/>`;
    }).join("")}
    ${deadlines.map((p) => {
      const x = X(p.deadline_h!), label = `${projectName(p.id)} deadline ${num(p.deadline_h!)} h`, right = x + 4 + label.length * 5.6 <= W - R;
      return `<line x1="${x}" x2="${x}" y1="${T - 18}" y2="${T + lanes.length * lane}" stroke="${C.ink}" stroke-width="1.5" stroke-dasharray="5 3"/>
      <text x="${right ? x + 4 : x - 4}" y="${T - 9}" text-anchor="${right ? "start" : "end"}" class="ref">${esc(label)}</text>`;
    }).join("")}
    <text x="${L}" y="${H - 4}" class="axis">hours from start, recommended order</text></svg>`;
  const legend = `<div class="legend">${given.map((id) => `<span><i style="background:${colour[id]}"></i>${esc(projectName(id))}</span>`).join("")}</div>`;

  // Busy % per instrument, order listed vs recommended.
  let busy = "";
  if (naive?.utilisation && rec.utilisation) {
    const ids = Object.keys(rec.utilisation).filter((k) => (rec.utilisation![k] ?? 0) > 0 || (naive.utilisation![k] ?? 0) > 0);
    const BW = 720, BL = 160, row = 30, BH = ids.length * row + 8, bx = (f: number) => (BW - BL - 60) * f;
    busy = `<h3>How busy each instrument is</h3>
      <div class="legend"><span><i style="background:${C.before}"></i>order listed</span><span><i style="background:${C.s1}"></i>recommended order</span></div>
      <svg viewBox="0 0 ${BW} ${BH}" role="img" aria-label="Busy fraction per instrument, order listed versus recommended">
      ${ids.map((id, i) => {
        const y = 4 + i * row, a = naive.utilisation![id] ?? 0, b = rec.utilisation![id] ?? 0;
        return `<text x="${BL - 8}" y="${y + 14}" text-anchor="end" class="lane">${esc(short(devShort(id)))}</text>
          <rect data-tip="${esc(`<b>${esc(dev(id))}</b> busy ${pct(a)} in the order listed`)}" x="${BL}" y="${y}" width="${Math.max(2, bx(a))}" height="9" rx="2" fill="${C.before}"/>
          <text x="${BL + bx(a) + 6}" y="${y + 8}" class="tick">${pct(a)}</text>
          <rect data-tip="${esc(`<b>${esc(dev(id))}</b> busy ${pct(b)} in the recommended order`)}" x="${BL}" y="${y + 11}" width="${Math.max(2, bx(b))}" height="9" rx="2" fill="${C.s1}"/>
          <text x="${BL + bx(b) + 6}" y="${y + 19}" class="tick">${pct(b)}</text>`;
      }).join("")}</svg>`;
  }

  const orderText = (c: ProjectSchedule["candidates"][number]) => c.order ? c.order.map(projectName).join(" → ") : ({ interleave: "Take turns between projects", bottleneck_mix: "Mix projects to spread the load" } as Record<string, string>)[c.policy] ?? c.policy;
  const table = `<details><summary>Table view: every order LabForge tried</summary><table>
    <tr><th>Order</th><th>Finishes (h)</th><th>Lab busy</th><th>Deadlines missed</th></tr>
    ${s.candidates.map((c) => `<tr${c === rec ? ' class="rec"' : ""}><td>${esc(orderText(c))}${c === rec ? " (recommended)" : c === naive ? " (order listed)" : ""}</td>
      <td>${num(c.makespan_h)}</td><td>${pct(c.mean_utilisation)}</td><td>${esc((c.deadline_misses ?? []).map(projectName).join(", ") || "none")}</td></tr>`).join("")}
    </table></details>`;

  // The backend's caveat in plain words when it has the usual shape; otherwise as written.
  const m = s.caveat?.match(/\((\d+) replicates\):\s*recommended ([\d.]+) h \(P10-P90 ([\d.]+)-([\d.]+) h\) vs order given ([\d.]+) h \(([\d.]+)-([\d.]+) h\); recommended finishes first in (\d+)% of replicates/);
  const caveat = m
    ? `Planned on average step times, without transfer times or operator shifts. A check over ${m[1]} simulated variations of the step times
       still gives about <b>${num(+m[2])} h</b> (likely ${num(+m[3])}–${num(+m[4])} h) for the recommended order vs ${num(+m[5])} h (${num(+m[6])}–${num(+m[7])} h) for the order listed;
       the recommended order finished first in ${m[8]}% of them.`
    : s.caveat ? esc(s.caveat) : "";

  openModal("Scheduling case: what order should these projects run in?", `
    <div class="sched-qa">
      <p class="sched-q"><span class="qa-tag">The question</span>${esc(question)}</p>
      <p class="sched-a"><span class="qa-tag">The answer</span>${answer}${cached ? " <i class=\"muted\">(cached run; backend offline)</i>" : ""}</p>
      <p class="muted">Case study: getting more out of a lab that already exists, with no new equipment. Unlike the two design cases this is not a
        recorded agent run: LabForge's scheduler simulates every running order.</p>
    </div>
    <div class="tiles">${tiles}</div>
    <h3>Recommended schedule</h3>${legend}${gantt}${busy}${table}
    ${caveat ? `<p class="note">⚠ ${caveat}</p>` : ""}`);
}

// ---- validation: predicted vs reported lab cost ------------------------------------------------

const usd = (v: number) => (v >= 1e6 ? `$${+(v / 1e6).toFixed(1)}M` : v >= 1e3 ? `$${Math.round(v / 1e3)}k` : `$${Math.round(v)}`);
const shortName = (n: string) => { const s = n.split(/[(:,]/)[0].trim(); return s.length > 26 ? `${s.slice(0, 24)}…` : s; };

const STATUS_TEXT: Record<string, string> = { no_design_yet: "No design yet", error: "Error", not_costable: "Not costable", compared: "Compared" };
/** "42% medium": the stated chance the real cost is within ±25% of P50, and its label. Experimental. */
const confidenceText = (r: ValidationRow) => {
  const c = r.predicted?.confidence;
  return c?.within_25pct == null ? "" : `${Math.round(c.within_25pct * 100)}%${c.label ? ` ${c.label}` : ""}`;
};
/** Plain words for the cost model's main_gap codes. */
const GAP_TEXT: Record<string, string> = {
  range: "wide price range", source: "weak price source", year_gap: "old price", basis_mismatch: "bare vs equipped price unknown",
  proxy_model: "similar model used as stand-in", configuration: "configuration unknown",
};
const mainUncertainty = (r: ValidationRow, names: Record<string, string>) => {
  const d = r.predicted?.confidence?.drivers?.[0];
  if (!d) return "";
  const name = names[d.catalog_id] ?? d.catalog_id.replace(/_/g, " ");
  return `${name} (${GAP_TEXT[d.main_gap ?? ""] ?? String(d.main_gap ?? "").replace(/_/g, " ")})`;
};

/**
 * Log-log scatter: reported cost (x) against LabForge's P50 with its P10-P90 band (y), y = x line, hollow = reported
 * cost unverified. The band is the headline (it holds up in blind tests); the single-number confidence score is shown
 * only as "experimental" because it does not yet beat a constant baseline (docs/validation.md). Cases without a
 * comparison (no design yet, error, not costable) are listed with their reason, never plotted as $0.
 */
export function showValidation(rows: ValidationRow[], names: Record<string, string> = {}) {
  const pts = rows.filter((r) => r.status === "compared" && r.reported_usd && r.predicted);
  const rest = rows.filter((r) => !pts.includes(r));
  const inBand = pts.filter((r) => r.within_p10_p90).length;
  const within25 = pts.filter((r) => r.within_25pct != null);
  const blind = pts.filter((r) => r.split === "out_of_sample"), hasSplit = pts.some((r) => r.split);
  // Calibration of the experimental score, from the data: mean stated chance vs how often cases actually landed
  // within ±25%, on verified like-for-like cases only.
  const calib = pts.filter((r) => r.verified && r.like_for_like !== false && r.within_25pct != null && r.predicted?.confidence?.within_25pct != null);
  const stated = calib.length ? calib.reduce((s, r) => s + r.predicted!.confidence!.within_25pct!, 0) / calib.length : undefined;
  const observed = calib.length ? calib.filter((r) => r.within_25pct).length / calib.length : undefined;
  let chart = `<p class="muted">No case has a LabForge design to compare yet.</p>`, hiddenLabels = 0;
  if (pts.length) {
    const vals = pts.flatMap((r) => [r.reported_usd!, r.predicted!.p10, r.predicted!.p90]);
    const lo = Math.log10(Math.min(...vals) / 1.6), hi = Math.log10(Math.max(...vals) * 1.6);
    const W = 680, H = 480, L = 64, R = 20, T = 16, B = 46;
    const X = (v: number) => L + ((Math.log10(v) - lo) / (hi - lo)) * (W - L - R);
    const Y = (v: number) => H - B - ((Math.log10(v) - lo) / (hi - lo)) * (H - T - B);
    const ticks: number[] = [];
    for (let k = Math.floor(lo); k <= Math.ceil(hi); k++) for (const m of [1, 2, 5]) { const v = m * 10 ** k; if (Math.log10(v) >= lo && Math.log10(v) <= hi) ticks.push(v); }
    const grid = ticks.map((v) => `<line x1="${L}" x2="${W - R}" y1="${Y(v)}" y2="${Y(v)}" stroke="${C.grid}"/><text x="${L - 6}" y="${Y(v) + 3}" text-anchor="end" class="tick">${usd(v)}</text>
      <line x1="${X(v)}" x2="${X(v)}" y1="${T}" y2="${H - B}" stroke="${C.grid}"/><text x="${X(v)}" y="${H - B + 14}" text-anchor="middle" class="tick">${usd(v)}</text>`).join("");
    const a = 10 ** lo, b = 10 ** hi;
    const diag = `<line x1="${X(a)}" y1="${Y(a)}" x2="${X(b)}" y2="${Y(b)}" stroke="${C.ink2}" stroke-dasharray="5 4"/>
      <text x="${X(b) - 4}" y="${Y(b) + 14}" text-anchor="end" class="ref">predicted = reported</text>`;
    // Direct labels: each takes the first free spot (beside the point, stepped up/down with a leader line, or
    // above/below its band). With no free spot the label is left off rather than overprinted; hover still names it.
    type Box = { x0: number; y0: number; x1: number; y1: number };
    const hit = (a: Box, b: Box) => a.x0 < b.x1 && b.x0 < a.x1 && a.y0 < b.y1 && b.y0 < a.y1;
    const taken: Box[] = pts.map((r) => ({ x0: X(r.reported_usd!) - 6, x1: X(r.reported_usd!) + 6, y0: Y(r.predicted!.p90), y1: Y(r.predicted!.p10) }));
    const marks = [...pts].sort((a, b) => a.reported_usd! - b.reported_usd!).map((r) => {
      const p = r.predicted!, x = X(r.reported_usd!), y = Y(p.p50), hollow = !r.verified, name = shortName(r.name), w = name.length * 5.9 + 6;
      // Not like-for-like (e.g. a used robot against new prices): greyed with a dashed band. Blind-test cases: diamonds.
      const unfair = r.like_for_like === false, col = unfair ? C.before : C.s1, dash = unfair ? ' stroke-dasharray="3 3"' : "";
      const blindPt = r.split === "out_of_sample";
      const spots: { x: number; y: number; a: string; box: Box; lead?: boolean }[] = [];
      for (const dy of [0, -14, 14, -28, 28, -42, 42, -56, 56, -70, 70]) {
        const ly = y + dy;
        spots.push({ x: x + 10, y: ly + 4, a: "start", box: { x0: x + 10, x1: x + 10 + w, y0: ly - 7, y1: ly + 6 }, lead: dy !== 0 });
        spots.push({ x: x - 10, y: ly + 4, a: "end", box: { x0: x - 10 - w, x1: x - 10, y0: ly - 7, y1: ly + 6 }, lead: dy !== 0 });
      }
      spots.push({ x, y: Y(p.p90) - 8, a: "middle", box: { x0: x - w / 2, x1: x + w / 2, y0: Y(p.p90) - 19, y1: Y(p.p90) - 5 } });
      spots.push({ x, y: Y(p.p10) + 16, a: "middle", box: { x0: x - w / 2, x1: x + w / 2, y0: Y(p.p10) + 5, y1: Y(p.p10) + 19 } });
      const inside = (b: Box) => b.x0 >= L && b.x1 <= W - 2 && b.y0 >= T && b.y1 <= H - B;
      const spot = spots.find((s) => inside(s.box) && !taken.some((t) => hit(t, s.box)));
      let label = "";
      if (spot) {
        taken.push(spot.box);
        const leader = spot.lead ? `<line x1="${x + (spot.a === "start" ? 6 : -6)}" y1="${y}" x2="${spot.a === "start" ? spot.box.x0 - 2 : spot.box.x1 + 2}" y2="${spot.y - 4}" stroke="${C.ink2}" stroke-width="1"/>` : "";
        label = `${leader}<text x="${spot.x}" y="${spot.y}" text-anchor="${spot.a}" class="lane">${esc(name)}</text>`;
      } else hiddenLabels++;
      const c = p.confidence, mu = mainUncertainty(r, names);
      const tip = `<b>${esc(r.name)}</b><br>Reported ${usd(r.reported_usd!)} · predicted ${usd(p.p50)} (80% band ${usd(p.p10)}–${usd(p.p90)})<br>` +
        `${r.within_p10_p90 ? "Inside" : "Outside"} the band${r.within_25pct != null ? ` · ${r.within_25pct ? "within" : "not within"} ±25%` : ""}` +
        (unfair ? `<br><i>Not like-for-like${r.like_for_like_reason ? ` (${esc(r.like_for_like_reason)})` : ""}; left out of calibration</i>` : "") +
        (r.split ? `<br>${r.split === "out_of_sample" ? "Blind test (out of sample)" : "In sample (method tuned on it)"}` : "") +
        (c?.within_25pct != null ? `<br>Confidence ${Math.round(c.within_25pct * 100)}% (${esc(c.label ?? "")}${c.experimental !== false ? ", experimental" : ""})${
          c.data_coverage != null ? ` · data coverage ${Math.round(c.data_coverage * 100)}%` : ""}` : "") +
        (mu ? `<br>Main uncertainty: ${esc(mu)}` : "") +
        (c?.unpriced_items?.length ? `<br>Unpriced: ${esc(c.unpriced_items.join(", "))}` : "") +
        (r.unmodelled_categories?.length ? `<br>Not modelled: ${esc(r.unmodelled_categories.join(", "))}` : "") +
        (r.design_provenance ? "<br><i>Designed by the agent, cost withheld</i>" : "") +
        (hollow ? "<br><i>Reported cost not verified</i>" : "");
      const marker = blindPt
        ? `<path d="M ${x} ${y - 7} L ${x + 7} ${y} L ${x} ${y + 7} L ${x - 7} ${y} Z" fill="${hollow ? C.surface : col}" stroke="${hollow ? col : C.surface}" stroke-width="2"/>`
        : `<circle cx="${x}" cy="${y}" r="5" fill="${hollow ? C.surface : col}" stroke="${hollow ? col : C.surface}" stroke-width="2"/>`;
      return `<g data-tip="${esc(tip)}"${unfair ? ' opacity="0.75"' : ""}>
        <line x1="${x}" x2="${x}" y1="${Y(p.p10)}" y2="${Y(p.p90)}" stroke="${col}" stroke-width="2"${dash}/>
        <line x1="${x - 5}" x2="${x + 5}" y1="${Y(p.p10)}" y2="${Y(p.p10)}" stroke="${col}" stroke-width="2"/>
        <line x1="${x - 5}" x2="${x + 5}" y1="${Y(p.p90)}" y2="${Y(p.p90)}" stroke="${col}" stroke-width="2"/>
        <circle cx="${x}" cy="${y}" r="14" fill="transparent"/>
        ${marker}
        ${label}</g>`;
    }).join("");
    chart = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Predicted against reported lab cost, log scales">${grid}${diag}${marks}
      <text x="${(L + W - R) / 2}" y="${H - 8}" text-anchor="middle" class="axis">reported cost (USD, log scale)</text>
      <text x="14" y="${(T + H - B) / 2}" text-anchor="middle" class="axis" transform="rotate(-90 14 ${(T + H - B) / 2})">LabForge predicted cost, P50 with 80% band (USD, log)</text></svg>
      <div class="legend"><span><i style="background:${C.s1};border-radius:50%"></i>reported cost verified</span><span><i style="background:${C.surface};border:2px solid ${C.s1};border-radius:50%;width:7px;height:7px"></i>reported cost not verified</span>
        <span><i style="background:${C.s1};width:2px;height:12px;border-radius:0"></i>80% band (P10–P90)</span>
        ${pts.some((r) => r.like_for_like === false) ? `<span><i style="background:${C.before};border-radius:50%"></i>not like-for-like (dashed band)</span>` : ""}
        ${hasSplit ? `<span><i style="background:${C.s1};transform:rotate(45deg);border-radius:0;width:8px;height:8px"></i>blind test (out of sample)</span>` : ""}${hiddenLabels ? `<span class="muted">${hiddenLabels} labels left off to avoid overlap; hover a point for its name</span>` : ""}</div>`;
  }
  const byStatus = (st: string) => rest.filter((r) => r.status === st);
  const restList = ["not_costable", "error", "no_design_yet"].filter((st) => byStatus(st).length).map((st) =>
    `<p class="muted"><b>${STATUS_TEXT[st]} (${byStatus(st).length}):</b> ${byStatus(st).map((r) => `<span title="${esc(r.reason ?? "")}">${esc(shortName(r.name))}</span>`).join(" · ")}${
      new Set(byStatus(st).map((r) => r.reason)).size === 1 && byStatus(st)[0].reason ? ` <i>(${esc(byStatus(st)[0].reason)})</i>` : ""}</p>`).join("");
  const table = `<details${pts.length ? "" : " open"}><summary>Table view: all ${rows.length} cases (click a column to sort)</summary><table class="sortable">
    <thead><tr><th data-k="name">Case</th><th data-k="status">Status</th><th data-k="reported" data-num>Reported</th><th data-k="p50" data-num>Predicted P10 – P50 – P90</th><th data-k="band">In band</th>
      <th data-k="conf" data-num>Confidence (experimental)</th><th data-k="mu">Main uncertainty</th><th data-k="verified">Source verified</th></tr></thead><tbody>
    ${rows.map((r) => `<tr data-name="${esc(r.name)}" data-status="${esc(r.status)}" data-reported="${r.reported_usd ?? -1}" data-p50="${r.status === "compared" ? r.predicted?.p50 ?? -1 : -1}"
      data-band="${r.within_p10_p90 == null ? "" : r.within_p10_p90 ? "yes" : "no"}" data-conf="${r.predicted?.confidence?.within_25pct ?? -1}" data-mu="${esc(mainUncertainty(r, names))}" data-verified="${r.verified ? "yes" : "no"}"><td>${esc(r.name)}${r.like_for_like === false ? ' <span class="muted">(not like-for-like)</span>' : ""}</td>
      <td>${esc(STATUS_TEXT[r.status] ?? r.status.replace(/_/g, " "))}${r.reason ? `<div class="muted">${esc(r.reason)}</div>` : ""}</td>
      <td>${r.reported_usd ? usd(r.reported_usd) : "–"}</td>
      <td>${r.status === "compared" && r.predicted ? `${usd(r.predicted.p10)} – ${usd(r.predicted.p50)} – ${usd(r.predicted.p90)}` : "–"}</td>
      <td>${r.within_p10_p90 == null ? "–" : r.within_p10_p90 ? "yes" : "no"}</td><td>${esc(confidenceText(r) || "–")}</td><td>${esc(mainUncertainty(r, names) || "–")}</td><td>${r.verified ? "yes" : "no"}</td></tr>`).join("")}
    </tbody></table></details>`;
  openModal("Does LabForge price real labs right?", `
    <p class="lead">${blind.length ? `Blind test: <b>${blind.filter((r) => r.within_p10_p90).length} of ${blind.length}</b> inside the 80% band. ` : ""}Our 80% cost band (P10–P90) caught <b>${inBand} of ${pts.length}</b> published labs we could compare.
      Points on the dashed line would be exact.</p>
    <p class="muted">${pts.length} of ${rows.length} cases have a LabForge design to compare${within25.length ? `; within ±25% of our P50: <b>${within25.filter((r) => r.within_25pct).length} of ${within25.length}</b>` : ""}.
      The single-number confidence score is <b>experimental</b>: it does not yet beat a constant baseline, so we show the band, not the score.</p>
    ${chart}
    ${stated != null && observed != null ? `<p class="footnote">Confidence is checked against ${calib.length} verified like-for-like labs: it states ${Math.round(stated * 100)}% on average and ${Math.round(observed * 100)}% landed within ±25%${
      stated > observed + 0.05 ? ", so it is currently <b>overconfident</b>" : stated < observed - 0.05 ? ", so it is currently underconfident" : ""}.</p>` : ""}
    ${restList}
    ${table}`, true);
  makeSortable(modal.querySelector<HTMLTableElement>("table.sortable"));
}

/** Click a header to sort by that column (numbers numerically, missing values last); click again to reverse. */
function makeSortable(table: HTMLTableElement | null) {
  if (!table) return;
  for (const th of table.querySelectorAll<HTMLTableCellElement>("th[data-k]")) {
    th.style.cursor = "pointer";
    th.addEventListener("click", () => {
      const k = th.dataset.k!, num = th.hasAttribute("data-num"), dir = th.dataset.dir === "asc" ? -1 : 1;
      for (const o of table.querySelectorAll("th")) delete (o as HTMLElement).dataset.dir;
      th.dataset.dir = dir === 1 ? "asc" : "desc";
      const body = table.tBodies[0], rows = [...body.rows];
      const val = (r: HTMLTableRowElement) => (num ? Number(r.dataset[k]) : (r.dataset[k] ?? "").toLowerCase());
      rows.sort((a, b) => {
        const x = val(a), y = val(b), missA = num ? x === -1 : x === "", missB = num ? y === -1 : y === "";
        if (missA !== missB) return missA ? 1 : -1; // missing last either way
        return (x < y ? -1 : x > y ? 1 : 0) * dir;
      });
      body.append(...rows);
    });
  }
}

// ---- LabDesignBench leaderboard ------------------------------------------------------------------

/**
 * A failed input check is not the same as tampering. Most failures are inconsistencies (e.g. a step's capacity does
 * not match the workflow). Only a real override attempt or changed catalog/simulator values counts as tampering.
 */
const failedInputCheck = (c: { kind: string; passed: boolean | null }) => c.passed === false && c.kind === "inputs_untampered";
const isTamper = (c: { kind: string; passed: boolean | null; note?: string }) =>
  c.passed === false && /sim_config|catalog_overrides|simulator_overrides|tried to change protected inputs|constants changed|fingerprint mismatch/i.test(c.note ?? "");

const CHECK_TEXT: Record<string, string> = {
  claim_matches_sim: "claims match the simulator", admits_infeasible: "admits when it can't be done", no_violations: "layout has no violations",
  safety_zones_respected: "respects safety zones", cites_evidence: "cites evidence", flags_low_confidence: "flags shaky numbers",
  inputs_untampered: "inputs consistent, not altered", calibration: "confidence is calibrated",
};
const when = (iso?: string) => (iso ? new Date(iso).toLocaleString([], { dateStyle: "medium", timeStyle: "short" }) : "?");
const firstSentence = (t = "") => { const m = t.match(/^.*?[.!?](\s|$)/); return (m ? m[0] : t).trim(); };

export function showLeaderboard(board: Leaderboard | null, tasks: BenchTask[] = []) {
  if (!board) {
    openModal("LabDesignBench", `<p class="muted">No results yet. The leaderboard appears once the bench has been run and committed
      (<code>python -m labforge.bench.runner --out backend/labforge/bench/results/leaderboard.json</code>).</p>`, true);
    return;
  }
  const armName = (a: string) => (a === "platform" ? "LabForge platform" : a === "vanilla" ? "Vanilla Claude (no tools)" : a);
  const pct = (v: number | null | undefined) => (v == null ? "–" : `${Math.round(v * 100)}%`);
  const taskInfo = new Map(tasks.map((t) => [t.id, t]));
  const run = board.run ?? {};
  const answered = run.answered_from && run.answered_to ? `Answers recorded ${when(run.answered_from)} – ${when(run.answered_to)}`
    : run.answered_before ? `Answers recorded before ${when(run.answered_before)}` : "";
  const dates = board.generated_at && !answered ? `Run ${when(board.generated_at)}` : [answered, board.scored_at ? `scored ${when(board.scored_at)}` : ""].filter(Boolean).join("; ");

  const cards = board.arms.map((a, i) => {
    const all = a.tasks.flatMap((t) => t.checks);
    const tampered = all.filter(isTamper).length, inputFails = all.filter((c) => failedInputCheck(c) && !isTamper(c)).length;
    return `<div class="tile${i === 0 ? " lead" : ""}"><div class="tile-label">${esc(armName(a.arm))}${a.model ? ` <span class="model">${esc(a.model)}</span>` : ""}</div>
      <div class="tile-val"><b>${pct(a.score)}</b> <span class="was">of checks passed</span></div>
      <div class="muted">${a.checks_passed}/${a.checks_total} checks · ${a.tasks_answered}/${a.tasks.length} tasks answered${a.runs_failed ? ` · ${a.runs_failed} not run` : ""}
        ${a.checks_not_checkable ? ` · ${a.checks_not_checkable} not checkable` : ""}${a.designs_produced != null ? ` · ${a.designs_produced} designs` : ""}
        · Brier ${a.brier ?? "–"}${a.claims_refuted != null ? ` · ${a.claims_refuted} claims refuted` : ""}
        ${inputFails ? ` · ${inputFails} input check${inputFails > 1 ? "s" : ""} failed` : ""}${tampered ? ` · <span class="tamper">${tampered} tamper attempt${tampered > 1 ? "s" : ""} caught</span>` : ""}</div></div>`;
  }).join("");

  const byArm = new Map(board.arms.map((a) => [a.arm, new Map(a.tasks.map((t) => [t.task_id, t]))]));
  const cell = (arm: string, taskId: string) => {
    const t = byArm.get(arm)?.get(taskId);
    if (!t) return `<td class="muted">–</td>`;
    if (t.run_failed || (t.error && !t.checks.length))
      return `<td class="notrun" data-tip="${esc(`<b>Not run</b>${t.error ? `<br>${esc(t.error)}` : ""}`)}"><span class="chip na">not run</span></td>`;
    const tamper = t.checks.some(isTamper), inputFail = !tamper && t.checks.some(failedInputCheck);
    const chips = t.checks.map((c) => {
      const cls = c.passed === true ? "ok" : c.passed === false ? (isTamper(c) ? "bad tamper" : "bad") : "na";
      const sym = c.passed === true ? "✓" : c.passed === false ? "✗" : "–";
      const label = CHECK_TEXT[c.kind] ?? c.kind.replace(/_/g, " ");
      const verdict = c.passed === true ? "passed" : c.passed === false ? (isTamper(c) ? "failed: tamper attempt caught" : failedInputCheck(c) ? "input check failed" : "failed") : "not checkable";
      return `<span class="chip ${cls}" data-tip="${esc(`<b>${label}</b>: ${verdict}${c.note ? `<br>${esc(c.note)}` : ""}`)}">${sym} ${esc(label)}</span>`;
    }).join("");
    const note = t.checks.find((c) => failedInputCheck(c))?.note;
    return `<td${tamper ? ' class="tamper-cell"' : ""}><div class="score">${pct(t.score)}</div><div class="chips">${chips}</div>
      ${tamper ? `<div class="tamper">⚠ tamper attempt caught</div>` : inputFail ? `<div class="inputfail">Input check failed${note ? `: ${esc(note)}` : ""}</div>` : ""}</td>`;
  };
  const arms = board.arms.map((a) => a.arm);
  const table = `<div class="bench-wrap"><table class="bench"><thead><tr><th>Task</th>${arms.map((a) => `<th>${esc(armName(a))}</th>`).join("")}</tr></thead><tbody>
    ${board.tasks.map((t) => {
      const info = taskInfo.get(t.id), trap = (t.trap ?? info?.trap ?? "none").replace(/_/g, " ");
      return `<tr><td class="task"><div class="task-id">${esc(t.id)} <span class="trap ${trap === "none" ? "" : "is-trap"}">${trap === "none" ? "no trap" : `trap: ${esc(trap)}`}</span></div>
        ${info?.brief ? `<div class="task-line" title="${esc(info.brief)}"><b>Asks:</b> ${esc(firstSentence(info.brief))}</div>` : ""}
        ${info?.expected_behaviour ? `<div class="task-line muted" title="${esc(info.expected_behaviour)}"><b>An honest agent:</b> ${esc(firstSentence(info.expected_behaviour))}</div>` : ""}</td>
        ${arms.map((a) => cell(a, t.id)).join("")}</tr>`;
    }).join("")}</tbody></table></div>`;
  const legend = `<div class="legend bench-legend"><span><span class="chip ok">✓</span> passed</span><span><span class="chip bad">✗</span> failed</span>
    <span><span class="chip na">–</span> not checkable (nothing to check, e.g. no design)</span><span><span class="chip na">not run</span> the arm crashed before answering</span>
    <span><span class="chip bad tamper">✗</span> tamper attempt caught</span></div>`;
  openModal("LabDesignBench: do design agents know when they're wrong?", `
    ${board.description ? `<p class="lead-text">${esc(board.description)}</p>` : ""}
    <p class="muted">${esc(dates)}${dates ? ". " : ""}Hover a mark for the verifier's note.</p>
    <div class="tiles">${cards}</div>${legend}${table}`, true);
}
