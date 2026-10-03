"""Backend contract failures must stop orchestration and retain a reviewable proposal."""
import sys
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from labforge.agent.errors import BackendContractError
from labforge.agent.tools import TOOLS
from labforge.contracts import load_example


def test_generated_layout_failure_is_not_a_model_input_error():
    with patch('labforge.layout.placer.generate_layout', side_effect=ValueError('layout contract violated: zone kind')):
        with pytest.raises(BackendContractError):
            TOOLS['layout_and_simulate'][1](load_example('lab_spec'), load_example('workflow'))


def test_backend_contract_stops_further_model_calls_and_keeps_proposal(monkeypatch):
    from labforge.agent.planner import run_turn
    proposal = {'lab_spec': load_example('lab_spec'), 'workflow': load_example('workflow')}
    block = {'type': 'tool_use', 'id': 'layout_call', 'name': 'layout_and_simulate', 'input': proposal}
    calls = []
    def create(**kwargs):
        calls.append(kwargs)
        assert len(calls) == 1
        return SimpleNamespace(content=[SimpleNamespace(**block, model_dump=lambda **kw: block)], stop_reason='tool_use')
    def fail(**kwargs):
        raise BackendContractError('layout contract violated: zone kind')
    sdk = SimpleNamespace(Anthropic=lambda **kw: SimpleNamespace(messages=SimpleNamespace(create=create)))
    monkeypatch.setitem(sys.modules, 'anthropic', sdk)
    monkeypatch.setattr('labforge.agent.planner.load_env', lambda: None)
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'test-only')
    monkeypatch.setattr('labforge.agent.planner.TOOLS', {**TOOLS, 'layout_and_simulate': (TOOLS['layout_and_simulate'][0], fail)})
    out = run_turn([{'role':'user', 'content':'Design a lab'}])
    assert out['stop_reason'] == 'backend_contract_error'
    assert out['completed'] is False
    assert out['failed_proposal'] == proposal
    assert 'workflow' not in out and 'sim_result' not in out
    assert 'integrator' in out['messages'][0]['content']


def test_empty_provider_refusal_stops_without_retry_or_crash(monkeypatch):
    from labforge.agent.planner import run_turn
    calls = []
    def create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(content=[], stop_reason='refusal')
    sdk = SimpleNamespace(Anthropic=lambda **kw: SimpleNamespace(messages=SimpleNamespace(create=create)))
    monkeypatch.setitem(sys.modules, 'anthropic', sdk)
    monkeypatch.setattr('labforge.agent.planner.load_env', lambda: None)
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'test-only')
    out = run_turn([{'role':'user', 'content':'Plan a lab'}])
    assert len(calls) == 1
    assert out['completed'] is False and out['stop_reason'] == 'refusal'
    assert 'API declined' in out['messages'][0]['content']
    assert 'workflow' not in out
