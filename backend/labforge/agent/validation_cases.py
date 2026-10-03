"""Planner adapter for Max's validation runner. Never reveal reported cost to the model."""
from labforge.agent.config import load_env
from labforge.agent.planner import run_turn
from labforge.agent.validation import validate_design
import os


def design_from_brief(case: dict) -> dict | None:
    load_env()
    if not os.getenv('ANTHROPIC_API_KEY'):
        return None  # Offline fixture is not a prediction for this case.
    brief = case.get('brief')
    if not isinstance(brief, str) or not brief.strip():
        raise ValueError('Validation case needs a nonempty brief')
    # The case's reported costs, notes, sources and verification status are withheld.
    result = run_turn([{'role': 'user', 'content': brief}])
    if not result.get('completed') or not result.get('lab_spec') or not result.get('workflow'):
        return None  # Missing requirements/catalog coverage must not become fabricated evidence.
    validate_design(result['lab_spec'], result['workflow'])
    return result['workflow']
