"""A replay refresh changes stochastic results, not the recorded design."""
import copy
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from labforge.agent.replay_resim import resimulate_record


RECORD = Path(__file__).parent / 'demo/scenarios_20261004_placer/xchem.json'


def test_resimulation_preserves_design_and_enforces_sample_floor():
    original = json.loads(RECORD.read_text())
    simulated = copy.deepcopy(original['output']['sim_result'])
    simulated['replicates'] = 50
    with patch('labforge.agent.replay_resim.simulate', return_value=simulated) as simulate:
        refreshed = resimulate_record(original)

    simulate.assert_called_once_with(
        original['output']['lab_spec'], original['output']['workflow'],
        original['output']['layout'], replicates=50, seed=0,
    )
    assert original['output']['sim_result']['replicates'] == 10
    assert refreshed['output']['sim_result']['replicates'] == 50
    assert refreshed['resimulation']['lab_spec_unchanged']
    assert refreshed['resimulation']['workflow_unchanged']
    assert refreshed['resimulation']['layout_unchanged']
    assert refreshed['gate']['checks']['planner_sample_size']
    assert refreshed['gate']['passed']
    assert 'no new agent/model run' in refreshed['output']['messages'][-1]['content']
    event = next(e for e in refreshed['events']
                 if e.get('type') == 'tool_end' and e.get('name') == 'layout_and_simulate')
    assert event['output']['sim_result']['replicates'] == 50

    with pytest.raises(ValueError, match='at least 50'):
        resimulate_record(original, replicates=49)
