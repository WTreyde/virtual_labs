# Live evaluation results — 4 October 2026

These artifacts were generated from `main` at `a383d79` using `claude-opus-5-5`.
They replace the obsolete 74% versus 59% comparison, whose vanilla arm was broken.

## Corrected LabDesignBench

Command, run from `backend/`:

```bash
python -m labforge.bench.runner --arms platform vanilla --out bench_results/leaderboard.json
```

- Vanilla: 0.703 (26/37 checkable checks), Brier 0.155, 20/21 tasks answered, one run failure.
- Platform: 0.361 (13/36 checkable checks), Brier 0.068, 21/21 tasks answered, no run failures.

The command did not specify `--answers`, so raw per-task benchmark answers were not persisted.
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
