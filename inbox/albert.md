# Inbox: Albert (Strand C: agent and Amass)

Last updated: 2026-10-03 17:20 BST by the integrator. Main at `087d2af`.

The integrator rewrites this file on every integration pass (every 30 min until the 09:00 freeze on 4 Oct).
Work the open items top to bottom. Done items drop off once your merged work on main shows them done.
Don't edit this file; report progress in your PR description.

## Open items

```
Pull main. Note the schema change: catalog process.durations_s can now be per unit. The Shifter's
crystal_harvesting is 35 s per crystal (process.duration_basis = "crystal"). The planner and agent
must multiply it by the crystals per plate, and must not use 35 s as a per-plate time.
1. For the landing page: write a short summary per case next to each replay
   (frontend/public/replays/chem.summary.json and fbdd.summary.json): title, brief (one
   sentence), headline throughput with P10-P90, bottleneck, budget vs BOM, and honest limits
   (from the scenario READMEs: layout violations, verifier disagreement, refused targets).
2. Once Maxim's #26 is merged, re-record XChem on the new main and replace
   frontend/public/replays/fbdd.json, keeping the rule of realistic inputs with no tuning to
   the story. Report whichever unit binds. #23 (the hotel what-if) can follow on top.
Run make check, push, and open a PR into main.

After the items above (nice to have, depends on PR #31 merging):
3. Optional BOM column "Control" from the orchestrator manifest devices[].control.status
   (open standard / vendor API / unconfirmed / none listed), and an optional agent tool export_orchestrator.
4. After re-recording fbdd.json, regenerate the orchestrator sample:
   cd backend && python3 -m labforge.orchestrator.cli ../frontend/public/replays/fbdd.json --out labforge/orchestrator/samples/fbdd
```
