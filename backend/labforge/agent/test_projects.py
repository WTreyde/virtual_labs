"""Scheduling boundary tests: shared hardware, supported semantics and output contract."""
import copy
import sys
from types import SimpleNamespace

import pytest

from labforge.agent.session import ToolSession
from labforge.agent.tools import TOOLS
from labforge.contracts import load_example, validate


def inputs():
    spec = load_example('lab_spec')
    projects = []
    for pid, dispense, read in [('dispense_heavy', 1800, 60), ('urgent', 60, 1800)]:
        workflow = copy.deepcopy(load_example('workflow'))
        for step in workflow['steps']:
            step['duration_s'] = {'dispense': dispense, 'read': read}.get(step['id'], step['duration_s'])
            step.pop('duration_uncertainty', None)
        projects.append({'id': pid, 'workflow': workflow, 'units': 10})
    return spec, projects


def test_schedule_tool_uses_real_engine_without_changing_design():
    spec, projects = inputs()
    before = copy.deepcopy(projects)
    session = ToolSession(TOOLS, [])
    result = session.tools['plan_projects'][1](lab_spec=spec, projects=projects)
    schedule = validate(result['project_schedule'], 'project_schedule')
    assert schedule['gain_vs_naive'] > .2
    assert schedule['gantt']
    assert session.project_schedule == schedule
    assert session.design is None
    assert projects == before
    projects[1].update(deadline_h=3, weight=5)
    assert session.plan_projects(spec, projects)['project_schedule']['objective'] == 'weighted_tardiness'


@pytest.mark.parametrize('mutation', ['duplicate_id', 'conflicting_hardware', 'unknown_catalog', 'cycle', 'batch', 'fanout', 'nan_weight', 'zero_units', 'negative_deadline'])
def test_invalid_or_unsupported_projects_never_reach_engine(mutation, monkeypatch):
    spec, projects = inputs()
    workflow = projects[1]['workflow']
    if mutation == 'duplicate_id': projects[1]['id'] = projects[0]['id']
    if mutation == 'conflicting_hardware': next(e for e in workflow['equipment'] if e['instance_id'] == 'hotel_1')['catalog_id'] = 'liconic_stx44'
    if mutation == 'unknown_catalog': workflow['equipment'][0]['catalog_id'] = 'invented_item'
    if mutation == 'cycle': workflow['steps'][0]['after'] = [workflow['steps'][-1]['id']]
    if mutation == 'batch': workflow['steps'][0]['batch_size'] = 2
    if mutation == 'fanout': workflow['steps'][0]['fan_out'] = 8
    if mutation == 'nan_weight': projects[1]['weight'] = float('nan')
    if mutation == 'zero_units': projects[1]['units'] = 0
    if mutation == 'negative_deadline': projects[1]['deadline_h'] = -1
    def unexpected(*args, **kwargs):
        pytest.fail('Invalid input reached the scheduling engine')
    monkeypatch.setattr('labforge.sim.portfolio.prioritise', unexpected)
    with pytest.raises(ValueError):
        ToolSession(TOOLS, []).plan_projects(spec, projects)


def test_schedule_output_is_validated(monkeypatch):
    spec, projects = inputs()
    monkeypatch.setattr('labforge.sim.portfolio.prioritise', lambda *args, **kwargs: {'recommended': 'invented'})
    with pytest.raises(ValueError):
        ToolSession(TOOLS, []).plan_projects(spec, projects)


@pytest.mark.parametrize('override', [None, 'user-selected-model'])
def test_planner_forwards_schedule_and_respects_model_override(monkeypatch, override):
    from labforge.agent.planner import run_turn
    spec, projects = inputs()
    block = {'type': 'tool_use', 'id': 'schedule_call', 'name': 'plan_projects',
             'input': {'lab_spec': spec, 'projects': projects}}
    text = {'type': 'text', 'text': 'Compare mean-duration policies; confirm with Monte Carlo.'}
    replies = iter([
        SimpleNamespace(content=[SimpleNamespace(**block, model_dump=lambda **kw: block)], stop_reason='tool_use'),
        SimpleNamespace(content=[SimpleNamespace(**text, model_dump=lambda **kw: text)], stop_reason='end_turn'),
    ])
    requests = []
    def create(**kwargs):
        requests.append(kwargs)
        return next(replies)
    sdk = SimpleNamespace(Anthropic=lambda **kw: SimpleNamespace(messages=SimpleNamespace(create=create)))
    monkeypatch.setitem(sys.modules, 'anthropic', sdk)
    monkeypatch.setattr('labforge.agent.planner.load_env', lambda: None)
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'test-only')
    if override: monkeypatch.setenv('ANTHROPIC_MODEL', override)
    else: monkeypatch.delenv('ANTHROPIC_MODEL', raising=False)
    output = run_turn([{'role': 'user', 'content': 'What order should these projects run?'}])
    assert output['completed']
    validate(output['project_schedule'], 'project_schedule')
    assert output['project_schedule']['gain_vs_naive'] > .2
    assert all(r['model'] == (override or 'claude-opus-5-5') for r in requests)
    assert 'workflow' not in output  # scheduling does not fabricate a new lab design
