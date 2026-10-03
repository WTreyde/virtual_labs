"""Cross-strand contracts: new catalog zones and model/tool history survive the gateway."""
from fastapi.testclient import TestClient
from unittest.mock import patch

from labforge.contracts import load_example, validate
from labforge.gateway import app
from labforge.layout.placer import generate_layout


def test_new_catalog_vibration_zone_validates():
    workflow = load_example('workflow')
    for equipment in workflow['equipment']:
        if equipment['instance_id'] == 'lh_1':
            equipment['catalog_id'] = 'beckman_echo_525'
    layout = generate_layout(load_example('lab_spec'), workflow)
    validate(layout, 'layout')
    assert any(zone['kind'] == 'vibration_free' for zone in layout['zones'])


def test_chat_preserves_full_tool_history_between_turns():
    history = [{'role':'assistant', 'content':[{'type':'tool_use', 'id':'call', 'name':'search_catalog', 'input':{}}]},
               {'role':'user', 'content':[{'type':'tool_result', 'tool_use_id':'call', 'content':'{}'}]},
               {'role':'user', 'content':'Increase the target'}]
    with patch('labforge.gateway.run_turn', return_value={'history':history, 'messages':[]}) as run:
        response = TestClient(app).post('/chat', json={'messages':history})
    assert response.status_code == 200
    assert response.json()['history'] == history
    run.assert_called_once_with(history)


def test_stream_route_uses_existing_adapter():
    async def stream(history):
        yield 'data: {"type":"result","output":{"history":[]}}\n\n'
    with patch('labforge.gateway.stream_turn', stream):
        response = TestClient(app).post('/chat/stream', json={'messages':[]})
    assert response.status_code == 200
    assert response.headers['content-type'].startswith('text/event-stream')
    assert '"type":"result"' in response.text
