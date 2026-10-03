# Strand B: vendor catalog, safety rules, LabDesignBench tasks (Max)

**Owns:** `backend/labforge/catalog/` (incl. `data/catalog.json`, `data/safety_rules.json`), `backend/labforge/bench/tasks/`.
**Produces:** `CatalogItem` list, `BenchTask` files.

## Tasks, in order
1. List every instrument in `docs/pipelines.md` (both scenarios) plus robots (arms, rails, mobile robots) and lab furniture: ~60 items. Commit the list in `scrape.py` `VENDOR_PAGES` early so Albert can plan against ids.
2. Scrape once (Modal + Claude extraction) into `data/catalog.json`; record every number's source and confidence in `provenance`. Hand-check the ~20 items used in the demos. Missing numbers get `confidence: "placeholder"`, never a silent guess.
3. Human operator entries (`category: transporter`, `transport.kind: human`) for each role used in the pipelines.
4. `safety_rules.json`: which hazards need which zones, clearances, egress; Maxim's validator reads it.
5. LabDesignBench: ~20 tasks across both domains in `bench/tasks/`, about half with traps (infeasible target, room too small, placeholder specs, tamperable simulator, missing capability, unsafe shortcut, budget too low). Each task's `expected_behaviour` should be something a domain expert agrees with. Roshan, Maxim and the integrator can review bio and chem tasks.

Use Devin for the per-vendor scraping tickets if helpful; keep the cached JSON in git so the demo never needs the network.

## Added after judge feedback (see docs/validation.md)
6. Validation cases in `backend/labforge/validation/cases/` (schema `validation_case`): find 6–10 published autonomous labs with reported costs, read each primary source, record exactly what the figure covers, and set `verified: true` only after checking. Three unverified seeds are there already.
7. Cost model in `validation/cost.py`: replace the placeholder integration-labour range and confidence-based price bands with sourced ranges; add per-item price `provenance` where vendors publish prices.
8. Where a case gives enough detail, hand-write its `workflow` from catalog ids so it can be costed without the agent.
