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

const MCKINSEY: Ref = { title: "Small but mighty: Priming biotech first-time launchers to compete with established players",
  publisher: "McKinsey & Company", date: "2025",
  url: "https://www.mckinsey.com/industries/life-sciences/our-insights/small-but-mighty-priming-biotech-first-time-launchers-to-compete-with-established-players",
  verified: false };
const NATURE_INDEX: Ref = { title: "Slow, difficult and expensive: How the lab supplies market is crippling African science",
  publisher: "Nature Index (survey of 130 researchers in 20 African countries; Mukhwana et al.)", date: "July 2024", verified: false };
const LAB_SURVEY: Ref = { title: "Survey of laboratory challenges (121 laboratory professionals)", publisher: "peer-reviewed article",
  date: "n.d.", verified: false };
const CRL: Ref = { title: "Analyses of FDA complete response letters, 2020–2024", publisher: "regulatory compliance analyses",
  date: "2025", verified: false };
const SCIEX: Ref = { title: "Lab Space Setup: What Biotech Startups Get Wrong", publisher: "Science Exchange", date: "May 2026", verified: false };

export function marketHtml(): string {
  const p1 = `<figure>${hero("3.3×", "growth over the last two decades in drugs coming from biotech first-time launchers")}${ref(MCKINSEY)}</figure>`;
  const p2 = `<figure><h4>Researchers with no institutional procurement support</h4>${bars([{ label: "No procurement support", value: 38 }])}${ref(NATURE_INDEX)}</figure>
    <figure><h4>Challenges reported by laboratory professionals</h4>${bars([{ label: "Lack of equipment", value: 60 }, { label: "Funding", value: 66 }, { label: "Access to training", value: 51 }])}${ref(LAB_SURVEY)}</figure>`;
  const p3 = `<figure><h4>FDA complete response letters citing quality or manufacturing deficiencies</h4>${bars([{ label: "CRLs 2020–2024", value: 74 }])}${ref(CRL)}</figure>
    <figure>${hero("4–6 weeks", "to open utility, gas and liquid-nitrogen accounts: experiments stall even after equipment arrives")}${ref(SCIEX)}</figure>`;
  return `<div class="answer">
    <p>Why a lab-design agent that knows what it doesn't know is worth building. Every figure below has a source; figures marked
    <span class="chip na">verification pending</span> are being checked against the opened source.</p>
    ${section(1, "More new drugs come from startups", "First-time biotech launchers bring a growing share of new medicines to market, but rarely have in-house lab-operations teams.", p1)}
    ${section(2, "Lab procurement and setup know-how is a gap", "Scientists are trained in science, not in selecting, procuring and commissioning lab infrastructure.", p2)}
    ${section(3, "Poor operational planning causes costly delays", "Infrastructure and operations gaps surface as delays and regulatory setbacks when they matter most.", p3)}
  </div>`;
}
