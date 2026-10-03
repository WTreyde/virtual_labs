"""Prevent setup-only human accounting and false Amass attribution."""
import copy

import pytest
from labforge.agent.session import ToolSession
from labforge.agent.tools import TOOLS
from labforge.agent.validation import validate_design
from labforge.contracts import load_example
from labforge.agent.test_demo_repair import previous_xchem


def test_shifter_still_requires_full_operator_time():
    run = previous_xchem()['output']
    with pytest.raises(ValueError, match='operator performs the entire'):
        validate_design(run['lab_spec'], run['workflow'])
    corrected = copy.deepcopy(run['workflow'])
    next(s for s in corrected['steps'] if s['capability'] == 'crystal_harvesting')['mode'] = 'manual'
    validate_design(run['lab_spec'], corrected)


def test_reviewed_source_authorises_citation_without_claiming_amass(monkeypatch):
    monkeypatch.setenv('AMASS_API_KEY', '')
    tools = {**TOOLS, 'layout_and_simulate': (TOOLS['layout_and_simulate'][0], lambda **kw: {
        'layout': load_example('layout'), 'sim_result': load_example('sim_result')})}
    session = ToolSession(tools, [])
    workflow = load_example('workflow')
    source = 'https://doi.org/10.1107/S2059798320014114'
    workflow['steps'][1]['evidence'] = [{'claim':'Retrieved mounting-rate comparison; not support for dispensing time', 'source':source, 'provider':'web'}]
    with pytest.raises(ValueError, match='Search evidence/catalog'):
        session.simulate(load_example('lab_spec'), workflow)
    result = session.search_evidence('crystal harvesting Shifter rates')
    assert result['status'] == 'unconfigured' and result['items'] == []
    assert result['reviewed_items'][0]['evidence']['provider'] == 'web'
    assert source in session.known_sources
    # Source admission does not prove numerical relevance: the report keeps that distinction.
    session.simulate(load_example('lab_spec'), workflow)
    report = session.report()['report_markdown']
    assert source in report and 'unconfigured' in report
    assert session.search_evidence('LC-MS sample duration')['reviewed_items'] == []
