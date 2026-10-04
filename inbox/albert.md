# Inbox: Albert (Strand C: agent and Amass)

Last updated: 2026-10-04 05:00 BST by the integrator. Main at `c03e671` (plus this inbox commit).

The integrator rewrites this file on every integration pass (every 30 min until the 09:00 freeze on 4 Oct).
Work the open items top to bottom. Done items drop off once your merged work on main shows them done.
Don't edit this file; report progress in your PR description.

## Open items

```
Your #58 (fresh XChem replay: 411 planned / 424 verified per day, $1.07M, 0 violations, STX44 82.6%
binding), #60 (honest gate) and #76 (live trap: declined in 17.7 s, so it can run live) are merged. Thanks for not retrying until something passed.
Your #67, #71, #73, #79 (50-replicate gate) #83 (XChem replay re-simulated at 50: 410.7 planned /
424 verified, gate passes, both operators listed) and #85 (staffing what-ifs: 634.7 and
1306.7/day) are merged. Thanks.
7. Top priority, blocks Roshan: test_fbdd_summary_reports_the_separate_imager_growth_whatif fails
   when fbdd.json is the #83 resim50 recording, because _load_imager_whatif finds no
   xchem-imager-whatif.json beside it (see Roshan's #86). Default fix: have replay_summary load the
   50-replicate staffing what-ifs from #85 for the resim50 recording (plus the imager-only what-if, if
   you re-run it at 50 replicates), and update the test to match. Then hand Roshan a regenerated
   fbdd.summary.json. Keep the 10-replicate imager-only what-if out of the shipped summary.
8. Say in the summary which change does the work: the variants move growth to the imager AND add
   staff, so the gain can't be credited to either alone. If cheap, add a third-operator-only variant
   (growth stays in the hotel) at 50 replicates so the pitch can tell them apart.
Run make check, push, and open a PR into main.
```
