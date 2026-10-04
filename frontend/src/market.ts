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
const NATURE_INDEX: Ref = { title: "Slow, difficult and expensive: How the lab supplies market is crippling African science",
  publisher: "Nature Index (survey of 130 life-sciences researchers in 20 African countries, Mukhwana et al.)", date: "2 July 2024",
  url: "https://www.nature.com/nature-index/news/slow-difficult-expensive-how-lab-supplies-market-crippling-african-science", verified: true };
const JALM: Ref = { title: "Current State and Needs of Clinical Laboratories in Selected Countries in Africa (121 respondents, 8 countries)",
  publisher: "J Appl Lab Med 11(5):1231-1242, doi 10.1093/jalm/jfag089", date: "September 2026",
  url: "https://pubmed.ncbi.nlm.nih.gov/42335177/", verified: true };
const TUFTS_DELAY: Ref = { title: "New Estimates on the Cost of a Delay Day in Drug Development (Smith, DiMasi, Getz)",
  publisher: "Therapeutic Innovation & Regulatory Science 58(5):855-862 (Tufts CSDD)", date: "September 2024",
  url: "https://pubmed.ncbi.nlm.nih.gov/38773058/", verified: true };
const TUFTS_ENROL: Ref = { title: "Enrollment Performance: Weighing the 'Facts' (Getz; Tufts CSDD study of ~16,000 sites, 151 trials)",
  publisher: "Applied Clinical Trials 21(5)", date: "May 2012",
  url: "https://www.appliedclinicaltrialsonline.com/view/enrollment-performance-weighing-facts", verified: true };

export function marketHtml(): string {
  const p1 = `<figure><h4>Share of new drugs originated by emerging biopharma</h4>${bars([{ label: "2015–2019", value: 53 }, { label: "2020–2024", value: 59 }], 1)}${ref(IQVIA)}</figure>
    <figure>${hero("85%", "of the 48 new drugs launched in 2024 were originated by emerging biopharma (41 of 48); 63% were also launched by one")}${ref(IQVIA)}</figure>`;
  const p2 = `<figure><h4>Life-sciences researchers with no institutional procurement support</h4>${bars([{ label: "No procurement support", value: 38 }])}
    <p class="small">Supplies can take 3–6 months to arrive ("not uncommon"). Survey of African researchers.</p>${ref(NATURE_INDEX)}</figure>
    <figure><h4>Most common challenges reported by clinical laboratories</h4>${bars([{ label: "Funding", value: 66 }, { label: "Lack of equipment", value: 60 }, { label: "Continuing education", value: 58 }, { label: "QC/EQA materials", value: 58 }, { label: "Lack of training", value: 51 }], 1)}
    <p class="small">Diagnostic laboratories in Africa, not biotech R&amp;D labs.</p>${ref(JALM)}</figure>`;
  const p3 = `<figure>${hero("$500,000", "in lost sales for each day a drug's development is delayed; running a phase II/III trial costs about $40,000 per day")}
    <p class="small">Average over 645 drugs launched since 2000. A Tufts white paper (Aug 2024) puts lost sales nearer $800,000/day.</p>${ref(TUFTS_DELAY)}</figure>
    <figure><h4>Clinical studies that missed their planned enrolment timeline</h4>${bars([{ label: "Timeline extended", value: 53 }, { label: "Completed on time", value: 47 }])}
    <p class="small">One in six took twice as long as planned or longer.</p>${ref(TUFTS_ENROL)}</figure>`;
  return `<div class="answer">
    <p>Why a lab-design agent that knows what it doesn't know is worth building. Every figure below was checked against its opened source (4 Oct 2026).</p>
    ${section(1, "More new drugs come from smaller biotechs", "Emerging biopharma companies now originate most new medicines, and most have no in-house lab-operations team.", p1)}
    ${section(2, "Lab procurement and setup know-how is a gap", "Scientists are trained in science, not in selecting, procuring and commissioning lab infrastructure.", p2)}
    ${section(3, "Delays are very expensive", "Operational delays are common and costly. The link to project and operations planning is inferred: we found no study that measures it as the root cause.", p3)}
    <p class="muted small">Not shown because unverified: McKinsey's first-time-launcher multiplier (page unreachable from our checks), a "20–30% budget underestimate" claim, and an "80% of trials miss enrolment" figure.</p>
  </div>`;
}
