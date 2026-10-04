import { health, LIVE_CHAT_MESSAGE } from "./api";
import { loadReplay, loadSummary, type RecordedRun } from "./replay";
import { loadScheduleCase, scheduleMC, type ScheduleCase } from "./schedulecase";
import { projectName } from "./views";
import { startTwinHero, twinHero } from "./twin";
import type { CaseSummary } from "./types";

/**
 * Strand A: the landing page (#/: pitch and two buttons) and the case-study page (#/cases). Each case subtitle is read
 * from that case's <name>.summary.json (planned vs independently checked throughput, gate, budget, bottleneck), or
 * from the replay itself when there is no summary; never hard-coded, so it stays true when recordings are replaced.
 */

/** `problem`: the request in plain words for the card; targets, room and budget are filled in from the recording. */
export const CASES = [
  { name: "chem", title: "768-compound library: two-step synthesis, LC-MS QC and protein screening",
    problem: "A medicinal-chemistry team wants a lab that makes a 768-compound library in two reaction steps, checks every compound's purity by LC-MS, and tests each one against a protein target, running around the clock." },
  { name: "fbdd", title: "XChem fragment screening: from E. coli expression to synchrotron shipping",
    problem: "A structural-biology team wants an XChem-style fragment-screening lab: make the protein, grow crystals, soak small fragments into them, harvest the crystals by hand and ship them to a synchrotron." },
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

/** The landing page (#/): title, the pitch, two buttons ("Design your own lab", "Case studies") and the twin hero. */
export function renderLanding(el: HTMLElement) {
  el.innerHTML = `
    <div class="landing-inner home">
      <h1 class="hero-title">Digital twin for autonomous labs</h1>
      <p class="pitch">Describe the autonomous lab you want. An agent designs it from real vendor equipment, lays it out, simulates it,
        and tells you which of its own numbers it doesn't trust.</p>
      <div class="big-buttons">
        <a class="big-btn own" href="#/design"><span class="big-label">Design your own lab</span><span class="big-sub">Chat with the agent about your brief</span></a>
        <a class="big-btn" href="#/cases"><span class="big-label">Case studies</span><span class="big-sub">Two lab designs and a scheduling plan, with what we checked</span></a>
      </div>
    </div>
    ${twinHero()}`;
  startTwinHero(el);
  // Say up front when live design is unavailable (public demo, no backend, or no API key).
  health().then(({ state, liveAgent, note }) => {
    const own = el.querySelector<HTMLElement>(".big-btn.own");
    if (!own || (state === "on" && liveAgent)) return;
    // Short on the button; the full setup note (note) is shown in the #/design banner.
    own.querySelector(".big-sub")!.textContent = state === "on"
      ? "Live agent off (no API key): replies use the offline worked example."
      : LIVE_CHAT_MESSAGE[state];
    if (state === "on" && note) own.title = note;
    own.classList.add("limited");
  });
}

/** The case-study page (#/cases): one card per recorded case, subtitles read from its summary or replay. */
/**
 * A case card as a short story a person can follow: the ask, what LabForge did, what it found, and why that matters.
 * Every number is read from the recording (lab_spec, workflow, layout, checked claims) and its summary; the
 * "why it matters" line is chosen by the outcome (target met or not), never written per case.
 */
export function caseStory(run: RecordedRun, s: CaseSummary, problem?: string): string {
  const o = run.output, ls = o.lab_spec ?? {}, t = s.headline_throughput, m = s.budget_vs_bom, b = s.bottleneck;
  const unit = unitOf(t.unit), perDay = perDay_(t.unit);
  const target = t.target ?? ls.throughput_target?.value, checked = t.verified_p50 ?? t.p50;
  const room = ls.room?.width_m && ls.room?.depth_m ? `${fmt(ls.room.width_m)} × ${fmt(ls.room.depth_m)} m room` : "";
  const budget = m?.budget ?? ls.constraints?.budget_usd;
  const nEq = o.workflow?.equipment.length ?? 0, viol = o.layout?.violations?.length ?? 0;
  const claims = (o.claims ?? []).filter((c) => c.status), refuted = claims.filter((c) => c.status === "refuted").length;
  const prob = o.sim_result?.throughput.prob_meets_target;
  const met = target != null && checked >= target;
  const overBudget = m?.bom != null && budget != null && m.bom > budget;
  const busy = b?.busy_fraction != null ? `${Math.round(b.busy_fraction * 100)}% busy` : "";
  const limit = b ? `${b.model ?? b.name ?? b.instance_id}${busy ? ` (${busy})` : ""}` : "";

  const ask = `${esc(problem ?? s.brief ?? "")}${target != null ? ` Goal: <b>${fmt(target)} ${esc(unit)}</b>` : ""}${room ? `, in a ${room}` : ""}${budget != null ? `, with a <b>${usd(budget)}</b> equipment budget` : ""}.`;
  const did = `Picked <b>${nEq} instruments</b> from real vendor catalogs, laid out the room${viol === 0 ? " with no layout violations" : ` (${viol} layout violation${viol === 1 ? "" : "s"} to fix)`},
    simulated it, and had an independent verifier check ${claims.length ? `its ${claims.length} key claims` : "its numbers"}.`;
  let found: string, why: string;
  if (met) {
    found = `<b>Meets the target:</b> ${fmt(checked)}${perDay} independently checked vs ${fmt(target!)} asked${prob != null ? ` (${Math.round(prob * 100)}% chance in simulation)` : ""}${
      m?.bom != null && budget != null ? `, for <b>${usd(m.bom)}</b> of the ${usd(budget)} budget` : ""}.${limit ? ` Busiest instrument: ${esc(limit)}.` : ""}`;
    const st = s.imager_staffing_whatifs as any, best = st?.variants?.third_operator;
    why = best?.verified_p50 != null
      ? `A costed, checked design in one conversation, plus a tested next step: with one more operator and the idle imager used for growth, the check gives about <b>${fmt(best.verified_p50)}${perDay}</b>, if the synchrotron can keep up.`
      : `A costed, checked design in one conversation, with its bottleneck and limits spelled out.`;
  } else {
    const pct = target ? Math.round((checked / target) * 100) : undefined;
    found = `<b>Can't be done as briefed:</b> about ${fmt(checked)}${perDay} independently checked vs ${fmt(target!)} asked${pct != null ? ` (${pct}% of the target)` : ""}${
      overBudget ? `, and the equipment would cost <b>${usd(m!.bom!)}</b> against a ${usd(budget!)} budget` : ""}.${limit ? ` Limiting step: <b>${esc(limit)}</b>.` : ""}`;
    why = `You learn the brief is out of reach, and exactly which step limits it, <b>before</b> committing ${overBudget ? usd(m!.bom!) + " to equipment" : "money to equipment"}.${
      refuted ? ` LabForge flagged its own ${refuted} failed claim${refuted === 1 ? "" : "s"} instead of hiding them.` : ""}`;
  }
  return storyHtml(ask, did, found, met, why);
}
const perDay_ = (u: string) => (unitOf(u).endsWith("per day") ? "/day" : ` ${unitOf(u)}`);

/**
 * A case story: the ask and what LabForge did are always shown. "What it found" and "Why it matters" keep their
 * headings, and each heading opens its own text on click (collapsed by default) so the cards stay short.
 */
function storyHtml(ask: string, did: string, found: string, good: boolean, why: string): string {
  return `<dl class="story">
      <dt>The ask</dt><dd>${ask}</dd>
      <dt>What LabForge did</dt><dd>${did}</dd>
    </dl>
    <details class="story-item"><summary>What it found</summary><div class="story-body ${good ? "good" : "bad"}">${found}</div></details>
    <details class="story-item"><summary>Why it matters</summary><div class="story-body why">${why}</div></details>`;
}

/** The scheduling case title, in the same "topic: detail" style as the design cases. */
export const SCHEDULE_CASE_TITLE = "Shared screening cell: three projects, one urgent deadline, best running order";

/**
 * The scheduling case card, in the same four parts as the design cases, from the queue and the /prioritise result:
 * the ask, what LabForge did, what it found and why it matters. Nothing is hard-coded.
 */
export function scheduleStory({ projects, result: s }: ScheduleCase): string {
  const given = projects.map((p) => p.id);
  const rec = s.candidates.find((c) => c.policy === s.recommended) ?? s.candidates[0];
  const naive = s.candidates.find((c) => c.order?.join(">") === given.join(">"));
  const instruments = new Set(projects.flatMap((p) => p.workflow.equipment.map((e) => e.instance_id))).size;
  const list = (xs: string[]) => (xs.length < 2 ? xs.join("") : `${xs.slice(0, -1).join(", ")} and ${xs.at(-1)}`);
  const due = projects.filter((p) => p.deadline_h != null);
  const asked = list(projects.map((p) => `${projectName(p.id).toLowerCase()} (${p.units} plates${p.deadline_h != null ? `, due within ${fmt(p.deadline_h)} h` : ""})`));
  const ask = `A screening team shares one existing cell, with ${instruments} instruments, between ${projects.length} projects: ${esc(asked)}.
    In what order should they run so ${due.length ? "the urgent work meets its deadline and " : ""}everything finishes soonest?`;
  const nOrders = s.candidates.filter((c) => c.order).length, nMixed = s.candidates.length - nOrders;
  const mc = scheduleMC(s.caveat);
  const did = `Simulated <b>all ${nOrders + nMixed} running orders</b> on the cell's instruments, picked the best for deadlines and finish time${
    mc ? `, and re-checked it over ${mc.reps} random variations of step times` : ""}.`;
  const fin = rec.project_finish_h ?? {}, firstDue = (rec.order ?? []).map((id) => projects.find((p) => p.id === id)).find((p) => p?.deadline_h != null);
  const orderText = (rec.order ?? []).map(projectName).join(" → ");
  const missedBefore = naive?.deadline_misses?.length ?? 0, missedAfter = rec.deadline_misses?.length ?? 0;
  // Finish times: the Monte Carlo medians when reported (same pair as the README and the case page), else average step times.
  const recH = mc?.rec ?? rec.makespan_h, naiveH = naive ? mc?.naive ?? naive.makespan_h : undefined;
  const saved = naiveH != null ? naiveH - recH : 0;
  const found = `<b>Best order: ${esc(orderText)}.</b> Everything is done in ${mc ? "about " : ""}${fmt(recH)} h${naiveH != null ? ` instead of ${fmt(naiveH)} h in the order listed` : ""}${mc ? ` (median of ${mc.reps} simulations)` : ""}${
    firstDue && fin[firstDue.id] != null ? `, and the ${esc(projectName(firstDue.id).toLowerCase())} finishes at ${fmt(fin[firstDue.id])} h (deadline ${fmt(firstDue.deadline_h!)} h)` : ""}.${
    missedBefore > missedAfter ? ` The order listed misses ${missedBefore} deadline${missedBefore === 1 ? "" : "s"}.` : ""}`;
  const why = saved > 0.05
    ? `The same lab gets about <b>${fmt(saved)} h</b> back and ${missedAfter === 0 ? "keeps every deadline" : "misses fewer deadlines"} with <b>no new equipment</b>: only the running order changes.`
    : `Shows that the order listed is already close to best, so time would be better spent elsewhere.`;
  return storyHtml(ask, did, found, missedAfter === 0, why);
}

export async function renderCases(el: HTMLElement) {
  el.innerHTML = `
    <div class="landing-inner">
      <h1 class="cases-title">Case studies</h1>
      <p class="pitch small">Three case studies modelled on real drug-discovery work: two lab designs answered by the LabForge agent and replayed here,
        and a plan for running projects through a lab that already exists. Each card says what was asked, what LabForge did and what it found.</p>
      <div class="cards">
        ${CASES.map((c) => `<div class="card frame-card" data-case="${c.name}">
          <div class="card-kicker">Case study · recorded agent run</div>
          <h2><a href="#/case/${c.name}">${esc(c.title)}</a></h2><div class="card-sub muted">Loading…</div><a class="card-go" href="#/case/${c.name}">Watch the replay ▸</a></div>`).join("")}
        <div class="card frame-card" data-case="schedule">
          <div class="card-kicker">Case study · scheduling run</div>
          <h2><a href="#/case/schedule">${esc(SCHEDULE_CASE_TITLE)}</a></h2><div class="card-sub muted">Loading…</div><a class="card-go" href="#/case/schedule">Open the schedule ▸</a></div>
      </div>
    </div>`;
  loadScheduleCase().then((sc) => {
    const sub = el.querySelector<HTMLElement>('[data-case="schedule"] .card-sub')!;
    sub.classList.remove("muted");
    sub.innerHTML = scheduleStory(sc);
  }).catch((e) => { el.querySelector('[data-case="schedule"] .card-sub')!.textContent = (e as Error).message; });
  await Promise.all(CASES.map(async (c) => {
    const sub = el.querySelector<HTMLElement>(`[data-case="${c.name}"] .card-sub`)!;
    try {
      const [summary, run] = await Promise.all([loadSummary(c.name), loadReplay(c.name)]);
      if (summary && run.output.workflow) {
        sub.classList.remove("muted");
        sub.innerHTML = caseStory(run, summary, c.problem);
        return;
      }
      const h = caseHeadline(run);
      sub.innerHTML = h.note ? esc(h.note) : `<div class="headline">${esc(h.throughput)}</div>
        <div class="muted">${esc(h.detail)}</div>${h.bottleneck ? `<div>Bottleneck: <b>${esc(h.bottleneck)}</b></div>` : ""}`;
    } catch (e) {
      sub.textContent = (e as Error).message;
    }
  }));
}
