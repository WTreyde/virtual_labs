"""Strand C: the planner agent. Owner: Albert.

`run_turn(history)` takes the chat so far, lets Claude call tools until it is done, and returns
the new assistant messages plus any LabSpec/Workflow/Layout/SimResult it produced.
Without ANTHROPIC_API_KEY it returns the worked example, so the UI and gateway work offline.

Tools are isolated per turn; checked claims use backend-held results.
"""
import json
import os

from labforge.agent.tools import TOOLS
from labforge.agent.config import load_env
from labforge.contracts import load_example
from labforge.agent.prompts import SYSTEM, system_prompt
from labforge.agent.session import ToolSession

MODEL = "claude-opus-5-5"



def offline_turn() -> dict:
    return {
        "messages": [{"role": "assistant", "content": "(offline demo) Here is the enzyme screening lab from the worked example."}],
        "lab_spec": load_example("lab_spec"),
        "workflow": load_example("workflow"),
        "layout": load_example("layout"),
        "sim_result": load_example("sim_result"),
    }


def run_turn(history: list[dict], max_steps: int = 12, on_event=None, stream_text: bool = False) -> dict:
    emit = on_event or (lambda event: None)
    load_env()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return offline_turn()

    if max_steps < 1:
        raise ValueError("max_steps must be positive")
    import anthropic

    workspace_id = os.environ.get("ANTHROPIC_WORKSPACE_ID", "").strip()
    client = anthropic.Anthropic(
        default_headers={"anthropic-workspace-id": workspace_id} if workspace_id else {}
    )
    messages = list(history)
    session = ToolSession(TOOLS, history)
    available_tools = session.tools
    completed = False
    stop_reason = 'tool_limit'
    produced: dict = {}
    for step_index in range(max_steps):
        emit({"type": "model_call", "step": step_index + 1, "model": os.environ.get("ANTHROPIC_MODEL", MODEL)})
        request = dict(
            model=os.environ.get("ANTHROPIC_MODEL", MODEL),
            max_tokens=16000,
            system=system_prompt(),
            tools=[definition for definition, _ in available_tools.values()],
            messages=messages,
        )
        if stream_text:
            with client.messages.stream(**request) as stream:
                for delta in stream.text_stream:
                    emit({'type': 'text_delta', 'text': delta, 'step': step_index + 1})
                response = stream.get_final_message()
        else:
            response = client.messages.create(**request)
        content = [b.model_dump(mode="json", exclude_none=True) for b in response.content]
        stop_reason = response.stop_reason
        messages.append({"role": "assistant", "content": content})
        for block in content if not stream_text else []:
            if block.get('type') == 'text' and block.get('text'):
                emit({'type': 'assistant_text', 'text': block['text']})
        if response.stop_reason != "tool_use":
            completed = response.stop_reason == "end_turn"
            break
        results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            emit({"type": "tool_start", "name": block.name, "input": block.input})
            try:
                _, fn = available_tools[block.name]
                out = fn(**block.input)
                produced.update({k: v for k, v in out.items() if k in ("layout", "sim_result")})
                if block.name == "layout_and_simulate":
                    produced.update(lab_spec=block.input["lab_spec"], workflow=block.input["workflow"])
                    produced.pop('claims', None)
                    produced.pop('report_markdown', None)
                    produced.pop('brier', None)
                    produced.pop('instrument_optimisation', None)
                if block.name == 'verify_claims':
                    produced.update(claims=out['claims'], brier=out['brier'])
                if block.name == 'create_report':
                    produced['report_markdown'] = out['report_markdown']
                if block.name == 'optimise_instrument':
                    produced['instrument_optimisation'] = out['instrument_optimisation']
                compact = {**out}
                if "sim_result" in compact:
                    compact["sim_result"] = {k: v for k, v in out["sim_result"].items() if k != "timeline"}
                emit({"type": "tool_end", "name": block.name, "output": compact})
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(compact)})
            except Exception as e:  # report tool failures back to Claude instead of crashing the loop
                emit({"type": "tool_error", "name": block.name, "error": str(e)})
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": str(e), "is_error": True})
        messages.append({"role": "user", "content": results})

    text = "".join(b.get("text", "") for b in messages[-1]["content"] if b.get("type") == "text") if messages[-1]["role"] == "assistant" else ""
    if not completed:
        reason = 'the API declined the request' if stop_reason == 'refusal' else 'the response or tool-call limit was reached'
        text += f"\nPlanning is incomplete: {reason}. Any returned design is provisional."
    if session.design is not None:
        produced.update(session.design)
        produced['claims'] = session.claims
        required_metrics = {'throughput.p50', 'layout.violations'}
        if session.design['lab_spec'].get('constraints', {}).get('budget_usd') is not None:
            required_metrics.add('bom.total_usd')
        checked_metrics = {c.get('metric') for c in session.claims}
        produced['verification_complete'] = required_metrics <= checked_metrics
        if not produced['verification_complete']:
            text += '\nThis design is provisional: required throughput, layout or budget claims have not all been checked.'
        if completed and session.claims:
            produced.update(session.report())
    if session.evidence:
        produced['evidence_searches'] = session.evidence
    if session.optimisations:
        produced['instrument_optimisations'] = session.optimisations
    if session.project_schedule is not None:
        produced['project_schedule'] = session.project_schedule
    if session.claim_history:
        produced['claim_history'] = session.claim_history
    return {"messages": [{"role": "assistant", "content": text.strip()}],
            "history": messages, "completed": completed, **produced}
