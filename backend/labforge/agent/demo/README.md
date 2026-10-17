# Recorded agent runs

Live `claude-opus-5-5` recordings and deterministic re-runs from 3–4 October 2026. They are kept as the evidence behind the numbers the app and README quote, so they are never edited after recording. Each folder's own README (where there is one) says how it was made; those notes are a log written at the time, so their follow-ups and names refer to the hackathon team and are not open tasks.

## Used by the app today

| Folder | What it is | Used by |
|---|---|---|
| `scenarios_20261003_chem_story_check/` | Chemistry replay: the agent's 768/day within $2M claims, both refuted by the verifier | `frontend/public/replays/chem.json` |
| `scenarios_20261004_resim50/` | XChem replay: the `scenarios_20261004_placer` design re-simulated at 50 replicates | `frontend/public/replays/fbdd.json` |
| `scenarios_20261004_staffing_whatifs/` | Verifier what-ifs on that design: imager growth, a third operator, a second shift | `replay_summary.py`, the XChem case page |
| `scenarios_20261004_placer/` | The live XChem recording the 50-replicate replay re-simulates, plus its imager what-if | `test_replay_resim.py` |
| `scenarios_20261003_harvesting/`, `scenarios_20261003_combined_main/` | Earlier recordings that tests and scripts still read | `test_duration_basis.py`, `test_hotel_whatif.py`, `test_demo_repair.py`, `replay_summary.py`, `copy_replays.py` |

## History only

| Folder | What it shows |
|---|---|
| `live_gate_20261003.json` | The first passing multi-turn live gate (condensed transcript) |
| `scenarios_20261003/`, `pr12_20261003/`, `scenarios_20261003_repaired/`, `scenarios_20261003_post_pr26/` | Earlier chemistry and XChem recordings, superseded by the replays above |
| `scenarios_20261004_neutral_chem/` | A check whether neutral wording avoids the chemistry provider refusal |
| `scenarios_20261004_final_live/` | The final live XChem run: planned 382.7/day, verified 0/day, gate failed. This is why the XChem demo is shown from the replay |
| `trap_timing_20261004/` | Timing of the live in-house X-ray trap brief (the agent declines) |
