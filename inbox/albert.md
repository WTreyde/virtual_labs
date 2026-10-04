# Inbox: Albert (Strand C: agent and Amass)

Last updated: 2026-10-04 04:00 BST by the integrator. Main at `65760fa` (plus this inbox commit).

The integrator rewrites this file on every integration pass (every 30 min until the 09:00 freeze on 4 Oct).
Work the open items top to bottom. Done items drop off once your merged work on main shows them done.
Don't edit this file; report progress in your PR description.

## Open items

```
Your #58 (fresh XChem replay: 411 planned / 424 verified per day, $1.07M, 0 violations, STX44 82.6%
binding), #60 (honest gate) and #76 (live trap: declined in 17.7 s, so it can run live) are merged. Thanks for not retrying until something passed.
Your #67, #71 (imager what-if) and #73 (single vanilla arm) are merged. Thanks.
Optional: the what-if records one bottleneck instance (skilled_operator_1); if both operators bind,
list both so Roshan's card can say so.
5. New, from your #79 (merged, thanks): the shipped XChem replay (frontend/public/replays/fbdd.*)
   was planned on 10 replicates but its summary still says gate_passed: true, which the new gate
   would fail. Before 09:00, with no new agent run: re-simulate the recorded design at 50 replicates,
   update the replay's planned numbers and gate (and hand Roshan the new summary file), or, if that
   isn't possible, mark the replay as gated under the old 10-replicate rule. Use 50 replicates for
   item 6 too.
6. Before 09:00, no new agent run: rerun the recorded XChem design through the verifier in two
   what-ifs: (a) growth plates in the imager plus a third operator, (b) the same plus a second shift.
   Report verified/day vs the 424 baseline. If neither beats 424, say so; the pitch then keeps
   "imager is spare capacity, staff are the next limit".
Run make check, push, and open a PR into main.
```
