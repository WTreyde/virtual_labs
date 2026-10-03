# Inbox: Roshan (Strand A: game client and report)

Last updated: 2026-10-03 23:15 BST by the integrator. Main at `7a6bc3a` (plus this inbox commit).

The integrator rewrites this file on every integration pass (every 30 min until the 09:00 freeze on 4 Oct).
Work the open items top to bottom. Done items drop off once your merged work on main shows them done.
Don't edit this file; report progress in your PR description.

## Open items

```
Your #47 (items 1-3) is merged. The team tested the demo tonight; their P0s come first, then your
remaining 18:45 items, then the P1s. All of frontend/ is yours, so most of the list is here.

P0
1. Live agent: switch the chat to POST /chat/stream (stream_turn, SSE) instead of POST /chat. Read
   GET /health: when live_agent is false, show a clear banner with health.live_agent_note (e.g. "Live
   agent off: no API key loaded ...") instead of silently showing the offline example. live_chat:false
   (public Space) keeps your current "Live design is off" message.
2. Validation tab: GET /validation now always returns 200 with one row per case (28), in seconds.
   Rows can have status "no_design_yet" (with reason), "error" (with reason) or "not_costable". When
   the fetch itself fails with an HTTP error, say "The backend returned an error (<status>)", not
   "Needs the backend". Render the predicted-vs-reported scatter from the compared rows; agent-made
   designs carry design_provenance (show "designed by the agent, cost withheld" on hover).
3. Bench tab (#/bench):
   - isTamper in views.ts: rename to "input check failed" and show the check's note. Say "tamper
     attempt caught" only for a real override attempt (note mentions sim_config, catalog_overrides or
     simulator_overrides) or changed catalog values. Nobody tampered in the current run.
   - One plain-language line per task: what the brief asks and what trap it tests (task brief, trap,
     expected_behaviour in backend/labforge/bench/tasks/*.json, plus the leaderboard description).
   - Nicer table: readable chips, a legend for pass / fail / not checkable, sticky header.
   - Leaderboard numbers now (Maxim #44, 21 tasks, one run): platform 74% vs vanilla 59%.
Then your open 18:45 items: 4 schedule label overlap, 5 Download agent skill button, 6 bench model and
dates, 7 validation band and "experimental" label.
P1 (team feedback)
4. Text-heavy areas: larger font, more line height, higher contrast.
5. LabForge logo at the top in a bright, highly visible colour.
6. Landing page: two buttons only, "Design your own lab" and "Case studies".
7. Case pages: keep the case's problem statement on screen.
8. Rename "Report for your boss" to "Report".
9. Evidence list: show only items with a real link; drop "reviewed"/"unavailable"-only entries.
10. Chemistry equipment panel: the close "x" on the left panel is too small; make it a big target.
11. Agent log under the total box: collapsible per step and tool call, with timings (Albert is adding
    structured events; agree the shape in your PRs).
12. Time labels: "Day 3, 14:05:22" (day into the run plus HH:MM:SS).
13. Schedule view: show human device names (catalog vendor and model, or the step name), not reader_1.
14. BOM: render layout proposed_mitigations as a "Proposed: ..." row with the price marked estimated
    (Maxim #44).
P2
15. Idle technicians: once Maxim adds a break area to the layout, animate idle walk/sit/coffee there.
Run make check and npm run check:replays, then push and open a PR into main. Small PRs are fine.
```
