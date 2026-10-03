# Virtual Labs

Digital twins of autonomous labs: describe a chemistry or biology lab in chat, and an agent picks real instruments, lays them out in 3D and simulates throughput to find bottlenecks.

- [ARCHITECTURE.md](ARCHITECTURE.md): system design and the team split
- [docs/pipelines.md](docs/pipelines.md): the chemistry and FBDD demo pipelines
- [CONTRIBUTING.md](CONTRIBUTING.md): branches, hourly sync, ownership
- [docs/team-prompts.md](docs/team-prompts.md): paste-in prompts for each team member's Claude
- [schemas/](schemas/): shared JSON contracts between strands
- [examples/](examples/): a worked enzyme-screening lab every strand can build against
- `python validate_examples.py` checks the examples against the schemas (needs `pip install jsonschema`)

## Quick start

For the standalone Claude agent and local test UI, see [Agent setup](backend/labforge/agent/LIVE_RUN.md).

```bash
make install    # backend (pip -e) + frontend (npm)
make check      # schemas, tests, typecheck: keep green
make backend    # API on :8000 (works offline without keys)
make frontend   # isometric lab on :5173
```
