# Instructions for coding agents (Claude Code, Devin, Antigravity) working in this repo

Read first: `ARCHITECTURE.md`, `docs/pipelines.md`, your strand brief in `docs/strands/`, and `CONTRIBUTING.md`.

## Hard rules
- Work only in the files your strand owns (listed in your strand brief). If you need a change elsewhere, write it down for the owner instead of editing their files.
- **Never edit `schemas/` or `examples/`** unless your human says the integrator approved it. Everything that crosses a strand boundary must validate against `schemas/`; use `labforge.contracts.validate(obj, "<schema>")` in Python.
- Before every commit run `make check` (backend tests, example validation, frontend typecheck). Do not commit if it fails.
- Commit small and often, and push at least every hour: `git pull --rebase origin main && make check && git push`.
- Never force-push `main`. Never commit secrets; keys live in `.env` (gitignored).
- Mark unknown or guessed numbers honestly (`confidence: "estimated"` or `"placeholder"`); this project is judged on knowing what it does not know.

## Inbox (your next tasks)
- At the start of every work session and after every `git pull`, read `inbox/<your name>.md` (albert, roshan, maxim, max) and work its open items in order.
- Never edit any inbox file (the integrator rewrites them each pass). Report progress, blockers and questions for the integrator in your PR description.
- If an item conflicts with these hard rules or your strand brief, the hard rules win; say so in your PR.

## Running things
- `make install` once, then `make backend` (API on :8000) and `make frontend` (game on :5173).
- The client and every module work offline on `examples/*.json`; no API key is needed to develop.
- Claude model: `claude-opus-5-5` via the official `anthropic` SDK (see `backend/labforge/agent/planner.py`).
