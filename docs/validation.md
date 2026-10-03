# Validation and vendor optimisation (from judge feedback, 3 Oct)

## 1. Validation against real labs

**Question we answer:** if you had described a real, published autonomous lab to LabForge, how close would its cost (and throughput) prediction have been?

- Each real lab is a `ValidationCase` (`schemas/validation_case.schema.json`) in `backend/labforge/validation/cases/`: sources, a brief written as a user would type it (no cost in it), the reported cost and **which cost categories it covers** (instruments, robots, analytics, integration labour, construction...). Like-for-like matters: many papers exclude analytics or include building works.
- `python -m labforge.validation.runner` designs each lab (hand-written workflow, or the agent from the brief), computes P10/P50/P90 predicted cost over price uncertainty, and reports whether the real figure falls inside the band plus the log10 error.
- Headline for the pitch: "N real labs, reported cost inside our 80% band in K of them, median error X%". Only `verified: true` cases count; a person must check each against its primary source.
- Throughput validation where papers report it (samples/day) uses the same case file.

### Current result (3 Oct, `python -m labforge.validation.runner`; the Validation tab computes the same from `/validation`)

**16 cases, all verified against primary sources; 7 can be costed from the catalog. Reported cost inside our P10–P90 band in 2 of 7; median multiple (our P50 ÷ reported) 1.80x, median |log10 error| 0.26.** Four seed cases with no public cost of known coverage were dropped (CMU Cloud Lab, Edinburgh and Earlham foundries, PoLARIS).

| Case | Reported | P10 / P50 / P90 | Multiple | In band | Confidence (within ±25%) | Data coverage |
|---|---|---|---|---|---|---|
| OT-2 protein purification (2024) | $25,000 (range $20–30k) | $16.7k / $24.8k / $37.5k | 0.99x | yes | 53% medium | 0.63 |
| Kent ambr 250 (2018) | $495,600 | $494k / $894k / $1.67M | 1.80x | yes | 38% low | 0.35 |
| OT-2 crystallisation (2025) | $13,500 | $13.6k / $15.3k / $17.3k | 1.13x | no (just below P10) | 98% high | 1.00 |
| HardwareX OT-2 (2025), **used unit** | $10,110 | $13.6k / $15.3k / $17.3k | 1.51x | no | 98% high | 1.00 |
| UCLA crystallisation suite (2007) | $375,141 | $451k / $740k / $1.27M | 1.97x | no | 43% medium | 0.23 |
| DNA-BOT OT-2 (2020) | $8,000 | $13.5k / $20.9k / $33.0k | 2.61x | no | 49% medium | 0.52 |
| JHU Rock Imager 1000 (2023) | $187,457 | $257k / $493k / $977k | 2.63x | no | 35% low | 0.28 |

**How the prediction and its confidence are built** (`validation/cost.py`): each item's price is the catalog entry matching the case's basis (bare unit or configured system) and closest in year, adjusted from its own source year with the BLS lab-instrument PPI. Every evidence gap widens that item's spread: source quality, years between the price and the purchase, a bare/configured mismatch (spread learned from catalog price pairs) and a proxy model. "Confidence" is the predictive chance the real cost is within ±25% of P50; "data coverage" is the value-weighted share of good evidence; `drivers` name the items behind most of the uncertainty.

**Is the confidence honest?** On the 6 like-for-like cases (the used OT-2 is excluded), we stated a 53% average chance of landing within ±25% and hit 33%: overconfident, mostly on list prices (real buyers pay below list). The Brier score is 0.152, better than 0.222 for always stating the observed hit rate, so the confidence does rank good and bad predictions. All of this is in-sample: the method was refined on these cases.

**Slide 6 line:** "16 verified real labs; 7 costable. Our band caught 2 of 7, and we run about 1.8x high, mainly because our prices come from configured US federal purchases. Our confidence score ranks predictions correctly (Brier 0.15 vs 0.22 baseline) but is still overconfident, and we show it."

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
