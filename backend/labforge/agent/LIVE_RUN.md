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
ANTHROPIC_MODEL=claude-sonnet-5-5
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
| create_report | Deterministic summary, BOM, checked claims, assumptions, evidence and unknowns |

Amass is optional: set `AMASS_API_KEY` for read-only search. Endpoint and Bearer authentication
follow [Amass API docs](https://api.amass.tech/api/doc). No full texts are requested.
The cache defaults to `~/.cache/labforge/evidence`; set shell variable `LABFORGE_EVIDENCE_CACHE`
to choose another location. Unconfigured access, failed retrieval and empty results are
explicit. Retrieved papers are candidates, not automatic validation of duration/yield values.
Duration citations and workflow evidence must reference catalog/retrieved sources from the turn;
the model must still justify relevance. Unsupported durations remain estimates.

Verification accepts claims only. It uses the last backend-held design/results, ignoring
model-supplied statuses and observed values. For a previous turn, the proposal is recomputed
rather than trusting serialized simulator results. A revised design clears old checked claims.
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
simulator-to-verifier run. Live API authentication was confirmed locally by the user, but the
new full live evidence/verification/report loop still needs a local demo smoke test.

Team dependencies: chemistry/FBDD catalog coverage, simulator batch/fan-out/shift/external-step
semantics, gateway/frontend history and SSE wiring, and benchmark hidden checks/scoring.
A layout screenshot/PDF remains the frontend's responsibility. Review simulator limitations
before interpreting any complex workflow. Model-based checks do not validate a physical lab.
