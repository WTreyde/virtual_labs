# Strand A: game client and report UI (Roshan)

**Owns:** `frontend/`. **Reads:** `Layout`, `SimResult`, `Workflow`, `CatalogItem`, `Claim` (see `schemas/`).

Already working: `make frontend` shows the example lab as shaded isometric boxes with moving plates, a bottleneck bubble and a BOM/throughput panel, with or without the backend.

## Tasks, in order
1. Pixel-art look: sprite per instrument category (liquid handler, arm, incubator, reader, LC-MS, crystal imager, centrifuge, human operator). Free CC0 isometric packs (e.g. Kenney) or generated pixel art; scale sprites to `footprint`.
2. Pokémon-style UI frame: dialogue box for agent messages at the bottom, stat card when you click an instrument (vendor, price, throughput, confidence badge from `data_confidence`/`provenance`).
3. Animate plates and operators from `SimResult.timeline` (fast-forward slider) instead of the looping dots.
4. Uncertainty panel: P10–P90 band, probability of meeting target, sensitivity list ("measure this first").
5. Claims panel: each agent claim with its confidence and the verifier's ✓/✗; Brier score.
6. Report: render `/report` Markdown to a printable page / PDF with a screenshot of the scene.
7. LabDesignBench leaderboard view: platform vs vanilla Claude per task.

Not playable: no walking character needed (team decision). Do not edit backend files; ask Albert/Maxim for API changes.

## Added after judge feedback (see docs/validation.md)
8. Vendor view: clicking an instrument offers "How could this instrument be better?", calling `POST /optimise` with its `instance_id`; chart throughput vs cycle-time multiplier (P10–P90 band) and show `headroom_note` in the dialogue box.
9. Validation view: scatter of predicted (P10–P90 bar) vs reported cost for each case from `GET /validation`, log scale, unverified cases greyed out.

## Added: project prioritisation (see docs/prioritisation.md)
10. Nice to have: Gantt chart from `POST /prioritise` (`gantt` rows, coloured by project) and lab-busy % for the recommended vs the given order.
