# Inbox: Maxim (Strand D: layout, sim, verifier, bench runner)

Last updated: 2026-10-04 00:05 BST by the integrator. Main at `4362f3b` (plus this inbox commit).

The integrator rewrites this file on every integration pass (every 30 min until the 09:00 freeze on 4 Oct).
Work the open items top to bottom. Done items drop off once your merged work on main shows them done.
Don't edit this file; report progress in your PR description.

## Open items

```
Your #53 is merged (lab-like layouts, break area, collision count fix). Albert is re-recording the
case replays so the demo shows it.
1. The integrator added "break_area" to the zone kind enum in schemas/layout.schema.json (optional, as
   you asked). Switch your break area to kind "break_area" (keep id and label).
2. From the critic: the vanilla arm produced 0 designs on all 21 tasks. Check whether the vanilla
   prompt or parser makes a design impossible (e.g. it asks for a format the reply never matches, or
   drops a design embedded in prose). If the runner is at fault, fix it now so the morning re-run is a
   fair comparison, and say in your PR what changed. If vanilla genuinely never designs, say so.
Run make check, push strand/sim, and open a PR into main.
```
