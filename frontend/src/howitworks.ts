/**
 * Strand A: #/how, a static schematic of how LabForge works behind the scenes. Plain inline SVG, no data calls.
 * Every box names something the code does today (backend/labforge/*, frontend/src/*); the one roadmap item is drawn
 * dashed and labelled "not built". Hover a box for the module it lives in.
 */

const C = { ink: "#1d2330", ink2: "#52514e", line: "#2b2f36", surface: "#fbfbf5", agent: "#2a78d6", engine: "#6b8fb3",
  verify: "#e0503c", out: "#eb6834", check: "#1baf7a", road: "#a9a7a1" };
const esc = (s: string) => s.replace(/[&<>"]/g, (c) => `&#${c.charCodeAt(0)};`);

/** Greedy word wrap by character count (system-ui at 12px is ~6.4 px per character). */
function wrap(text: string, width: number): string[] {
  const max = Math.floor(width / 6.4), out: string[] = [];
  let cur = "";
  for (const w of text.split(" ")) {
    if (cur && (cur + " " + w).length > max) { out.push(cur); cur = w; } else cur = cur ? `${cur} ${w}` : w;
  }
  if (cur) out.push(cur);
  return out;
}

function box(x: number, y: number, w: number, h: number, title: string, body: string, color: string,
  tip: string, opts: { dashed?: boolean; fill?: string } = {}): string {
  const lines = body ? wrap(body, w - 24) : [];
  const dash = opts.dashed ? ` stroke-dasharray="6 5"` : "";
  return `<g data-tip="${esc(tip)}">
    <rect x="${x}" y="${y}" width="${w}" height="${h}" rx="8" fill="${opts.fill ?? C.surface}" stroke="${color}" stroke-width="2.5"${dash}/>
    <rect x="${x}" y="${y}" width="6" height="${h}" rx="3" fill="${color}"${opts.dashed ? ` opacity="0.5"` : ""}/>
    <text x="${x + 16}" y="${y + 22}" class="hw-title">${esc(title)}</text>
    ${lines.map((l, i) => `<text x="${x + 16}" y="${y + 42 + i * 16}" class="hw-body">${esc(l)}</text>`).join("")}
  </g>`;
}

function chip(x: number, y: number, w: number, label: string, color: string): string {
  return `<rect x="${x}" y="${y}" width="${w}" height="24" rx="12" fill="#fff" stroke="${color}" stroke-width="1.5"/>
    <text x="${x + w / 2}" y="${y + 16}" text-anchor="middle" class="hw-chip">${esc(label)}</text>`;
}

/** Polyline arrow through the given points, optional label at (lx, ly). */
function arrow(pts: [number, number][], color = C.line, label = "", lx = 0, ly = 0, dashed = false): string {
  const d = pts.map(([x, y], i) => `${i ? "L" : "M"}${x},${y}`).join(" ");
  const id = color === C.verify ? "hw-head-red" : "hw-head";
  return `<path d="${d}" fill="none" stroke="${color}" stroke-width="2"${dashed ? ` stroke-dasharray="5 4"` : ""} marker-end="url(#${id})"/>
    ${label ? `<text x="${lx}" y="${ly}" class="hw-label" style="fill:${color}">${esc(label)}</text>` : ""}`;
}

function diagram(): string {
  const W = 1120, H = 1018;
  const s: string[] = [];

  // Tier 1: browser
  s.push(box(20, 14, 1080, 88, "Browser: TypeScript + Phaser 3 game client (isometric pixel art, animated, not playable)", "", C.line,
    "frontend/src: main.ts, LabScene.ts, views.ts. Hash routes; every page also works offline from examples/ and public/."));
  const tabs = ["Case studies", "Design your own", "Bench", "Validation", "Schedule", "Protocols", "Report + BOM", "Agent skill"];
  tabs.forEach((t, i) => s.push(chip(36 + i * 132, 60, 122, t, C.engine)));

  // Tier 2: gateway and replays
  s.push(box(20, 150, 760, 68, "FastAPI gateway", "/chat/stream (SSE)  /catalog  /layout  /simulate  /verify  /report  /optimise  /prioritise  /validation  /bench",
    C.line, "backend/labforge/gateway.py. Also serves the built game for the one-URL demo (make demo)."));
  s.push(box(810, 150, 290, 68, "Recorded runs (replays)", "Earlier live agent runs saved as JSON and played back with no backend call.",
    C.line, "frontend/public/replays/*.json, frontend/src/replay.ts. The case studies and the public Hugging Face Space run this way."));
  s.push(arrow([[400, 102], [400, 148]], C.line, "REST + SSE", 408, 130));
  s.push(arrow([[955, 102], [955, 148]], C.line, "static files", 963, 130));

  // Tier 3: planner, engines, verifier
  s.push(box(20, 262, 330, 344, "Planner agent: Claude tool-use loop",
    "claude-opus-5-5 via the Anthropic SDK. Turns a plain-English brief into a LabSpec and Workflow, picks equipment, simulates, reads the bottlenecks and revises. Tools it may call:",
    C.agent, "backend/labforge/agent/planner.py, session.py, tools.py. Without ANTHROPIC_API_KEY it returns the worked example, so everything runs offline."));
  const tools = ["search_catalog", "search_evidence", "layout_and_simulate", "verify_claims", "optimise_instrument", "plan_projects", "create_report"];
  tools.forEach((t, i) => s.push(chip(36 + (i % 2) * 152, 384 + Math.floor(i / 2) * 32, 144, t, C.agent)));
  s.push(arrow([[185, 218], [185, 260]], C.line, "/chat/stream", 193, 242));

  s.push(box(390, 262, 360, 78, "Vendor catalogue (cached JSON)", "79 instruments and robots, scraped once; every field tagged datasheet, literature, estimate or placeholder.",
    C.engine, "backend/labforge/catalog: scrape.py ran once; store.py searches data/catalog.json."));
  s.push(box(390, 350, 360, 78, "Amass BiomedCore evidence", "Literature candidates for step durations and yields. A paper title is never taken as proof of a number.",
    C.engine, "backend/labforge/agent/amass.py (24 h cache) and reviewed_evidence.py. Missing access is reported, not hidden."));
  s.push(box(390, 438, 360, 78, "Layout engine", "Greedy start, then simulated annealing. Safety zones and clearances; each handoff gets an arm, mobile robot or person (A* walk).",
    C.engine, "backend/labforge/layout: placer.py, safety.py, validate.py. Violations are returned, never silently fixed."));
  s.push(box(390, 526, 360, 80, "Monte Carlo simulator (SimPy)", "Samples every uncertain duration; operators with shifts, batches, storage hotels, synchrotron queue. Gives P10/P50/P90, P(meets target), bottlenecks.",
    C.engine, "backend/labforge/sim/simulate.py. Replicates run serially, in local processes or on Modal (parallel.py)."));
  for (const y of [301, 389, 477, 566]) s.push(arrow([[350, y], [388, y]], C.agent));

  s.push(box(790, 262, 310, 344, "Independent verifier",
    "The agent submits claims only, e.g. \"throughput.p50 >= 300, confidence 0.8\". The verifier ignores the agent's numbers: it re-derives the layout from the placements and re-runs the Monte Carlo itself. Each claim comes back supported, refuted or unverifiable, with a Brier score for calibration. A tamper check makes sure catalogue values and simulator constants were not edited.",
    C.verify, "backend/labforge/verify/verifier.py and tamper.py. Verifier inputs are held by the backend, never passed in by the agent."));
  s.push(arrow([[300, 262], [300, 240], [945, 240], [945, 260]], C.agent, "claims (verify_claims)", 520, 234));
  s.push(arrow([[788, 477], [752, 477]], C.verify));
  s.push(arrow([[788, 566], [752, 566]], C.verify));
  s.push(`<text x="806" y="468" class="hw-label" style="fill:${C.verify}">re-runs layout + sim</text>`);
  s.push(arrow([[945, 606], [945, 630], [185, 630], [185, 608]], C.verify, "refuted claim: the agent must retract it and say so", 200, 648, true));

  // Tier 4: outputs
  s.push(`<text x="20" y="694" class="hw-tier">What a design produces (LabSpec, Workflow, Layout, SimResult, Claims; all validated against schemas/)</text>`);
  s.push(arrow([[570, 606], [570, 676]], C.out, "design", 578, 660));
  const outs: [string, string, string][] = [
    ["Game view", "Operators and robots walk the simulated timeline; bottlenecks get speech bubbles.", "frontend/src/LabScene.ts, timeline.ts, sprites.ts."],
    ["BOM + boss report", "Prices with confidence, throughput band, risks, unknowns and the checked claims.", "backend/labforge/agent/report.py; frontend/src/report.ts prints it."],
    ["Vendor what-if", "Sweep one instrument's cycle time, capacity or uptime: elasticity, headroom, next bottleneck.", "backend/labforge/sim/whatif.py, POST /optimise."],
    ["Project schedule", "Simulates orders and mixes of several projects on one lab and recommends one.", "backend/labforge/sim/portfolio.py, POST /prioritise."],
    ["Agent skill export", "SKILL.md + tools.json so an agent can run the lab. A pure function of the design.", "backend/labforge/orchestrator/skills.py. No Claude or simulator call."],
  ];
  outs.forEach(([t, b, tip], i) => s.push(box(20 + i * 219, 706, 204, 110, t, b, C.out, tip)));

  // Tier 5: checks on the twin itself
  s.push(`<text x="20" y="852" class="hw-tier">Checks on the twin itself</text>`);
  const checks: [string, string, string][] = [
    ["Cost validation", "Designs published autonomous labs from their briefs: does the real cost fall in our P10–P90 band?", "backend/labforge/validation, GET /validation, docs/validation.md."],
    ["Known bottlenecks", "4 published labs whose authors named the bottleneck: does the simulator find the same one?", "backend/labforge/known_bottlenecks (Liverpool chemist, 2× XChem harvesting, OT-2)."],
    ["Protocol library", "20 published protocols (10 per pipeline) mapped to the workflow steps they cover.", "backend/labforge/protocols/library, frontend/public/protocols."],
    ["LabDesignBench", "21 trap briefs (impossible targets, tiny rooms, unsafe shortcuts). Our agent vs Claude with no tools, scored on a verifier recomputation.", "backend/labforge/bench: tasks/ and runner.py."],
  ];
  checks.forEach(([t, b, tip], i) => s.push(box(20 + i * 274, 864, 259, 104, t, b, C.check, tip)));

  // Roadmap
  s.push(box(20, 978, 1080, 34, "Roadmap, not built: the exported agent runs a real lab and its measurements flow back to recalibrate the twin.", "",
    C.road, "Pitch tier 3 (orchestrator with real-lab feedback). Nothing in the repo does this yet.", { dashed: true, fill: "#f4f3ee" }));

  return `<svg class="hw-svg" viewBox="0 0 ${W} ${H}" role="img" aria-label="LabForge architecture schematic">
    <defs>
      <marker id="hw-head" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="${C.line}"/></marker>
      <marker id="hw-head-red" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="${C.verify}"/></marker>
    </defs>
    ${s.join("\n")}
  </svg>`;
}

export function howItWorksHtml(): string {
  return `<div class="howitworks">
    <p class="hw-lede">One brief in, one checked lab design out. Claude does the planning; deterministic code does the
      maths; a separate verifier re-checks every number the agent claims. Hover a box to see where it lives in the code.</p>
    ${diagram()}
    <h3>One brief, end to end</h3>
    <ol>
      <li>You describe the lab. The browser streams the brief to <code>/chat/stream</code>.</li>
      <li>Claude drafts a <b>LabSpec</b> and <b>Workflow</b>, picks equipment from the cached catalogue, and looks up step durations in Amass.</li>
      <li><code>layout_and_simulate</code> places the room and runs the Monte Carlo; Claude reads the bottlenecks and revises.</li>
      <li>Claude states its claims with a confidence. The verifier recomputes the design itself and marks each claim supported, refuted or unverifiable.</li>
      <li>A refuted claim has to be retracted in the reply and the report. Numbers that are only estimates stay labelled as estimates.</li>
      <li>The browser animates the result and offers the BOM, the boss report, vendor what-ifs and the agent skill export.</li>
    </ol>
    <p class="muted">Every box crossing a module boundary is JSON validated against <code>schemas/</code>. Without an API key
      the whole site still runs from <code>examples/</code> and the recorded replays.</p>
  </div>`;
}
