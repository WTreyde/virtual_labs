# Inbox: Roshan (Strand A: game client and report)

Last updated: 2026-10-04 06:00 BST by the integrator. Main at `dc71974` (plus this inbox commit).

The integrator rewrites this file on every integration pass (every 30 min until the 09:00 freeze on 4 Oct).
Work the open items top to bottom. Done items drop off once your merged work on main shows them done.
Don't edit this file; report progress in your PR description.

## Open items

```
Your #70, #74, #77 (landing page), #80 (brief on screen), #82 (Report), #86 (linked evidence), #89 (close targets) and #92 (50-rep XChem replay +
staffing card) are merged. Thanks.
Top priority (before 09:00): Albert's #91 (held) regenerates the XChem summary with a
third-operator-only control. Copy backend/labforge/agent/demo/scenarios_20261004_resim50/fbdd.summary.json
from origin/strand/agent-isolate-staffing into frontend/public/replays/fbdd.summary.json (branch off main;
I checked that the copy makes test_replay_summary pass with #91). Show the control on the idle-capacity card:
third operator only, growth still in the hotel, 410.7/day (no gain; STX44 binds). Then neither change
alone helps; together 634.7/day. Add "assumes the synchrotron keeps up" next to 635 and 1,307 (see
Maxim's #93: at about 180 s per crystal, 635/day needs about 33 h of beam a day).
P1 (team feedback)
8. Time labels: "Day 3, 14:05:22" (day into the run plus HH:MM:SS).
9. Schedule view: human device names (catalog vendor and model, or the step name), not reader_1.
10. BOM: proposed mitigations as "Proposed: ..." rows (price estimated); cost P10-P90 band with
    confidence marked "experimental".
P2
11. Break area: draw the zone with kind "break_area" as a write-up corner using its label.
Run make check and npm run check:replays, then push and open a PR into main. Small PRs are fine.
```
