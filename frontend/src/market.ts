/**
 * #/market: why LabForge matters. Three points, each figure with a source link, and three pillar buttons whose
 * explanations appear on hover (the page's data-tip tooltip). Chart text is set at least twice the body-text size.
 */
const C = { s1: "#2a78d6", rest: "#d9d7cf", ink: "#1d2330", ink2: "#52514e", grid: "#e4e3dd" };
const esc = (s: string) => s.replace(/[&<>"]/g, (c) => `&#${c.charCodeAt(0)};`);
const BODY = 12;        // px: paragraphs, notes, sources
const CHART = 26;       // px: chart labels, values, figure titles (>= 2x BODY)

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

function hero(value: string, caption: string): string {
  return `<div style="font-size:${CHART * 2.4}px;font-weight:700;line-height:1;color:${C.s1}">${esc(value)}</div>
    <div style="font-size:${CHART}px;line-height:1.25;color:${C.ink};margin-top:8px">${esc(caption)}</div>`;
}

/** Percentage bars in HTML (not SVG) so text renders at exact sizes: big value, large label. */
const BAR_LABEL = 44, BAR_VALUE = 120;
function bars(rows: Bar[]): string {
  return rows.map((r) => `<div data-tip="${esc(`<b>${esc(r.label)}</b>: ${r.value}%`)}" style="margin:6px 0 14px">
    <div style="font-size:${BAR_LABEL}px;line-height:1.1;color:${C.ink};margin-bottom:8px">${esc(r.label)}</div>
    <div style="display:flex;align-items:center;gap:18px">
      <div style="flex:1;height:56px;background:${C.grid};border-radius:6px;overflow:hidden">
        <div style="width:${r.value}%;height:100%;background:${C.s1};border-radius:6px"></div></div>
      <div style="font-size:${BAR_VALUE}px;font-weight:700;line-height:1;color:${C.ink}">${r.value}%</div></div></div>`).join("");
}

/** McKinsey Exhibit 1 replica: share of NMEs by company type per period, first-time launchers highlighted. */
const NME = [
  { period: "2000–05", total: 183, first: 9, recent: 2, established: 89 },
  { period: "2006–11", total: 172, first: 9, recent: 5, established: 87 },
  { period: "2012–17", total: 265, first: 14, recent: 8, established: 78 },
  { period: "2018–23", total: 346, first: 29, recent: 14, established: 57 },
];
function nmeChart(): string {
  const H = 420, px = (v: number) => (H * v) / 100, LBL = 14, BIG = 60;
  const seg = (v: number, fill: string, ink: string, name: string, period: string) =>
    `<div data-tip="${esc(`<b>${esc(name)}</b>, ${period}: ${v}% of NMEs`)}" style="height:${px(v)}px;background:${fill};border-top:2px solid #fbfbf5;
      display:flex;align-items:center;justify-content:center;font-size:${LBL}px;font-weight:600;color:${ink};overflow:visible">${v >= 6 ? v : ""}</div>`;
  const cols = NME.map((d) => `<div style="display:flex;flex-direction:column;align-items:center;gap:8px">
      <div style="width:110px;height:${H}px;display:flex;flex-direction:column;justify-content:flex-end;position:relative">
        ${seg(d.first, C.s1, "#fff", "First-time launchers", d.period)}
        ${seg(d.recent, "#8db6e6", C.ink, "Recent launchers (first product after 2001)", d.period)}
        ${seg(d.established, C.rest, C.ink, "Established pharmaceutical companies", d.period)}
        ${d.recent < 6 ? `<span style="position:absolute;right:-22px;top:${px(d.first) - 2}px;font-size:${LBL}px;color:${C.ink}">${d.recent}</span>` : ""}
      </div>
      <div style="font-size:${LBL}px;font-weight:600;color:${C.ink}">${d.period}</div>
      <div style="font-size:${LBL - 2}px;color:${C.ink2}">${d.total} NMEs</div></div>`).join("");
  const key = (fill: string, name: string) => `<span style="display:inline-flex;align-items:center;gap:8px;margin-right:22px">
    <span style="width:12px;height:12px;border-radius:4px;background:${fill}"></span>${name}</span>`;
  return `<div style="font-size:${LBL}px;color:${C.ink};margin-bottom:14px">${key(C.s1, "First-time launchers")}${key("#8db6e6", "Recent launchers")}${key(C.rest, "Established pharma")}</div>
    <div style="display:flex;align-items:flex-start;gap:34px;flex-wrap:wrap">
      <div style="display:flex;gap:34px">${cols}</div>
      <div style="padding-top:10px"><div style="font-size:${BIG}px;font-weight:700;line-height:1;color:${C.s1}">3.3×</div>
        <div style="font-size:${LBL + 4}px;line-height:1.25;color:${C.ink};max-width:200px;margin-top:8px">increase in first-time launchers' share of new molecular entities since <span style="white-space:nowrap">2006–11</span></div></div></div>`;
}

function section(n: number, heading: string, claim: string, figures: string): string {
  return `<section style="margin:22px 0 30px"><h3 style="margin-bottom:4px">${n}. ${esc(heading)}</h3>
    <p style="font-size:${BODY}px;color:${C.ink2};margin:0 0 14px">${esc(claim)}</p>
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(440px,1fr));gap:28px">${figures}</div></section>`;
}

const PILLARS: { name: string; tip: string }[] = [
  { name: "Confidence", tip: "<b>Confidence</b><br>Every number carries its source and a confidence label, and the agent names the inputs it is unsure of before anyone signs a purchase order." },
  { name: "Safety", tip: "<b>Safety</b><br>Instruments are laid out to sourced safety rules: fume hoods, cryogen areas with oxygen monitoring, biosafety cabinet clearances, guarded robot arms." },
  { name: "Efficiency", tip: "<b>Efficiency</b><br>Real, priced instruments for each protocol step, a simulated throughput band, and the bottleneck named, so you buy the right kit first." },
];

function pillars(): string {
  const btn = (p: { name: string; tip: string }) => `<button type="button" data-tip="${esc(p.tip)}"
    style="font-size:${CHART}px;font-weight:700;padding:14px 28px;border-radius:10px;border:2px solid ${C.s1};background:#fff;color:${C.s1};cursor:help">${esc(p.name)}</button>`;
  return `<section style="margin:10px 0 24px;text-align:center"><h3>What an autonomous-lab designer adds</h3>
    <div style="display:flex;gap:18px;justify-content:center;flex-wrap:wrap;margin-top:12px">${PILLARS.map(btn).join("")}</div>
    <p class="muted" style="font-size:${BODY - 1}px;margin-top:10px">Hover a pillar for details.</p></section>`;
}

const MCKINSEY: Ref = { title: "Small but mighty: Priming biotech first-time launchers to compete with established players, Exhibit 1 (data: FDA CBER and CDER novel drug approvals; Evaluate Pharma, Feb 2024)",
  publisher: "McKinsey & Company", date: "2024",
  url: "https://www.mckinsey.com/industries/life-sciences/our-insights/small-but-mighty-priming-biotech-first-time-launchers-to-compete-with-established-players",
  verified: true };
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
  const p1 = `<figure style="grid-column:1/-1"><h4 style="font-size:${CHART / 2}px;line-height:1.2;margin:0 0 10px;color:${C.ink}">New molecular entities per period, by company type (%)</h4>${nmeChart()}
    ${note("Figures may not sum to 100% because of rounding. Recent launchers are companies that launched their first product after 2001.")}${ref(MCKINSEY)}</figure>`;
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
