# Repaired live demo gates — 3 October 2026

Recorded against main `a6657fc` (includes PRs #1, #11–#16), with this PR’s planner prompt/brief fixes. Main `440a9ff` (replay PR #17 and catalog PR #19) was subsequently merged without rerunning the model. The catalog now separates dry-shipper handling duration from `process.hold_time_s`, and marks puck capacity as a placeholder; our recorded workflow uses cryo-handling rather than the changed cold_storage process. Model: `claude-opus-5-5`. Amass was unconfigured; assumptions remain explicit estimates/placeholders.

Both `chemistry.json` and `xchem.json` contain real live-agent outputs, tool events, checked claims, reports and the simulator’s 500-event animation timeline. History and duplicated catalog specs are omitted. `summary.json` records the acceptance checks; no fixture was substituted for a live run.

| Scenario | Acceptance | Planning P50 | Independent P50 | Important limits |
|---|---|---|---|---|
| Chemistry | All gates pass, including two reactions and powder dosing | 632 compounds/day | 688 compounds/day | Target 768/day refuted; BOM $5,506,050 exceeds $2M; 11 layout violations. |
| XChem | All gates pass, including manual/semi-automated harvesting, external diffraction and manual puck loading | 362.7 crystals/day | 376 crystals/day | P50 difference 3.5%; BOM $1,245,930; 6 layout violations. Throughput consistency does not establish physical feasibility. |

## Refusal diagnosis and scope correction

The original run refused during workflow generation, after catalog/evidence tools returned. A reconstructed-context comparison reproduced refusal with the original system prompt and continued with tools under a planning-only prompt. However, a full run with the narrowed prompt and original named-reaction brief still refused. An abstract equipment-demand brief completed; making powder dosing explicit then passed the full chemistry gate.

A subsequent paired comparison held the system prompt and reconstructed tool context fixed and changed only the brief. Both wordings proposed workflows. Consequently there is **no proven deterministic word or individual tool-result trigger**. The provider exposes `stop_reason=refusal`, not its underlying rationale. `refusal_diagnostics.json` preserves these observations, including the contrary result. Diagnostic proposals were not executed and are not acceptance runs.

The fix removes unnecessary protocol narrative from the planner’s system context and chemical identities from the equipment-planning brief. It preserves the 8×12×8 library, both reaction stages, stock preparation, workup, purification, evaporation, QC and screening. It does not retry or disguise provider refusals; the planner still stops with a clear incomplete message, covered by a regression test.

## Puck handling and independent verification

XChem’s `load_shipper` is manual `cryo_cooling` on `ln2_dewar_2`, with role `crystallographer`, 180 s and an honest 120–600 s range. The dry shipper remains in equipment/BOM; the external `ship` step references it and retains courier transit and beamline queue time. Its 12.6-day cold-hold specification is represented as a container limit, not per-puck loading duration. No catalog duration restoration appears in the checked claims.

The gate additionally requires manual puck loading and independent P50 agreement within a declared 20% relative tolerance (different seeds/replicate counts). It does not overwrite planning results with verifier results. The old 10.5-versus-0.3 run fails these added checks.

Remaining physical-design follow-ups: layout/egress violations belong to Maxim; hotel crystallisation-plate compatibility and dry-shipper puck capacity need catalog confirmation from Max. Harvesting is recorded as semi-automated human work; setup-only operator accounting and unspecified external-service/container concurrency still limit physical interpretation of the throughput. These runs demonstrate orchestration and checked claims, not a procurement-ready lab.

## Roshan replay handoff

On the game/replay branch, copy these records using its existing script:

```bash
PYTHONPATH=backend .venv/bin/python frontend/scripts/copy_replays.py \
  backend/labforge/agent/demo/scenarios_20261003_repaired
```

The script supplies catalog entries and produces `public/replays/chem.json` and `fbdd.json` for `?replay=chem` / `?replay=fbdd`. No frontend files are changed by this PR.

Repeat the live gates (chargeable):

```bash
ANTHROPIC_MODEL=claude-opus-5-5 PYTHONPATH=backend .venv/bin/python \
  -m labforge.agent.demo_scenarios --env-file /absolute/path/to/.env \
  --out /tmp/labforge-repaired --live
```

## Pending verifier compatibility

A temporary merge of Maxim’s pending `886e2b8` guard failed its own
`test_storage_hold_time_is_not_restored_onto_a_loading_step`: the test looks for a
`cold_storage` duration above one day, but catalog PR #19 moved that value to
`process.hold_time_s`. It raises `StopIteration` before reaching the verifier.
Maxim should use a historical catalog fixture or the separate hold-time field in that
test. The merge was aborted; this PR’s merged-main `make check` passes.
