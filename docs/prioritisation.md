# Project prioritisation (user idea, 3 Oct)

**Question we answer:** a lab has several projects queued (e.g. a chemistry library screen and two enzyme campaigns). In what order, or mix, should they run so the lab stays busy and urgent projects finish on time?

**How (baseline already works):** `labforge.sim.portfolio.prioritise(projects)` and `POST /prioritise`. Each project is a Workflow on the lab's equipment ids, a number of labware units, and optionally a `weight` and `deadline_h`. It simulates every sequential order (up to 6 projects), round-robin interleaving, and a bottleneck-aware mix that releases work from whichever project stresses the least-loaded instrument. It recommends the shortest makespan, or the least weighted lateness when deadlines exist. Output: `schemas/project_schedule.schema.json` (candidates, recommendation, saving versus the order given, Gantt rows).

**Example from the tests:** a dispense-heavy and a read-heavy project on the enzyme lab finish in 6.2 h in the recommended order versus 11.0 h in the order given, a 44% saving, because the two projects then load different instruments at the same time.

**Honest limits:** mean durations, no transfer times, no operator shifts. The recommendation should be confirmed with the Monte Carlo simulator before we quote it, which is the first follow-up task.

## Owners and cut line for the 09:00 freeze
| Work | Owner | Must-have by freeze? |
|---|---|---|
| Confirm recommended vs naive schedule in the Monte Carlo simulator (P10–P90 makespan) | Maxim | Yes, a single comparison |
| Demo scenario: 3 projects (chem library screen, enzyme campaign, urgent re-test with deadline) | Max | Yes |
| Agent tool `plan_projects` so a user can ask "what order should I run these?" | Albert | Nice to have |
| Gantt chart and "lab busy %" before/after in the UI | Roshan | Nice to have; a static chart in the slides is the fallback |
| Transfer times, operator shifts, smarter search (more than 6 projects) | Maxim | After the hackathon |

Multi-site coordination (shipping compounds, sharing data between labs worldwide) is pitch-only and not part of the product.
