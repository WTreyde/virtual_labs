# Validation and vendor optimisation (from judge feedback, 3 Oct)

## 1. Validation against real labs

**Question we answer:** if you had described a real, published autonomous lab to LabForge, how close would its cost (and throughput) prediction have been?

- Each real lab is a `ValidationCase` (`schemas/validation_case.schema.json`) in `backend/labforge/validation/cases/`: sources, a brief written as a user would type it (no cost in it), the reported cost and **which cost categories it covers** (instruments, robots, analytics, integration labour, construction...). Like-for-like matters: many papers exclude analytics or include building works.
- `python -m labforge.validation.runner` designs each lab (hand-written workflow, or the agent from the brief), computes P10/P50/P90 predicted cost over price uncertainty, and reports whether the real figure falls inside the band plus the log10 error.
- Headline for the pitch: "N real labs, reported cost inside our 80% band in K of them, median error X%". Only `verified: true` cases count; a person must check each against its primary source.
- Throughput validation where papers report it (samples/day) uses the same case file.

Seed cases (all unverified, from a first search):

| Case | Reported | Covers | Source |
|---|---|---|---|
| Low-cost 3D-printed flow SDL (2026) | $5,000 | hardware, excl. analytics | [Chemistry World](https://www.chemistryworld.com/news/human-in-the-loop-approach-could-cut-costs-of-robotic-labs-by-90/4023311.article), possibly [Nature Synthesis 2026](https://www.nature.com/articles/s44160-026-01053-0) |
| Same team's earlier commercial-parts version | $50,000 | hardware, excl. analytics | same article |
| CMU Cloud Lab | $40M | whole project incl. construction | [CMU](https://www.cmu.edu/news/stories/archives/2021/august/first-academic-cloud-lab.html) |

Still to find (target 6–10 verified): Liverpool mobile robotic chemist (Burger et al., Nature 2020), Berkeley A-Lab, Argonne Polybot, an Opentrons-based biology SDL, a vendor workcell quote (HighRes/Biosero/Chemspeed), and ideally an XChem-style crystallography facility. Review articles with cost tables are a good shortcut.

## 2. Optimisation for vendors

**Question we answer:** for a given lab, how much would it be worth to make instrument X faster or bigger, and when does improving it stop paying off?

- `labforge.sim.whatif.optimise_instrument(spec, workflow, layout, instance_id)` sweeps the instrument's cycle time (0.5x to 1.2x) and parallel capacity (+1, +2) through the Monte Carlo simulator with common random numbers.
- Output (`schemas/instrument_optimisation.schema.json`): throughput curve with P10–P90, elasticity near baseline (≈0 means "not the limit here"), the next bottleneck, and a plain-language note such as "halving the reader's cycle time raises throughput 40%; after that the LC-MS becomes the limit".
- Gateway: `POST /optimise` with `instance_id`. UI: a "vendor view" chart when you click an instrument.
- Demo line: an LC-MS vendor sees that a 30% faster gradient lifts library throughput by Y%, while a faster plate reader would change nothing in this lab.

## Owners
| Work | Owner |
|---|---|
| Find, transcribe and verify validation cases; cost model ranges; validation runner | Max (Strand B) |
| Agent designs labs from case briefs (`design_from_brief`) | Albert (Strand C) |
| What-if sweeps, transfer-time and uptime sweeps, Modal parallelism | Maxim (Strand D) |
| Vendor view chart and validation scatter (predicted vs reported cost) | Roshan (Strand A) |
| Schemas, `/optimise` and `/validation` routes | Integrator |
