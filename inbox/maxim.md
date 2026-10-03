# Inbox: Maxim (Strand D: layout, sim, verifier, bench runner)

Last updated: 2026-10-03 17:40 BST by the integrator. Main at `9998609`.

The integrator rewrites this file on every integration pass (every 30 min until the 09:00 freeze on 4 Oct).
Work the open items top to bottom. Done items drop off once your merged work on main shows them done.
Don't edit this file; report progress in your PR description.

## Open items

```
Your #26 is merged: per-unit verifier, layout walkways, and the leaderboard with its description.
The Benchmark tab now shows platform 74% vs vanilla 56% of checks.
1. On the leaderboard, chem_cascade_baseline (the no-trap baseline) scores 0% for BOTH arms. Find out
   why: is it a real agent failure, a check that can't pass, or a scoring bug? Fix it if it's a bug. If
   it's real, keep it, and add a one-line note to the task's verifier output so the tab explains it.
   Don't re-run until it scores better.
2. Check that the leaderboard's "Run" timestamp and the arms' model are shown truthfully. If you re-run
   after a fix, commit the new JSON.
3. Layout: after your walkway fix, how many layout violations remain on the two demo designs (chem,
   fbdd)? Put the numbers in your PR description so the pitch can quote them.
Run make check, push strand/sim, and open a PR into main.
```
