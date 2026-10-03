# Inbox: Roshan (Strand A: game client and report)

Last updated: 2026-10-04 00:05 BST by the integrator. Main at `4362f3b` (plus this inbox commit).

The integrator rewrites this file on every integration pass (every 30 min until the 09:00 freeze on 4 Oct).
Work the open items top to bottom. Done items drop off once your merged work on main shows them done.
Don't edit this file; report progress in your PR description.

## Open items

```
Your #51 is merged: streaming live chat with the "live agent off" banner, validation tab (28 rows,
band headline, score marked experimental), schedule labels, Download agent skill. Thanks.
P0
1. Bench tab (#/bench):
   - isTamper in views.ts: say "input check failed" and show the check's note. Say "tamper attempt
     caught" only for a real override attempt (note mentions sim_config, catalog_overrides or
     simulator_overrides) or changed catalog values. Nobody tampered in the current run.
   - One plain-language line per task: what the brief asks and what trap it tests (brief, trap,
     expected_behaviour in backend/labforge/bench/tasks/*.json, plus the leaderboard description).
   - Readable chips, a legend for pass / fail / not checkable, sticky header; show arm.model and the
     answered/scored dates (old item 6); tasks with run_failed show as "not run".
2. Chemistry case (from the critic): show the verifier's refuted claims next to the BOM, e.g. "Budget:
   refuted, BOM $5.89M vs $2M brief" and "Throughput: 312/day vs 768 target", from chem.summary.json
   (budget_vs_bom and the verified claims). A passed gate must not be the only thing on screen.
P1 (team feedback)
3. Agent log under the total box: collapsible per step and tool call with timings, using Albert's #52
   events (pair start and end by event_id; duration_ms, status, summary).
4. Text-heavy areas: larger font, more line height, higher contrast.
5. LabForge logo at the top in a bright, highly visible colour.
6. Landing page: two buttons only, "Design your own lab" and "Case studies".
7. Case pages: keep the case's problem statement on screen.
8. Rename "Report for your boss" to "Report".
9. Evidence list: show only items with a real link; drop "reviewed"/"unavailable"-only entries.
10. Chemistry equipment panel: make the close "x" on the left panel a big target.
11. Time labels: "Day 3, 14:05:22" (day into the run plus HH:MM:SS).
12. Schedule view: human device names (catalog vendor and model, or the step name), not reader_1.
13. BOM: render layout proposed_mitigations as a "Proposed: ..." row, price marked estimated.
P2
14. Break area: draw the break_area zone (Maxim's #53; zone id "break_area", kind "human_only" now and
    "break_area" soon, so accept both) as a coffee/write-up corner using its label. Idle staff already
    walk there once Albert re-records the replays.
Run make check and npm run check:replays, then push and open a PR into main. Small PRs are fine.
```
