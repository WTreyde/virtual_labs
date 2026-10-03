# Inbox: Maxim (Strand D: layout, sim, verifier, bench runner)

Last updated: 2026-10-03 18:45 BST by the integrator. Main at `1fef7ae` (plus this inbox commit).

The integrator rewrites this file on every integration pass (every 30 min until the 09:00 freeze on 4 Oct).
Work the open items top to bottom. Done items drop off once your merged work on main shows them done.
Don't edit this file; report progress in your PR description.

## Open items

```
Your #38 is merged (failed runs no longer scored, truthful run time and model, layout counts, and
the planner vs verifier gap traced to Monte Carlo noise). Thanks; the follow-ups for Albert and Roshan
are in their inboxes.
1. Finish the 21-task leaderboard re-run you started and commit leaderboard.json in a new PR.
2. Optional, if time: the one remaining XChem layout violation is a real safety flag (non-collaborative
   arm_1 next to manual steps). If the layout engine can propose the mitigation (light curtain or
   pass-through) as a BOM line with a placeholder price, the pitch can show it.
Run make check, push strand/sim, and open a PR into main.
```
