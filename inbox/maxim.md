# Inbox: Maxim (Strand D: layout, sim, verifier, bench runner)

Last updated: 2026-10-04 00:30 BST by the integrator. Main at `ae825c6` (plus this inbox commit).

The integrator rewrites this file on every integration pass (every 30 min until the 09:00 freeze on 4 Oct).
Work the open items top to bottom. Done items drop off once your merged work on main shows them done.
Don't edit this file; report progress in your PR description.

## Open items

```
Your #57 is merged (fair vanilla arm, break_area kind). Good catch on the vanilla prompt.
1. XChem pitch dependency: the simulator models the Rock Imager 1000 as one camera (capacity 1), so a
   "grow plates in the imager" design can't be simulated honestly. Let a storage/incubation step use
   the instrument's catalog storage_slots (970 for the Rock Imager, per Max's #46) as its capacity,
   while imaging stays one plate at a time. Add a test. Albert records the what-if once this lands;
   Max's quick run (#56) suggests about 226/day with the operators as the next limit.
2. Morning re-run prep: make sure python -m labforge.bench.runner --arms platform vanilla runs end to
   end on current main (one task each is enough tonight) so the 08:05 re-run is one command. Don't
   regenerate the leaderboard tonight unless you have API budget; the morning run replaces it.
3. Optional, for the sponsor slide: if any sim ran on Modal, record one timing (replicates, wall time)
   in bench/results/README.md or your PR. If it didn't, say so; the slide will not claim it.
Run make check, push strand/sim, and open a PR into main.
```
