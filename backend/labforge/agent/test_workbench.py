"""Workbench request tests without binding a network port."""
import io
import json
import os
import unittest
from unittest.mock import Mock, patch
from labforge.agent.test_ui import Handler, TOKEN, safe_error


class WorkbenchTests(unittest.TestCase):
    def test_api_error_is_actionable_and_redacted(self):
        exc = Exception('not exposed')
        exc.body = {'error': {'message': 'Invalid parameter for key secret-test'}}
        exc.status_code = 400
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'secret-test'}):
            message = safe_error(exc)
        self.assertIn('HTTP 400', message)
        self.assertIn('Invalid parameter', message)
        self.assertNotIn('secret-test', message)

    def handler(self, path, body=None, authorized=True):
        handler = object.__new__(Handler)
        handler.path = path
        data = json.dumps(body or {}).encode()
        handler.headers = {'Content-Length':str(len(data)), 'X-Workbench-Token':TOKEN if authorized else 'invalid'}
        handler.rfile = io.BytesIO(data)
        handler.wfile = io.BytesIO()
        handler.send_response = Mock()
        handler.send_header = Mock()
        handler.end_headers = Mock()
        return handler

    def test_offline_stream_is_explicit_and_complete(self):
        h = self.handler('/run',{'brief':'test','offline':True})
        h.do_POST()
        events = [json.loads(line) for line in h.wfile.getvalue().splitlines()]
        self.assertEqual(events[0]['type'],'fixture')
        self.assertEqual(events[-1]['type'],'result')
        self.assertIn('timeline',events[-1]['output']['sim_result'])

    def test_request_requires_local_token(self):
        h = self.handler('/run',{'brief':'test'},authorized=False)
        h.do_POST()
        h.send_response.assert_called_once_with(403)

    def test_html_served_without_key(self):
        h = self.handler('/')
        h.do_GET()
        body = h.wfile.getvalue().decode()
        self.assertIn('LabForge planner workbench',body)
        self.assertIn(TOKEN,body)
        self.assertNotIn('__TOKEN__',body)


if __name__ == '__main__':
    unittest.main()
