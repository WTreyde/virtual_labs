# Contributing

## Workflow
- `main` always works. Branch off it, open a pull request, and keep it small.
- Run `make check` before pushing. CI (`.github/workflows/check.yml`) runs the same checks on every push and pull request, and every push to `main` redeploys the GitHub Pages demo (`.github/workflows/pages.yml`).

## Contracts
- The JSON schemas in `schemas/` are the interface between the components (agent, catalog, layout, simulator, verifier, game client). Code against `examples/*.json`, not against another component's internals.
- Adding an optional field is safe. Renaming or removing one needs `examples/` and every reader updated in the same change.

## Where things live
| Path | What |
|---|---|
| `frontend/` | Game client, report and the case-study, validation, bench, schedule and protocol views |
| `backend/labforge/agent/` | Planner agent, its tools, Amass evidence, the boss report, recorded demo runs |
| `backend/labforge/catalog/` | Vendor catalog, scrape scripts, safety rules |
| `backend/labforge/layout/`, `sim/`, `verify/` | Layout engine, Monte Carlo simulator and what-ifs, independent verifier |
| `backend/labforge/bench/` | LabDesignBench tasks, runner and saved results |
| `backend/labforge/validation/`, `known_bottlenecks/` | Cost validation against published labs, known-bottleneck cases |
| `backend/labforge/protocols/`, `orchestrator/` | Published protocol library, orchestrating-agent export |
| `backend/labforge/gateway.py`, `contracts.py` | The HTTP API and schema validation |
| `schemas/`, `examples/` | Data contracts and a worked example |
| `deploy/pages/` | Static export for the GitHub Pages build |
