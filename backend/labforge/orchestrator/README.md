# Orchestrating-agent export

A designed and simulated lab becomes instructions for the LLM agent that will run it:

- `SKILL.md`: a skill file for the orchestrating agent (devices, workflow and handoffs, run order, safety rules, when to call a person, what the twin expects).
- `tools.json`: the device and tool manifest. Each `devices[]` entry is a device sheet (capabilities used, limits with confidence, safety, control interface) plus MCP-shaped tool definitions; `global_tools` adds `request_human`, `record_measurement` and `pause_line`.

```
cd backend && python3 -m labforge.orchestrator.cli ../frontend/public/replays/fbdd.json --out /tmp/fbdd-agent
```

In Python: `labforge.orchestrator.build_orchestrator(spec, workflow, layout, catalog, sim_result, claims, schedule)` or `from_replay(path)`. Pure function of the design; no Claude or simulator calls. Samples for both case studies are in `samples/`.

## Where each part comes from

| Output | Source in the twin |
|---|---|
| Tools and their enums | workflow steps per equipment instance; layout transfers per transporter |
| Limits | catalog `process`, `storage_slots`, `access_points[].labware`, `transport`, with provenance confidence |
| Run order | dependency waves of the workflow; dispatch paced by the sim's busiest instrument; project order from `/prioritise` if given |
| Pause-and-escalate times | 1.5 x each step's high duration bound |
| Pre-flight gate | unresolved layout violations; placeholder catalog values to measure on the first run |
| Safety rules | `catalog/data/safety_rules.json`, catalog `safety`, spec hazards |
| Escalation | manual/external steps, operator shifts, hold times, instruments with no confirmed API, low P(meets target), refuted claims |

## Honest limits

- The dispatch policy is a drum-buffer-rope heuristic from utilisation, not an optimised schedule.
- Tool definitions describe what the agent should call; they are not drivers. Instruments marked `unconfirmed` or `vendor_software_only` need a verified driver or a person.
- Aligned with device-description standards such as Anthropic's Model Hardware Standard; not an implementation of it (spec not public).
- Not yet done (pitch only): run the generated agent against the simulator as a mock lab and score its throughput and safety violations.
