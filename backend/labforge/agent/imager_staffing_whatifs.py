"""Verify two deterministic XChem imager/staffing what-ifs without a model call.

Variant A moves crystal-growth residence to the existing Rock Imager and adds a
third operator. Variant B keeps that change and models a second staffed shift as
16 hours/day of availability for each of the three operators. Both variants use
the independent verifier with 50 Monte Carlo replicates.
"""
import argparse
import copy
import json
from pathlib import Path

from labforge.agent.errors import redacted_json
from labforge.agent.imager_growth_whatif import move_growth_to_imager
from labforge.agent.report import render_report
from labforge.contracts import validate
from labforge.layout.placer import generate_layout
from labforge.verify.verifier import brier_score, recompute, verify_claims


VERIFY_REPLICATES = 50
VERIFY_SEED = 12345
RECORDED_BASELINE_P50 = 424.0


def prepare_variant(baseline: dict, shift_hours: float) -> tuple[dict, dict, dict]:
    """Copy the design, move growth to the imager, and staff three operators."""
    original = baseline['output']
    lab_spec = copy.deepcopy(original['lab_spec'])
    if len(lab_spec.get('operators', [])) != 1:
        raise ValueError('Expected one recorded operator-role definition.')
    before_operators = copy.deepcopy(lab_spec['operators'])
    lab_spec['operators'][0]['count'] = 3
    lab_spec['operators'][0]['shift_hours'] = shift_hours
    workflow, growth_audit = move_growth_to_imager(original['workflow'])
    validate(lab_spec, 'lab_spec')
    return lab_spec, workflow, {
        **growth_audit,
        'operators_before': before_operators,
        'operators_after': copy.deepcopy(lab_spec['operators']),
        'unchanged_except_growth_assignment': all(
            before == after or before['id'] in {row['step_id'] for row in growth_audit['changed_fields']}
            for before, after in zip(original['workflow']['steps'], workflow['steps'])
        ),
        'equipment_unchanged': workflow['equipment'] == original['workflow']['equipment'],
        'non_operator_lab_spec_unchanged': {
            key: value for key, value in lab_spec.items() if key != 'operators'
        } == {
            key: value for key, value in original['lab_spec'].items() if key != 'operators'
        },
    }


def verify_variant(baseline: dict, name: str, shift_hours: float) -> dict:
    lab_spec, workflow, audit = prepare_variant(baseline, shift_hours)
    proposed_layout = generate_layout(lab_spec, workflow)
    verified = recompute(lab_spec, workflow, proposed_layout,
                         replicates=VERIFY_REPLICATES, seed=VERIFY_SEED)
    target = lab_spec['throughput_target']['value']
    claims = [
        {'id': f'{name}_beats_recorded_baseline',
         'statement': f'{name} reaches at least the recorded verified baseline of {RECORDED_BASELINE_P50:g} crystals/day.',
         'metric': 'throughput.p50', 'comparator': '>=',
         'predicted_value': RECORDED_BASELINE_P50, 'confidence': 0.5},
        {'id': f'{name}_meets_target',
         'statement': f'{name} reaches the requested target of {target:g} crystals/day.',
         'metric': 'throughput.p50', 'comparator': '>=',
         'predicted_value': target, 'confidence': 0.5},
        {'id': f'{name}_budget', 'statement': f'{name} stays within the recorded equipment budget.',
         'metric': 'bom.total_usd', 'comparator': '<=',
         'predicted_value': lab_spec['constraints']['budget_usd'], 'confidence': 0.8},
        {'id': f'{name}_layout', 'statement': f'{name} has no layout violations.',
         'metric': 'layout.violations', 'comparator': '==', 'predicted_value': 0, 'confidence': 0.8},
    ]
    checked = verify_claims(claims, workflow, verified['layout'], verified['sim'],
                            spec=lab_spec, recomputed=verified)
    report = render_report(lab_spec, workflow, verified['layout'], verified['sim'], claims=checked)
    return {
        'name': name,
        'method': 'deterministic recorded-design what-if; no agent/model call',
        'baseline_verified_p50': RECORDED_BASELINE_P50,
        'change': ('Move crystal-growth residence to the Rock Imager; staff three operators for '
                   f'{shift_hours:g} hours/day.'),
        'shift_model': ('The simulator represents a second shift as 16 hours/day availability for each operator; '
                        'it does not model shift handoff overhead.' if shift_hours == 16 else
                        'One 8-hour staffed shift.'),
        'verification_config': {'replicates': VERIFY_REPLICATES, 'seed': VERIFY_SEED},
        'audit': audit,
        'output': {
            'status': 'completed', 'completed': True, 'stop_reason': 'deterministic_verifier',
            'lab_spec': lab_spec, 'workflow': workflow, 'layout': verified['layout'],
            'sim_result': verified['sim'], 'claims': checked, 'brier': brier_score(checked),
            'report_markdown': report, 'verification_complete': True,
        },
        'restored_catalog_durations': verified['restored'],
    }


def variant_summary(record: dict) -> dict:
    sim = record['output']['sim_result']
    throughput = sim['throughput']
    operator_utilisation = [row for row in sim['utilisation']
                            if row['instance_id'].startswith('skilled_operator_')]
    binding = [b for b in sim['bottlenecks'] if b['severity'] in ('high', 'medium')]
    return {
        'verified_p50': throughput['p50'], 'p10': throughput['p10'], 'p90': throughput['p90'],
        'unit': throughput['unit'], 'baseline_verified_p50': RECORDED_BASELINE_P50,
        'delta_vs_baseline': round(throughput['p50'] - RECORDED_BASELINE_P50, 1),
        'beats_baseline': throughput['p50'] > RECORDED_BASELINE_P50,
        'operator_utilisation': operator_utilisation,
        'binding_limits': binding,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('baseline', type=Path)
    parser.add_argument('output_directory', type=Path)
    args = parser.parse_args()
    baseline = json.loads(args.baseline.read_text())
    args.output_directory.mkdir(parents=True, exist_ok=True)
    variants = {
        'third_operator': verify_variant(baseline, 'third_operator', 8),
        'second_shift': verify_variant(baseline, 'second_shift', 16),
    }
    for name, record in variants.items():
        (args.output_directory / f'{name}.json').write_text(redacted_json(record))
    summary = {
        'method': 'independent verifier recomputation; no agent/model call',
        'verification_config': {'replicates': VERIFY_REPLICATES, 'seed': VERIFY_SEED},
        'recorded_baseline_verified_p50': RECORDED_BASELINE_P50,
        'variants': {name: variant_summary(record) for name, record in variants.items()},
    }
    (args.output_directory / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')


if __name__ == '__main__':
    main()
