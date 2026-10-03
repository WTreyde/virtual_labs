"""Hotel remedy is conditional and cannot erase a completed baseline."""
import copy
import json
from pathlib import Path

from labforge.agent import demo_scenarios as demo


def recorded_baseline():
    return json.loads((Path(__file__).parent / 'demo/scenarios_20261003_harvesting/xchem.json').read_text())['output']


def test_real_baseline_offers_hotel_remedy_but_not_camera_or_operator_repair():
    output = recorded_baseline()
    output['sim_result']['utilisation'].append({'instance_id': 'operator_only', 'busy_fraction': 1})
    before = copy.deepcopy(output)
    assert 'growth_hotel_1' in demo.hotel_whatif_request(output)
    assert output == before
    next(u for u in output['sim_result']['utilisation'] if u['instance_id'] == 'imager_1')['busy_fraction'] = .99
    assert demo.hotel_whatif_request(output) is None
    output['completed'] = False
    assert demo.hotel_whatif_request(output) is None


def test_failed_followup_preserves_baseline_and_separate_checkpoints(monkeypatch, tmp_path):
    baseline = recorded_baseline()
    baseline['history'] = [{'role': 'user', 'content': 'original brief'}]
    calls = []

    def fake_turn(history, on_event, **kwargs):
        calls.append(history)
        on_event({'type': 'model_call', 'step': 1})
        if len(calls) == 1:
            return copy.deepcopy(baseline)
        raise RuntimeError('follow-up unavailable')

    monkeypatch.setenv('ANTHROPIC_API_KEY', 'test-only')
    monkeypatch.setattr(demo, 'load_env', lambda: None)
    monkeypatch.setattr(demo, 'run_turn', fake_turn)
    monkeypatch.setattr('sys.argv', ['demo', '--scenario', 'xchem', '--live', '--hotel-whatif', '--out', str(tmp_path)])
    assert demo.main() == 2
    recorded = json.loads((tmp_path / 'xchem.json').read_text())
    assert recorded['output']['workflow'] == baseline['workflow']
    assert recorded['output']['sim_result'] == baseline['sim_result']
    assert (tmp_path / 'xchem-events.json').exists()
    assert (tmp_path / 'xchem-whatif-events.json').exists()
    assert json.loads((tmp_path / 'xchem-whatif.json').read_text())['output']['error']
    assert calls[1][0] == baseline['history'][0]
    assert len(calls) == 2
