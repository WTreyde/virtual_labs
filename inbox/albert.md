# Inbox: Albert (Strand C: agent and Amass)

Last updated: 2026-10-03 23:15 BST by the integrator. Main at `7a6bc3a` (plus this inbox commit).

The integrator rewrites this file on every integration pass (every 30 min until the 09:00 freeze on 4 Oct).
Work the open items top to bottom. Done items drop off once your merged work on main shows them done.
Don't edit this file; report progress in your PR description.

## Open items

```
The team tested the demo tonight. Two P0 bugs are partly yours; do them first.
The integrator already fixed the gateway side: GET /validation never calls the agent any more, and
GET /health now returns api_key_loaded, live_agent and live_agent_note.

1. P0, live agent never runs ("(offline demo) Here is the enzyme screening lab..." even with a key).
   a. agent/config.load_env skips any key already in os.environ, even an EMPTY one, so a shell that
      exports ANTHROPIC_API_KEY= hides the .env key. Treat an empty existing value as unset.
   b. planner.run_turn: make stream_text default to True (or always stream internally). The UI calls
      POST /chat, which uses run_turn without streaming, and long turns fail in the SDK with
      "Streaming is required for operations that may take longer than 10 minutes". Your test
      test_chat_preserves_full_tool_history_between_turns pins run_turn(history) with no kwargs, which
      is why the gateway did not pass stream_text itself; changing the default keeps that test valid.
   c. agent/validation_cases.design_from_brief: call run_turn(..., stream_text=True) like
      bench/runner._ask does. Max's new "--design-missing" generator will call it.
   Test it live: key in the repo-root .env, restart the backend, Design your own lab, see a new design.
2. P1 #11, agent log under the total box: emit structured events per step and tool call (name, start,
   end/duration, status, short summary) so Roshan can render a collapsible log with timings. Agree the
   event shape with Roshan in your PR.
3. Still open from 18:45 (the XChem pitch depends on it): record the "grow plates in the Rock Imager"
   what-if on current main. Max's #46 is merged: the imager holds 970 SBS plates (full config),
   incubates between inspections, one setpoint per unit (20 C needs the Peltier model). Use those
   values, change nothing else, report planned and verified throughput and the new bottleneck honestly,
   save next to xchem-whatif.json and add it to fbdd.summary.json under "imager_growth_whatif" with
   fields planned_p50, verified_p50, unit (Roshan's #47 reads those names).
4. Still open: agent/tools.py at least 50 replicates (now 10); noise-aware planner-vs-verifier gate in
   agent/demo_scenarios.py (Maxim's #44 has the numbers).
Run make check, push, and open a PR into main.
```
