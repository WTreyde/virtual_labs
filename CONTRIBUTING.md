# How we stay in sync (5 people, about 26 hours)

## Branches
- `main` always works. The integrator merges into it.
- Each strand works on its own branch: `strand/game`, `strand/catalog`, `strand/agent`, `strand/sim`.
- Open a pull request into `main` early (draft is fine) and keep it small; merge at least every 2–3 hours so nobody drifts.

## Every hour, on the hour
1. `git fetch origin && git rebase origin/main` (or merge, if you prefer) on your strand branch.
2. `make check`, then fix anything red before doing anything else.
3. `git push`.
4. Post one line in the team chat: what landed, what's next, anything blocking.

## Contracts
- The JSON schemas in `schemas/` are the only interface between strands. Code against `examples/*.json`, not against another strand's internals.
- Need a schema change? Ask the integrator. Adding an optional field is quick; renaming or removing one needs everyone told and `examples/` updated in the same commit.
- `make check` must stay green on `main`. CI runs the same checks on every push and PR.

## Ownership (one owner per directory avoids merge conflicts)
| Path | Strand | Owner |
|---|---|---|
| `frontend/` | A: game client and report UI | Roshan |
| `backend/labforge/catalog/`, `backend/labforge/bench/tasks/`, `backend/labforge/validation/` | B: catalog, safety rules, benchmark tasks, validation cases | Max |
| `backend/labforge/agent/` | C: planner agent, Amass, report | Albert |
| `backend/labforge/layout/`, `sim/` (incl. `whatif.py`), `verify/`, `bench/runner.py` | D: layout, simulation, vendor what-ifs, verifier, bench scoring | Maxim |
| `schemas/`, `examples/`, `backend/labforge/gateway.py`, `contracts.py`, CI | Integrator | team lead |

## Freeze
- 09:00 on 4 Oct: feature freeze on `main`; only fixes after that.
- 12:00: final `main` tagged `demo`; record the backup video from it.
