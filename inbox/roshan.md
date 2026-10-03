# Inbox: Roshan (Strand A: game client and report)

Last updated: 2026-10-04 01:05 BST by the integrator. Main at `0e50d7f` (plus this inbox commit).

The integrator rewrites this file on every integration pass (every 30 min until the 09:00 freeze on 4 Oct).
Work the open items top to bottom. Done items drop off once your merged work on main shows them done.
Don't edit this file; report progress in your PR description.

## Open items

```
Your #62 (collapsible agent log with timings) is merged. Note: the XChem replay was re-recorded
(#58): 424/day verified vs a 300 target, $1.07M, 0 violations, STX44 82.6% busy, imager camera 8.5%.
Check the XChem page reads correctly with it (the fix card, stat cards and verdicts).
P1 (team feedback)
1. Text-heavy areas: larger font, more line height, higher contrast.
2. LabForge logo at the top in a bright, highly visible colour.
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
