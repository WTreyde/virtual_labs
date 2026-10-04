"""Recompute a recorded XChem design with crystal growth in the Rock Imager hotel.

This is deliberately deterministic: it changes only the candidate instance on crystal-growth
residence steps, then reruns layout, simulation, independent verification and the report. It
does not ask a model to rewrite the workflow or silently tune any assumptions.
"""
import argparse
import copy
import json
from pathlib import Path

from labforge.agent.demo_scenarios import catalog_gaps, check_scenario
from labforge.agent.errors import redacted_json
from labforge.agent.session import ToolSession
from labforge.agent.tools import TOOLS


def move_growth_to_imager(workflow: dict) -> tuple[dict, dict]:
    """Return a copy with growth residence moved to the existing Rock Imager."""
    changed = copy.deepcopy(workflow)
    equipment = {e['instance_id']: e['catalog_id'] for e in changed['equipment']}
    imagers = [instance for instance, catalog_id in equipment.items()
               if catalog_id == 'formulatrix_rock_imager_1000']
    if len(imagers) != 1:
        raise ValueError('The recorded design must contain exactly one Rock Imager 1000 instance.')
    imager = imagers[0]
    replacements = []
    for step in changed['steps']:
        if step['capability'] == 'incubation' and 'growth residence' in step['name'].lower():
            before = list(step['candidate_instances'])
            step['candidate_instances'] = [imager]
            replacements.append({'step_id': step['id'], 'before': before, 'after': [imager]})
    if not replacements:
        raise ValueError('The recorded design has no crystal-growth residence steps.')
    return changed, {'changed_fields': replacements,
                     'rule': 'Only candidate_instances on crystal-growth residence steps changed.'}


def record_whatif(baseline: dict) -> dict:
    """Run and independently check the single-change what-if."""
    original = baseline['output']
    lab_spec = copy.deepcopy(original['lab_spec'])
    workflow, audit = move_growth_to_imager(original['workflow'])
    layout_result = TOOLS['layout_and_simulate'][1](lab_spec=lab_spec, workflow=workflow)

    session = ToolSession(TOOLS, [])
    session.design = copy.deepcopy({'lab_spec': lab_spec, 'workflow': workflow, **layout_result})
    target = lab_spec['throughput_target']['value']
    claims = [
        {'id': 'imager_whatif_throughput',
         'statement': f'Imager-growth what-if reaches the target of {target:g} crystals/day.',
         'metric': 'throughput.p50', 'comparator': '>=', 'predicted_value': target, 'confidence': 0.5},
        {'id': 'imager_whatif_budget', 'statement': 'Imager-growth what-if stays within budget.',
         'metric': 'bom.total_usd', 'comparator': '<=',
         'predicted_value': lab_spec['constraints']['budget_usd'], 'confidence': 0.8},
        {'id': 'imager_whatif_layout', 'statement': 'Imager-growth what-if has no layout violations.',
         'metric': 'layout.violations', 'comparator': '==', 'predicted_value': 0, 'confidence': 0.8},
    ]
    checked = session.verify(claims)
    report = session.report()
    output = {
        'status': 'completed',
        'message': 'The recorded design was recomputed with growth residence in the Rock Imager.',
        'messages': [{'role': 'assistant', 'content':
                      'Deterministic what-if: crystal growth uses the Rock Imager storage hotel; all other workflow inputs are unchanged.'}],
        'completed': True, 'stop_reason': 'end_turn', 'lab_spec': lab_spec, 'workflow': workflow,
        **layout_result, **checked, **report, 'verification_complete': True,
    }
    gate = check_scenario('xchem', output, catalog_gaps()['xchem'])
    return {
        'baseline_source': baseline.get('source'),
        'method': 'deterministic recorded-design what-if; no model call',
        'change': 'Move crystal-growth residence from the STX44 to the Rock Imager 1000 storage hotel.',
        'audit': {
            **audit,
            'lab_spec_unchanged': lab_spec == original['lab_spec'],
            'step_count_unchanged': len(workflow['steps']) == len(original['workflow']['steps']),
            'equipment_unchanged': workflow['equipment'] == original['workflow']['equipment'],
        },
        'output': output, 'gate': gate,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('baseline', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    baseline = json.loads(args.baseline.read_text())
    args.output.write_text(redacted_json(record_whatif(baseline)))


if __name__ == '__main__':
    main()
