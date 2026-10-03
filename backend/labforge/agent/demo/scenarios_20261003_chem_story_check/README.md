# Current-main chemistry story check — 3 October 2026

Recorded live with `claude-opus-5-5` from main `3d20f59` after the XChem replay
and per-unit verifier work merged. This is a fresh, chemistry-only run of the fixed
demo brief; no inputs, equipment counts, durations or simulator settings were tuned
to match the pitch.

The complete orchestration gate passed: catalog coverage, two reaction stages, flow
units, simulation, independent claim checks and report generation all completed.

## Result

- Planning throughput is P10/P50/P90 212.8/312.0/372.8 compounds/day.
- The independent verifier reports P50 320 compounds/day, 2.5% above the planning
  median. Both refute the 768 compounds/day target.
- `swing_1` and `swing_2`, both Chemspeed SWING XL reaction units, are the binding
  instruments at 99.8% calendar-time utilisation. They cap throughput near 313
  compounds/day.
- `lcms_1` and `lcms_2` are not binding: their utilisations are 35.2% and 24.4%.
- The demo pitch should therefore describe SWING XL reaction capacity as the limit
  for this recorded design, not LC-MS and not powder dosing. The dedicated Quantos
  powder doser is at 29.7% utilisation.

This is a model-based equipment-demand result, not evidence from an operated lab.
The run retains its refuted claims, layout qualifications, provisional timing and
evidence limitations. The acceptance gate demonstrates complete orchestration; it
does not make the physical design procurement-ready.

## Published assets

`frontend/scripts/copy_replays.py` copies `chemistry.json` to
`frontend/public/replays/chem.json`, including only the catalog records used by the
design and a simulator-recomputed animation timeline when the recording omitted one.
`labforge.agent.replay_summary` generates `chem.summary.json` from that same record.
The chemistry orchestrator sample is regenerated directly from the published replay.

Repeat the chargeable run with:

```bash
ANTHROPIC_MODEL=claude-opus-5-5 PYTHONPATH=backend .venv/bin/python \
  -m labforge.agent.demo_scenarios --env-file /absolute/path/to/.env \
  --scenario chemistry --live \
  --out backend/labforge/agent/demo/scenarios_20261003_chem_story_check
```
