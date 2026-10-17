# LabForge architecture

## In one line

Describe the autonomous lab you want; an agent designs it from real vendor equipment, lays it out as an animated isometric world, simulates it, and **says which of its own numbers it does not trust**. A benchmark catches design agents that fudge it.

## Novelty check (web search, 3 Oct 2026; quick, not exhaustive)

| Closest work | What it does | Gap we fill |
|---|---|---|
| [Labware-Layout Planner, Digital Discovery 2026](https://pubs.rsc.org/en/content/articlehtml/2026/dd/d6dd00026f) | NL protocol → labware positions on one robot's deck | We do whole rooms: equipment selection, placement, transport, humans |
| [LLM agents for reconfigurable manufacturing layout, CIRP 2026](https://www.sciencedirect.com/science/article/pii/S0007850626000144), [Digital Twin Builder, ICML 2026](https://icml.cc/virtual/2026/67875) | LLM layout / twin generation for factories | Not lab science, no protocol reasoning, no calibrated uncertainty |
| [HighRes ready work cells](https://highresbio.com/applications/ready-work-cells/), [Cellario](https://highresbio.com/software/cellario/scheduling-software), [Biosero GBG](https://biosero.com/) | Vendor-locked workcell design and scheduling, done by sales engineers | Vendor-agnostic, from a natural-language brief, in minutes |
| [AutoBio](https://arxiv.org/html/2505.14030v1) | Simulation benchmark for robot manipulation in bio labs | Benchmarks robot skills, not lab-design agents' honesty |

Inferred conclusion: NL → vendor-agnostic, room-scale lab design with throughput simulation, uncertainty and an honesty benchmark looks unclaimed.

## Design principles

1. **Epistemic agent.** Every number carries provenance and a range (`uncertain_number` in [`schemas/common.schema.json`](schemas/common.schema.json)): datasheet, literature (via Amass), estimate, or placeholder. The simulator runs Monte Carlo over those ranges and reports P10/P50/P90 throughput, the probability of meeting the target, and a sensitivity ranking.
2. **Claims and falsification.** The agent states its claims with a confidence ([`claim.schema.json`](schemas/claim.schema.json)), e.g. "meets 768 compounds/day, p=0.8". An independent verifier checks each against the simulator, layout validator and BOM. Calibration (Brier score) is shown in the UI and the report.
3. **LabDesignBench.** 21 briefs with hidden checks ([`bench_task.schema.json`](schemas/bench_task.schema.json)), most of them traps: impossible targets, rooms too small, placeholder specs, a simulator config the agent *could* edit to inflate throughput, unsafe shortcuts. Agents are scored on admitting infeasibility, not tampering, and calibration, against the same Claude model without tools.
4. **Safe, standard control.** Layout rules for fume hoods, BSL zones, cryogens, robot/human envelopes; the BOM flags each instrument's control standard (SiLA 2, OPC-UA, vendor SDK) so the design is controllable, not just pretty.
5. **Validated against real labs.** Published autonomous labs with known costs are `ValidationCase`s; LabForge designs each from its brief and we report whether the real cost falls inside our P10–P90 band, like-for-like on what the figure covers ([`docs/validation.md`](docs/validation.md)). Separately, `backend/labforge/known_bottlenecks/` checks that the simulator finds the bottleneck that published labs report.
6. **Optimisation for vendors.** For any instrument in a designed lab, sweep its cycle time and capacity through the simulator: elasticity, headroom, and what becomes the bottleneck next ([`docs/validation.md`](docs/validation.md#2-optimisation-for-vendors)).
7. **Project prioritisation.** For several projects queued on one lab, simulate orders and mixes and recommend the one that finishes soonest or meets deadlines ([`docs/prioritisation.md`](docs/prioritisation.md)).

## System

```
 ┌──────── Game client (Phaser 3, isometric pixel art) + HTML overlay ────────┐
 │  Lab world  │  Chat panel  │  Metrics + uncertainty │  BOM │ Report button  │
 └──────┬──────────────────────────────────────────────────────────────────────┘
        │ REST + SSE (or static JSON snapshots on GitHub Pages)
 ┌──────▼──────────────────────── API gateway (FastAPI) ───────────────────────┐
 │ /chat  /catalog  /layout  /simulate  /verify  /report  /bench  /optimise ... │
 └───┬──────────────┬──────────────────┬──────────────────┬───────────────────┘
     │              │                  │                  │
 Planner agent   Catalog (cached   Layout engine +     Verifier + bench
 (Claude, tools; JSON, scraped     Monte Carlo sim     (claims vs sim,
  Amass for      once)             (SimPy; optional    tamper checks,
  evidence)                         Modal fan-out)      calibration)
```

Data contracts live in [`schemas/`](schemas/); a worked example in [`examples/`](examples/); the two scientific pipelines in [`docs/pipelines.md`](docs/pipelines.md). Conventions: metres, seconds, floor `x`/`y` from the room corner, `z` up; ids are snake_case.

Core modelling rule: every labware handoff is a transfer edge that must be served by a transporter (arm, rail, mobile robot, or **human operator**) whose reach covers both access points. Humans are slow, flexible transporters with shift hours, and they also run manual steps (purification, crystal fishing).

## Components

- **Planner agent** (`backend/labforge/agent/`): a Claude tool-use loop. It elicits a `LabSpec`, builds a `Workflow` from the templates in `docs/pipelines.md`, picks equipment, calls layout and simulation, iterates on bottlenecks, states `Claim`s and answers refutations honestly. Tools: `search_catalog`, `layout_and_simulate`, `search_evidence` (Amass, optional), `verify_claims`, `create_report`, `optimise_instrument`, `plan_projects`. Setup and commands: [`backend/labforge/agent/LIVE_RUN.md`](backend/labforge/agent/LIVE_RUN.md).
- **Catalog** (`backend/labforge/catalog/`): vendor specs and prices scraped once and cached in `data/catalog.json`, each field tagged with provenance; safety rules in `data/safety_rules.json`.
- **Layout engine** (`backend/labforge/layout/`): greedy placement around transporters, then refinement; enforces zones, clearances, egress and reachability, and reports `violations`.
- **Simulator** (`backend/labforge/sim/`): SimPy model with batch steps, fan-out, operators with shifts and external queues; Monte Carlo replicates run serially, in local processes or on Modal (`LABFORGE_SIM_BACKEND`). Also the vendor what-ifs (`whatif.py`) and project prioritisation (`portfolio.py`).
- **Verifier** (`backend/labforge/verify/`): restores catalog values, recomputes layout and simulation, checks each claim, detects tampering and computes calibration.
- **LabDesignBench** (`backend/labforge/bench/`): tasks, runner and saved results.
- **Game client** (`frontend/`): the isometric scene, chat, metrics, BOM, the boss report, and the case-study, validation, bench, schedule, protocols and How it works views.

## Tools used

| Tool | Used for |
|---|---|
| Claude API | Planner agent, scraper extraction, report writing |
| Amass | Optional evidence search: literature candidates for protocol durations and yields, cited per workflow step |
| Modal | Optional: the one-off vendor scrape and Monte Carlo fan-out. None of the quoted results were computed on Modal. |

## Changing a schema

Add optional fields freely. Renaming or removing a field needs every reader and the example in `examples/` updated in the same commit.
