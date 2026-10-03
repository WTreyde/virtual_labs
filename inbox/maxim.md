# Inbox: Maxim (Strand D: layout, sim, verifier, bench runner)

Last updated: 2026-10-03 18:05 BST by the integrator. Main at `37035bf`.

The integrator rewrites this file on every integration pass (every 30 min until the 09:00 freeze on 4 Oct).
Work the open items top to bottom. Done items drop off once your merged work on main shows them done.
Don't edit this file; report progress in your PR description.

## Open items

```
1. On the leaderboard, chem_cascade_baseline (the no-trap baseline) scores 0% for BOTH arms. Find out
   why: is it a real agent failure, a check that can't pass, or a scoring bug? Fix it if it's a bug; if
   it's real, keep it and add a one-line explanation to the task's verifier output.
2. Max's #37 added 5 bench tasks (21 total). Re-run the leaderboard on current main
     cd backend && python -m labforge.bench.runner --arms platform vanilla \
        --out labforge/bench/results/leaderboard.json
   and commit it, so slide 5 and the Bench tab cover all 21 tasks.
3. Planner vs verifier on the new XChem run: planner P50 124 < verifier 172 crystals/day (gate red at
   20%). Find which modelling difference causes it (seeds and replicates, operator shifts, or residence
   handling in the verifier's re-simulation). Albert's inbox has the same item, so coordinate. Report
   the cause; don't widen the tolerance to pass.
4. Layout violation counts on the two demo designs (chem, fbdd; XChem now has 1) for the pitch. Put
   them in your PR description.
Run make check, push strand/sim, and open a PR into main.
```
