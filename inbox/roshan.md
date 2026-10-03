# Inbox: Roshan (Strand A: game client and report)

Last updated: 2026-10-03 18:45 BST by the integrator. Main at `1fef7ae` (plus this inbox commit).

The integrator rewrites this file on every integration pass (every 30 min until the 09:00 freeze on 4 Oct).
Work the open items top to bottom. Done items drop off once your merged work on main shows them done.
Don't edit this file; report progress in your PR description.

## Open items

```
Your #39 items 1-2 are merged (panel and honesty). Thanks.
User decision (3 Oct 18:33): on the XChem page, the fix is no longer "add a second hotel". The pitch says
the twin caught the planner leaving the 1,000-slot Rock Imager at 4% busy while the 44-slot hotel is at
85%, and that growing plates in the imager costs $0. The demo driver clicks the hotel, then the imager.
1. Replaces old item 3. On #/case/fbdd:
   - The imager's stat card must show its utilisation prominently (e.g. "Rock Imager: 4% busy,
     1,000 plate slots") next to the hotel's 85%, read from the replay data, not hard-coded.
   - "The fix" card: don't present the second hotel as the fix. Show the imager option. Once Albert's
     imager what-if lands, show it from fbdd.summary.json key "imager_growth_whatif" (planned and
     verified throughput). Until then show it as "not yet simulated", without numbers.
2. Public demo mode: read GET /health `live_chat`. When it's false, the "Design your own" card and
   #/design say "Live design is off in this public demo" instead of a chat box that errors.
3. frontend/scripts/cache_offline.py fails with KeyError: output on *.summary.json. Skip those files.
4. #/schedule: the x-axis title and the "urgent_retest deadline 8 h" label overlap.
5. A "Download agent skill" button next to "Report for your boss" (SKILL.md and tools.json from
   backend/labforge/orchestrator/samples/<case>/, copied into public/ for offline use).
6. Bench tab (from Maxim's #38): show arm.model on each tile; when generated_at is missing, show
   "Answers recorded before <run.answered_before>; scored <scored_at>"; tasks with run_failed show as
   "not run". Add runs_failed?, model?, scored_at? and run? to the Leaderboard type.
7. Validation tab (from Max's #42): show the band; label the confidence score "experimental" (it
   doesn't yet beat a constant baseline). Show not_costable cases as such, not as $0.
Run make check and npm run check:replays, then push and open a PR into main.
```
