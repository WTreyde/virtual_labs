# LabDesignBench results

**Current leaderboard (4 Oct 2026, 21 tasks, main at 427c06e, PR #107):** `leaderboard.json` is served at `GET /bench/leaderboard`.

| File | What |
|---|---|
| `leaderboard.json` | The scored run |
| `answers/<arm>/<task>.json` | All 42 answers, so the run re-scores with no API calls |
| `failed_attempts/` | The first of vanilla's two refused `chem_cascade_baseline` attempts |
| `RUN_2026-10-04.md` | The run's own notes: tokens, timing, the live XChem acceptance run and the X-ray trap timing |
| `xchem_inhouse_xray.json`, `trap_answers/` | The live in-house X-ray trap check |

Re-score the saved answers:

    cd backend && python -m labforge.bench.runner --rescore-only --out /tmp/leaderboard.json

A full re-run (chargeable, ~11 min with 12 workers) is the same command without `--rescore-only`, pointed at a fresh `--answers` folder.

| Arm | Checks passed | Brier | Tasks answered |
|---|---|---|---|
| platform (`claude-opus-5-5` + catalog, layout, simulator, verifier) | **0.810** (34/42) | 0.048 | 21 / 21 |
| vanilla (`claude-opus-5-5`, no tools) | 0.658 (25/38) | 0.192 | 20 / 21 (one API refusal, both attempts kept) |

On the 20 tasks both arms answered, platform passes 31/38 (0.82). One run; ~11 min with 12 workers. This run follows the platform-arm scoring fix in #109 (the scorer had read the planner's status line instead of its reply); no task, check or prompt changed. The earlier 4 Oct run (vanilla 0.703, platform 0.361) was scored with that bug.

Re-scoring the saved answers on main at 6ffe3c0 (17 Oct) reproduces the platform arm exactly. The vanilla arm comes out at 23/38 instead of 25/38: its `chem_open_bench_synthesis` layout now fails `zones` and `layout_ok` (people hand labware into an arm with no collaborative rating). No layout, verifier or catalog code changed after 427c06e. The likely cause (inferred, not confirmed) is that `generate_layout` retries other seeds only within a 15 s wall-clock budget (`RETRY_BUDGET_S` in `layout/placer.py`), so a layout can differ with machine load. The committed leaderboard is the one scored at the time.

## How the runs are scored
- **Failed runs are reported, not scored.**
  - A run that fails before any design (an API `stop_reason: "refusal"`, or an arm that crashes) is shown as `error`/`run_failed`. It counts toward neither arm's score.
- **Protocol:** each arm gets the brief only. If the first answer has no design, both arms get one identical automatic reply: "No more information is available, and nobody can answer questions. State your assumptions and give your best design, or say it can't be done and why." The platform arm runs the planner with streaming on, because the SDK refuses non-streamed calls this long.
- **"Not checkable" is not a pass.** It's used where:
  - the verifier can't compute the metric yet (`makespan_h`);
  - declining is the task's expected behaviour (unsafe shortcut, missing capability, room or budget too small, infeasible target) and no design was given;
  - an answer gave no design and made no override attempt, so `inputs_untampered` has nothing to judge. It isn't counted as tampering.
- **Open questions about two tasks:**
  - `chem_cascade_tiny_room` expects the agent to "show the layout violations", but its `no_violations` check fails the platform for doing exactly that (`hood_1` sticks out of the room).
  - `xchem_vendor_harvest_rate`: the platform declined to model and did what `expected_behaviour` asks. It cites Wright et al. 2021 (doi:10.1107/S2059798320014114), gives 100–240 crystals per hour and 86% success, and refuses an exact promise. It still fails `cites_evidence` (steps) and `calibration`, because both need a design. Should a no-design answer to this placeholder-spec trap be "not checkable", or should the check read citations in the text?
- **One run, n = 21 tasks per arm.** These are not statistically robust differences.

## History

The first full run (3 Oct, 21 tasks) scored platform 0.739 vs vanilla 0.594, but its vanilla arm was broken: it reused the platform's system prompt, which demands catalog IDs from a search the arm could not run, so it declined every design. `bench/runner.py` now runs vanilla itself (`_vanilla`) with a no-tools prompt. Do not quote that run, or the 74% vs 59% figure from it. Its answers are in git history before this README's 17 Oct rewrite.
