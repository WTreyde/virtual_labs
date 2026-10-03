"""Offline contract and tool-loop checks: python -m unittest labforge.agent.test_first_layer."""
import copy
import json
import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from labforge.agent.planner import run_turn
from labforge.agent.prompts import system_prompt
from labforge.agent.tools import _search_catalog
from labforge.agent.validation import validate_design
from labforge.contracts import load_example


class FirstLayerTests(unittest.TestCase):
    def setUp(self):
        self.spec = load_example("lab_spec")
        self.workflow = load_example("workflow")

    def test_valid_example_and_prompt(self):
        validate_design(self.spec, self.workflow)
        self.assertIn('duration_uncertainty', system_prompt())
        self.assertIn('reaction stage 1', system_prompt())

    def test_invalid_designs(self):
        mutations = [
            lambda w: w.update(lab_spec_id="different"),
            lambda w: w["equipment"][0].update(catalog_id="invented"),
            lambda w: w["equipment"].append(copy.deepcopy(w["equipment"][0])),
            lambda w: w["steps"][0].update(candidate_instances=["missing"]),
            lambda w: w["steps"][1].update(candidate_instances=["reader_1"]),
            lambda w: w["steps"][0].update(after=["read"]),
            lambda w: w["steps"][0].update(after=["missing"]),
            lambda w: w["steps"][1].update(duration_uncertainty={"value":1800,"low":2000,"high":2500}),
            lambda w: w["steps"][1].update(fan_out=0),
            lambda w: w["steps"][1].update(candidate_instances=[]),
        ]
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                workflow = copy.deepcopy(self.workflow)
                mutate(workflow)
                with self.assertRaises(ValueError):
                    validate_design(self.spec, workflow)

    def test_catalog_sources_available(self):
        item = _search_catalog(capability="liquid_handling")["items"][0]
        self.assertTrue(item["source_urls"])
        self.assertIn("provenance", item)

    def test_offline_fixture_is_explicit(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY":"", "LABFORGE_ENV_FILE":"/missing/test/.env"}):
            out = run_turn([{"role":"user","content":"design chemistry"}])
        self.assertIn("offline demo", out["messages"][0]["content"])
        self.assertIn("timeline", out["sim_result"])

    def tool_block(self):
        data = {"type":"tool_use","id":"call_1","name":"layout_and_simulate",
                "input":{"lab_spec":self.spec,"workflow":self.workflow}}
        return SimpleNamespace(**data, model_dump=lambda **kw: data)

    def run_fake(self, fn, max_steps=2):
        tool = self.tool_block()
        text = SimpleNamespace(type="text", text="Computed result", model_dump=lambda **kw: {"type":"text","text":"Computed result"})
        create = Mock(side_effect=[SimpleNamespace(content=[tool],stop_reason="tool_use"),
                                   SimpleNamespace(content=[text],stop_reason="end_turn")])
        constructor = Mock(return_value=SimpleNamespace(messages=SimpleNamespace(create=create)))
        sdk = SimpleNamespace(Anthropic=constructor)
        with patch.dict(sys.modules, {"anthropic":sdk}), patch.dict(os.environ, {"ANTHROPIC_API_KEY":"test-only"}), patch.dict("labforge.agent.planner.TOOLS", {"layout_and_simulate":({},fn)}):
            out = run_turn([{"role":"user","content":"design"}], max_steps=max_steps, stream_text=False)
        self.assertNotIn('betas', create.call_args.kwargs)
        self.assertNotIn('fallbacks', create.call_args.kwargs)
        workspace_id = os.environ.get('ANTHROPIC_WORKSPACE_ID', '').strip()
        constructor.assert_called_once_with(default_headers={'anthropic-workspace-id': workspace_id} if workspace_id else {})
        return out

    def test_workspace_header_is_sent(self):
        with patch.dict(os.environ, {'ANTHROPIC_WORKSPACE_ID': 'wrk_test'}):
            self.run_fake(lambda **kw: {})

    def test_tool_result_keeps_ui_timeline_and_serializable_history(self):
        sim = load_example("sim_result")
        out = self.run_fake(lambda **kw: {"layout":load_example("layout"),"sim_result":sim})
        self.assertTrue(out["completed"])
        self.assertIn("timeline", out["sim_result"])
        result = json.loads(out["history"][2]["content"][0]["content"])
        self.assertNotIn("timeline", result["sim_result"])
        json.dumps(out)

    def test_validation_error_is_returned_to_model(self):
        def invalid(**kw):
            raise ValueError("unknown catalog_id")
        out = self.run_fake(invalid)
        result = out["history"][2]["content"][0]
        self.assertTrue(result["is_error"])
        self.assertIn("unknown catalog_id", result["content"])
        self.assertNotIn("workflow", out)

    def test_env_loading_preserves_shell_settings(self):
        from labforge.agent.config import load_env
        from tempfile import TemporaryDirectory
        from pathlib import Path
        with TemporaryDirectory() as temp:
            path = Path(temp) / ".env"
            path.write_text('ANTHROPIC_API_KEY="test-only"\nANTHROPIC_MODEL=claude-sonnet-5-5\n')
            with patch.dict(os.environ, {"ANTHROPIC_MODEL":"shell-model"}, clear=True):
                load_env(path)
                self.assertEqual(os.environ["ANTHROPIC_API_KEY"], "test-only")
                self.assertEqual(os.environ["ANTHROPIC_MODEL"], "shell-model")

    def test_env_loading_replaces_empty_shell_settings(self):
        from labforge.agent.config import load_env
        from tempfile import TemporaryDirectory
        from pathlib import Path
        with TemporaryDirectory() as temp:
            path = Path(temp) / ".env"
            path.write_text('ANTHROPIC_API_KEY="from-file"\nANTHROPIC_MODEL=claude-opus-5-5\n')
            with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "", "ANTHROPIC_MODEL": ""}, clear=True):
                load_env(path)
                self.assertEqual(os.environ["ANTHROPIC_API_KEY"], "from-file")
                self.assertEqual(os.environ["ANTHROPIC_MODEL"], "claude-opus-5-5")

    def test_cli_requires_key_for_live_run(self):
        from labforge.agent.cli import main
        from contextlib import redirect_stderr
        from io import StringIO
        err = StringIO()
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY":"", "LABFORGE_ENV_FILE":"/missing/test/.env"}), redirect_stderr(err):
            code = main(["--brief", "design"])
        self.assertEqual(code, 1)
        self.assertIn("ANTHROPIC_API_KEY is missing", err.getvalue())

    def test_cli_offline_is_valid_json(self):
        from labforge.agent.cli import main
        from contextlib import redirect_stdout
        from io import StringIO
        output = StringIO()
        with redirect_stdout(output):
            code = main(["--brief", "design", "--offline"])
        self.assertEqual(code, 0)
        self.assertIn("offline demo", json.loads(output.getvalue())["messages"][0]["content"])

    def test_exhaustion_is_explicit(self):
        out = self.run_fake(lambda **kw: {}, max_steps=1)
        self.assertFalse(out["completed"])
        self.assertIn("incomplete", out["messages"][0]["content"])


if __name__ == "__main__":
    unittest.main()
