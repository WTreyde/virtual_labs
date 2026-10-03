# Inbox: Max (Strand B: catalog, safety, bench tasks, validation)

Last updated: 2026-10-03 17:40 BST by the integrator. Main at `9998609`.

The integrator rewrites this file on every integration pass (every 30 min until the 09:00 freeze on 4 Oct).
Work the open items top to bottom. Done items drop off once your merged work on main shows them done.
Don't edit this file; report progress in your PR description.

## Open items

```
Your #30 is merged (evidence-aware confidence and calibration, plus the schedule/validation checks).
1. The XChem bottleneck is now the Cytomat 2 growth hotel. Confirm from the vendor spec that it holds
   crystallisation plates (SBS SD-2 or MRC) at 20 C, how many plates it holds, and how long an
   inspection-cycle load/unload takes. The 80% busy figure depends on these numbers. Source each value
   and mark its confidence honestly.
2. Dry shipper puck capacity: replace the 3-puck placeholder with the vendor figure, if one is published.
3. Low priority, pitch support: a list of vendors that publicly back a lab hardware standard (e.g. Tecan,
   Danaher, QIAGEN, Universal Robots), each with a source link. Verify each one and don't guess. Put the
   list in your PR description; ask the integrator before adding a schema field to tag them.
Run make check, push strand/catalog, and open a PR into main.
```
