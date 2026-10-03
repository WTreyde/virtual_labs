"""A per-crystal catalog duration cannot be used as a whole-plate duration."""
import json
from pathlib import Path

import pytest
from labforge.agent.validation import validate_design


def test_shifter_duration_is_scaled_to_the_actual_batch():
    output = json.loads((Path(__file__).parent / 'demo/scenarios_20261003_harvesting/xchem.json').read_text())['output']
    step = next(s for s in output['workflow']['steps'] if s['capability'] == 'crystal_harvesting')
    step['params']['units_per_run'] = 32
    step['duration_s'] = 35
    step.pop('duration_uncertainty', None)
    with pytest.raises(ValueError, match='per-crystal time as a plate duration'):
        validate_design(output['lab_spec'], output['workflow'])
    step['duration_s'] = 35 * 32
    validate_design(output['lab_spec'], output['workflow'])
    step['params'].pop('units_per_run')
    step['params'].pop('crystals_harvested_per_plate')
    with pytest.raises(ValueError, match='declare positive params.units_per_run'):
        validate_design(output['lab_spec'], output['workflow'])
