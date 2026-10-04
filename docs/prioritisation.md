# Project prioritisation (user idea, 3 Oct)

**Question we answer:** a lab has several projects queued (e.g. a chemistry library screen and two enzyme campaigns). In what order, or mix, should they run so the lab stays busy and urgent projects finish on time?

**How (baseline already works):** `labforge.sim.portfolio.prioritise(projects)` and `POST /prioritise`. Each project is a Workflow on the lab's equipment ids, a number of labware units, and optionally a `weight` and `deadline_h`. It simulates every sequential order (up to 6 projects), round-robin interleaving, and a bottleneck-aware mix that releases work from whichever project stresses the least-loaded instrument. It recommends the shortest makespan, or the least weighted lateness when deadlines exist. Output: `schemas/project_schedule.schema.json` (candidates, recommendation, saving versus the order given, Gantt rows).

**Example from the tests:** a dispense-heavy and a read-heavy project on the enzyme lab finish in 6.2 h in the recommended order versus 11.0 h in the order given, a 44% saving, because the two projects then load different instruments at the same time.

**Honest limits:** the policy search uses mean durations, with no transfer times and no operator shifts. The recommendation is then checked with the Monte Carlo simulator over duration uncertainty (result below).

## Demo queue (Strand B)

`backend/labforge/catalog/data/demo_prioritise_queue.json` is a ready `POST /prioritise` body: three projects share one screening cell (UPLC-MS, Opentrons Flex, Echo 650, Multidrop, PlateLoc, LiCONiC incubator, PHERAstar, UR5e), given in the order they were queued:

| Project | Plates | Heaviest instrument | Deadline |
|---|---|---|---|
| Enzyme campaign | 72 | liquid handler (30 min/plate) | none |
| Chemistry library screen (768 compounds) | 8 | LC-MS QC (~4 h/plate) | none |
| Urgent re-test of hits (LC-MS re-check, dose-response) | 2 | LC-MS (1 h/plate) | 8 h, weight 5 |

Result from `POST /prioritise` (3 Oct, current catalog):

| | Given order | Recommended (re-test > library > enzyme) |
|---|---|---|
| Urgent re-test finishes | 46.7 h (38.7 h late) | **3.2 h (on time)** |
| All projects finish | 46.7 h | **39.2 h (16% sooner)** |
| Mean instrument utilisation | 21% | 25% |

**Monte Carlo check (4 Oct, main at 427c06e, 30 replicates over duration uncertainty):**

| | Given order | Recommended |
|---|---|---|
| All projects finish, P50 | 49.8 h | **43.9 h** |
| P10–P90 | 42.5–64.8 h | 37.4–51.7 h |
| Recommended finishes first | | **30 of 30 runs** |

**Quoted everywhere (README, the Scheduling case card and page, the pitch): these Monte Carlo P50s, 43.9 h vs 49.8 h, about 6 h or 12% sooner.** The 16% above is the single run on mean step times only.

The P50s are longer than the mean-duration figures above because slow draws on the bottleneck instruments compound; the ranking holds in every run. Reproduce with `labforge.sim.portfolio.prioritise` on the demo queue (its `caveat` field carries these numbers).

Why: the re-test needs the LC-MS, which the library would otherwise hold for ~32 h, and the enzyme campaign loads the liquid handler instead, so running the library early overlaps the two bottlenecks. Step durations are planning estimates from `docs/pipelines.md` (each step's `params.duration_source`). The queue sizes were chosen so the demo shows the effect: with fewer than ~50 plates queued, every project fits into the lab at once and the order barely matters.

## Owners and cut line for the 09:00 freeze
| Work | Owner | Must-have by freeze? |
|---|---|---|
| Confirm recommended vs naive schedule in the Monte Carlo simulator (P10–P90 makespan) | Maxim | Done (see above) |
| Demo scenario: 3 projects (chem library screen, enzyme campaign, urgent re-test with deadline) | Max | Yes |
| Agent tool `plan_projects` so a user can ask "what order should I run these?" | Albert | Nice to have |
| Gantt chart and "lab busy %" before/after in the UI | Roshan | Nice to have; a static chart in the slides is the fallback |
| Transfer times, operator shifts, smarter search (more than 6 projects) | Maxim | After the hackathon |

Multi-site coordination (shipping compounds, sharing data between labs worldwide) is pitch-only and not part of the product.
