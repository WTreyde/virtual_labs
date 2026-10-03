# Strand C: planner agent, Amass evidence, boss report (Albert)

**Owns:** `backend/labforge/agent/`. **Produces:** `LabSpec`, `Workflow`, `Claim`s, the report. **Calls:** catalog search, layout, simulate, verify.

Already working: `planner.run_turn()` runs a Claude tool-use loop (`claude-opus-5-5`, server-side refusal fallback enabled) with `search_catalog` and `layout_and_simulate`; it returns the worked example when `ANTHROPIC_API_KEY` is unset.

## Tasks, in order
1. System prompt and few-shot templates for both pipelines in `docs/pipelines.md`, so the agent emits valid `LabSpec`/`Workflow` JSON (validate with `labforge.contracts.validate`, return errors to Claude as tool errors).
2. Follow-up questions: the agent asks for missing essentials (throughput, room size, budget, hazards) before designing.
3. Amass (`amass.py`): cite literature for step durations and yields; attach as `evidence`; when nothing is found, widen `duration_uncertainty` and say so.
4. Claims: after each design emit `Claim`s with confidences; call the verifier; when a claim is refuted, the agent must say so plainly and revise.
5. Iterate on bottlenecks: add parallel units, swap models, request layout changes, stop when the target is met or explain why it cannot be.
6. Report: Claude-written executive summary, BOM, throughput band, risks, unknowns, assumptions.
7. Stream agent text to the UI (SSE) once the gateway route exists.
8. The "vanilla" bench arm: same model, no tools, asked for design + claims as JSON. This is what we compare against.
