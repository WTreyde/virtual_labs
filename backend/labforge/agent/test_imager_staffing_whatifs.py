"""Staffing what-ifs preserve the recorded design outside declared changes."""
import json
from pathlib import Path

from labforge.agent.imager_staffing_whatifs import prepare_variant


RECORD = Path(__file__).parent / 'demo/scenarios_20261004_resim50/xchem.json'


def test_variants_change_only_growth_assignment_and_operator_availability():
    baseline = json.loads(RECORD.read_text())
    original = baseline['output']

    for shift_hours in (8, 16):
        spec, workflow, audit = prepare_variant(baseline, shift_hours)
        assert spec['operators'][0]['count'] == 3
        assert spec['operators'][0]['shift_hours'] == shift_hours
        assert audit['equipment_unchanged']
        assert audit['non_operator_lab_spec_unchanged']
        assert audit['unchanged_except_growth_assignment']
        assert original['workflow']['equipment'] == workflow['equipment']
        changed = {row['step_id'] for row in audit['changed_fields']}
        assert changed == {'grow_d1', 'grow_d2', 'grow_d3'}
        assert all(step['candidate_instances'] == ['imager_1']
                   for step in workflow['steps'] if step['id'] in changed)

    spec, workflow, audit = prepare_variant(baseline, 8, move_growth=False)
    assert spec['operators'][0]['count'] == 3
    assert not audit['changed_fields']
    assert workflow == original['workflow']

    assert original['lab_spec']['operators'][0]['count'] == 2
    assert original['lab_spec']['operators'][0]['shift_hours'] == 8
