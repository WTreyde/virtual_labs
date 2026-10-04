/**
 * #/market: why LabForge matters. Three points, each figure with a source link, and three pillar buttons whose
 * explanations appear on hover (the page's data-tip tooltip). Chart text is set at least twice the body-text size.
 */
const C = { s1: "#2a78d6", rest: "#d9d7cf", ink: "#1d2330", ink2: "#52514e", grid: "#e4e3dd" };
const esc = (s: string) => s.replace(/[&<>"]/g, (c) => `&#${c.charCodeAt(0)};`);
const BODY = 12;        // px: paragraphs, notes, sources
const CHART = 26;       // px: chart labels, values, figure titles (>= 2x BODY)
const BAR_LABEL = 44, BAR_VALUE = 120;  // px: bar labels; every percentage value

type Ref = { title: string; publisher: string; date: string; url?: string; verified: boolean };
type Bar = { label: string; value: number };

function ref(r: Ref): string {
  const link = r.url ? `<a href="${esc(r.url)}" target="_blank" rel="noopener">${esc(r.title)}</a>` : esc(r.title);
  return `<p class="muted" style="font-size:${BODY - 1}px;margin-top:10px">Source: ${link}, ${esc(r.publisher)}, ${esc(r.date)}.</p>`;
}

function note(text: string): string {
  return `<p style="font-size:${BODY}px;color:${C.ink2};margin:8px 0 0">${esc(text)}</p>`;
}

function title(text: string): string {
  return `<h4 style="font-size:${CHART}px;line-height:1.2;margin:0 0 10px;color:${C.ink}">${esc(text)}</h4>`;
}

function hero(value: string, caption: string, size = CHART * 2.4): string {
  return `<div style="font-size:${size}px;font-weight:700;line-height:1;color:${C.s1}">${esc(value)}</div>
    <div style="font-size:${CHART}px;line-height:1.25;color:${C.ink};margin-top:8px">${esc(caption)}</div>`;
}

/** Percentage bars in HTML (not SVG) so text renders at exact sizes: big value, large label. */
function bars(rows: Bar[]): string {
  return rows.map((r) => `<div data-tip="${esc(`<b>${esc(r.label)}</b>: ${r.value}%`)}" style="margin:6px 0 14px">
    <div style="font-size:${BAR_LABEL}px;line-height:1.1;color:${C.ink};margin-bottom:8px">${esc(r.label)}</div>
    <div style="display:flex;align-items:center;gap:18px">
      <div style="flex:1;height:56px;background:${C.grid};border-radius:6px;overflow:hidden">
        <div style="width:${r.value}%;height:100%;background:${C.s1};border-radius:6px"></div></div>
      <div style="font-size:${BAR_VALUE}px;font-weight:700;line-height:1;color:${C.ink}">${r.value}%</div></div></div>`).join("");
}

function section(n: number, heading: string, claim: string, figures: string): string {
  return `<section style="margin:22px 0 30px"><h3 style="margin-bottom:4px">${n}. ${esc(heading)}</h3>
    <p style="font-size:${BODY}px;color:${C.ink2};margin:0 0 14px">${esc(claim)}</p>
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(440px,1fr));gap:28px">${figures}</div></section>`;
}

const PILLARS: { name: string; line: string; tip: string }[] = [
  { name: "Confidence", line: "Every number sourced. Every unknown named.",
    tip: "<b>Confidence</b><br>Every number carries its source and a confidence label, and the agent names the inputs it is unsure of before anyone signs a purchase order." },
  { name: "Safety", line: "Laid out to real safety rules.",
    tip: "<b>Safety</b><br>Instruments are laid out to sourced safety rules: fume hoods, cryogen areas with oxygen monitoring, biosafety cabinet clearances, guarded robot arms." },
  { name: "Efficiency", line: "The right kit, the bottleneck found first.",
    tip: "<b>Efficiency</b><br>Real, priced instruments for each protocol step, a simulated throughput band, and the bottleneck named, so you buy the right kit first." },
];

/** Pillar cards in the logo's pixel font: pale blue at rest, bright blue on hover (with the detail tooltip). */
function pillars(): string {
  const card = (p: { name: string; line: string; tip: string }) => `<div class="mk-card" data-tip="${esc(p.tip)}">
      <div class="mk-name">${esc(p.name)}</div><div class="mk-line">${esc(p.line)}</div></div>`;
  return `<style>
    .mk-pillars { font-family: "Press Start 2P", ui-monospace, monospace; }
    .mk-row { display: flex; gap: 24px; flex-wrap: wrap; justify-content: center; margin: 16px 0 6px; }
    .mk-card { width: 300px; min-height: 170px; border-radius: 14px; padding: 20px; box-sizing: border-box; cursor: help;
      display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center;
      background: #dbe9f9; color: #174a8b; border: 3px solid #b9d3f2; transition: background .25s, color .25s, border-color .25s, transform .25s; }
    .mk-card:hover { background: #2a78d6; color: #fff; border-color: #174a8b; transform: translateY(-3px); }
    .mk-name { font-size: 20px; letter-spacing: 1px; }
    .mk-line { font-size: 10px; line-height: 1.7; margin-top: 14px; }
    .mk-pillars h3 { font-family: inherit; font-size: 14px; line-height: 1.6; }
  </style>
  <section class="mk-pillars" style="margin:26px 0 20px;text-align:center">
    <h3>What an autonomous-lab designer adds</h3>
    <div class="mk-row">${PILLARS.map(card).join("")}</div>
    <p class="muted" style="font-family:system-ui,sans-serif;font-size:${BODY - 1}px">Hover a card for details.</p></section>`;
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
  const p1 = `<figure>${hero("85%", "of the 48 new drugs launched in 2024 were originated by emerging biopharma (41 of 48)", BAR_VALUE)}${ref(IQVIA)}</figure>`;
  const p2 = `<figure>${title("US lab professionals reporting significant downtime")}${bars([{ label: "Significant downtime", value: 60 }])}
    ${note('"Nearly 60%", due to equipment failures, missed calibration and hard-to-find assets. A vendor-run survey.')}${ref(MACHINEQ)}</figure>
    <figure>${hero("$500k", "lost sales per day of delay in drug development; a phase II/III trial costs ~$40k a day to run")}
    ${note("Average over 645 drugs launched since 2000. A Tufts white paper (Aug 2024) puts lost sales nearer $800k/day.")}${ref(TUFTS_DELAY)}</figure>`;
  const p3 = `<figure>${title("Lab heads with no training in managing people")}${bars([{ label: "No management training", value: 67 }])}
    ${note('"Two-thirds" in a Nature survey of 3,200+ scientists. Scientists are trained to do experiments, not to run labs; no survey we found measures hardware and instrumentation know-how directly.')}${ref(NATURE_LEAD)}</figure>
    <figure>${hero("4–6 weeks", "to set up gas and liquid-nitrogen supply accounts: hardware detail wet-lab founders rarely plan for")}
    ${note("Practitioner observation from a lab-operations team, not survey data.")}${ref(SCIEX)}</figure>`;
  return `<div class="market">
    <p style="font-size:${BODY}px;color:${C.ink2}">Why a lab-design agent that knows what it doesn't know is worth building. Every figure was checked against its opened source (4 Oct 2026).</p>
    ${section(1, "Most new drugs now start in emerging biotechs", "Emerging biopharma companies originate most new medicines, and most have no in-house lab-operations team.", p1)}
    ${section(2, "Lab operations gaps cause costly delays", "Equipment downtime is common, and every day of delay in drug development is expensive. The link to lab planning is inferred: we found no study measuring it as the root cause.", p2)}
    ${section(3, "Why an autonomous lab", "Founders and lab heads come from the wet lab, not from hardware and instrumentation. An agent that designs, lays out and simulates the lab fills that gap.", p3)}
    ${pillars()}
  </div>`;
}
