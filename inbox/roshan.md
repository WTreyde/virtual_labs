# Inbox: Roshan (Strand A: game client and report)

Last updated: 2026-10-04 05:00 BST by the integrator. Main at `c03e671` (plus this inbox commit).

The integrator rewrites this file on every integration pass (every 30 min until the 09:00 freeze on 4 Oct).
Work the open items top to bottom. Done items drop off once your merged work on main shows them done.
Don't edit this file; report progress in your PR description.

## Open items

```
Your #70, #74, #77 (landing page), #80 (brief on screen), #82 (Report) and #86 (linked evidence only) are merged. Thanks.
Top priority (before 09:00), blocked on Albert's item 7 (the failing summary test you found in
#86; thanks for not committing past it). Albert's #83 re-simulated the XChem replay at 50 replicates. When Albert hands you the regenerated summary, copy
backend/labforge/agent/demo/scenarios_20261004_resim50/xchem.json and fbdd.summary.json into
frontend/public/replays/ (fbdd.json, fbdd.summary.json; use his newer summary file), rebuild, and run npm run check:replays.
The shipped replay still carries the old 10-replicate gate. Planned P50 is now 410.7/day (band
336-523), verified 424/day, and both operators sit at about 72% of their shift.
P1 (team feedback)
7. Chemistry equipment panel: make the close "x" on the left panel a big target.
8. Time labels: "Day 3, 14:05:22" (day into the run plus HH:MM:SS).
9. Schedule view: human device names (catalog vendor and model, or the step name), not reader_1.
10. BOM: proposed mitigations as "Proposed: ..." rows (price estimated); cost P10-P90 band with
    confidence marked "experimental".
P2
11. Break area: draw the zone with kind "break_area" as a write-up corner using its label.
Run make check and npm run check:replays, then push and open a PR into main. Small PRs are fine.
```
