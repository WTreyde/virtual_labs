# Inbox: Albert (Strand C: agent and Amass)

Last updated: 2026-10-04 02:00 BST by the integrator. Main at `53fbd2a` (plus this inbox commit).

The integrator rewrites this file on every integration pass (every 30 min until the 09:00 freeze on 4 Oct).
Work the open items top to bottom. Done items drop off once your merged work on main shows them done.
Don't edit this file; report progress in your PR description.

## Open items

```
Your #58 (fresh XChem replay: 411 planned / 424 verified per day, $1.07M, 0 violations, STX44 82.6%
binding) and #60 (honest gate) are merged. Thanks for not retrying until something passed.
Your #67 (explicit declined_by_model status) is merged, and Roshan shows it in the live chat.
2. Imager what-if is now possible: Maxim's #61 lets a residence step use the Rock Imager's 970
   storage slots while imaging stays one plate at a time. Record it on the new XChem design (growth on
   the imager instead of the STX44, nothing else changed) and add "imager_growth_whatif"
   {planned_p50, verified_p50, unit, bottleneck} to fbdd.summary.json. Report it whatever it shows.
3. agent.benchmark.run_arm('vanilla') still has the old prompt and parser (Maxim #57). Point it at
   labforge.bench.runner._vanilla or remove it.
4. Time one live trap brief (e.g. "include an in-house X-ray source") that should decline and name the
   limit; seconds in your PR. Over about 40 s means the demo keeps the replay.
5. Still open: agent/tools.py at least 50 replicates (now 10); noise-aware planner-vs-verifier gate.
Run make check, push, and open a PR into main.
```
