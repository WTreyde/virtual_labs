"""The imager remedy changes resource assignment, never the recorded assumptions."""
import copy
import json
from pathlib import Path

from labforge.agent.imager_growth_whatif import move_growth_to_imager


def test_only_growth_residence_moves_to_the_imager():
    root = Path(__file__).resolve().parents[3]
    baseline = json.loads((root / 'frontend/public/replays/fbdd.json').read_text())
    original = baseline['output']['workflow']
    changed, audit = move_growth_to_imager(original)

    expected = copy.deepcopy(original)
    growth_ids = []
    for step in expected['steps']:
        if step['capability'] == 'incubation' and 'growth residence' in step['name'].lower():
            growth_ids.append(step['id'])
            step['candidate_instances'] = ['imager_1']

    assert changed == expected
    assert original == baseline['output']['workflow']
    assert [row['step_id'] for row in audit['changed_fields']] == growth_ids
    assert 'soak_residence' not in growth_ids
