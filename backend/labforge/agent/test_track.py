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
        # These tests exercise claims over a deliberately mocked simulation. Keep the
        # verifier on those supplied results; independent recomputation is tested separately.
        from labforge.agent.session import verify_claims as original_verify
        def fixture_verify(claims, workflow, layout, sim):
            return original_verify(claims, workflow, layout, sim)
        patcher = patch('labforge.agent.session.verify_claims', fixture_verify)
        patcher.start()
        self.addCleanup(patcher.stop)
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

    def test_multiple_check_batches_preserve_refutation(self):
        self.design()
        self.session.verify([claim()])
        self.session.verify([{**claim(), 'id': 'budget', 'metric': 'bom.total_usd', 'comparator': '<=', 'predicted_value': 400000}])
        self.assertEqual(len(self.session.claims), 2)
        self.assertEqual(self.session.claims[0]['status'], 'refuted')
        self.assertIn('Refutation history', self.session.report()['report_markdown'])

    def test_capacity_bound_uses_correct_target_arithmetic(self):
        from labforge.agent.tools import capacity_checks
        self.spec['throughput_target']['value'] = 100
        checks = capacity_checks(self.spec, self.workflow)
        dispense = next(row for row in checks['steps'] if row['step_id'] == 'dispense')
        self.assertEqual(dispense['target_processing_seconds_per_day'], 180000)
        self.assertEqual(dispense['minimum_parallel_slots_for_target'], 3)
        self.assertEqual(dispense['upper_bound_plates_per_day'], 48)

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

    def test_nonplate_flow_needs_explicit_counting_sink(self):
        from labforge.agent.validation import validate_design
        self.spec['throughput_target']['unit'] = 'compounds_per_day'
        with self.assertRaisesRegex(ValueError, 'count_throughput'):
            validate_design(self.spec, self.workflow)
        self.workflow['steps'][-1]['params'] = {'count_throughput': True, 'units_per_labware': 96}
        validate_design(self.spec, self.workflow)
        self.workflow['steps'][-1]['params']['units_per_labware'] = 0
        with self.assertRaisesRegex(ValueError, 'positive'):
            validate_design(self.spec, self.workflow)

    def test_unsupported_throughput_stays_unverifiable_and_report_explains_why(self):
        self.result['simulation_limitations'] = ['Legacy simulator does not convert plate output units.']
        self.design()
        checked = self.session.verify([claim()])['claims'][0]
        self.assertEqual(checked['status'], 'unverifiable')
        self.assertNotIn('verified_value', checked)
        self.assertIn('Simulator limitations', self.session.report()['report_markdown'])

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

    def test_new_verifier_receives_backend_spec_for_independent_recompute(self):
        self.design()
        seen = {}
        def independent(claims, workflow, layout, sim, spec=None):
            seen['spec'] = spec
            return [{**c, 'status': 'refuted', 'verified_value': 12,
                     'verifier_note': 'recomputed by the verifier'} for c in claims]
        with patch('labforge.agent.session.verify_claims', independent):
            result = self.session.verify([claim()])
        self.assertEqual(seen['spec'], self.spec)
        self.assertEqual(result['claims'][0]['verified_value'], 12)

    def test_legacy_verifier_keeps_four_argument_contract(self):
        self.design()
        def legacy(claims, workflow, layout, sim):
            return [{**c, 'status': 'refuted', 'verified_value': 20} for c in claims]
        with patch('labforge.agent.session.verify_claims', legacy):
            self.assertEqual(self.session.verify([claim()])['claims'][0]['verified_value'], 20)

    def test_report_discloses_independent_verifier_disagreement(self):
        self.design()
        self.session.claims = [{**claim(), 'status':'refuted', 'verified_value':0.3}]
        text = self.session.report()['report_markdown']
        self.assertIn('Independent verifier comparison', text)
        self.assertIn('not present the planning number as independently confirmed', text)

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

    def test_vendor_sweeps_preserve_design_and_reject_catalog_ids(self):
        self.design()
        before = copy.deepcopy(self.session.design)
        output = self.session.optimise('lh_1')
        self.assertEqual(output['simulation_config'], {'hours': 48, 'replicates': 8, 'seed': 0})
        self.assertTrue(output['cycle_time_scope'])
        self.assertIn('whole affected step', output['limitation'])
        result = output['instrument_optimisation']
        self.assertEqual(self.session.design, before)
        self.assertEqual(result['instance_id'], 'lh_1')
        params = {s['parameter'] for s in result['sweeps']}
        self.assertTrue({'cycle_time', 'capacity'} <= params)
        self.assertGreater(result['sweeps'][0]['elasticity'], 0)
        with self.assertRaises(ValueError):
            self.session.optimise('opentrons_flex')


class VerifierIntegrationTests(unittest.TestCase):
    def test_real_engine_checks_are_independent_when_spec_api_is_available(self):
        import inspect
        from labforge.agent.session import verify_claims
        session = ToolSession(TOOLS, [])
        session.simulate(load_example('lab_spec'), load_example('workflow'))
        checked = session.verify([claim(500)])['claims']
        self.assertEqual(checked[0]['status'], 'refuted')
        if 'spec' in inspect.signature(verify_claims).parameters:
            self.assertIn('recomputed by the verifier', checked[0]['verifier_note'])


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


class ValidationAdapterTests(unittest.TestCase):
    def test_reported_cost_is_withheld_and_only_valid_live_design_returned(self):
        from labforge.agent.validation_cases import design_from_brief
        spec, workflow = load_example('lab_spec'), load_example('workflow')
        case = {'brief': 'Design an enzyme screening lab', 'reported': {'cost': {'value_usd': 99912345}}, 'notes': 'Do not reveal this private answer'}
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-only'}), patch('labforge.agent.validation_cases.run_turn', return_value={'completed': True, 'lab_spec': spec, 'workflow': workflow}) as run:
            self.assertEqual(design_from_brief(case), workflow)
        run.assert_called_once_with([{'role': 'user', 'content': case['brief']}], stream_text=True)

    def test_unanswered_requirements_or_offline_access_are_not_fixture_predictions(self):
        from labforge.agent.validation_cases import design_from_brief
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': ''}), patch('labforge.agent.validation_cases.load_env'), patch('labforge.agent.validation_cases.run_turn') as run:
            self.assertIsNone(design_from_brief({'brief': 'Incomplete brief'}))
            run.assert_not_called()
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-only'}), patch('labforge.agent.validation_cases.run_turn', return_value={'completed': True, 'messages': [{'role': 'assistant', 'content': 'What room size?'}]}):
            self.assertIsNone(design_from_brief({'brief': 'Incomplete brief'}))


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
            out = run_turn([{'role': 'user', 'content': 'design'}], on_event=events.append, stream_text=False)
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
            out = run_turn([{'role': 'user', 'content': 'hello'}], on_event=events.append)
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
