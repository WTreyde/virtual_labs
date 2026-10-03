# Inbox: Maxim (Strand D: layout, sim, verifier, bench runner)

Last updated: 2026-10-03 17:20 BST by the integrator. Main at `087d2af`.

The integrator rewrites this file on every integration pass (every 30 min until the 09:00 freeze on 4 Oct).
Work the open items top to bottom. Done items drop off once your merged work on main shows them done.
Don't edit this file; report progress in your PR description.

## Open items

```
1. PR #26 is held. With Max's #24 merged, test_duration_floor_is_compared_per_unit_not_per_plate
   fails. catalog_units() must return 1 when process.duration_basis[capability] names a unit
   other than "labware" (now in the schema). Make the test self-contained with both cases.
   Details are in the PR comment. Merge main, run make check, push.
2. Demo-critical, still open: the leaderboard is empty, and the new Benchmark tab needs it. Run
     cd backend && python -m labforge.bench.runner --arms platform vanilla \
        --out labforge/bench/results/leaderboard.json
   (needs ANTHROPIC_API_KEY), then commit the JSON.
3. For the Benchmark tab: add a one-paragraph "what LabDesignBench measures" (trap briefs,
   tamper checks, platform vs vanilla) to the leaderboard JSON as a "description" field, or as
   backend/labforge/bench/README.md, and tell Roshan which.
Open a PR into main.
```
