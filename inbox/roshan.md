# Inbox: Roshan (Strand A: game client and report)

Last updated: 2026-10-04 00:30 BST by the integrator. Main at `ae825c6` (plus this inbox commit).

The integrator rewrites this file on every integration pass (every 30 min until the 09:00 freeze on 4 Oct).
Work the open items top to bottom. Done items drop off once your merged work on main shows them done.
Don't edit this file; report progress in your PR description.

## Open items

```
Your #55 is merged: the bench tab and the verifier verdicts beside the BOM close the P0s. Thanks.
P1 (team feedback)
1. Agent log under the total box: collapsible per step and tool call with timings, using Albert's #52
   events (pair start and end by event_id; duration_ms, status, summary).
2. Text-heavy areas: larger font, more line height, higher contrast.
3. LabForge logo at the top in a bright, highly visible colour.
4. Landing page: two buttons only, "Design your own lab" and "Case studies".
5. Case pages: keep the case's problem statement on screen.
6. Rename "Report for your boss" to "Report".
7. Evidence list: show only items with a real link; drop "reviewed"/"unavailable"-only entries.
8. Chemistry equipment panel: make the close "x" on the left panel a big target.
9. Time labels: "Day 3, 14:05:22" (day into the run plus HH:MM:SS).
10. Schedule view: human device names (catalog vendor and model, or the step name), not reader_1.
11. BOM: render layout proposed_mitigations as a "Proposed: ..." row, price marked estimated; show the
    cost P10-P90 band and mark confidence "experimental" (Max's #56 adds confidence.experimental).
P2
12. Break area: draw the zone with kind "break_area" (Maxim's #57) as a write-up corner using its label.
Run make check and npm run check:replays, then push and open a PR into main. Small PRs are fine.
```
