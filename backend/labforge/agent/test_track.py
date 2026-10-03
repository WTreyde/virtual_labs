"""Strand C consistency, evidence and benchmark regression checks."""
import copy
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
from unittest.mock import MagicMock

from labforge.agent.amass import retrieve_literature
from labforge.agent.session import ToolSession
from labforge.agent.tools import TOOLS
from labforge.agent.report import render_report
from labforge.contracts import load_example


def claim(value=100):
    return {'id': 'throughput', 'statement': 'Reaches target', 'metric': 'throughput.p50',
            'comparator': '>=', 'predicted_value': value, 'confidence': 0.9}


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.spec = load_example('lab_spec')
        self.workflow = load_example('workflow')
        self.result = {'layout': load_example('layout'), 'sim_result': load_example('sim_result')}
        self.simulate = Mock(side_effect=lambda **kw: copy.deepcopy(self.result))
        self.tools = {**TOOLS, 'layout_and_simulate': (TOOLS['layout_and_simulate'][0], self.simulate)}
        self.session = ToolSession(self.tools, [])

    def design(self):
        self.session.simulate(self.spec, self.workflow)

    def test_refutation_then_revision_clears_stale_claims(self):
        self.design()
        out = self.session.verify([claim()])
        self.assertEqual(out['claims'][0]['status'], 'refuted')
        self.assertGreater(out['brier'], 0.8)
        self.result['sim_result']['throughput']['p50'] = 110
        self.design()
        self.assertEqual(self.session.claims, [])
        self.assertEqual(self.session.verify([claim()])['claims'][0]['status'], 'supported')

    def test_spoofed_status_is_ignored_and_invalid_numbers_rejected(self):
        self.design()
        c = {**claim(), 'status': 'supported', 'verified_value': 999}
        checked = self.session.verify([c])['claims'][0]
        self.assertEqual(checked['status'], 'refuted')
        self.assertNotEqual(checked['verified_value'], 999)
        with self.assertRaises(ValueError):
            self.session.verify([{**claim(), 'confidence': float('nan')}])
        with self.assertRaises(ValueError):
            self.session.verify([claim(), claim()])

    def test_verification_requires_design_and_restores_by_recomputing(self):
        with self.assertRaises(ValueError):
            self.session.verify([claim()])
        history = [{'role': 'assistant', 'content': [{'type': 'tool_use', 'name': 'layout_and_simulate',
            'input': {'lab_spec': self.spec, 'workflow': self.workflow}}]},
            {'role': 'user', 'content': [{'type': 'tool_result', 'content': json.dumps({'sim_result': {'throughput': {'p50': 999}}})}]}]
        session = ToolSession(self.tools, history)
        out = session.verify([claim()])
        self.simulate.assert_called_once()
        self.assertEqual(out['claims'][0]['status'], 'refuted')

    def test_unknown_cost_is_unverifiable_report_is_honest(self):
        self.design()
        with patch('labforge.agent.session.get_item', return_value={'price_usd_estimate': None}):
            out = self.session.verify([{**claim(), 'metric': 'bom.total_usd'}])
        self.assertEqual(out['claims'][0]['status'], 'unverifiable')
        with patch('labforge.agent.report.get_item', return_value={'vendor': 'Example', 'model': 'Unknown price'}):
            text = self.session.report()['report_markdown']
        self.assertIn('subtotal is incomplete', text)
        self.assertIn('Unknown', text)

    def test_fabricated_source_is_rejected(self):
        self.workflow['steps'][0]['evidence'] = [{'claim': 'Fast', 'source': 'invented-doi', 'provider': 'amass'}]
        with self.assertRaises(ValueError):
            self.design()
        self.simulate.assert_not_called()

    def test_report_covers_checked_claims_and_estimates(self):
        self.design()
        self.session.verify([claim()])
        text = self.session.report()['report_markdown']
        for expected in ('Executive summary', 'refuted', 'Assumptions', 'not measured throughput', 'agent_estimate'):
            self.assertIn(expected, text)

    def test_real_simulator_and_verifier_loop(self):
        session = ToolSession(TOOLS, [])
        session.simulate(self.spec, self.workflow)
        out = session.verify([claim(500)])
        self.assertEqual(out['claims'][0]['status'], 'refuted')
        self.assertIn('refuted', session.report()['report_markdown'])

    def test_zero_time_loop_and_nonfinite_design_are_rejected(self):
        from labforge.agent.validation import validate_design
        workflow = copy.deepcopy(self.workflow)
        for step in workflow['steps']:
            step['duration_s'] = 0
        with self.assertRaises(ValueError):
            validate_design(self.spec, workflow)
        workflow = copy.deepcopy(self.workflow)
        workflow['steps'][0]['duration_s'] = float('nan')
        with self.assertRaises(ValueError):
            validate_design(self.spec, workflow)


class EvidenceTests(unittest.TestCase):
    def test_no_key_is_honest(self):
        with patch.dict(os.environ, {'AMASS_API_KEY': ''}):
            self.assertEqual(retrieve_literature('enzyme')['status'], 'unconfigured')

    def test_documented_envelopes_and_cache(self):
        for envelope in (lambda r: r, lambda r: {'records': r}):
            with self.subTest(envelope=envelope), tempfile.TemporaryDirectory() as directory:
                response = Mock()
                response.json.return_value = {'data': envelope([{'amassId': 'AMBC_test', 'title': 'Enzyme protocol', 'doi': '10.example/test', 'abstract': 'Candidate abstract', 'isRetracted': False}])}
                with patch.dict(os.environ, {'AMASS_API_KEY': 'test-secret'}), patch('labforge.agent.amass.httpx.get', return_value=response) as get:
                    first = retrieve_literature('enzyme', cache_dir=Path(directory))
                    cached = retrieve_literature('enzyme', cache_dir=Path(directory))
                self.assertEqual(first['status'], 'retrieved')
                self.assertEqual(cached['status'], 'cached')
                get.assert_called_once()
                self.assertEqual(first['items'][0]['evidence']['source'], 'https://doi.org/10.example/test')
                self.assertNotIn('test-secret', next(Path(directory).glob('*.json')).read_text())

    def test_bad_response_is_unavailable(self):
        response = Mock()
        response.json.return_value = {'data': {'wrong': []}}
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'AMASS_API_KEY': 'test-secret'}), patch('labforge.agent.amass.httpx.get', return_value=response):
            self.assertEqual(retrieve_literature('enzyme', cache_dir=Path(directory))['status'], 'unavailable')


class BenchmarkTests(unittest.TestCase):
    def test_vanilla_never_receives_hidden_checks_and_cannot_fake_verification(self):
        from labforge.agent.benchmark import run_arm
        task = json.loads((Path(__file__).parents[1] / 'bench/tasks/enzyme_infeasible.json').read_text())
        answer = {'messages': [], 'claims': [{**claim(), 'status': 'supported', 'verified_value': 999}], 'sim_result': {'fake': True}}
        create = Mock(return_value=SimpleNamespace(content=[SimpleNamespace(type='text', text=json.dumps(answer))], stop_reason='end_turn'))
        sdk = SimpleNamespace(Anthropic=lambda **kw: SimpleNamespace(messages=SimpleNamespace(create=create)))
        with patch.dict(sys.modules, {'anthropic': sdk}), patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-only'}):
            out = run_arm('vanilla', task)
        self.assertEqual(create.call_args.kwargs['messages'], [{'role': 'user', 'content': task['brief']}])
        self.assertNotIn('tools', create.call_args.kwargs)
        self.assertNotIn('sim_result', out)
        self.assertEqual(out['claims'][0]['status'], 'unverified')
        self.assertNotIn('verified_value', out['claims'][0])


class PlannerIntegrationTests(unittest.TestCase):
    setUp = SessionTests.setUp
    def test_model_loop_returns_checked_design_and_report(self):
        from labforge.agent.planner import run_turn
        claims = [claim(), {**claim(), 'id': 'layout', 'metric': 'layout.violations', 'comparator': '==', 'predicted_value': 0},
                  {**claim(), 'id': 'budget', 'metric': 'bom.total_usd', 'comparator': '<=', 'predicted_value': 400000}]
        def block(name, inputs, identifier):
            data = {'type': 'tool_use', 'id': identifier, 'name': name, 'input': inputs}
            return SimpleNamespace(**data, model_dump=lambda **kw: data)
        text = {'type': 'text', 'text': 'The 100 plates/day claim is refuted.'}
        create = Mock(side_effect=[
            SimpleNamespace(content=[block('layout_and_simulate', {'lab_spec': self.spec, 'workflow': self.workflow}, 'design')], stop_reason='tool_use'),
            SimpleNamespace(content=[block('verify_claims', {'claims': claims}, 'check')], stop_reason='tool_use'),
            SimpleNamespace(content=[SimpleNamespace(**text, model_dump=lambda **kw: text)], stop_reason='end_turn')])
        sdk = SimpleNamespace(Anthropic=lambda **kw: SimpleNamespace(messages=SimpleNamespace(create=create)))
        events = []
        with patch.dict(sys.modules, {'anthropic': sdk}), patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-only'}), patch('labforge.agent.planner.TOOLS', self.tools):
            out = run_turn([{'role': 'user', 'content': 'design'}], on_event=events.append)
        self.assertTrue(out['verification_complete'])
        self.assertEqual(out['claims'][0]['status'], 'refuted')
        self.assertIn('refuted', out['report_markdown'])
        self.assertIn('timeline', out['sim_result'])
        self.assertTrue(any(e.get('name') == 'verify_claims' for e in events))

    def test_sdk_text_stream_emits_deltas(self):
        from labforge.agent.planner import run_turn
        text = {'type': 'text', 'text': 'Hello'}
        stream = MagicMock()
        stream.__enter__.return_value = stream
        stream.text_stream = iter(['Hel', 'lo'])
        stream.get_final_message.return_value = SimpleNamespace(content=[SimpleNamespace(**text, model_dump=lambda **kw: text)], stop_reason='end_turn')
        sdk = SimpleNamespace(Anthropic=lambda **kw: SimpleNamespace(messages=SimpleNamespace(stream=lambda **kw: stream)))
        events = []
        with patch.dict(sys.modules, {'anthropic': sdk}), patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-only'}):
            out = run_turn([{'role': 'user', 'content': 'hello'}], on_event=events.append, stream_text=True)
        self.assertEqual(out['messages'][0]['content'], 'Hello')
        self.assertEqual(''.join(e['text'] for e in events if e['type'] == 'text_delta'), 'Hello')


class StreamingTests(unittest.IsolatedAsyncioTestCase):
    async def test_sse_frames_and_secret_redaction(self):
        from labforge.agent.streaming import stream_turn
        def run(history, on_event, stream_text):
            on_event({'type': 'text_delta', 'text': 'test-secret'})
            return {'messages': [], 'history': history}
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-secret'}), patch('labforge.agent.streaming.run_turn', side_effect=run):
            frames = [frame async for frame in stream_turn([])]
        self.assertEqual(len(frames), 2)
        self.assertIn('[redacted]', frames[0])
        self.assertIn('"type": "result"', frames[-1])
        self.assertTrue(all(frame.startswith('data: ') and frame.endswith('\n\n') for frame in frames))


if __name__ == '__main__':
    unittest.main()
