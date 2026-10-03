# Virtual Labs: architecture and team split

Working name: **LabForge** (rename freely). Deadline: demo at 13:00 on 4 Oct 2026. Track 2 (Originator).

## Pitch in one line

Describe the autonomous lab you want; an agent designs it from real vendor equipment, lays it out as an animated Pokémon-style isometric world, simulates it, and **tells you exactly which of its own numbers it does not trust** — and a benchmark catches design agents that fudge it.

## Novelty check (web search, 3 Oct 2026; quick, not exhaustive)

| Closest work | What it does | Gap we fill |
|---|---|---|
| [Labware-Layout Planner, Digital Discovery 2026](https://pubs.rsc.org/en/content/articlehtml/2026/dd/d6dd00026f) | NL protocol → labware positions on one robot's deck | We do whole rooms: equipment selection, placement, transport, humans |
| [LLM agents for reconfigurable manufacturing layout, CIRP 2026](https://www.sciencedirect.com/science/article/pii/S0007850626000144), [Digital Twin Builder, ICML 2026](https://icml.cc/virtual/2026/67875) | LLM layout / twin generation for factories | Not lab science, no protocol reasoning, no calibrated uncertainty |
| [HighRes ready work cells](https://highresbio.com/applications/ready-work-cells/), [Cellario](https://highresbio.com/software/cellario/scheduling-software), [Biosero GBG](https://biosero.com/) | Vendor-locked workcell design and scheduling, done by sales engineers | Vendor-agnostic, from a natural-language brief, in minutes |
| [AutoBio](https://arxiv.org/html/2505.14030v1) | Simulation benchmark for robot manipulation in bio labs | Benchmarks robot skills, not lab-design agents' honesty |

Inferred conclusion: NL → vendor-agnostic, room-scale lab design with throughput simulation, uncertainty and an honesty benchmark looks unclaimed.

## Track 2 angle (this is what judges should remember)

1. **Epistemic agent.** Every number carries provenance and a range (`uncertain_number` in [`schemas/common.schema.json`](schemas/common.schema.json)): datasheet, literature (via Amass), estimate, or placeholder. The simulator runs Monte Carlo over those ranges and reports P10/P50/P90 throughput, the probability of meeting the target, and a sensitivity ranking ("measure LC-MS run time before buying; it moves throughput most").
2. **Claims and falsification.** The agent must state its claims with a confidence ([`claim.schema.json`](schemas/claim.schema.json)), e.g. "meets 768 compounds/day, p=0.8". An independent verifier checks each against the simulator, layout validator and BOM. Calibration (Brier score) is shown in the UI and the report.
3. **LabDesignBench.** ~20 briefs with hidden checks ([`bench_task.schema.json`](schemas/bench_task.schema.json)), including traps: impossible targets, rooms too small, placeholder specs, a simulator config the agent *could* edit to inflate throughput, unsafe shortcuts. We score agents on admitting infeasibility, not tampering, and calibration. Demo: a leaderboard showing our platform solving tasks that vanilla Claude without tools gets wrong.
4. **Safe, standard control.** Layout rules for fume hoods, BSL zones, cryogens, robot/human envelopes; the BOM flags each instrument's control standard (SiLA 2, OPC-UA, vendor SDK) so the design is controllable, not just pretty.

## Judge feedback (3 Oct): validation and vendor optimisation

Details and owners in [`docs/validation.md`](docs/validation.md).

5. **Validated against real labs.** Published autonomous labs with known costs become `ValidationCase`s; LabForge designs each from its brief and we report whether the real cost falls inside our P10–P90 band (like-for-like on what the figure covers).
6. **Optimisation for vendors.** For any instrument in a designed lab, sweep its cycle time and capacity through the simulator: elasticity, headroom, and what becomes the bottleneck next. Tells a vendor which spec improvement is worth building for which kind of lab.

## Demo flow (5 minutes)

1. Type the chemistry brief. Agent asks two follow-ups, cites literature via Amass for step durations, picks equipment.
2. The isometric lab appears: robots and pixel-art operators carry plates; a speech bubble over the LC-MS says "I'm the bottleneck (32 h per library)".
3. Agent proposes a second LC-MS; throughput band tightens; it flags that powder-dosing times are only estimates.
4. Switch to the FBDD crystallography lab: crystal fishing by humans is the limit; the agent refuses to claim it can automate it without evidence.
5. Click "Report for your boss": PDF with BOM, layout, throughput with uncertainty, risks and unknowns.
6. LabDesignBench leaderboard: one agent quietly edited the sim config; our verifier caught it.

## System

```
 ┌──────── Game client (Phaser 3, isometric pixel art) + HTML overlay ────────┐
 │  Lab world  │  Chat panel  │  Metrics + uncertainty │  BOM │ Report button  │
 └──────┬──────────────────────────────────────────────────────────────────────┘
        │ REST + SSE
 ┌──────▼─────────────── API gateway (FastAPI, on the integrator's machine) ───┐
 │ /chat  /catalog  /layout  /simulate  /verify  /report  /bench               │
 └───┬──────────────┬──────────────────┬──────────────────┬───────────────────┘
     │              │                  │                  │
 Planner agent   Catalog (cached   Layout engine +     Verifier + bench
 (Claude, tools; JSON, scraped     Monte Carlo sim     (claims vs sim,
  Amass for      once on Modal)    (SimPy; fan-out     tamper checks,
  evidence)                         on Modal)           calibration)
```

Data contracts live in [`schemas/`](schemas/); a worked example in [`examples/`](examples/); the two scientific pipelines in [`docs/pipelines.md`](docs/pipelines.md). Conventions: metres, seconds, floor `x`/`y` from the room corner, `z` up; ids are snake_case.

Core modelling rule: every labware handoff is a transfer edge that must be served by a transporter (arm, rail, mobile robot, or **human operator**) whose reach covers both access points. Humans are slow, flexible transporters with shift hours, and they also run manual steps (purification, crystal fishing).

## Where each sponsor tool fits

| Tool | Used for |
|---|---|
| Claude API | Planner agent, scraper extraction, report writing, crystal-image triage (vision) |
| Amass | Evidence: literature for protocol durations and yields (BiomedCore), target and known ligands for library design (GeneCore, DrugCore, PatentCore). Cited per workflow step. |
| Modal | One-off parallel vendor scrape; Monte Carlo simulation fan-out (hundreds of replicates); LabDesignBench runs |
| Devin | Well-specified tickets: per-vendor scraping, schema-to-type generation, test writing |
| Antigravity | Optional IDE agent for the game client strand |

## Strands (four people, plus the integrator)

### Strand A: Game client and report UI
- Phaser 3 isometric scene: floor tiles, room walls, zones tinted (fume hood, BSL2, cold room). Instruments as pixel-art sprites sized from catalog footprints; robots and operators as walking characters animated along `Layout.transfers[].path` using `SimResult.timeline`.
- Pokémon touches (view only, not playable): dialogue box for the agent; click an instrument for its stat card (vendor, price, throughput, confidence badge); bottlenecks shown as speech bubbles and red auras.
- HTML overlay: chat, metrics with P10–P90 bars and probability of meeting target, BOM table, claims panel with verifier ticks/crosses.
- "Report for your boss" button renders the report (from `/report`) to PDF.
- Builds against `examples/*.json` immediately; sprites from free isometric packs (e.g. Kenney, CC0) plus generated pixel art.

### Strand B: Vendor catalog, safety rules, LabDesignBench
- Scrape ~60 instruments across both pipelines once (Modal job, Claude extraction to `CatalogItem` with per-field `provenance`), cache as `catalog/catalog.json`; hand-check the 20 that appear in demos.
- `/catalog` search endpoint (by capability, labware, budget).
- Safety rules file (zones, clearances, hazards) consumed by the layout validator.
- Write the ~20 LabDesignBench tasks with traps and hidden checks.

### Strand C: Planner agent and evidence
- Claude tool-use loop: elicit `LabSpec` → `Workflow` (using the templates in `docs/pipelines.md`) → equipment → call layout and simulate → iterate on bottlenecks.
- Amass integration: attach `evidence` to each step's durations and yields; widen ranges where no evidence exists.
- Emit `Claim`s with confidences after each design; respond to refuted claims honestly.
- Writes the boss report (exec summary, BOM, layout image, throughput band, risks and unknowns, assumptions).

### Strand D: Layout engine, simulator, verifier
- Placement: greedy cluster around transporters, then simulated annealing; enforce zones, clearances, egress, reachability; output `violations`.
- SimPy model with batch steps, fan-out, operators with shifts, external queues; Monte Carlo on Modal → P10/P50/P90, `prob_meets_target`, sensitivity, bottlenecks.
- Verifier: checks each `Claim`, hashes inputs to detect tampering, computes calibration; runs LabDesignBench and outputs a leaderboard JSON.

### Integrator (your machine)
- Owns `schemas/` and the FastAPI gateway; wires strands; runs the demo; keeps `python validate_examples.py` green.

## Timeline to 13:00 tomorrow

| When (3–4 Oct) | Milestone |
|---|---|
| by 13:00 today | Schemas v0.2 frozen; every strand runs on example JSON |
| by 18:00 | Agent → layout → sim → game view works end to end on the chemistry demo with a stub catalog |
| by 23:00 | Real catalog, Monte Carlo, claims + verifier, FBDD scenario |
| by 09:00 | LabDesignBench run, boss report, polish sprites |
| 09:00–12:00 | Freeze features, rehearse, record backup video |
| 12:00–13:00 | Buffer |

## Changing a schema

Add optional fields freely. Renaming or removing a field needs a heads-up to everyone and an updated example in the same commit.
