import { loadReplay, loadSummary, type RecordedRun } from "./replay";
import type { CaseSummary } from "./types";

/**
 * Strand A: the landing page (#/). Two recorded case studies and "Design your own lab". Each case subtitle is read
 * from that case's <name>.summary.json (planned vs independently checked throughput, gate, budget, bottleneck), or
 * from the replay itself when there is no summary; never hard-coded, so it stays true when recordings are replaced.
 */

export const CASES = [
  { name: "chem", title: "768-compound library: two-step synthesis, LC-MS QC and protein screening" },
  { name: "fbdd", title: "XChem fragment screening: from E. coli expression to synchrotron shipping" },
];

const esc = (s: unknown) => String(s ?? "").replace(/[&<>"]/g, (c) => `&#${c.charCodeAt(0)};`);
const fmt = (n: number) => (Math.abs(n) >= 100 ? Math.round(n).toLocaleString() : String(+n.toFixed(1)));
const SEVERITY: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3 };
const unitOf = (u: string) => u.replace(/_/g, " ");
const perDay = (u: string) => unitOf(u).replace(/^\S+ per day$/, "/day");
const usd = (v: number) => (v >= 1e6 ? `$${+(v / 1e6).toFixed(2)}M` : `$${Math.round(v / 1e3)}k`);

/** Headline facts from a summary file: the planning number next to the independent check, plus gate and budget. */
export function summaryHeadline(s: CaseSummary) {
  const t = s.headline_throughput;
  const throughput = `${fmt(t.p50)} ${unitOf(t.unit)} planned`;
  const checked = t.verified_p50 != null ? `${fmt(t.verified_p50)}${perDay(t.unit)} independently checked` : undefined;
  const detail = [
    t.p10 != null && t.p90 != null ? `planned P10–P90 ${fmt(t.p10)}–${fmt(t.p90)}` : "",
    t.target != null ? `target ${fmt(t.target)}` : "",
  ].filter(Boolean).join(" · ");
  const b = s.bottleneck;
  const bottleneck = b ? `${b.model ? `${b.model} (${b.instance_id})` : b.name ?? b.instance_id}${b.busy_fraction != null ? `, busy ${Math.round(b.busy_fraction * 100)}%` : ""}` : undefined;
  const m = s.budget_vs_bom;
  const budget = m?.bom != null && m.budget != null ? `Equipment ${usd(m.bom)} vs budget ${usd(m.budget)}${m.claim_status ? ` (claim ${m.claim_status})` : ""}` : undefined;
  const gate = s.gate_passed == null ? undefined : s.gate_passed ? "Checks: passed" : "Checks: not all passed";
  return { throughput, checked, detail, bottleneck, budget, gate };
}

/** The "What we checked" box for a case page: planned vs checked, gate, budget and every recorded limit. */
export function summaryBox(s: CaseSummary): string {
  const h = summaryHeadline(s), t = s.headline_throughput, m = s.budget_vs_bom;
  const day = (v: number) => `${fmt(v)}${perDay(t.unit)}`;
  return `<b>What we checked</b>
    <div class="check-row"><span>Planned (simulation)</span><span>${esc(day(t.p50))}</span></div>
    ${t.verified_p50 != null ? `<div class="check-row"><span>Independent check</span><span>${esc(day(t.verified_p50))}</span></div>` : ""}
    ${t.target != null ? `<div class="check-row"><span>Target</span><span>${esc(day(t.target))}</span></div>` : ""}
    ${m?.bom != null && m.budget != null ? `<div class="check-row"><span>Equipment / budget</span><span>${esc(`${usd(m.bom)} / ${usd(m.budget)}`)}</span></div>` : ""}
    ${h.gate ? `<div class="check-row"><span>Gate</span><span class="${s.gate_passed ? "ok" : "warn"}">${esc(h.gate)}</span></div>` : ""}
    ${s.limits?.length ? `<div class="limits-title">Limits</div><ul class="limits">${s.limits.map((l) => `<li>${esc(l)}</li>`).join("")}</ul>` : ""}`;
}

/** Headline facts for a recorded run, or why there are none. */
export function caseHeadline(run: RecordedRun): { throughput?: string; detail?: string; bottleneck?: string; note?: string } {
  const sim = run.output.sim_result, wf = run.output.workflow;
  if (!sim || !wf) return { note: "This recording stopped before producing a design; open it to see why." };
  const t = sim.throughput, unit = String(t.unit ?? "").replace(/_/g, " ");
  const detail = [
    t.p10 != null && t.p90 != null ? `P10–P90 ${fmt(t.p10)}–${fmt(t.p90)}` : "",
    t.target != null ? `target ${fmt(t.target)}` : "",
    t.prob_meets_target != null ? `${Math.round(t.prob_meets_target * 100)}% chance of meeting it` : "",
  ].filter(Boolean).join(" · ");
  const b = [...sim.bottlenecks].filter((x) => x.kind !== "long_transfer" && x.instances?.length)
    .sort((x, y) => (SEVERITY[x.severity] ?? 9) - (SEVERITY[y.severity] ?? 9))[0];
  let bottleneck: string | undefined;
  if (b) {
    const id = b.instances![0], eq = wf.equipment.find((e) => e.instance_id === id);
    const model = eq && run.catalog?.[eq.catalog_id]?.model;
    const busy = sim.utilisation.find((u) => u.instance_id === id)?.busy_fraction;
    bottleneck = `${model ? `${model} (${id})` : id}${busy != null ? `, busy ${Math.round(busy * 100)}%` : ""}`;
  }
  return { throughput: `${fmt(t.p50 ?? t.value)} ${unit}`, detail, bottleneck };
}

export async function renderLanding(el: HTMLElement) {
  el.innerHTML = `
    <div class="landing-inner">
      <p class="pitch">Describe the autonomous lab you want. An agent designs it from real vendor equipment, lays it out, simulates it,
        and tells you which of its own numbers it doesn't trust.</p>
      <div class="cards">
        ${CASES.map((c) => `<a class="card frame-card" href="#/case/${c.name}" data-case="${c.name}">
          <div class="card-kicker">Case study · recorded agent run</div>
          <h2>${esc(c.title)}</h2><div class="card-sub muted">Loading…</div><div class="card-go">Watch the replay ▸</div></a>`).join("")}
        <a class="card frame-card own" href="#/design">
          <div class="card-kicker">Live</div>
          <h2>Design your own lab</h2>
          <div class="card-sub">Chat with the agent about your own brief. It picks equipment, lays out the room, simulates it and writes the report.
            <span class="muted">Needs the backend with an API key.</span></div>
          <div class="card-go">Start designing ▸</div></a>
      </div>
    </div>`;
  await Promise.all(CASES.map(async (c) => {
    const sub = el.querySelector<HTMLElement>(`[data-case="${c.name}"] .card-sub`)!;
    try {
      const summary = await loadSummary(c.name);
      if (summary) {
        const h = summaryHeadline(summary);
        sub.innerHTML = `<div class="headline">${esc(h.throughput)}</div>
          ${h.checked ? `<div class="checked">${esc(h.checked)}</div>` : ""}
          <div class="muted">${esc(h.detail)}</div>
          ${h.bottleneck ? `<div>Bottleneck: <b>${esc(h.bottleneck)}</b></div>` : ""}
          ${h.budget ? `<div class="muted">${esc(h.budget)}</div>` : ""}
          ${h.gate ? `<div class="${summary.gate_passed ? "ok" : "warn"}">${esc(h.gate)}${summary.limits?.length ? ` · ${summary.limits.length} known limits` : ""}</div>` : ""}`;
        return;
      }
      const h = caseHeadline(await loadReplay(c.name));
      sub.innerHTML = h.note ? esc(h.note) : `<div class="headline">${esc(h.throughput)}</div>
        <div class="muted">${esc(h.detail)}</div>${h.bottleneck ? `<div>Bottleneck: <b>${esc(h.bottleneck)}</b></div>` : ""}`;
    } catch (e) {
      sub.textContent = (e as Error).message;
    }
  }));
}
