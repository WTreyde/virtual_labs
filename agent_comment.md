# Judge's comments: LabForge (Virtual Labs)

Reviewer: Claude (coding agent on Strand B), acting as a judge. Written 3 Oct 2026, evening, from `main` at the time of writing plus the open Strand B PR.

**Conflict of interest:** I built much of Strand B (catalog, safety rules, bench tasks, cost validation). I've tried to score against the evidence in the repo rather than effort, and I call out weaknesses in my own work.

## Scores

| Criterion | Score | One-line verdict |
|---|---|---|
| Technicality | **17 / 20** | Deep, end-to-end and tested; the planner and verifier still disagree on throughput in the live runs. |
| Creativity | **17 / 20** | "A lab-design agent that is graded on honesty" is a fresh angle; the isometric presentation is a bonus. |
| Usefulness | **14 / 20** | Real problem and real vendor data, but cost and throughput are not validated well enough to buy equipment on. |
| Demo | **15 / 20** | Recorded replays and a keyless public build make it safe; the honest results are messy for a 5-minute story. |
| Track / sponsor alignment | **16 / 20** | Track 2 is the spine of the project; sponsor-tool usage beyond Claude is thinner than the plan promised. |
| **Total** | **79 / 100** | |

---

## 1. Technicality: 17 / 20

**Strengths**
- **A real system, not a mock-up.** It has a Claude tool-use planner, catalog search, a layout engine with a safety validator, a SimPy Monte Carlo simulator (operators with shifts, batch steps, external queues), an independent verifier with tamper detection, a project scheduler, and an export of designs as an orchestrating-agent skill file plus MCP-style tools. Everything is wired through JSON schemas, with `make check` covering 147+ tests, schema validation and the frontend typecheck.
- **Contracts discipline.** Every strand validates against `schemas/`. That is unusual for a hackathon and is why five people could work in parallel.
- **The verifier is independent.** It re-simulates designs, restores catalog durations an agent tried to shorten, and checks claims against its own numbers. The per-crystal duration-basis fix (PR #24, #26) shows the team chasing a real modelling error rather than papering over it.
- **Known-bottleneck check.** The simulator finds the published bottleneck in 4 real labs (Liverpool mobile chemist: GC, 94% busy; XChem harvesting; an OT-2 platform), with throughput within about ±15%.
- **Cost model with uncertainty.** Per-item price provenance, prices adjusted from their source year with the BLS lab-instrument index, evidence-aware spreads, and a blind out-of-sample test: **9 of 12 published purchases inside the 80% band**.

**Weaknesses**
- **Planner and verifier disagree.** In the latest XChem replay the planner gives a P50 of 124 crystals/day and the verifier 172; the acceptance gate stays red. The team reports this honestly, but it means the core loop is not yet self-consistent.
- **Layout violations persist** (1–11 depending on the run), mostly unguarded robot hand-offs.
- **Some components never ran for real.** The Modal scraper exists but the catalog was filled by research agents; Modal Monte Carlo fan-out code exists (`sim/modal_app.py`), but it's unclear it was used in the recorded runs.
- **The confidence score fails out of sample** (Brier worse than a constant baseline in both blind rounds). The band works; the single number doesn't.

## 2. Creativity: 17 / 20

**Strengths**
- **Honesty as the product.** Most "AI designs X" projects optimise for an impressive answer. LabForge makes the agent state claims with confidence, has a verifier refute them, and scores agents on **admitting infeasibility and not tampering**. LabDesignBench is the most original piece: 21 briefs, 19 of them traps (impossible targets, rooms too small, editable simulator settings, missing capabilities, unsafe shortcuts).
- **Physical honesty, not just textual.** Catalog numbers carry source and confidence, so placeholders are visible, and the system says *which* unknown matters most ("measure this first").
- **Presentation.** An isometric, Pokémon-style lab with walking operators and bottleneck speech bubbles makes simulation output legible to non-specialists.
- **Useful spin-offs:** project prioritisation (which order to run the queue), vendor what-if ("is a faster reader worth it here?"), and exporting a design as an agent skill file for the robot that will run it.

**Weaknesses**
- The individual parts (layout optimisation, discrete-event simulation, LLM planning) are known techniques. The novelty is the combination and the honesty framing, so the pitch must lead with that.
- Scope sprawl: scheduling, vendor view, orchestrator export and validation all compete for attention with the core idea.

## 3. Usefulness: 14 / 20

**Strengths**
- **Real pain point.** Designing an automated lab today means weeks with vendor sales engineers and vendor-locked tools. A vendor-agnostic first draft in minutes, with costs and bottlenecks, is valuable to pharma automation leads, core facilities and grant writers.
- **Real data.** 79 catalog items with sourced prices (mostly US federal purchase records), footprints, durations and safety flags; sourced safety rules (NIH DRM, OSHA, NFPA 45, BMBL); 4 human operator roles with BLS wages.
- **Actionable outputs:** BOM with confidence, bottleneck plus the next bottleneck, a project-order recommendation with a deadline check, and a boss report.

**Weaknesses**
- **Not decision-grade yet.**
  - **Cost:** individual estimates still miss by 0.5×–3× (only the 80% band holds up).
  - **Throughput:** validated on 4 published labs only.
  - **Placeholders:** many catalog fields are still placeholders (clearances, some durations, two prices). A buyer would still need vendor quotes, which the tool itself says.
- **The two flagship designs don't meet their own targets** (chemistry ~312 vs 768 compounds/day; XChem ~124–248 vs 300 crystals/day). That's honest, but a user wants "here's how to hit it".
- The live agent sometimes hits API refusals on the chemistry brief, a reliability risk for real users.

## 4. Demo: 15 / 20

**Strengths**
- **Built to survive demo day.** Recorded live replays (`frontend/public/replays/`) drive the game without the network or API keys; a replay-only Docker/Hugging Face Space build exists; `snapshot/` branches freeze a fallback.
- **The app runs locally:** both servers start cleanly with `make backend` / `make frontend`.
- **Many tabs to show:** design, case studies, schedule (urgent re-test 46.7 h → 3.2 h, 16% faster queue), validation scatter, bench leaderboard, gallery.
- **A strong moment is available:** on LabDesignBench, the tool-using platform arm scores **0.83 vs 0.65** for the same model without tools. On the tamperable-simulator trap it scores **1.0 vs 0.0**, with a Brier score of 0.023.

**Weaknesses**
- **The honest numbers make a tangled story.**
  - "Target refuted, gate red, planner and verifier disagree, layout violations remain" is right, but hard to land in 5 minutes.
  - The XChem bottleneck story changed three times today (harvesting → STX44 hotel → Rock Imager).
  - The pitch must be re-checked against the final data: the Rock Imager holds 970 plates, not 1,000, at one temperature per unit.
- **The leaderboard is partial:** 15 tasks scored (6 newer tasks not yet run), one run failed with a refusal, and the "none"-trap control scored only 0.33.
- Live mode is risky on stage; stick to replays.

**Advice:** lead with one clean arc. Brief → isometric lab → "this is the bottleneck, and here's what we don't know" → one what-if → leaderboard (tamper trap 1.0 vs 0.0) → validation ("our 80% band caught 9 of 12 labs we'd never seen").

## 5. Track / sponsor alignment: 16 / 20

**Track 2 (agents that know when they're wrong): excellent, about 10/10 on its own.**
- Uncertain numbers with provenance, claims with stated confidence, an independent verifier, Brier scores, a benchmark that rewards admitting infeasibility, pre-registered tests, blind out-of-sample validation, and docs that report the failures (confidence score not generalising, target refuted).

**Sponsor tools: uneven.**

| Tool | Evidence in the repo | Verdict |
|---|---|---|
| Claude API | Planner, live runs on `claude-opus-5-5`, vanilla bench arm | ✅ central |
| Claude Code | Most of the codebase and research (agents, PRs) | ✅ heavy, though judges may not count it |
| Amass | Integrated in the agent (`session.py`, `prompts.py`); credentials available in one recorded run, unavailable in another | ⚠️ present but light; few evidence citations visible in outputs |
| Modal | `sim/modal_app.py`, `sim/parallel.py`, `catalog/scrape_modal.py` | ⚠️ code exists; the catalog scrape was not run on Modal, and Monte Carlo fan-out use in the demo is unclear |
| Hugging Face | `deploy/hf-space` replay-only Space | ✅ if the Space is actually published |
| Devin / Antigravity | No visible trace | ❌ not used, or not shown |

**To gain points before the freeze:** show one real Modal run (e.g. the LabDesignBench run or Monte Carlo fan-out with a timing number), show Amass citations attached to step durations in a replay, and publish the HF Space link on the final slide.

---

## Top 5 fixes before 09:00 (highest score impact for least effort)

1. **One demo story, frozen:** pick the XChem or chemistry arc, re-check every number on the slides against the latest replay and catalog (970 plates; HC/DC2 or Peltier temperature caveats).
2. **Re-run the leaderboard on all 21 tasks**, or say on the slide that 15 were scored.
3. **Make the planner–verifier gap a feature:** show it on screen as "the agent claimed X, our verifier measured Y". It's the best Track 2 moment in the system.
4. **Prove the sponsor tools:** one Modal run with a timing, one Amass-cited step duration, the HF Space URL.
5. **Show the band, not the score:** in the cost UI, display the P10–P90 band and label the confidence percentage "experimental".

---

## Fix status (overnight, 4 Oct 00:00–01:00)

Rule followed: CLAUDE.md says to edit only my strand (B) and write handoffs for the rest; human instructions win over these comments.

| Comment | Status | Where |
|---|---|---|
| Many catalog fields are still placeholders (Usefulness) | **Partly fixed:** 22 of 88 placeholders in demo instruments replaced with sourced values; 6 bad agent values rejected; the rest documented as unsourced | PR #56 |
| Show the band, not the score (Demo, fix 5) | **Backend fixed:** `confidence.experimental = true` plus a note; UI handed to Roshan | PR #56 |
| Pitch numbers must match the data (fix 1) | **Checked:** Rock Imager 970 plates, one temperature per unit (PR #46). **New risk found:** no recorded run shows "grow in the Rock Imager". A local what-if gives P50 143 → 226 crystals/day, still under 300, with the operators becoming the limit | PR #46, PR #56 |
| Planner vs verifier disagreement | Handed off (Maxim/Albert) | PR #56 |
| Layout violations | Handed off (Maxim) | PR #56 |
| Leaderboard on all 21 tasks | Handed off (Maxim); costs API credits, not run | PR #56 |
| Sponsor proof: Modal, Amass, HF Space | Handed off (Maxim, Albert, integrator) | PR #56 |
| Confidence score fails out of sample | Open. Needs more cases and a fresh blind round before it can be fixed fairly | — |

**Revised score if PR #56's handoffs land:** Usefulness +1 (fewer placeholders), Demo +1 (an honest Rock Imager arc whose next bottleneck is the staff); the others are unchanged until the handed-off items are done.
