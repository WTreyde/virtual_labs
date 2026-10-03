"""Run one planner turn without waiting for the frontend or gateway.

PYTHONPATH=backend python -m labforge.agent.cli --brief 'Design an enzyme screening lab...'
Pipe stdout to a JSON file, then pass that file with --session on the next turn.
Use --offline for an explicitly labelled fixture without an API key.
"""
import argparse
import json
import os
import sys
from pathlib import Path

from labforge.agent.planner import run_turn
from labforge.agent.config import load_env


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--brief', required=True, help='User request or follow-up')
    parser.add_argument('--session', type=Path, help='Previous JSON response containing history')
    parser.add_argument('--offline', action='store_true', help='Use worked fixture, not live planning')
    parser.add_argument('--max-steps', type=int, default=12)
    parser.add_argument('--env-file', type=Path, help='Use a specific .env file; shell variables still take precedence')
    args = parser.parse_args(argv)
    try:
        if args.env_file is not None and not args.env_file.is_file():
            raise FileNotFoundError('The specified .env file does not exist')
        if args.env_file is not None:
            os.environ['LABFORGE_ENV_FILE'] = str(args.env_file.resolve())
        load_env(args.env_file)
        if args.max_steps < 1:
            raise ValueError('--max-steps must be positive')
        if not args.offline and not os.environ.get('ANTHROPIC_API_KEY'):
            raise ValueError('ANTHROPIC_API_KEY is missing. Set it in your shell, or use --offline for the fixture.')
        history = []
        if args.session:
            session = json.loads(args.session.read_text())
            history = session.get('history')
            if not isinstance(history, list):
                raise ValueError('Session has no history; an offline fixture cannot be resumed as live planning.')
        history = [*history, {'role':'user', 'content':args.brief}]
        if args.offline:
            from labforge.agent.planner import offline_turn
            out = offline_turn()
        else:
            out = run_turn(history, max_steps=args.max_steps)
        print(json.dumps(out, indent=2))
        return 0 if out.get('completed', True) else 2
    except Exception as exc:
        # Credentials may appear in SDK error messages; do not print those messages.
        if isinstance(exc, (ValueError, FileNotFoundError, json.JSONDecodeError)):
            print(f'Planner could not run: {exc}', file=sys.stderr)
        elif isinstance(exc, ModuleNotFoundError):
            print(f'Missing dependency: {exc.name}. Install backend/.[dev] dependencies.', file=sys.stderr)
        else:
            print(f'Planner failed ({type(exc).__name__}). Check API access, model configuration and dependencies.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
