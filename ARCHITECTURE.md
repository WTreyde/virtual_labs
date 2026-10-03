# Virtual Labs: architecture and team split

Draft for alignment. Defaults are marked **(default)** and will change once the team answers the open questions.

## What the demo shows

1. A user types a lab brief in chat, e.g. *"Automated enzyme variant screening, 20 x 96-well plates per day: liquid handling, 37 °C incubation, absorbance readout, sealing."*
2. The agent asks follow-up questions if needed, then produces a **LabSpec** (structured requirements).
3. The agent turns the spec into a **Workflow** (ordered steps, each needing a capability) and picks real instruments from the **Catalog**.
4. The layout engine places instruments and robots in a room and produces a **Layout**, keeping every plate handoff within reach of a transfer robot.
5. The simulator runs the workflow on the layout and returns a **SimResult**: plates/day, utilisation per instrument, bottlenecks, transfer distances.
6. The browser shows the lab in 3D, with bottlenecks highlighted. The user says "double the throughput" or "make it fit in 6 x 4 m" and the agent iterates.

## System diagram

```
 ┌───────────────────────── Frontend (React + three.js) ─────────────────────────┐
 │  Chat panel  │  3D lab viewer (instruments, robots, transfer paths)  │ Metrics │
 └──────────────┬────────────────────────────────────────────────────────────────┘
                │ REST/JSON  (+ SSE for streamed agent messages)
 ┌──────────────▼──────────── API gateway (FastAPI) ─────────────────────────────┐
 │  POST /chat   GET /catalog   POST /layout   POST /simulate   GET /project/:id │
 └───────┬────────────────────────┬──────────────────────┬──────────────────────┘
         │                        │                      │
 ┌───────▼────────┐     ┌─────────▼────────┐   ┌─────────▼──────────────────┐
 │ Planner agent  │────▶│ Equipment catalog│   │ Layout engine + simulator  │
 │ (Claude API,   │tools│ (curated JSON of │   │ (placement optimiser,      │
 │  tool use)     │────▶│ vendor specs)    │   │  discrete-event sim)       │
 └────────────────┘     └──────────────────┘   └────────────────────────────┘
        the agent calls catalog search, layout and simulate as tools
```

Stack **(default)**: Python 3.11 + FastAPI backend, React + Vite + react-three-fiber frontend, Claude API for the agent, SimPy for simulation. Everything passes JSON objects defined in [`schemas/`](schemas/); examples are in [`examples/`](examples/).

## Shared contracts (the only thing strands must agree on)

| Object | Schema | Produced by | Consumed by |
|---|---|---|---|
| LabSpec | `schemas/lab_spec.schema.json` | Agent | Agent, frontend |
| CatalogItem | `schemas/catalog_item.schema.json` | Catalog | Agent, layout, sim, frontend (3D size, colour) |
| Workflow | `schemas/workflow.schema.json` | Agent | Layout, sim, frontend |
| Layout | `schemas/layout.schema.json` | Layout engine | Sim, frontend |
| SimResult | `schemas/sim_result.schema.json` | Simulator | Agent, frontend |

Conventions: metres and seconds everywhere. Floor coordinates are `x` (along room width) and `y` (along room depth) from the room's corner; `z` is height. The frontend maps this to three.js (`y` up) as `(x, z, -y)`. IDs are lowercase snake_case strings.

The key modelling idea: every instrument has **access points** (where a plate goes in and out), and every workflow step that moves labware between two instruments is a **transfer edge**. A layout is valid only if each transfer edge is served by a transporter (robot arm, rail, mobile robot or human) whose reach covers both access points. Transfer time comes from distance and transporter speed, which is what lets the simulator find "robot A hands to robot B across the room" bottlenecks.

## Strands

Each strand can be built and tested alone against the example JSON files, so nobody blocks on anybody else.

### Strand 1: Interface (frontend)
- Chat panel with streamed agent replies and quick actions ("re-plan", "optimise layout").
- 3D viewer: room, instruments as boxes sized from catalog footprints (GLB models later if time), robot reach circles, animated transfer paths coloured by load, bottlenecks in red.
- Metrics panel: plates/day vs target, utilisation bars, bill of materials with cost.
- Drag an instrument to move it, which calls `POST /simulate` and refreshes metrics.
- **Builds against:** `examples/*.json` from hour one, no backend needed.

### Strand 2: Equipment catalog (vendor specs)
- Curate ~30 real instruments across capabilities: liquid handlers, robot arms, mobile robots, incubators, plate readers, sealers, centrifuges, plate hotels, dispensers, thermocyclers, (bio) automated colony pickers, (chem) dosing units, reactors, HPLC.
- For each: vendor, model, footprint, height, access points, plate formats, throughput/timing, power, cost estimate, source URL.
- `GET /catalog?capability=...` search endpoint, exposed to the agent as a tool.
- Stretch: an LLM-assisted scraper that turns a vendor datasheet URL or PDF into a CatalogItem.

### Strand 3: Agent (planner)
- Claude conversation that elicits a LabSpec, then designs a Workflow and an equipment list.
- Tools: `search_catalog`, `generate_layout`, `simulate`, `update_spec`.
- Iteration loop: read SimResult bottlenecks, then add a parallel instrument, swap a model, or ask the layout engine to move things, until targets are met or the agent explains the trade-off.
- Owns the prompt templates and 2–3 demo scenarios (one biology, one chemistry).

### Strand 4: Layout engine and simulator
- Placement: given room size, equipment and transfer edges, place footprints without overlap, with clearances and walls, minimising weighted transfer distance, and make every edge reachable by some transporter. Start with a greedy cluster-around-the-arm placer, then add simulated-annealing refinement.
- Simulator: SimPy discrete-event run of N plates through the workflow, with instrument capacities, durations and transfer times from the layout. Outputs throughput, utilisation, queue waits and named bottlenecks.
- Validation: overlaps, unreachable edges, room overflow, returned as `violations` in the Layout.

### Lead / integrator (fifth person)
- Owns `schemas/`, the FastAPI gateway and project storage (in-memory or JSON files), CI that validates examples against schemas, and wiring strands together.
- Owns the demo script and pitch, and acts as the tie-breaker on interface changes.

## Suggested timeline (adjust to the real deadline)

| Phase | Goal |
|---|---|
| First 2 h | Schemas frozen at v0.1, each strand runs standalone on example JSON |
| Middle | Gateway wires agent → layout → sim → frontend end to end with a stub catalog |
| Last third | Real catalog, layout optimiser, polished 3D, demo scenarios rehearsed |
| Final hour | Freeze code, rehearse demo, record backup video |

## Rules for changing a schema

Add optional fields freely. Renaming or removing a field needs a heads-up to everyone and an updated example in the same commit.
