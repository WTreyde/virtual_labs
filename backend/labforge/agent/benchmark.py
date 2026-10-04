"""Strand C benchmark arms. Strand D owns hidden checks and scoring.

python -m labforge.agent.benchmark --arm vanilla --task path/to/task.json
"""
import argparse
import json
import os
from pathlib import Path

from labforge.agent.config import load_env
from labforge.agent.planner import run_turn
from labforge.contracts import validate


def run_arm(arm: str, task: dict, *, on_event=None) -> dict:
    load_env()
    validate(task, 'bench_task')
    if not os.getenv('ANTHROPIC_API_KEY'):
        raise ValueError('Benchmark arms require live credentials; fixtures cannot measure agent performance')
    # Never expose task checks, expected behaviour or trap label to either model arm.
    history = [{'role': 'user', 'content': task['brief']}]
    if arm == 'platform':
        return run_turn(history, on_event=on_event)
    if arm != 'vanilla':
        raise ValueError('arm must be vanilla or platform')
    # One canonical no-tools protocol and parser lives with the scoring runner. Pass only
    # the public brief so hidden checks, expected behaviour and trap labels cannot leak.
    from labforge.bench.runner import _vanilla
    answer = _vanilla({'brief': task['brief']})
    answer['benchmark_arm'] = 'vanilla'
    return answer


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--arm', required=True, choices=['vanilla', 'platform'])
    parser.add_argument('--task', required=True, type=Path)
    parser.add_argument('--env-file', type=Path)
    args = parser.parse_args()
    if args.env_file:
        if not args.env_file.is_file():
            parser.error('The specified .env file does not exist')
        os.environ['LABFORGE_ENV_FILE'] = str(args.env_file.resolve())
        load_env(args.env_file)
    try:
        print(json.dumps(run_arm(args.arm, json.loads(args.task.read_text())), indent=2))
    except Exception as exc:
        parser.exit(1, f'Benchmark failed ({type(exc).__name__}); check credentials, task contract and model output.\n')


if __name__ == '__main__':
    main()
