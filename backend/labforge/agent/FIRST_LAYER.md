# Strand C handoff

The first-layer validation and planner loop have been extended into the complete standalone
agent interface. Follow [LIVE_RUN.md](LIVE_RUN.md) for setup, tools, demo prompts, checks,
CLI/benchmark commands, and gateway/SSE integration.

Implemented: schema-guided Opus planning, semantic validation, provenance, tool error
repair, full UI timelines, preserved history, optional Amass retrieval/cache, backend-held
claim checks, deterministic reports, token streaming, and vanilla/platform benchmark arms.

The integrator should preserve result.history between turns and wire the SSE adapter into
the gateway. Strand D should import the agent benchmark run_arm and supply independent
hidden checks; agent claims are not ground-truth outcomes. Max should extend the catalog
before chemistry/FBDD demos, and Maxim should confirm duration units and simulator semantics.

No schema, gateway, main frontend, catalog or simulator/verifier implementation changes
are included in this strand. Live end-to-end demo validation must be run locally.
