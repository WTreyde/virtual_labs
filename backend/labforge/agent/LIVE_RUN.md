# Agent setup and local demo

## Install

Run from a source checkout's repository root. Python 3.11+ and `uv` are required:

```bash
uv venv --python 3.11
uv pip install --python .venv/bin/python -e './backend[dev]'
cp .env.example .env
```

Copy the example only when `.env` does not already exist. With no `uv`, use
`python3 -m venv .venv` and `.venv/bin/python -m pip install -e './backend[dev]'`.
Keep the source checkout: the planner reads shared schemas, examples and pipeline documents.

## Configure Claude

Edit the repository-root `.env`:

```dotenv
ANTHROPIC_MODEL=claude-opus-5-5
ANTHROPIC_API_KEY=your-api-key
ANTHROPIC_WORKSPACE_ID=
```

Use an Anthropic API key, preferably scoped to your intended workspace. For an unscoped
key, set `ANTHROPIC_WORKSPACE_ID` to the workspace ID: the client sends the required
`anthropic-workspace-id` header. The account needs API access and sufficient billing credits.
The model can be overridden with a model ID available to your account. Amass credentials
are not required for the current two-tool planner; evidence retrieval is not wired in yet.

`.env` is Git-ignored. Do not commit credentials or paste them into chat. Keys remain on
the Python server, never in the browser. Shell environment variables take precedence.
Restart the server after editing credentials because loaded values remain in its environment.

## Start the test UI

```bash
PYTHONPATH=backend .venv/bin/python -m labforge.agent.test_ui
```

Open http://127.0.0.1:8011. Use `--port 8012` if that port is occupied.
For credentials in another checkout, explicitly select that file:

```bash
env -u ANTHROPIC_API_KEY -u ANTHROPIC_WORKSPACE_ID \
  PYTHONPATH=backend .venv/bin/python -m labforge.agent.test_ui \
  --env-file /absolute/path/to/virtual_labs/.env
```

This example clears shell overrides for key/workspace. No copying between checkouts is needed.
The workbench is a local debugging interface, separate from the team's main frontend.
It binds to loopback and requires a page-generated token for run requests.

## Try the decision loop

1. Select **Enzyme screening** and run the complete brief below.
2. Inspect catalog search, proposed workflow, validation errors and simulation events.
3. Ask: **Can this design reach 100 plates/day with the same room and budget? Evaluate before claiming success.**
4. Inspect whether the agent reruns the tools, identifies a bottleneck and qualifies infeasibility.
5. Use **New conversation** before testing a different scenario.

Complete starting brief:

> Design an enzyme-screening lab for 40 96-well plates/day, operating 24 hours/day in a 6 m by 4 m room, with a USD 400000 equipment budget. BSL1; no flammable solvents or cryogens. Dispense enzyme and substrate, seal, incubate at 37 C for one hour, then read absorbance at 405 nm. Use only catalog equipment. Label processing times as estimates and report simulation limitations.

Other useful prompts:

- I want an automated enzyme-screening lab. What information do you need before designing it?
- Which processing times are estimates, and what evidence would reduce their uncertainty?
- Add a second liquid handler if the catalog and remaining budget permit, then rerun and compare throughput.
- Can the catalog support LC-MS quality control? Disclose missing capabilities instead of inventing equipment.

The system prompt is visible in the UI. Tool events expose actions and inputs/results,
not private model reasoning. Tool events and assistant text stream as they occur; the final
response contains the full recommendation. The claims/report panel shows checked results. Follow-ups retain model/tool history. Offline fixture mode calls neither
Claude nor the simulator and must not be presented as a successful live run.

A design turn can return messages, LabSpec, Workflow, Layout, SimResult, claims, Brier score,
evidence searches, report_markdown, history, completed and verification_complete.
verification_complete means the requested classes of checks were submitted, not that
all claims were supported or that the design is feasible. A follow-up-question turn may return only text and history. A completed
turn is not necessarily a completed design. Simulation numbers are model-based estimates.

## CLI and checks

```bash
PYTHONPATH=backend .venv/bin/python -m labforge.agent.cli \
  --brief 'I want an enzyme-screening lab. What information do you need?' \
  > /tmp/labforge-session.json

PYTHONPATH=backend .venv/bin/python -m labforge.agent.cli \
  --session /tmp/labforge-session.json \
  --brief '40 plates/day; 6 m by 4 m room; USD 400000 budget; 24 hours/day; BSL1, no solvents.' \
  > /tmp/labforge-followup.json

PYTHONPATH=backend .venv/bin/python -m labforge.agent.cli --offline --brief demo
PYTHONPATH=backend .venv/bin/python -m unittest labforge.agent.test_first_layer labforge.agent.test_workbench labforge.agent.test_track
.venv/bin/python validate_examples.py
```

The CLI also accepts `--env-file /absolute/path/to/.env`. Exit codes: 0 = completed turn,
1 = failure, 2 = incomplete response/tool loop. Offline fixtures cannot be resumed as live sessions.

## Troubleshooting

| Symptom | Action |
|---|---|
| 401 / invalid API key | Check the exact `.env` path, copy the full active key, clear shell overrides, restart. Use `--env-file` when there are multiple checkouts. |
| Workspace header required | Use a workspace-scoped key or set `ANTHROPIC_WORKSPACE_ID`. |
| Missing dependency | Install the backend into the same `.venv` used to launch the server. |
| Model unavailable | Set `ANTHROPIC_MODEL` to a model your account can access, then restart. |
| Billing/rate limit | Check API credits/access; wait or reduce requests for rate limits. |
| No equipment matches | This is a catalog coverage gap; the planner should disclose it. |
| Tool validation error | The model can repair its proposal; persistent errors require checking shared contracts. |
| Port already in use | Stop the previous server or choose another `--port`. |

The UI includes redacted API error details. Never include keys in screenshots or bug reports.

## Implemented tools and team integration

| Tool | Responsibility |
|---|---|
| search_catalog | Equipment specs, sources, safety, estimates |
| layout_and_simulate | Contract/semantic checks, layout and 10 simulation replicates |
| search_evidence | Amass BiomedCore literature candidates with a 24-hour, credential-scoped cache |
| verify_claims | Backend-held throughput, layout and BOM consistency checks |
| create_report | Deterministic summary, BOM, checked claims, refutation history, assumptions and unknowns |
| optimise_instrument | Hypothetical cycle-time/capacity sweeps, elasticity, headroom and next bottleneck |

Amass is optional: set `AMASS_API_KEY` for read-only search. Endpoint and Bearer authentication
follow [Amass API docs](https://api.amass.tech/api/doc). No full texts are requested.
The cache defaults to `~/.cache/labforge/evidence`; set shell variable `LABFORGE_EVIDENCE_CACHE`
to choose another location. Unconfigured access, failed retrieval and empty results are
explicit. Retrieved papers are candidates, not automatic validation of duration/yield values.
Duration citations and workflow evidence must reference catalog/retrieved sources from the turn;
the model must still justify relevance. Unsupported durations remain estimates.

Verification accepts claims only. It uses the last backend-held design/results, ignoring
model-supplied statuses and observed values. For a previous turn, the proposal is recomputed
rather than trusting serialized simulator results. A revised design clears current checked claims; the audit retains historical checks. Additional
verification batches for one design preserve earlier claims and refutations. Per-step capacity
checks supply deterministic processing-time bounds and minimum parallel slots, rather than
relying on mental arithmetic. These bounds are optimistic and do not prove throughput.
Unknown equipment costs make BOM assertions unverifiable. Brier scores demonstrate model-based
consistency scoring; this small demo cannot establish calibration in actual laboratories.

For gateway streaming, the integrator can use:

```python
from fastapi.responses import StreamingResponse
from labforge.agent.streaming import stream_turn

# In a gateway route that already validates ChatRequest:
return StreamingResponse(stream_turn(req.messages), media_type="text/event-stream")
```

SSE frames are JSON `data:` events: model_call, text_delta, tool_start, tool_end,
tool_error, result or error, with keepalive comments. Preserve `result.output.history`
on the next request. The existing /chat route can still call run_turn synchronously.
A disconnect stops further calls at the next event boundary; an in-flight API call may finish.
No gateway/frontend/schema changes are included in this strand.

For Strand D's benchmark runner, import:

```python
from labforge.agent.benchmark import run_arm
answer = run_arm("platform", task)  # or "vanilla"
```

Both arms receive only task.brief, never hidden checks or trap labels. The vanilla arm
has no tools and cannot return trusted simulation/verification results. The scoring runner
must independently evaluate proposals; Strand D owns the checks and leaderboard wiring.

```bash
PYTHONPATH=backend .venv/bin/python -m labforge.agent.benchmark \
  --arm vanilla --task backend/labforge/bench/tasks/enzyme_infeasible.json
```

## Validation and remaining integration

Run all backend checks with live credentials explicitly disabled for offline tests:

```bash
env ANTHROPIC_API_KEY= AMASS_API_KEY= PYTHONPATH=backend \
  .venv/bin/python -m pytest backend/tests backend/labforge/agent/test_*.py -q
.venv/bin/python validate_examples.py
```

Tests cover model/tool orchestration, refutation and revision, history replay, secret redaction,
Amass envelopes and cache, the no-tools benchmark arm, streaming, unknown prices, and a real
simulator-to-verifier run. The live multi-turn gate passed on 2026-10-03; a condensed transcript is saved in
`demo/live_gate_20261003.json`. It demonstrates orchestration, not physical validation.

Team dependencies: chemistry/FBDD catalog coverage, simulator batch/fan-out/shift/external-step
semantics, gateway/frontend history and SSE wiring, and benchmark hidden checks/scoring.
A layout screenshot/PDF remains the frontend's responsibility. Review simulator limitations
before interpreting any complex workflow. Model-based checks do not validate a physical lab.

## Repeatable live gate

```bash
PYTHONPATH=backend .venv/bin/python -m labforge.agent.live_gate \
  --env-file /absolute/path/to/.env --out /tmp/labforge-live-gate
```

This makes chargeable Claude calls for a fixed baseline, an inflated target, one equipment
revision, and vendor sensitivity comparison. It writes each transcript/result before advancing,
then checks completion, refutation, unchanged assumptions and throughput improvement.
Use `--resume-baseline /path/to/baseline.json` to reuse an already completed baseline.
A passing gate demonstrates live orchestration under the model, not a buildable physical lab.
Layout violations must remain visible even when numerical throughput improves.

Max's validation runner now delegates to `labforge.agent.validation_cases.design_from_brief`.
Only case.brief is sent to Claude; reported costs, notes and sources are withheld. Missing
credentials, follow-up questions, unsupported catalogs or incomplete planning return no design,
not a fixture or invented estimate. The current seed briefs omit essential requirements and
still require catalog expansion and source verification before headline cost validation.

The workbench and game gateway load code once at startup. Restart both after updating the
branch. For a separate gateway port, use frontend environment `VITE_API=http://127.0.0.1:8001`.

The saved gate produced 47.0 plates/day at baseline and refuted the unchanged design's
100-plate target. Adding a second handler improved P50 to 93.3 but still missed the target
and introduced a layout overlap. Both vendor sweeps ran without changing the design.
Cycle-time sweeps scale entire workflow steps, including all parallel candidates; capacity
sweeps change only the selected instance. Tool metadata and prompts disclose this distinction.
The saved vendor response predates that disclosure; interpret its handler gains as step-wide.
The sensitivity baseline uses 48 hours and 8 replicates, so it differs from the main simulation.
Amass was unconfigured in this run; all duration estimates remain explicitly unvalidated.

## Project scheduling

`plan_projects(lab_spec, projects)` wraps `labforge.sim.portfolio.prioritise`. Every project
has an ID, a validated Workflow on the shared lab, a positive integer `units` count of
workflow labware units, and optional positive `weight` and nonnegative `deadline_h`.
Shared equipment IDs must identify the same catalog item in all projects. The interactive
tool supports up to six projects and 1000 total units; batch_size and fan_out must be 1.
The returned `project_schedule` validates against the shared schema and is exposed in
the planner response. Scheduling leaves the current design and checked claims unchanged.
This compares mean-duration release policies; it omits transfers, operator shifts and
stochastic failures. Monte Carlo confirmation remains Strand D's responsibility.

## Chemistry and XChem acceptance

```bash
ANTHROPIC_MODEL=claude-opus-5-5 PYTHONPATH=backend .venv/bin/python \
  -m labforge.agent.demo_scenarios --env-file /absolute/path/to/.env \
  --out /tmp/labforge-scenarios --live
```

Omit `--live` for catalog coverage only. Live mode makes chargeable calls for both full
demo briefs and stores credential-redacted results without model/tool history. Success
requires the complete pipeline, simulation, checked claims and report. XChem must retain
manual harvesting, external diffraction and no in-house X-ray equipment. A catalog-blocked
response is saved but does not pass the end-to-end gate; exit status 2 signals unmet gates.

On main `3535097`, both live Opus scenario attempts completed but stopped on missing
catalog entries; neither returned a full design, simulation or checked report. Saved results
are in `demo/scenarios_20261003/`. Missing equipment is assigned to Max in
[issue #9](https://github.com/WTreyde/virtual_labs/issues/9). Rerun after catalog expansion.
External/in-silico steps do not require local catalog instruments; the XChem response's
suggestion of a service catalog entry is optional, not a prerequisite. The prompt now makes
that distinction explicit. No in-house diffraction item is required or permitted in this demo.

## Combined-main integration (3 Oct)

The planner passes the backend-held LabSpec to the new independent verifier. Non-plate
workflows need exactly one terminal counting step with positive `params.units_per_labware`.
The sink must have no successor; a counter on the assay readout is insufficient when storage
or hit analysis follows it. Legacy simulator limitations keep throughput unverifiable.

Backend output contract errors stop the loop with `stop_reason=backend_contract_error` and
retain `failed_proposal` for the owning strand; the model is not asked to redesign around a
backend/schema defect. The shared layout schema accepts the catalog's vibration_free zones.
The game retains full model/tool history and uses the checked planner report. Gateway
`POST /chat/stream` exposes the existing SSE adapter; the game still uses synchronous chat.

The demo runner supports `--scenario chemistry` or `--scenario xchem`, writes events as they
arrive, and records the API stop reason. Gate success means complete orchestration and
checked model claims, not that the target, budget or physical layout are feasible. Inspect
refuted claims and layout violations separately. Missing evidence remains an explicit estimate.

## Repaired demo replay (3 Oct)

`demo/scenarios_20261003_repaired/` contains successful live chemistry and XChem orchestration
gates, checked reports and animation timelines. Chemistry’s brief is an abstract equipment-demand
request, with both reaction stages and powder dosing explicit; the system uses planning templates
rather than detailed protocol narratives. Refusals remain terminal, clear incomplete results.
Controlled comparisons do not establish a deterministic word-level refusal trigger.

Puck loading is operator-attended handling (`manual_bench` or `cryo_cooling`), while the dry
shipper remains a storage/transit container with external shipping/queue assumptions. XChem’s
gate rejects storage-as-loading and independent P50 gaps above 20%. The recorded planning
P50 362.7 and independent 376 crystals/day differ by 3.5%, with no catalog duration restoration.
Both recordings retain refuted feasibility claims and layout issues; passing gates means
complete orchestration, not a procurement-ready design. See the recordings’ README for Roshan’s
replay-copy command, metrics, diagnostic limits and owning-strand follow-ups.

## Per-unit catalog times and landing summaries

Catalog `process.duration_basis` is a capability-to-unit map. The Shifter now gives
`durations_s.crystal_harvesting = 35` and `duration_basis.crystal_harvesting = "crystal"`.
Workflow durations still describe one processing run: declare numeric
`params.units_per_run` (mount attempts), multiply per-crystal time and uncertainty
bounds by the count, and distinguish attempts from successful output. For 32 attempts,
the mean is 1120 seconds, not 35 seconds per plate. Planner validation requires an
explicit count and rejects durations below the scaled catalog floor. The independent
verifier owns checking that the count also agrees with downstream output/fan-out.

The landing assets `frontend/public/replays/{chem,fbdd}.summary.json` report the exact
recorded planning P10/P50/P90, independent P50, busiest instrument, checked BOM versus
budget and refuted claims. They do not recompute an old replay against a new catalog.
After copying a new replay, regenerate both summaries with:

```bash
PYTHONPATH=backend .venv/bin/python -m labforge.agent.replay_summary frontend/public/replays
```

Fresh XChem recording is blocked until verifier PR #26 merges. Until then the published
FBDD summary explicitly retains the historical 312 versus 112 disagreement. Hotel
what-if PR #23 remains a separate follow-up; do not replace the baseline with a remedy.

Compatibility check against pending #26 (`9dabf23`) after the per-crystal catalog update:
`test_duration_floor_is_compared_per_unit_not_per_plate` fails because it still expects
`7200 * 32 / 96`, while the catalog now gives 35 seconds per crystal. Its
`catalog_units` helper does not yet read `process.duration_basis`, so it infers 96
from the plate instead of one crystal. Maxim owns updating that conversion and test:
for 32 attempts, mean is 1120 seconds and the catalog low is 15 * 32 = 480 seconds;
a 300-second proposal should be restored on that basis. The temporary merge was
aborted; this PR does not modify verifier code or pretend that compatibility passes.
