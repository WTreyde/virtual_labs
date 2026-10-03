# Inbox: Maxim (Strand D: layout, sim, verifier, bench runner)

Last updated: 2026-10-03 23:30 BST by the integrator. Main at `5c8d56d` (plus this inbox commit).

The integrator rewrites this file on every integration pass (every 30 min until the 09:00 freeze on 4 Oct).
Work the open items top to bottom. Done items drop off once your merged work on main shows them done.
Don't edit this file; report progress in your PR description.

## Open items

```
Your #44 is merged (21-task leaderboard 74% vs 59%, noise analysis, light-curtain mitigation). Thanks.
The team tested the demo tonight; two items are yours.
1. P2 #15, instrument placement looks random. First check whether the case scenes use a fresh
   generate_layout or the recorded replay layout (recorded replays keep old placements; if so, say which
   replays need re-recording and Albert will do it). If it's the current placer: align benches to walls
   and a grid, group instruments by process stage in workflow order, keep aisles straight. Layout
   violations must not get worse (chem 0, fbdd 1 today).
2. P2 #16, technicians all return to one spot when idle. Add a break area (kitchen or coffee corner) to
   the generated layout as a zone that never blocks walkways, and give operators an idle target there.
   Roshan animates it once it's in the layout.
Run make check, push strand/sim, and open a PR into main.
```
