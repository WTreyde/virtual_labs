# Inbox: Roshan (Strand A: game client and report)

Last updated: 2026-10-03 17:40 BST by the integrator. Main at `9998609`.

The integrator rewrites this file on every integration pass (every 30 min until the 09:00 freeze on 4 Oct).
Work the open items top to bottom. Done items drop off once your merged work on main shows them done.
Don't edit this file; report progress in your PR description.

## Open items

```
Pull main (your #33 app shell is merged; the integrator checked all 7 routes under make demo with no errors).
1. Case pages (#/case/fbdd and #/case/chem, 1600x900): while the replay runs, the right-hand panel's
   agent log overlaps itself ("camera capacity and per-inspection duration..." lines are drawn on top of
   each other, and "Bill of materials" collides with the next line). Give the log its own scrolling box
   with normal line-height. See labforge/screenshots/9-fbdd-case-panel.png in the project files.
2. Honesty on the landing card: the XChem card shows 312 crystals/day, but fbdd.summary.json also has
   verified_p50 = 112 and gate_passed = false. Show the independent check next to the headline (e.g.
   "312/day planned · 112/day independently checked") and the limits on the case page. Same for chem.
   Albert will replace fbdd.json with a new recording, so read the numbers from the summary file, never
   hard-code them.
3. #/schedule: the x-axis title "hours from start, recommended order" and the "urgent_retest deadline 8 h"
   label overlap. Move the deadline label to the top of its line.
4. A "Download agent skill" button next to "Report for your boss". It saves SKILL.md and tools.json for
   the current case from backend/labforge/orchestrator/samples/<case>/ (copy them into public/ for
   offline use), and from the gateway once the integrator adds a route.
Run make check and npm run check:replays, then push and open a PR into main.
```
