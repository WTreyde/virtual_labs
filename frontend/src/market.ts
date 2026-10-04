/**
 * #/market: why LabForge matters, as three points with headline numbers, charts and a reference under every figure.
 * Figures come from the team's market research; each carries `verified` until an opened source confirms it.
 */
const C = { s1: "#2a78d6", s2: "#eb6834", rest: "#d9d7cf", ink: "#1d2330", ink2: "#52514e", grid: "#e4e3dd" };
const esc = (s: string) => s.replace(/[&<>"]/g, (c) => `&#${c.charCodeAt(0)};`);

type Ref = { title: string; publisher: string; date: string; url?: string; verified: boolean };
type Bar = { label: string; value: number };

function ref(r: Ref): string {
  const link = r.url ? `<a href="${esc(r.url)}" target="_blank" rel="noopener">${esc(r.title)}</a>` : esc(r.title);
  const badge = r.verified ? "" : ` <span class="chip na" title="Number not yet confirmed against the opened source">verification pending</span>`;
  return `<p class="muted small">Source: ${link}, ${esc(r.publisher)}, ${esc(r.date)}.${badge}</p>`;
}

function hero(value: string, caption: string): string {
  return `<div class="hero-stat"><div style="font-size:44px;font-weight:700;color:${C.ink}">${esc(value)}</div>
    <div class="muted">${esc(caption)}</div></div>`;
}

/** Horizontal percentage bars, one series (title names it), value labels in ink, highlight = first bar. */
function bars(rows: Bar[], highlight = 0): string {
  const W = 520, L = 230, H = 26, top = 6, max = 100;
  const x = (v: number) => ((W - L - 40) * v) / max;
  const body = rows.map((r, i) => {
    const y = top + i * (H + 8);
    return `<g data-tip="${esc(`<b>${esc(r.label)}</b>: ${r.value}%`)}">
      <text x="${L - 8}" y="${y + H / 2 + 4}" text-anchor="end" font-size="12" fill="${C.ink2}">${esc(r.label)}</text>
      <rect x="${L}" y="${y}" width="${x(100)}" height="${H}" rx="4" fill="${C.grid}"/>
      <rect x="${L}" y="${y}" width="${Math.max(2, x(r.value))}" height="${H}" rx="4" fill="${i === highlight ? C.s1 : C.rest}"/>
      <text x="${L + x(r.value) + 6}" y="${y + H / 2 + 4}" font-size="12" fill="${C.ink}">${r.value}%</text></g>`;
  }).join("");
  return `<svg viewBox="0 0 ${W} ${top + rows.length * (H + 8)}" width="100%" role="img">${body}</svg>`;
}

function section(n: number, title: string, claim: string, figures: string): string {
  return `<section style="margin:18px 0 26px"><h3>${n}. ${esc(title)}</h3><p>${esc(claim)}</p>
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:20px">${figures}</div></section>`;
}

const IQVIA: Ref = { title: "Global Trends in R&D 2025: Progress in Recapturing Momentum in Biopharma Innovation",
  publisher: "IQVIA Institute", date: "March 2025",
  url: "https://www.iqvia.com/insights/the-iqvia-institute/reports-and-publications/reports/global-trends-in-r-and-d", verified: true };
const MACHINEQ: Ref = { title: "Comcast's MachineQ Survey Reveals Nearly 60% of Lab Professionals Reported Unplanned Downtime (400+ US lab professionals, Censuswide)",
  publisher: "Comcast press release", date: "19 February 2025",
  url: "https://corporate.comcast.com/press/releases/comcast-machineq-survey-lab-professionals-reported-unplanned-downtime", verified: true };
const TUFTS_DELAY: Ref = { title: "New Estimates on the Cost of a Delay Day in Drug Development (Smith, DiMasi, Getz)",
  publisher: "Therapeutic Innovation & Regulatory Science 58(5):855-862 (Tufts CSDD)", date: "September 2024",
  url: "https://pubmed.ncbi.nlm.nih.gov/38773058/", verified: true };
const NATURE_LEAD: Ref = { title: "Research institutions must put the health of labs first (Nature survey of 3,200+ scientists)",
  publisher: "Nature (editorial)", date: "May 2018", url: "https://www.nature.com/articles/d41586-018-05159-0", verified: true };
const SCIEX: Ref = { title: "Lab Startup Playbook: What It Actually Takes to Get a Lab Space Operationally Ready",
  publisher: "Science Exchange", date: "28 May 2026", url: "https://www.scienceexchange.com/blog/lab-startup-space-operationally-ready", verified: true };

export function marketHtml(): string {
  const p1 = `<figure>${hero("85%", "of the 48 new drugs launched in 2024 were originated by emerging biopharma companies (41 of 48)")}${ref(IQVIA)}</figure>`;
  const p2 = `<figure><h4>US lab professionals reporting significant downtime</h4>${bars([{ label: "Significant downtime", value: 60 }])}
    <p class="small">"Nearly 60%", due to equipment failures, missed calibration schedules and difficulty locating lab assets. A vendor-run survey.</p>${ref(MACHINEQ)}</figure>
    <figure>${hero("$500,000", "in lost sales for each day a drug's development is delayed; running a phase II/III trial costs about $40,000 per day")}
    <p class="small">Average over 645 drugs launched since 2000. A Tufts white paper (Aug 2024) puts lost sales nearer $800,000/day.</p>${ref(TUFTS_DELAY)}</figure>`;
  const p3 = `<figure><h4>Lab heads with no training in managing people</h4>${bars([{ label: "No management training", value: 67 }])}
    <p class="small">"Two-thirds" of lab heads in a Nature survey of 3,200+ scientists. Scientists are trained to do experiments, not to run labs; no survey we found measures hardware and instrumentation know-how directly.</p>${ref(NATURE_LEAD)}</figure>
    <figure>${hero("4–6 weeks", "to set up utility, gas and liquid-nitrogen supply accounts: the kind of hardware and operations detail a wet-lab founder rarely knows to plan for")}
    <p class="small">Practitioner observation from a lab-operations team, not survey data.</p>${ref(SCIEX)}</figure>
    <figure><h4>What an autonomous-lab designer adds</h4><ul class="small">
      <li>Picks real, priced instruments for each protocol step, with sources and confidence for every number.</li>
      <li>Lays them out to safety rules (fume hoods, cryogens, biosafety cabinets) and simulates throughput.</li>
      <li>Names the bottleneck and the inputs it is unsure of before anyone signs a purchase order.</li></ul></figure>`;
  return `<div class="answer">
    <p>Why a lab-design agent that knows what it doesn't know is worth building. Every figure below was checked against its opened source (4 Oct 2026).</p>
    ${section(1, "Most new drugs now start in emerging biotechs", "Emerging biopharma companies originate most new medicines, and most have no in-house lab-operations team.", p1)}
    ${section(2, "Lab operations gaps cause costly delays", "Equipment downtime is common, and every day of delay in drug development is expensive. The link to lab planning is inferred: we found no study measuring it as the root cause.", p2)}
    ${section(3, "Why an autonomous lab", "Founders and lab heads come from the wet lab, not from hardware and instrumentation. An agent that designs, lays out and simulates the lab fills that gap.", p3)}
    <p class="muted small">Not shown because unverified: McKinsey's first-time-launcher multiplier (page unreachable from our checks), a "20–30% budget underestimate" claim, and an "80% of trials miss enrolment" figure.</p>
  </div>`;
}
