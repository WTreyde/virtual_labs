# Strand D: layout engine, Monte Carlo simulator, verifier, bench scoring (Maxim)

**Owns:** `backend/labforge/layout/`, `sim/`, `verify/`, `bench/runner.py`. **Produces:** `Layout`, `SimResult`, verified `Claim`s, bench scores.

Already working: ring placement around one arm with operator fallback; overlap/out-of-room/unreachable checks; SimPy Monte Carlo with P10/P50/P90, utilisation and bottlenecks; claim verification and Brier score.

## Tasks, in order
1. Simulator realism needed by the demo pipelines: `batch_size` (evaporator, centrifuge), `fan_out` (library split into many plates), operators with shift hours doing manual steps, external steps with queue time (synchrotron), in-silico steps.
2. Placement for many instruments: cluster equipment by transfer frequency around each transporter, multiple arms/rails, mobile robot or human links between clusters; then simulated annealing on weighted transfer distance; respect `locked` placements.
3. Safety validator from `catalog/data/safety_rules.json`: zones (fume hood, BSL2, cryogen), clearances, walkways, egress; emit `violations`.
4. Sensitivity analysis: which uncertain durations move throughput most; fill `SimResult.sensitivity`.
5. Run Monte Carlo replicates and bench tasks in parallel on Modal.
6. Verifier: tamper detection (hash simulator inputs and catalog values the agent is not allowed to change), more metrics, per-task checks in `bench/runner.py` (`admits_infeasible`, `claim_matches_sim`, `inputs_untampered`, `calibration`, ...). Output a leaderboard JSON for Roshan.
