# Instructions for coding agents working in this repo

Read first: `ARCHITECTURE.md`, `docs/pipelines.md` and `CONTRIBUTING.md`.

## Rules
- `schemas/` is the contract between components. Everything that crosses a component boundary must validate against it; use `labforge.contracts.validate(obj, "<schema>")` in Python. A schema change ships with its updated example in `examples/` in the same commit.
- Run `make check` (backend tests, example validation, frontend typecheck) before every commit. Do not commit if it fails.
- Never force-push `main`. Never commit secrets; keys live in `.env` (gitignored).
- Mark unknown or guessed numbers honestly (`confidence: "estimated"` or `"placeholder"`). Knowing what it does not know is the point of this project.
- Numbers quoted in docs come from committed runs. Do not change a quoted number without re-running what produced it.

## Running things
- `make install` once, then `make backend` (API on :8000) and `make frontend` (game on :5173), or `make demo` for both on :8000.
- The client and every module work offline on `examples/*.json` and the recorded replays; no API key is needed to develop.
- Claude model: `claude-opus-5-5` via the official `anthropic` SDK (see `backend/labforge/agent/planner.py`). Live agent runs need your own `ANTHROPIC_API_KEY` in `.env`.
