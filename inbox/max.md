# Inbox: Max (Strand B: catalog, safety, bench tasks, validation)

Last updated: 2026-10-03 18:05 BST by the integrator. Main at `37035bf`.

The integrator rewrites this file on every integration pass (every 30 min until the 09:00 freeze on 4 Oct).
Work the open items top to bottom. Done items drop off once your merged work on main shows them done.
Don't edit this file; report progress in your PR description.

## Open items

```
Your #37 is merged (operators, safety rules, 21 bench tasks, blind out-of-sample validation 4/6 in band).
1. The XChem bottleneck is now a LiCONiC STX44 used as the growth/soak hotel (44 slots, 85% busy), and
   its fix is a second STX44. Confirm from the vendor spec whether the STX44 holds crystallisation plates
   (SBS SD-2 or MRC) at 20 C and its plate capacity, and how long a load/unload takes. Source each value
   and mark the confidence honestly. If it can't hold them, say so; that changes the demo story.
2. Dry shipper puck capacity: replace the 3-puck placeholder with the vendor figure, if one is published.
3. Low priority, pitch support: a list of vendors that publicly back a lab hardware standard, each with
   a verified source link. Put it in your PR description; ask the integrator before adding a schema field.
Run make check, push strand/catalog, and open a PR into main.
```
