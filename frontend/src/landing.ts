import { loadReplay, type RecordedRun } from "./replay";

/**
 * Strand A: the landing page (#/). Two recorded case studies and "Design your own lab". Each case subtitle is read
 * from that case's replay file (throughput band, target, top capacity bottleneck), never hard-coded, so it stays
 * true when the recordings are replaced.
 */

export const CASES = [
  { name: "chem", title: "768-compound library: two-step synthesis, LC-MS QC and protein screening" },
  { name: "fbdd", title: "XChem fragment screening: from E. coli expression to synchrotron shipping" },
];

const esc = (s: unknown) => String(s ?? "").replace(/[&<>"]/g, (c) => `&#${c.charCodeAt(0)};`);
const fmt = (n: number) => (Math.abs(n) >= 100 ? Math.round(n).toLocaleString() : String(+n.toFixed(1)));
const SEVERITY: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3 };

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
      const h = caseHeadline(await loadReplay(c.name));
      sub.innerHTML = h.note ? esc(h.note) : `<div class="headline">${esc(h.throughput)}</div>
        <div class="muted">${esc(h.detail)}</div>${h.bottleneck ? `<div>Bottleneck: <b>${esc(h.bottleneck)}</b></div>` : ""}`;
    } catch (e) {
      sub.textContent = (e as Error).message;
    }
  }));
}
