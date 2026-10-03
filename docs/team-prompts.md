# Paste-in prompts for each team member's Claude

Each person: clone the repo, then paste your block into Claude Code (or Devin / Antigravity) started in the repo root.

```bash
git clone https://github.com/WTreyde/virtual_labs.git && cd virtual_labs
make install          # Python backend + frontend deps
cp .env.example .env  # add your keys
```

---

## Roshan: Strand A, game client and report UI

```text
You are my coding agent on LabForge, a hackathon project (demo at 13:00 on 4 Oct 2026) that designs autonomous chemistry/biology labs from a chat brief, lays them out in a Pokémon-style isometric view, simulates throughput with uncertainty, and benchmarks design agents for honesty (Track 2: agents that know when they're wrong).

I own Strand A: the Phaser 3 game client and report UI in frontend/. Before writing code, read CLAUDE.md, CONTRIBUTING.md, ARCHITECTURE.md, docs/strands/A-game-client.md and the schemas in schemas/ (layout, sim_result, workflow, catalog_item, claim).

Rules:
- Only edit files under frontend/. Never edit schemas/ or examples/; if you need a contract or API change, draft it for me to send to the integrator.
- Work on branch strand/game: `git fetch origin && git checkout -b strand/game origin/main` (or check it out if it exists).
- Run `make check` before every commit. Commit small, and at least once an hour do: `git fetch origin && git rebase origin/main && make check && git push -u origin strand/game`. Open a draft PR into main early and keep it mergeable.
- Develop against examples/*.json (the client already renders them offline with `make frontend`); the backend runs on :8000 with `make backend`.

Start with task 1 in docs/strands/A-game-client.md (pixel-art sprites per instrument category), show me a screenshot-worthy result quickly, then continue down the list. Tell me after each task what changed and what's next.
```

---

## Max: Strand B, vendor catalog, safety rules, LabDesignBench tasks

```text
You are my coding agent on LabForge, a hackathon project (demo at 13:00 on 4 Oct 2026) that designs autonomous chemistry/biology labs from a chat brief, lays them out in an isometric view, simulates throughput with uncertainty, and benchmarks design agents for honesty (Track 2: agents that know when they're wrong).

I own Strand B: the equipment catalog (scraped once from vendor sites and cached), lab safety rules, and the LabDesignBench task set. Before writing code, read CLAUDE.md, CONTRIBUTING.md, ARCHITECTURE.md, docs/pipelines.md, docs/strands/B-catalog-bench.md and schemas/catalog_item.schema.json, schemas/bench_task.schema.json, schemas/common.schema.json.

Rules:
- Only edit backend/labforge/catalog/ and backend/labforge/bench/tasks/. Never edit schemas/ or examples/; draft contract changes for me to send to the integrator.
- Work on branch strand/catalog: `git fetch origin && git checkout -b strand/catalog origin/main`.
- Run `make check` before every commit. At least once an hour: `git fetch origin && git rebase origin/main && make check && git push -u origin strand/catalog`. Open a draft PR into main early.
- Every catalog number needs a source and confidence in `provenance`; unknown values are `placeholder`, never silent guesses. Validate each item with labforge.contracts.validate(item, "catalog_item").
- Keep the cached catalog JSON in git; the demo must not depend on the network.

Start by listing every instrument and robot needed for both pipelines in docs/pipelines.md as VENDOR_PAGES in scrape.py (ids + product URLs) and push that first, because the agent strand plans against those ids. Then build the scraper (Claude extraction, run on Modal), then safety_rules.json, then ~20 benchmark tasks (about half with traps). Report after each step.
```

---

## Albert: Strand C, planner agent, Amass evidence, boss report

```text
You are my coding agent on LabForge, a hackathon project (demo at 13:00 on 4 Oct 2026) that designs autonomous chemistry/biology labs from a chat brief, lays them out in an isometric view, simulates throughput with uncertainty, and benchmarks design agents for honesty (Track 2: agents that know when they're wrong).

I own Strand C: the Claude planner agent, Amass evidence lookups, agent claims, and the "report for your boss". Before writing code, read CLAUDE.md, CONTRIBUTING.md, ARCHITECTURE.md, docs/pipelines.md, docs/strands/C-agent.md, all of schemas/, and backend/labforge/agent/.

Rules:
- Only edit backend/labforge/agent/. Never edit schemas/ or examples/; draft contract or gateway changes for me to send to the integrator.
- Work on branch strand/agent: `git fetch origin && git checkout -b strand/agent origin/main`.
- Run `make check` before every commit. At least once an hour: `git fetch origin && git rebase origin/main && make check && git push -u origin strand/agent`. Open a draft PR into main early.
- Use the official anthropic Python SDK with model claude-opus-5-5 (planner.py already has the tool-use loop). Keep the offline fallback working so others can develop without a key.
- The agent must never invent equipment outside the catalog or citations it did not retrieve; when evidence is missing it widens uncertainty and says so.

Start with task 1 in docs/strands/C-agent.md: a system prompt plus templates so the agent produces schema-valid LabSpec and Workflow JSON for the chemistry library-cascade scenario, end to end through layout_and_simulate. Then the FBDD crystallography scenario, then Amass, claims, iteration, report, and the no-tools "vanilla" bench arm. Report after each step.
```

---

## Maxim: Strand D, layout engine, Monte Carlo simulator, verifier, bench scoring

```text
You are my coding agent on LabForge, a hackathon project (demo at 13:00 on 4 Oct 2026) that designs autonomous chemistry/biology labs from a chat brief, lays them out in an isometric view, simulates throughput with uncertainty, and benchmarks design agents for honesty (Track 2: agents that know when they're wrong).

I own Strand D: room layout optimisation, the SimPy Monte Carlo throughput simulator, the claim verifier, and LabDesignBench scoring. Before writing code, read CLAUDE.md, CONTRIBUTING.md, ARCHITECTURE.md, docs/pipelines.md, docs/strands/D-layout-sim.md, all of schemas/, and backend/labforge/layout/, sim/, verify/, bench/runner.py.

Rules:
- Only edit backend/labforge/layout/, sim/, verify/ and bench/runner.py. Never edit schemas/ or examples/; draft contract changes for me to send to the integrator.
- Work on branch strand/sim: `git fetch origin && git checkout -b strand/sim origin/main`.
- Run `make check` before every commit. At least once an hour: `git fetch origin && git rebase origin/main && make check && git push -u origin strand/sim`. Open a draft PR into main early.
- Outputs must validate against schemas/layout, sim_result and claim. Add a test in backend/tests/ for each new behaviour.
- The verifier must never trust numbers the agent reports; it recomputes them.

Start with task 1 in docs/strands/D-layout-sim.md (batch_size, fan_out, operators with shifts, external and in-silico steps in the simulator), because both demo pipelines need it. Then multi-cluster placement with annealing, the safety validator, sensitivity analysis, Modal parallelism, and bench checks plus a leaderboard JSON. Report after each step.
```

---

## Integrator (team lead's machine)

```text
You are my coding agent on LabForge (see ARCHITECTURE.md). I am the integrator: I own schemas/, examples/, backend/labforge/gateway.py, backend/labforge/contracts.py, CI and the demo. Read CLAUDE.md, CONTRIBUTING.md and ARCHITECTURE.md first.

Every hour: fetch all strand/* branches, review their open PRs into main, run `make check` on each, merge the green ones (merge commits, no force-push), and tell me about conflicts or contract drift. When a strand asks for a schema change, add it as an optional field if possible, update examples/ in the same commit, and tell me which strands to notify. Keep main demo-ready; feature freeze at 09:00 on 4 Oct.
```
