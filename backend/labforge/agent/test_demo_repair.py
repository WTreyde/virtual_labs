"""Regression cases from the recorded combined-main demos."""
import copy
import json
from pathlib import Path

from labforge.agent.demo_scenarios import check_scenario, throughput_comparison
from labforge.agent.validation import validate_design
from labforge.verify.tamper import restore_protected


def previous_xchem():
    path = Path(__file__).parent / 'demo/scenarios_20261003_combined_main/xchem.json'
    return json.loads(path.read_text())


def test_puck_handling_preserves_transit_without_restoring_storage_duration():
    run = previous_xchem()
    workflow = copy.deepcopy(run['output']['workflow'])
    harvesting = next(s for s in workflow['steps'] if s['capability'] == 'crystal_harvesting')
    harvesting['mode'] = 'manual'
    harvesting['params']['units_per_run'] = 48  # Historical proposal explicitly states 48 crystals.
    loading = next(s for s in workflow['steps'] if s['id'] == 'load_shipper')
    loading.update(capability='manual_bench', candidate_instances=['bench_1'], duration_s=900)
    loading['duration_uncertainty'].update(value=900, low=300, high=1800)
    loading['params']['duration_basis'] = 'agent_estimate: manual puck loading at cryogenic handling bench'
    next(s for s in workflow['steps'] if s['id'] == 'synchrotron')['params']['transport_container_instance'] = 'dry_shipper_1'
    validate_design(run['output']['lab_spec'], workflow)
    _, restored = restore_protected(workflow)
    assert not any(r.startswith('load_shipper:') for r in restored)
    assert workflow['equipment'] == run['output']['workflow']['equipment']
    assert next(s for s in workflow['steps'] if s['id'] == 'synchrotron')['params']['queue_time_s'] == 345600
    assert loading['mode'] == 'manual' and loading['operator_role'] == 'scientist'


def test_gate_rejects_recorded_storage_mismatch_and_requires_independent_agreement():
    run = previous_xchem()
    gate = check_scenario('xchem', run['output'], {k: run['gate'][k] for k in ('missing_capabilities', 'catalog_ids')})
    assert not gate['checks']['puck_loading_is_handling']
    assert not gate['checks']['independent_throughput_agreement']
    assert not gate['passed']
    comparison = throughput_comparison(run['output'])
    assert comparison['planned_p50'] == 10.5 and comparison['verified_p50'] == 0.3
    corrected = copy.deepcopy(run['output'])
    for c in corrected['claims']:
        if c['metric'] == 'throughput.p50':
            c['verified_value'] = 9.5
    assert throughput_comparison(corrected)['agrees']
    for c in corrected['claims']:
        if c['metric'] == 'throughput.p50':
            c['verifier_note'] = 'checked against supplied result, not independently recomputed'
    assert not throughput_comparison(corrected)['agrees']
