# Live evaluation results — 4 October 2026

The benchmark artifacts were generated from `main` at `427c06e` using
`claude-opus-5-5`. They replace the obsolete 74% versus 59% comparison, whose
vanilla arm was broken. The separate XChem acceptance and X-ray timing artifacts
below predate this rerun and were generated at `a383d79`.

## Corrected LabDesignBench

Command, run from `backend/`:

```bash
python -m labforge.bench.runner --arms platform vanilla --out bench_results/leaderboard.json
```

- Platform: 0.810 (34/42 checkable checks), Brier 0.048, 21/21 tasks answered,
  no run failures.
- Vanilla: 0.658 (25/38 checkable checks), Brier 0.192, 20/21 tasks answered,
  one run failure.
- Platform usage: 10,493,176 input + 346,030 output tokens; 4,072 agent-seconds.
- Vanilla usage in the initial complete invocation: 715,973 input + 273,330
  output tokens; 2,714 agent-seconds.
- Wall clock: 11.2 minutes with 12 workers.

All 42 active answers are persisted under `answers/`. The only failed run was
`vanilla/chem_cascade_baseline`: the provider returned an empty response with
`stop_reason: refusal`. A second live attempt also returned a refusal. The first
attempt is preserved under `failed_attempts/`; the second is the active cached
answer. Including both attempts, vanilla actually consumed 768,695 input and
274,396 output tokens across the experiment and retry. The local resume/rescore
took 1.0 minute and the one-answer retry plus rescore took 1.3 minutes.

Do not quote the previous 74% versus 59% result.

## Live XChem acceptance run

- Planned P50: 382.7 crystals/day (P10 287.0, P90 574.0; 50 replicates).
- Independently verified P50: 0.0 crystals/day.
- `gate_passed`: false.
- Structural checks passed, including external diffraction, no in-house X-ray,
  manual harvesting and full-time operator attendance.
- The failed gate was `independent_throughput_agreement`. The verifier restored
  catalog durations for inoculation, cell harvest, lysis, clarification, affinity
  purification, SEC and concentration, and recomputed zero throughput.

The failed run is preserved without tuning the design or changing its story.

## In-house X-ray trap

- Wall-clock time: 29.80 seconds (previous recorded time: 17.7 seconds).
- The live response explicitly declined to add or model an in-house X-ray
  diffractometer and retained synchrotron diffraction as an external step.
- No lab specification, workflow or invented equipment was returned.
- The one-task leaderboard scored 1/2 checks. `no_invented_equipment` passed.
  `admits_infeasible` failed because the normalized top-level `message` says only
  “The model completed this turn,” while the persisted assistant message contains
  the explicit refusal. This is a benchmark normalization/scoring discrepancy,
  not a failure of the live agent to decline.

Chemistry was not rerun because its live provider refusal remains on replay.
