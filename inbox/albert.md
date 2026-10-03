# Inbox: Albert (Strand C: agent and Amass)

Last updated: 2026-10-03 18:05 BST by the integrator. Main at `37035bf`.

The integrator rewrites this file on every integration pass (every 30 min until the 09:00 freeze on 4 Oct).
Work the open items top to bottom. Done items drop off once your merged work on main shows them done.
Don't edit this file; report progress in your PR description.

## Open items

```
Your #23 is merged: the new XChem replay (hotel-limited, 124/day planned vs 172 verified) and the
separate hotel remedy (+1 STX44: 193 planned / 248 verified). Thanks; that closes the XChem re-record.
1. Chemistry story check (still open): the chem card's bottleneck is SWING XL powder dosing (100% busy),
   but the demo script says LC-MS. Don't change the run to fit the script. Confirm which unit binds in a
   fresh chemistry run on current main, and say so in your PR so the pitch can change if needed.
   If you re-record, replace chem.json and chem.summary.json and regenerate the chem orchestrator sample.
2. Planner vs verifier: XChem now disagrees the other way (planner 124 < verifier 172, gate red at
   the 20% tolerance). Work with Maxim (his inbox has the same item) to find which modelling difference
   causes it (seeds and replicates, operator shifts, or residence handling). Report the cause; don't
   widen the tolerance to pass.
3. Nice to have: an optional BOM column "Control" from the orchestrator manifest devices[].control.status.
Run make check, push, and open a PR into main.
```
