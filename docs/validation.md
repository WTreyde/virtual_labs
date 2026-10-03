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

### Out-of-sample test (the fair one)

After the in-sample work above, the cost model was **frozen at commit 02d7678** and 6 new cases were collected blind (NIH S10 awards for a Biomek i7, two ÄKTA pure systems, a PHERAstar FSX, an NT8 and a Rock Imager 2; none cited anywhere in the catalog). Scored against the frozen model:

| Case | Year | Reported | P10 / P50 / P90 | Multiple | In band |
|---|---|---|---|---|---|
| UMich PHERAstar FSX | 2026 | $155,178 | $116k / $192k / $328k | 1.24x | yes |
| Thomas Jefferson NT8 (LCP) | 2019 | $93,950 | $48k / $72k / $110k | 0.77x | yes |
| Temple ÄKTA pure L (proxy) | 2016 | $52,599 | $40k / $72k / $134k | 1.37x | yes |
| Sanford Burnham Biomek i7 Hybrid | 2024 | $594,187 | $183k / $326k / $599k | 0.55x | yes |
| Eastern Washington ÄKTA pure 25 | 2026 | $176,423 | $69k / $95k / $133k | 0.54x | no |
| Baylor Rock Imager 2 (proxy) | 2021 | $136,284 | $222k / $436k / $889k | 3.20x | no |

**Out-of-sample: 4 of 6 inside P10–P90; median multiple 1.00x (3 high, 3 low, so no systematic bias); 1 of 6 within ±25%.** The estimates generalise better than the in-sample numbers suggested: the ~1.8x in-sample bias came from those cases' quirks (old prices, a used robot, an unknown ambr model). **The confidence score does not generalise:** it stated a 45% average chance of landing within ±25% against 17% observed, and its Brier score (0.229) is worse than a constant baseline (0.139). Caveat: S10 award amounts can include service or accessories.

After the test, a 2021 NIH Formulatrix "Rock Imager" purchase ($183,143, model unstated, placeholder confidence) was added to the catalog. It brings both Rock Imager cases inside the band (JHU 1.10x, Baylor 1.33x), but that is after the fact for both and does not count as out-of-sample. Current in-sample result with it: 3 of 7 in band, median 1.51x.

### Uncertainty terms and a second blind round

After round 1, two uncertainty terms were added, both sized from catalog evidence outside the validation cases: **grant award with unknown contents** (spread 0.25, from five award-vs-purchase pairs) and **configurable systems** (spread floor 0.31, from configured-price ranges within product families). 15 instruments were added to the catalog (79 items). The model was then frozen again at **973d0f5** and 6 new cases were collected blind (4 NIH S10 awards, one MRC grant, one French public tender):

| Case | Year | Reported | Multiple | In band |
|---|---|---|---|---|
| UTSW Echo 555 | 2019 | $336,900 | 0.89x | yes |
| CNRS-IGBMC crystal imager (tender) | 2023 | ~$460,000 | 0.78x | yes |
| Baylor dragonfly + mosquito HV | 2026 | $305,578 | 0.72x | yes |
| Ohio State mosquito | 2010 | $111,200 | 0.63x | yes |
| Stony Brook Mantis + PHERAstar | 2020 | $173,354 | 1.25x | yes |
| Newcastle 2 x Rock Imager 1000 (MRC) | 2023 | ~$988,930 | 0.46x | no |

Round 2 (category-corrected): **5 of 6 in band; median 0.75x (we guessed low); 1 of 6 within ±25%; stated 33% vs observed 17%; Brier 0.171 vs 0.139 baseline.** Raw as collected: 3 of 4 costable cases in band (two listed only "instruments" for an imager, which the catalog files as analytics; the collection prompt had omitted that convention, and the corrected numbers apply one mechanical rule to all six). A bug that returned $0 with full confidence when nothing could be priced is fixed; such cases now report `not_costable`.

**Both blind rounds together (12 cases): 9 of 12 inside the 80% band (75%).** The band holds up. The centre drifts (1.00x, then 0.75x; grants averaged ~16% above purchase prices in the calibration pairs, and that shift is deliberately not applied), and the confidence percentage does not yet beat a constant baseline in either round.

**Slide 6 line:** "Tested blind twice on 12 labs we had never seen, our 80% cost band caught 9 of 12. We show that band, and we say plainly that our single-number confidence score is not yet reliable."

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
