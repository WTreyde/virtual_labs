"""Strand C benchmark arms. Strand D owns hidden checks and scoring.

python -m labforge.agent.benchmark --arm vanilla --task path/to/task.json
"""
import argparse
import json
import os
from pathlib import Path

from labforge.agent.config import load_env
from labforge.agent.planner import MODEL, run_turn
from labforge.agent.prompts import system_prompt
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
    import anthropic
    workspace = os.getenv('ANTHROPIC_WORKSPACE_ID', '').strip()
    client = anthropic.Anthropic(default_headers={'anthropic-workspace-id': workspace} if workspace else {})
    response = client.messages.create(model=os.getenv('ANTHROPIC_MODEL') or MODEL, max_tokens=16000,
        system=system_prompt() + '\nBENCHMARK ARM: you have no tools. Return ONLY a JSON object containing messages (role/content objects), lab_spec, workflow, claims. Claims must have status unverified. If you cannot design, return messages explaining the gap and omit the design. Do not claim you ran tools.',
        messages=history)
    text = ''.join(b.text for b in response.content if b.type == 'text').strip()
    if text.startswith('```') and text.endswith('```'):
        text = '\n'.join(text.splitlines()[1:-1])
    answer = json.loads(text)
    if not isinstance(answer, dict):
        raise ValueError('Vanilla arm must return a JSON object')
    # Ignore any claimed simulation/verification result: this arm has not run those tools.
    answer = {k: v for k, v in answer.items() if k in ('messages', 'lab_spec', 'workflow', 'claims')}
    for field in ('lab_spec', 'workflow'):
        if field in answer:
            validate(answer[field], field)
    for claim in answer.get('claims', []):
        claim['status'] = 'unverified'
        claim.pop('verified_value', None)
        claim.pop('verifier_note', None)
        validate(claim, 'claim')
    answer.update(completed=response.stop_reason == 'end_turn', benchmark_arm='vanilla', history=[*history, {'role': 'assistant', 'content': text}])
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
