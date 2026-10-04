/**
 * A single, static architecture diagram for #/how. Every component shown here
 * maps to code that runs today; sponsor marks sit beside the component they power.
 */

const C = {
  ink: "#172033",
  agent: "#d97757",
  evidence: "#6e5bd7",
  engine: "#087f78",
  verify: "#c64242",
  output: "#2767a8",
};

const esc = (s: string) => s.replace(/[&<>"]/g, (c) => `&#${c.charCodeAt(0)};`);

function wrap(text: string, width: number): string[] {
  const max = Math.floor(width / 6.5);
  const lines: string[] = [];
  let line = "";
  for (const word of text.split(" ")) {
    if (line && `${line} ${word}`.length > max) {
      lines.push(line);
      line = word;
    } else {
      line = line ? `${line} ${word}` : word;
    }
  }
  if (line) lines.push(line);
  return lines;
}

function multiline(x: number, y: number, text: string, width: number, className = "hw-body", gap = 18): string {
  return wrap(text, width).map((line, i) =>
    `<text x="${x}" y="${y + i * gap}" class="${className}">${esc(line)}</text>`,
  ).join("");
}

function panel(
  x: number,
  y: number,
  w: number,
  h: number,
  title: string,
  body: string,
  color: string,
  tip: string,
  kicker = "",
): string {
  return `<g class="hw-node" data-tip="${esc(tip)}">
    <rect x="${x}" y="${y}" width="${w}" height="${h}" rx="15" class="hw-panel"/>
    <path d="M${x + 1},${y + 15} Q${x + 1},${y + 1} ${x + 15},${y + 1} H${x + w - 15} Q${x + w - 1},${y + 1} ${x + w - 1},${y + 15}" fill="none" stroke="${color}" stroke-width="4"/>
    ${kicker ? `<text x="${x + 22}" y="${y + 30}" class="hw-kicker" style="fill:${color}">${esc(kicker)}</text>` : ""}
    <text x="${x + 22}" y="${y + (kicker ? 59 : 38)}" class="hw-title">${esc(title)}</text>
    ${multiline(x + 22, y + (kicker ? 87 : 67), body, w - 44)}
  </g>`;
}

function claudeBadge(x: number, y: number): string {
  return `<g class="hw-brand" aria-label="Claude by Anthropic">
    <rect x="${x}" y="${y}" width="150" height="42" rx="10" fill="#f7eee7"/>
    <image href="/brands/claude.svg" x="${x + 13}" y="${y + 8}" width="124" height="27" preserveAspectRatio="xMidYMid meet"/>
  </g>`;
}

function amassBadge(x: number, y: number): string {
  return `<g class="hw-brand" aria-label="Amass">
    <rect x="${x}" y="${y}" width="116" height="42" rx="10" fill="#efeafd"/>
    <image href="/brands/amass.svg" x="${x + 9}" y="${y + 7}" width="98" height="28" preserveAspectRatio="xMidYMid meet"/>
  </g>`;
}

function modalBadge(x: number, y: number): string {
  return `<g class="hw-brand" aria-label="Modal">
    <rect x="${x}" y="${y}" width="116" height="42" rx="10" fill="#0c0f0b"/>
    <image href="/brands/modal.svg" x="${x + 9}" y="${y + 10}" width="98" height="22" preserveAspectRatio="xMidYMid meet"/>
  </g>`;
}

function huggingFaceBadge(x: number, y: number): string {
  return `<g class="hw-brand" aria-label="Hosted on Hugging Face Spaces">
    <rect x="${x}" y="${y}" width="300" height="76" rx="14" fill="#fff6cf" stroke="#efd77a"/>
    <image href="/brands/huggingface.svg" x="${x + 12}" y="${y + 8}" width="65" height="60" preserveAspectRatio="xMidYMid meet"/>
    <text x="${x + 90}" y="${y + 31}" class="hw-brand-name hw-brand-hf">Hugging Face</text>
    <text x="${x + 90}" y="${y + 56}" class="hw-brand-meta hw-brand-host">Hosted on Hugging Face</text>
  </g>`;
}

function pill(x: number, y: number, w: number, label: string, color = C.ink): string {
  return `<rect x="${x}" y="${y}" width="${w}" height="28" rx="8" fill="#fff" stroke="${color}" stroke-opacity=".32"/>
    <text x="${x + w / 2}" y="${y + 18}" text-anchor="middle" class="hw-pill">${esc(label)}</text>`;
}

function arrow(path: string, color = C.ink, label = "", x = 0, y = 0, dashed = false): string {
  return `<path d="${path}" class="hw-arrow" stroke="${color}"${dashed ? ` stroke-dasharray="7 6"` : ""} marker-end="url(#hw-arrowhead)"/>
    ${label ? `<text x="${x}" y="${y}" class="hw-flow-label" style="fill:${color}">${esc(label)}</text>` : ""}`;
}

function diagram(): string {
  const s: string[] = [];

  s.push(`<text x="32" y="50" class="hw-display">One brief in. One verified lab design out.</text>`);
  s.push(`<text x="32" y="80" class="hw-subtitle">The model plans; evidence and simulation test the design; an independent verifier checks the claims.</text>`);

  s.push(panel(32, 132, 220, 148, "Plain-English brief",
    "Target, room, budget, shifts and scientific constraints.", C.output,
    "A user brief is converted into schema-validated LabSpec and Workflow objects.", "INPUT"));
  s.push(panel(320, 112, 390, 188, "Planner agent",
    "Builds the workflow, selects real equipment, calls tools, reads bottlenecks and revises the design.", C.agent,
    "backend/labforge/agent/planner.py — the Claude tool-use loop.", "REASONING LOOP"));
  s.push(claudeBadge(538, 132));
  s.push(huggingFaceBadge(838, 165));
  s.push(pill(342, 245, 104, "LabSpec", C.agent));
  s.push(pill(456, 245, 112, "Workflow", C.agent));
  s.push(pill(578, 245, 108, "Claims", C.agent));
  s.push(arrow("M252 206H318", C.output));

  s.push(`<text x="32" y="358" class="hw-section">TOOLS THE AGENT CAN CALL</text>`);
  s.push(panel(32, 384, 342, 188, "Evidence layer",
    "Searches 79 vendor items and retrieves literature. Every number keeps its source and uncertainty range.", C.evidence,
    "backend/labforge/catalog and backend/labforge/agent/amass.py.", "REAL-WORLD INPUTS"));
  s.push(amassBadge(236, 405));
  s.push(pill(54, 522, 136, "search_catalog", C.evidence));
  s.push(pill(200, 522, 150, "search_evidence", C.evidence));

  s.push(panel(414, 384, 342, 188, "Digital twin",
    "Places equipment with safety clearances, then samples uncertain durations to calculate throughput, queues and bottlenecks.", C.engine,
    "backend/labforge/layout and backend/labforge/sim. Modal is available as the Monte Carlo replicate backend.", "LAYOUT + MONTE CARLO"));
  s.push(modalBadge(618, 405));
  s.push(pill(436, 522, 138, "layout engine", C.engine));
  s.push(pill(584, 522, 148, "Monte Carlo", C.engine));

  s.push(panel(796, 384, 372, 188, "Independent verifier",
    "Ignores the agent’s reported results, rebuilds the layout and simulation, checks tampering, and marks each claim supported, refuted or unverifiable.", C.verify,
    "backend/labforge/verify/verifier.py and tamper.py.", "FALSIFICATION"));
  s.push(pill(818, 522, 98, "recompute", C.verify));
  s.push(pill(926, 522, 96, "compare", C.verify));
  s.push(pill(1032, 522, 112, "Brier score", C.verify));

  s.push(arrow("M430 300V340H203V382", C.evidence, "evidence", 322, 329));
  s.push(arrow("M515 300V382", C.engine, "simulate", 523, 345));
  s.push(arrow("M625 300V340H982V382", C.verify, "claims", 902, 329));
  s.push(arrow("M796 484H774V326H676", C.verify, "refute → revise", 782, 316, true));

  s.push(`<text x="32" y="635" class="hw-section">CHECKED DESIGN CONTRACT</text>`);
  s.push(`<rect x="32" y="660" width="1136" height="152" rx="18" class="hw-output-band"/>`);
  const outputs: [number, string, string][] = [
    [54, "Room layout", "Placements, safety zones and every handoff path"],
    [326, "Throughput", "P10 / P50 / P90, target probability and bottleneck"],
    [598, "Decision pack", "Bill of materials, report, risks and unknowns"],
    [870, "Honesty record", "Checked claims, confidence and verifier status"],
  ];
  outputs.forEach(([x, title, body]) => {
    s.push(`<circle cx="${x + 18}" cy="701" r="18" fill="${C.output}" opacity=".12"/>`);
    s.push(`<path d="M${x + 10} 701l6 6 11-13" fill="none" stroke="${C.output}" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round"/>`);
    s.push(`<text x="${x + 48}" y="698" class="hw-output-title">${esc(title)}</text>`);
    s.push(multiline(x + 48, 722, body, 206, "hw-output-body", 17));
  });
  s.push(arrow("M600 572V658", C.output, "verified result", 610, 626));

  s.push(`<rect x="32" y="842" width="1136" height="46" rx="12" class="hw-rail"/>`);
  s.push(`<text x="54" y="870" class="hw-rail-text">Integrity rails</text>`);
  s.push(`<text x="172" y="870" class="hw-rail-copy">JSON schemas  •  source-labelled uncertainty  •  immutable catalogue values  •  hidden trap briefs</text>`);

  return `<div class="hw-diagram-frame"><svg class="hw-svg" viewBox="0 0 1200 920" role="img" aria-labelledby="hw-diagram-title hw-diagram-desc">
    <title id="hw-diagram-title">LabForge system architecture</title>
    <desc id="hw-diagram-desc">A plain-English lab brief goes to a Claude planner agent. The agent calls Amass-backed evidence search, catalogue search, layout, and Modal-backed simulation tools. An independent verifier recomputes its claims before producing a checked design.</desc>
    <defs>
      <marker id="hw-arrowhead" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10Z" fill="context-stroke"/></marker>
    </defs>
    ${s.join("\n")}
  </svg></div>`;
}

export function howItWorksHtml(): string {
  return `<div class="howitworks">${diagram()}</div>`;
}
