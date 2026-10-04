# Inbox: Roshan (Strand A: game client and report)

Last updated: 2026-10-04 02:30 BST by the integrator. Main at `5b2141f` (plus this inbox commit).

The integrator rewrites this file on every integration pass (every 30 min until the 09:00 freeze on 4 Oct).
Work the open items top to bottom. Done items drop off once your merged work on main shows them done.
Don't edit this file; report progress in your PR description.

## Open items

```
Your #70 (logo) is merged.
P0 (new): XChem "The fix" card must be honest about the what-if (Albert's #71).
0. fbdd.summary.json imager_growth_whatif now says: planned P50 560, verified P50 411 crystals/day,
   bottleneck "both skilled operators, 97%". The baseline is 424 verified. So growing in the imager
   gives no checked gain (411 vs 424, within noise); operators become the limit. Show it that way,
   e.g. "Simulated: no throughput gain (424 -> 411/day checked); next limit: operators 97%", and
   compare verified with verified. Don't headline the 560 planned figure, and don't call it a fix.
P1 (team feedback)
3. Landing page: two buttons only, "Design your own lab" and "Case studies".
4. Case pages: keep the case's problem statement on screen.
5. Rename "Report for your boss" to "Report".
6. Evidence list: show only items with a real link; drop "reviewed"/"unavailable"-only entries.
7. Chemistry equipment panel: make the close "x" on the left panel a big target.
8. Time labels: "Day 3, 14:05:22" (day into the run plus HH:MM:SS).
9. Schedule view: human device names (catalog vendor and model, or the step name), not reader_1.
10. BOM: proposed mitigations as "Proposed: ..." rows (price estimated); cost P10-P90 band with
    confidence marked "experimental".
P2
11. Break area: draw the zone with kind "break_area" as a write-up corner using its label.
Run make check and npm run check:replays, then push and open a PR into main. Small PRs are fine.
```
