# Inbox: Maxim (Strand D: layout, sim, verifier, bench runner)

Last updated: 2026-10-04 05:30 BST by the integrator. Main at `e4e6ea8` (plus this inbox commit).

The integrator rewrites this file on every integration pass (every 30 min until the 09:00 freeze on 4 Oct).
Work the open items top to bottom. Done items drop off once your merged work on main shows them done.
Don't edit this file; report progress in your PR description.

## Open items

```
Your #61 is merged (imager storage slots, one-command bench re-run, honest Modal status). Thanks.
(This file was blank on main from 01:30 to 05:30 by an integrator error; sorry.)
1. Optional, only if safe before the 09:00 freeze: the XChem sim gives shipping-to-diffraction
   unlimited capacity, so the verified 635/day (imager growth + third operator, #85) never meets a
   beamtime limit. docs/pipelines.md:55 gives 1-5 min per crystal, which is 11-53 h of beam per
   day at that rate. Add an optional synchrotron beamtime cap (hours per day or per visit, confidence
   "estimated") to the sim/verifier with a test. Leave default behaviour unchanged unless the cap
   is set, so the recorded replays don't move. If it isn't merged by 09:00, it stays a known
   limitation (the pitch already says "assumes beamtime keeps up").
The 08:05 checklist runs your morning bench command.
```
