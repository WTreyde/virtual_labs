# XChem replay: deterministic 50-replicate refresh

This refresh makes no agent or external API call. It reruns the exact recorded
LabSpec, workflow and layout from `scenarios_20261004_placer/xchem.json` with
seed 0 and 50 Monte Carlo replicates, then regenerates the deterministic report
and current scenario gate.

## Result

- Planning P10/P50/P90: **336.0 / 410.7 / 522.7 crystals/day**.
- Probability of meeting the 300/day model target: **0.94**.
- Independent verifier P50 retained from the checked claims: **424.0/day**.
- Planner/verifier relative difference: **3.1%**, within the 20% gate limit.
- The gate passes its new explicit 50-replicate sample-size requirement.
- The STX44 growth hotel remains the busiest instrument at **82.4%**.
- Both operators are reported separately at **72.9%** and **72.3%** of shift.

The resimulation audit in `xchem.json` confirms that LabSpec, workflow and
layout are unchanged. The original live answer remains in the message history;
the final message clearly labels the deterministic refresh.

## Frontend-owner handoff

`fbdd.summary.json` is the regenerated baseline-only landing summary. The
frontend owner can copy `xchem.json` to `frontend/public/replays/fbdd.json` and
the summary beside it. This Strand C change deliberately does not edit
`frontend/`, which is owned by Strand A. The old imager what-if is omitted from
this summary until the requested 50-replicate staffing what-ifs are recorded.
