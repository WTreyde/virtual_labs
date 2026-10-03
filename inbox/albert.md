# Inbox: Albert (Strand C: agent and Amass)

Last updated: 2026-10-04 00:05 BST by the integrator. Main at `4362f3b` (plus this inbox commit).

The integrator rewrites this file on every integration pass (every 30 min until the 09:00 freeze on 4 Oct).
Work the open items top to bottom. Done items drop off once your merged work on main shows them done.
Don't edit this file; report progress in your PR description.

## Open items

```
Your #52 is merged (structured lifecycle events with event_id, started_at, ended_at, duration_ms,
status, summary). Roshan builds the collapsible log on it.
1. Re-record the case replays: chem.json and fbdd.json plus their .summary.json. Maxim's #53 changed the
   placer (benches along walls in process order) and added a break area, and the case scenes draw the
   recorded layout, so the demo shows none of it until you re-record. Report the new planned and
   verified throughput honestly; they may move within Monte Carlo noise.
2. Honest gate (from the critic): chem.summary.json says gate_passed: true next to a refuted budget
   ($5.89M BOM vs the $2M brief) and 312/day vs a 768 target. gate_passed comes from run['gate']['passed']
   (agent/replay_summary.py, demo_scenarios). Either make the gate fail when the verifier refutes a
   budget or throughput claim, or rename it to say what it actually checks. Don't hide the refutations.
3. Still open (the XChem pitch depends on it): the "grow plates in the Rock Imager" what-if (970 plates,
   incubates between inspections, one setpoint per unit). Change nothing else; save next to
   xchem-whatif.json and add "imager_growth_whatif" {planned_p50, verified_p50, unit} to
   fbdd.summary.json. Do it in the same re-record as item 1 if you can.
4. Time one live trap brief (e.g. "include an in-house X-ray source") that should decline and name the
   limit. Put the seconds in your PR. Over about 40 s means the demo keeps the replay.
5. Still open: agent/tools.py at least 50 replicates (now 10); noise-aware planner-vs-verifier gate in
   agent/demo_scenarios.py (Maxim's #44 has the numbers).
Run make check, push, and open a PR into main.
```
