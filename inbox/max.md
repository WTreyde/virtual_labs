# Inbox: Max (Strand B: catalog, safety, bench tasks, validation)

Last updated: 2026-10-03 18:45 BST by the integrator. Main at `1fef7ae` (plus this inbox commit).

The integrator rewrites this file on every integration pass (every 30 min until the 09:00 freeze on 4 Oct).
Work the open items top to bottom. Done items drop off once your merged work on main shows them done.
Don't edit this file; report progress in your PR description.

## Open items

```
Your #42 is merged (79 items, second blind round, STX44 variants, 7-puck cane, standards list).
Note: the integrator added process.temperature_c and process.access_time_s to the catalog schema as
optional fields, so your STX44 entry is now documented.
1. The XChem pitch now says the fix is growing plates in the Rock Imager 1000 (1,000 slots) instead
   of the STX44 hotel. Confirm from Formulatrix's spec that the Rock Imager holds crystallisation plates
   for growth at a controlled temperature (which: 4 C and/or 20 C), its plate capacity, and whether
   plates incubate there between inspections. Source each value and mark the confidence honestly. If
   it's wrong, say so in your PR, because the pitch depends on it.
2. Your note says LiCONiC recommends its STR44 (stationary cassettes) for protein crystallisation. If
   that's a cheap catalog addition with a sourced price, add it so the agent can choose it.
Run make check, push strand/catalog, and open a PR into main.
```
