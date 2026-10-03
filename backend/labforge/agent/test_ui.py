"""Local planner workbench: PYTHONPATH=backend python -m labforge.agent.test_ui."""
import argparse
import importlib.util
import json
import os
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from labforge.agent.config import load_env
from labforge.agent.errors import safe_error, redacted_json
from labforge.agent.planner import MODEL, offline_turn, run_turn
from labforge.agent.prompts import system_prompt

TOKEN = secrets.token_urlsafe(24)




class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def send_json(self, value, status=200):
        body = json.dumps(value).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == '/':
            html = Path(__file__).with_name('test_ui.html').read_text().replace('__TOKEN__', TOKEN)
            body = html.encode()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(body)
        elif self.path == '/status':
            load_env()
            self.send_json({'model': os.getenv('ANTHROPIC_MODEL') or MODEL,
                            'key_present': bool(os.getenv('ANTHROPIC_API_KEY')),
                            'dependencies': {name: importlib.util.find_spec(name) is not None for name in ['anthropic','simpy']}})
        elif self.path == '/prompt':
            self.send_json({'prompt': system_prompt()})
        else:
            self.send_json({'error':'Not found'},404)

    def do_POST(self):
        if self.path != '/run' or self.headers.get('X-Workbench-Token') != TOKEN:
            self.send_json({'error':'Invalid local request'},403)
            return
        try:
            size = int(self.headers.get('Content-Length','0'))
            if not 0 < size <= 2_000_000:
                raise ValueError()
            req = json.loads(self.rfile.read(size))
            if not isinstance(req.get('brief'),str) or not req['brief'].strip():
                raise ValueError()
            history = req.get('history',[])
            if not isinstance(history,list):
                raise ValueError()
        except (ValueError, TypeError):
            self.send_json({'error':'Invalid request'},400)
            return
        self.send_response(200)
        self.send_header('Content-Type','application/x-ndjson')
        self.send_header('Cache-Control','no-store')
        self.send_header('Connection','close')
        self.end_headers()
        self.close_connection = True
        def emit(event):
            # Do not disclose configured secrets even if an exception echoes one.
            data = redacted_json(event)
            self.wfile.write((data+'\n').encode())
            self.wfile.flush()
        try:
            load_env()
            if req.get('offline'):
                emit({'type':'fixture','message':'Offline example; no LLM or simulator called.'})
                out = offline_turn()
            else:
                if not os.getenv('ANTHROPIC_API_KEY'):
                    emit({'type':'error','message':'No Claude key configured in this working copy.'})
                    return
                out = run_turn([*history,{'role':'user','content':req['brief']}],on_event=emit,stream_text=True)
            emit({'type':'result','output':out})
        except (BrokenPipeError, ConnectionResetError):
            return
        except Exception as exc:
            emit({'type':'error','message':safe_error(exc)})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port',type=int,default=8011)
    parser.add_argument('--env-file', type=Path, help='Load credentials from this .env file instead of the workspace copy')
    args = parser.parse_args()
    if args.env_file is not None:
        if not args.env_file.is_file():
            parser.error('The specified .env file does not exist')
        os.environ['LABFORGE_ENV_FILE'] = str(args.env_file.resolve())
        load_env(args.env_file)
    server = ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    print(f'Planner workbench: http://127.0.0.1:{args.port}',flush=True)
    server.serve_forever()


if __name__ == '__main__':
    main()
