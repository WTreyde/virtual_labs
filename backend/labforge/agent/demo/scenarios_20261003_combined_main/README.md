# Combined-main live gate, 3 October 2026

Based on main with PRs #1, #11 and #12 plus this PR's schema, planner and integration fixes. Model: `claude-opus-5-5`. Amass was unavailable; duration and yield assumptions remain estimates.

| Scenario | Result | Details / owner |
|---|---|---|
| Chemistry | Gate fails | Catalog coverage is complete, but the provider returned `stop_reason=refusal` before emitting a workflow. No specific missing capability, labware or field was identified. Albert/API integration must resolve this; do not assign a fabricated catalog gap to Max. |
| XChem | All orchestration gates pass | Full workflow, checked claims and report; manual harvesting, external diffraction and no in-house X-ray. The 300-crystal/day target is refuted. |

XChem's planning P50 is 10.5 crystals/day; the independent verifier observes 0.3 after restoring the catalog duration for `load_shipper`. BOM is $951,626 and layout violations are zero. This is not a validated physical design. Albert should review the handling-versus-storage capability chosen for that step; Max/Maxim should review the applicable catalog duration and restoration rule. The report now calls out verifier/planning disagreements explicitly.

Shared blockers fixed in this PR:
- Integrator: `vibration_free` was emitted by the layout engine but absent from the layout schema; the enum now includes it.
- Albert/Maxim: pass the backend-held LabSpec into independent verification; require terminal output-unit conversion for compounds/crystals.
- Roshan: preserve full model/tool history, retain checked reports and show API errors in the game; prevent overlapping chat submissions.
- Integrator/Roshan: `POST /chat/stream` now exposes the existing SSE adapter. The current game still uses synchronous chat; streaming consumption is optional follow-up work.

`summary.json` contains the exact gates. Raw recommendations and checked reports are in the scenario JSON files. Catalog specs are omitted from tool-end events to keep these traces compact; proposals and source references remain. Provider refusals and failed gates are preserved.

Repeat from the repository root (chargeable):

```bash
ANTHROPIC_MODEL=claude-opus-5-5 PYTHONPATH=backend .venv/bin/python \
  -m labforge.agent.demo_scenarios --env-file /absolute/path/to/.env \
  --out /tmp/labforge-combined-main --live
```
