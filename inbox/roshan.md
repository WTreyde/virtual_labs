# Inbox: Roshan (Strand A: game client and report)

Last updated: 2026-10-03 18:05 BST by the integrator. Main at `37035bf`.

The integrator rewrites this file on every integration pass (every 30 min until the 09:00 freeze on 4 Oct).
Work the open items top to bottom. Done items drop off once your merged work on main shows them done.
Don't edit this file; report progress in your PR description.

## Open items

```
Pull main (Albert's new fbdd.json, summary and what-if are merged).
1. Case pages (#/case/fbdd and #/case/chem, 1600x900): while the replay runs, the right-hand panel's
   agent log overlaps itself (lines are drawn on top of each other, and "Bill of materials" collides
   with the next line). Give the log its own scrolling box with normal line-height.
2. Honesty on the landing cards: show the independent check next to the headline (XChem is now
   "124/day planned, 172/day independently checked") from *.summary.json (verified_p50, gate_passed,
   limits), never hard-coded.
3. XChem case page: show "The fix" from Albert's remedy record
   (backend/labforge/agent/demo/scenarios_20261003_post_pr26/xchem-whatif.json, summarised in its
   README): adding a second LiCONiC STX44 hotel (+$40,000) raises throughput from 124 to 193/day planned
   (172 to 248/day checked). Copy the numbers into a small static JSON in public/replays/ (e.g.
   fbdd.remedy.json) rather than loading the full backend record.
4. Public demo mode: read GET /health `live_chat`. When it's false (the public Hugging Face Space), the
   "Design your own" card and #/design should say "Live design is off in this public demo" instead of
   showing a chat box that errors.
5. frontend/scripts/cache_offline.py fails with KeyError: output on the new *.summary.json files.
   Make it skip them.
6. #/schedule: the x-axis title and the "urgent_retest deadline 8 h" label overlap.
7. A "Download agent skill" button next to "Report for your boss", saving SKILL.md and tools.json from
   backend/labforge/orchestrator/samples/<case>/ (copy them into public/ for offline use).
Run make check and npm run check:replays, then push and open a PR into main.
```
