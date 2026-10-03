# Inbox: Albert (Strand C: agent and Amass)

Last updated: 2026-10-03 18:45 BST by the integrator. Main at `1fef7ae` (plus this inbox commit).

The integrator rewrites this file on every integration pass (every 30 min until the 09:00 freeze on 4 Oct).
Work the open items top to bottom. Done items drop off once your merged work on main shows them done.
Don't edit this file; report progress in your PR description.

## Open items

```
Your #41 is merged: the chemistry bottleneck is the two SWING XL reaction units (99.8% busy), with
312/day planned and 320/day verified. That closes the chemistry story check.
User decision (3 Oct 18:33): the XChem pitch now says the twin caught the planner leaving the 1,000-slot
Rock Imager at 4% busy while the 44-slot hotel sits at 85%, and that the real fix is growing plates in
the imager at $0. The second-hotel what-if is no longer the pitch's fix.
1. Back that claim with a run: record a what-if on current main where crystallisation plates grow and
   soak in the Rock Imager (its catalog capacity and temperature) instead of the STX44, with nothing
   else changed. Report the new throughput (planned and verified) and the new bottleneck honestly,
   whatever they are. Save it next to xchem-whatif.json and add its numbers to fbdd.summary.json under
   a clearly named key (e.g. "imager_growth_whatif"). If the imager can't hold growth plates
   realistically (Max is confirming), say so and don't record it.
2. From Maxim's #38 (planner vs verifier gap = Monte Carlo noise, not a model difference):
   - agent/tools.py: run the reported design's simulation with at least 50 replicates (7 s each).
   - agent/demo_scenarios.py: make the planner-vs-verifier gate noise-aware (e.g. is the planner's P50
     inside the verifier's bootstrap interval for the median), not a fixed 20% on two noisy medians. Keep
     the seeds different on each side.
   - agent/benchmark.py: record response.stop_reason in the vanilla arm before json.loads.
3. Nice to have: an optional BOM column "Control" from the orchestrator manifest devices[].control.status.
Run make check, push, and open a PR into main.
```
