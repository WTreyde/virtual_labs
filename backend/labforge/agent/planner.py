"""Strand C: the planner agent. Owner: Albert.

`run_turn(history)` takes the chat so far, lets Claude call tools until it is done, and returns
the new assistant messages plus any LabSpec/Workflow/Layout/SimResult it produced.
Without ANTHROPIC_API_KEY it returns the worked example, so the UI and gateway work offline.

TODO(Albert): system prompt with the pipeline templates in docs/pipelines.md, claims with
confidences after every design, iterate on bottlenecks, stream text to the UI over SSE.
"""
import json
import os

import anthropic

from labforge.agent.tools import TOOLS
from labforge.contracts import load_example

MODEL = "claude-opus-5-5"
SYSTEM = (
    "You design autonomous chemistry and biology labs from real commercial equipment. "
    "Use search_catalog to pick instruments; never invent equipment that is not in the catalog. "
    "Write a LabSpec and Workflow as JSON that follow the project schemas, then call layout_and_simulate "
    "and improve the design until it meets the throughput target or you can explain why it cannot. "
    "For every number you state, say where it comes from and how sure you are. If something is unknown, say so."
)


def offline_turn() -> dict:
    return {
        "messages": [{"role": "assistant", "content": "(offline demo) Here is the enzyme screening lab from the worked example."}],
        "lab_spec": load_example("lab_spec"),
        "workflow": load_example("workflow"),
        "layout": load_example("layout"),
        "sim_result": load_example("sim_result"),
    }


def run_turn(history: list[dict], max_steps: int = 12) -> dict:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return offline_turn()

    client = anthropic.Anthropic()
    messages = list(history)
    produced: dict = {}
    for _ in range(max_steps):
        response = client.beta.messages.create(
            model=MODEL,
            max_tokens=16000,
            system=SYSTEM,
            output_config={"effort": "high"},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            tools=[definition for definition, _ in TOOLS.values()],
            messages=messages,
        )
        messages.append({"role": "assistant", "content": response.content})
        if response.stop_reason != "tool_use":
            break
        results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            _, fn = TOOLS[block.name]
            try:
                out = fn(**block.input)
                produced.update({k: v for k, v in out.items() if k in ("layout", "sim_result")})
                if block.name == "layout_and_simulate":
                    produced.update(lab_spec=block.input["lab_spec"], workflow=block.input["workflow"])
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(out)})
            except Exception as e:  # report tool failures back to Claude instead of crashing the loop
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": str(e), "is_error": True})
        messages.append({"role": "user", "content": results})

    text = "".join(b.text for b in messages[-1]["content"] if getattr(b, "type", None) == "text") if messages[-1]["role"] == "assistant" else ""
    return {"messages": [{"role": "assistant", "content": text}], **produced}
