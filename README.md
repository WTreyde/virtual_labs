# Virtual Labs

Digital twins of autonomous labs: describe a chemistry or biology lab in chat, and an agent picks real instruments, lays them out in 3D and simulates throughput to find bottlenecks.

- [ARCHITECTURE.md](ARCHITECTURE.md): system design and the team split
- [docs/pipelines.md](docs/pipelines.md): the chemistry and FBDD demo pipelines
- [schemas/](schemas/): shared JSON contracts between strands
- [examples/](examples/): a worked enzyme-screening lab every strand can build against
- `python validate_examples.py` checks the examples against the schemas (needs `pip install jsonschema`)
