"""Strand C: the planner agent. Owner: Albert.

`run_turn(history)` takes the chat so far, lets Claude call tools until it is done, and returns
the new assistant messages plus any LabSpec/Workflow/Layout/SimResult it produced.
Without ANTHROPIC_API_KEY it returns the worked example, so the UI and gateway work offline.

Tools are isolated per turn; checked claims use backend-held results.
"""
import json
import os
import time
from datetime import datetime, timezone

from labforge.agent.tools import TOOLS
from labforge.agent.config import load_env
from labforge.agent.errors import BackendContractError
from labforge.contracts import load_example
from labforge.agent.prompts import SYSTEM, system_prompt
from labforge.agent.session import ToolSession

MODEL = "claude-opus-5-5"


def _now() -> str:
    """Return a compact, timezone-explicit timestamp for the live event log.

    Lifecycle events share ``event_id`` and ``step``. Starts have status ``running``;
    terminal events add ``ended_at``, ``duration_ms`` and status ``succeeded`` or
    ``failed``. Existing event types and payloads remain available to replay clients.
    """
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _tool_summary(name: str, output: dict) -> str:
    """Summarise a tool result without duplicating its potentially large payload."""
    if name == "search_catalog":
        items = output.get("items", output.get("results", []))
        return f"Found {len(items)} catalog item{'s' if len(items) != 1 else ''}."
    if name == "search_evidence":
        items = output.get("items", output.get("results", []))
        return f"Found {len(items)} evidence result{'s' if len(items) != 1 else ''}."
    if name == "layout_and_simulate":
        sim = output.get("sim_result", {})
        throughput = sim.get("throughput", {})
        value = throughput.get("p50")
        unit = throughput.get("unit")
        violations = len(output.get("layout", {}).get("violations", []))
        result = "Simulated the proposed lab"
        if value is not None:
            result += f" at p50 {value:g}{f' {unit}' if unit else ''}"
        return f"{result}; {violations} layout violation{'s' if violations != 1 else ''}."
    if name == "verify_claims":
        counts: dict[str, int] = {}
        for claim in output.get("claims", []):
            status = claim.get("status", "unknown")
            counts[status] = counts.get(status, 0) + 1
        detail = ", ".join(f"{count} {status}" for status, count in sorted(counts.items()))
        return f"Checked {sum(counts.values())} claim{'s' if sum(counts.values()) != 1 else ''}{f': {detail}' if detail else ''}."
    summaries = {
        "create_report": "Created the design report.",
        "optimise_instrument": "Completed the instrument what-if sweep.",
        "plan_projects": "Created the project schedule.",
    }
    return summaries.get(name, f"Completed {name}.")


def _elapsed_ms(started: float) -> int:
    return max(0, round((time.monotonic() - started) * 1000))



def offline_turn() -> dict:
    return {
        "status": "offline_demo",
        "message": "Live model access is unavailable; showing the offline worked example.",
        "messages": [{"role": "assistant", "content": "(offline demo) Here is the enzyme screening lab from the worked example."}],
        "lab_spec": load_example("lab_spec"),
        "workflow": load_example("workflow"),
        "layout": load_example("layout"),
        "sim_result": load_example("sim_result"),
    }


def run_turn(history: list[dict], max_steps: int = 12, on_event=None, stream_text: bool = True) -> dict:
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
        step = step_index + 1
        model = os.environ.get("ANTHROPIC_MODEL", MODEL)
        model_event_id = f"model-step-{step}"
        model_started_at = _now()
        model_started = time.monotonic()
        emit({"type": "model_call", "event_id": model_event_id, "name": model,
              "step": step, "model": model, "started_at": model_started_at,
              "status": "running", "summary": f"Started planning step {step}."})
        request = dict(
            model=model,
            max_tokens=24000,
            system=system_prompt(),
            tools=[definition for definition, _ in available_tools.values()],
            messages=messages,
        )
        try:
            if stream_text:
                with client.messages.stream(**request) as stream:
                    for delta in stream.text_stream:
                        emit({'type': 'text_delta', 'text': delta, 'step': step})
                    response = stream.get_final_message()
            else:
                response = client.messages.create(**request)
        except Exception:
            emit({"type": "model_result", "event_id": model_event_id, "name": model,
                  "step": step, "started_at": model_started_at, "ended_at": _now(),
                  "duration_ms": _elapsed_ms(model_started), "status": "failed",
                  "summary": f"Planning step {step} failed."})
            raise
        content = [b.model_dump(mode="json", exclude_none=True) for b in response.content]
        stop_reason = response.stop_reason
        tool_count = sum(block.get("type") == "tool_use" for block in content)
        summary = (f"Planning step {step} requested {tool_count} tool call"
                   f"{'s' if tool_count != 1 else ''}." if tool_count else
                   f"Planning step {step} finished with {stop_reason or 'an unknown stop reason'}.")
        emit({"type": "model_result", "event_id": model_event_id, "name": model,
              "step": step, "started_at": model_started_at, "ended_at": _now(),
              "duration_ms": _elapsed_ms(model_started), "status": "succeeded",
              "summary": summary, "stop_reason": stop_reason})
        messages.append({"role": "assistant", "content": content})
        for block in content if not stream_text else []:
            if block.get('type') == 'text' and block.get('text'):
                emit({'type': 'assistant_text', 'text': block['text']})
        if response.stop_reason != "tool_use":
            completed = response.stop_reason == "end_turn"
            break
        results = []
        backend_blocked = False
        for block in response.content:
            if block.type != "tool_use":
                continue
            tool_started_at = _now()
            tool_started = time.monotonic()
            emit({"type": "tool_start", "event_id": block.id, "name": block.name,
                  "step": step, "started_at": tool_started_at, "status": "running",
                  "summary": f"Started {block.name}.", "input": block.input})
            try:
                if backend_blocked:
                    raise BackendContractError('Skipped: a previous backend output failed its contract.')
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
                emit({"type": "tool_end", "event_id": block.id, "name": block.name,
                      "step": step, "started_at": tool_started_at, "ended_at": _now(),
                      "duration_ms": _elapsed_ms(tool_started), "status": "succeeded",
                      "summary": _tool_summary(block.name, out), "output": compact})
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(compact)})
            except Exception as e:  # report tool failures back to Claude instead of crashing the loop
                if isinstance(e, BackendContractError):
                    backend_blocked = True
                    produced.setdefault('backend_errors', []).append(str(e))
                    if block.name == 'layout_and_simulate':
                        produced['failed_proposal'] = block.input
                    for key in ('lab_spec', 'workflow', 'layout', 'sim_result', 'claims', 'report_markdown', 'brier'):
                        produced.pop(key, None)
                emit({"type": "tool_error", "event_id": block.id, "name": block.name,
                      "step": step, "started_at": tool_started_at, "ended_at": _now(),
                      "duration_ms": _elapsed_ms(tool_started), "status": "failed",
                      "summary": f"{block.name} failed.", "error": str(e)})
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": str(e), "is_error": True})
        messages.append({"role": "user", "content": results})
        if backend_blocked:
            stop_reason = 'backend_contract_error'
            break

    text = "".join(b.get("text", "") for b in messages[-1]["content"] if b.get("type") == "text") if messages[-1]["role"] == "assistant" else ""
    if stop_reason == 'refusal':
        status = 'declined_by_model'
        status_message = 'The model declined this request; no completed live design was produced.'
    elif stop_reason == 'backend_contract_error':
        status = 'blocked_by_backend'
        status_message = 'A backend output failed its contract; the integrator must repair it before retrying.'
    elif completed:
        status = 'completed'
        status_message = 'The model completed this turn.'
    else:
        status = 'incomplete'
        status_message = 'The response or tool-call limit was reached before planning completed.'
    if not completed:
        text += f"\nPlanning is incomplete. {status_message} Any returned design is provisional."
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
    return {"status": status, "message": status_message,
            "messages": [{"role": "assistant", "content": text.strip()}],
            "history": messages, "completed": completed, "stop_reason": stop_reason, **produced}
