"""Landing facts must come from the same record as the animated replay."""
import json
from pathlib import Path

import pytest
from labforge.agent.replay_summary import _load_imager_whatif, summarise

REPLAYS = Path(__file__).resolve().parents[3] / 'frontend/public/replays'


@pytest.mark.parametrize('name', ['chem', 'fbdd'])
def test_landing_summary_preserves_recorded_results_and_refutations(name):
    record = json.loads((REPLAYS / f'{name}.json').read_text())
    whatif = _load_imager_whatif(record) if name == 'fbdd' else None
    summary = summarise(name, record, whatif)
    assert summary == json.loads((REPLAYS / f'{name}.summary.json').read_text())
    o = record['output']
    for key in ('p10', 'p50', 'p90', 'unit'):
        assert summary['headline_throughput'][key] == o['sim_result']['throughput'][key]
    assert summary['headline_throughput']['verified_p50'] == next(c['verified_value'] for c in o['claims'] if c['metric'] == 'throughput.p50')
    assert summary['bottleneck']['instance_id'] in {e['instance_id'] for e in o['workflow']['equipment']}
    required = {'throughput.p50', 'bom.total_usd', 'layout.violations'}
    refuted = any(c['metric'] in required and c['status'] == 'refuted' for c in o['claims'])
    assert summary['gate_passed'] == (record['gate']['passed'] and not refuted)
    for c in o['claims']:
        if c['status'] == 'refuted' and c['metric'] != 'layout.violations':
            assert any(c['statement'] in limit for limit in summary['limits'])


def test_fbdd_summary_reports_the_separate_imager_growth_whatif():
    root = Path(__file__).resolve().parents[3]
    record = json.loads((root / 'backend/labforge/agent/demo/scenarios_20261004_resim50/xchem.json').read_text())
    whatif = _load_imager_whatif(record)
    assert whatif['kind'] == 'imager_staffing_bundle'
    summary = summarise('fbdd', record, whatif)
    assert 'imager_growth_whatif' not in summary  # do not ship the stale 10-replicate result
    staffing = summary['imager_staffing_whatifs']
    assert staffing['verification_config']['replicates'] == 50
    assert set(staffing['variants']) == {'third_operator_only', 'third_operator', 'second_shift'}
    assert staffing['variants']['third_operator']['verified_p50'] == 634.7
    assert staffing['variants']['second_shift']['verified_p50'] == 1306.7
    assert staffing['isolated_effects'] is not None
    assert 'isolates added staff' in staffing['attribution']
