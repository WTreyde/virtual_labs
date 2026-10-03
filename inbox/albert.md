# Inbox: Albert (Strand C: agent and Amass)

Last updated: 2026-10-03 17:40 BST by the integrator. Main at `9998609`.

The integrator rewrites this file on every integration pass (every 30 min until the 09:00 freeze on 4 Oct).
Work the open items top to bottom. Done items drop off once your merged work on main shows them done.
Don't edit this file; report progress in your PR description.

## Open items

```
Pull main (your #29 summaries are merged; Maxim's #26 per-unit verifier and leaderboard are merged).
1. Decision from the user (3 Oct 17:20): the XChem story is that the crystal growth hotel (Cytomat,
   80% busy) is the bottleneck. Drop any push toward a harvesting-limited design. Re-record XChem on
   the new main, which has the per-crystal Shifter rate and the per-unit verifier. Present the hotel as
   the limit (if it still binds), and add the hotel fix (a second or larger hotel) as the what-if.
   Your draft #23 is that recording, so finish it on the new main. Same rule as before: realistic
   inputs, no tuning, and report whichever unit binds. Then replace frontend/public/replays/fbdd.json,
   fbdd.summary.json and fbdd.whatif.json, and check that the planner and verifier P50 now roughly agree
   (they were 312 vs 112).
2. Chemistry story check: the chem card says the bottleneck is SWING XL powder dosing (100% busy), but
   the demo script says LC-MS. Don't change the run to fit the script. Confirm which unit binds, and if
   it's the doser, say so in your PR so the pitch can change.
3. Regenerate the orchestrator samples after re-recording:
   cd backend && python3 -m labforge.orchestrator.cli ../frontend/public/replays/fbdd.json --out labforge/orchestrator/samples/fbdd
4. Nice to have: an optional BOM column "Control" from the orchestrator manifest devices[].control.status.
Run make check, push, and open a PR into main.
```
