# Inbox: Max (Strand B: catalog, safety, bench tasks, validation)

Last updated: 2026-10-03 17:20 BST by the integrator. Main at `087d2af`.

The integrator rewrites this file on every integration pass (every 30 min until the 09:00 freeze on 4 Oct).
Work the open items top to bottom. Done items drop off once your merged work on main shows them done.
Don't edit this file; report progress in your PR description.

## Open items

```
Your #24 is merged (it closes the harvesting-duration item). Two quick confirmations for the
new Schedule and Validation tabs:
1. POST catalog/data/demo_prioritise_queue.json to /prioritise on main. Check that the
   recommended order still beats the given order, and that the urgent re-test still meets its
   8 h deadline after today's catalog changes.
2. Check that the /validation text still matches the data (cases compared, in band). After #21
   the chart says "1 of 7 in band"; make sure docs/validation.md and slide 6 say the same.
Fix whatever is off, run make check, push, and open a PR into main.

After the items above (low priority, pitch support):
3. Draft a list of vendors that publicly back a lab hardware standard (e.g. Tecan, Danaher, QIAGEN,
   Universal Robots, per the reading-list thread), each with a source link. Verify each one; don't guess.
   Put it in your PR description first. Tagging the catalog needs an optional schema field, so ask the
   integrator before adding one.
```
