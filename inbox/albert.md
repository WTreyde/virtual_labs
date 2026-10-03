# Inbox: Albert (Strand C: agent and Amass)

Last updated: 2026-10-04 00:30 BST by the integrator. Main at `ae825c6` (plus this inbox commit).

The integrator rewrites this file on every integration pass (every 30 min until the 09:00 freeze on 4 Oct).
Work the open items top to bottom. Done items drop off once your merged work on main shows them done.
Don't edit this file; report progress in your PR description.

## Open items

```
Merged since your last inbox: Maxim's #53/#57 (lab-like layouts, break area, fair vanilla bench arm),
Max's #56 (22 catalog placeholders now sourced; sim-relevant: Genevac HT6 12 plates and 9,000 s per
run, Q700 lysis 130 s, KMR iiwa pick/place 20 s), Roshan's #55 (verifier verdicts beside the BOM).
1. Re-record the case replays (chem.json, fbdd.json and their .summary.json) on current main. They
   still show the old layouts and the old catalog values. Report the new planned and verified
   throughput and bottleneck honestly; they will move.
2. Honest gate: chem.summary.json says gate_passed: true next to a refuted budget and throughput.
   Roshan's page now explains it ("checks the process ran, not that the lab meets the brief"); make the
   field name or the gate say the same (e.g. pipeline_ok), or fail it on refuted brief claims.
3. Imager what-if: Max's local run (#56) gives P50 226/day (169-308) with growth in a 970-slot imager
   hotel, now limited by both operators at 98-99%, still under the 300 target. The simulator models
   the imager as one camera, so Maxim is adding slot capacity first. Once his PR lands, record it
   properly and add "imager_growth_whatif" {planned_p50, verified_p50, unit, bottleneck} to
   fbdd.summary.json.
4. agent.benchmark.run_arm('vanilla') still has the old prompt and parser that made design impossible
   (Maxim #57). Point it at labforge.bench.runner._vanilla or delete it, so nothing relies on it.
5. Time one live trap brief (e.g. "include an in-house X-ray source") that should decline and name the
   limit; seconds in your PR. Over about 40 s means the demo keeps the replay.
6. Still open: agent/tools.py at least 50 replicates (now 10); noise-aware planner-vs-verifier gate.
Run make check, push, and open a PR into main.
```
