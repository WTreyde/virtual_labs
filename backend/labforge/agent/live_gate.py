"""Live multi-turn demo gate. Saves each completed result before starting the next turn.

PYTHONPATH=backend python -m labforge.agent.live_gate --env-file /path/to/.env --out /path/to/results
This makes chargeable Claude calls. Missing Amass is an explicit test of estimate disclosure.
"""
import argparse
import json
import os
from pathlib import Path
from datetime import datetime, timezone

from labforge.agent.config import load_env
from labforge.agent.errors import redacted_json, safe_error
from labforge.agent.planner import MODEL, run_turn

BRIEFS = [
    ('baseline', 'Design an enzyme-screening lab for 40 96-well plates/day, operating 24 hours/day in a 6 m by 4 m room, with a USD 400000 equipment budget. BSL1; no flammable solvents or cryogens. Dispense enzyme and substrate, seal, incubate at 37 C for one hour, then read absorbance at 405 nm. For this baseline use exactly one opentrons_flex, one agilent_plateloc, one liconic_stx44, one bmg_clariostar, one ur5e and one generic_plate_hotel. Use 1800 seconds per plate for dispensing, 10 seconds for sealing, 3600 for incubation and 90 for reading. These are estimates: label them and supply plausible uncertainty ranges. Do not add equipment or optimise this baseline. Search evidence for enzyme-screening protocol duration; if unavailable disclose that. Simulate, verify throughput/budget/layout claims and create the report. Do not claim measured or safety-certified performance.'),
    ('challenge', 'Now the target is 100 plates/day. Keep the same equipment, room, budget, durations and uncertainty ranges exactly unchanged. Rerun with the new target and submit a throughput.p50 >= 100 claim to the verifier so the explicit test is visible. Treat it as a candidate claim; do not assert it is true without support. Report whether it is refuted, retract it if so and create a report. Do not add equipment or revise the durations in this turn.'),
    ('revision', 'Add exactly one additional opentrons_flex liquid handler to the last design and let both units serve the existing dispensing step in parallel. Preserve the 100 plates/day target, all other equipment, room, budget and duration assumptions. Stop after this single equipment change. Rerun simulation, check throughput/budget/layout claims, create the report and compare with the previous result. Explicitly disclose any layout violations or unmet target; do not claim physical feasibility if the layout fails.'),
    ('vendor', 'For the current design, is it useful for a vendor to make the liquid handler faster, compared with making the reader faster? Call optimise_instrument for one liquid handler and the reader, and explain returned elasticity, headroom and next-bottleneck results. Keep the design unchanged and disclose layout and model limitations.'),
]


def check_gate(results):
    rows = {r['phase']: r['output'] for r in results}
    checks = {}
    for name in ('baseline', 'challenge', 'revision'):
        out = rows.get(name, {})
        checks[name + '_complete'] = bool(out.get('completed') and out.get('verification_complete') and out.get('report_markdown'))
    baseline, challenge, revision = (rows.get(k, {}) for k in ('baseline', 'challenge', 'revision'))
    checks['challenge_refuted'] = any(c.get('metric') == 'throughput.p50' and c.get('predicted_value') == 100 and c.get('comparator') == '>=' and c.get('status') == 'refuted' for c in challenge.get('claims', []))
    checks['revision_improves_throughput'] = revision.get('sim_result', {}).get('throughput', {}).get('p50', 0) > challenge.get('sim_result', {}).get('throughput', {}).get('p50', float('inf'))
    def unchanged(a, b, equipment=True):
        if not a.get('lab_spec') or not b.get('lab_spec'):
            return False
        x, y = a['workflow'], b['workflow']
        duration = lambda w: {s['id']: (s['duration_s'], s.get('duration_uncertainty')) for s in w['steps']}
        identities = lambda w: sorted((e['instance_id'], e['catalog_id']) for e in w['equipment'])
        return a['lab_spec']['room'] == b['lab_spec']['room'] and a['lab_spec'].get('constraints') == b['lab_spec'].get('constraints') and duration(x) == duration(y) and (not equipment or identities(x) == identities(y))
    checks['challenge_keeps_design_assumptions'] = unchanged(baseline, challenge)
    checks['revision_keeps_duration_assumptions'] = unchanged(challenge, revision, equipment=False)
    vendor = rows.get('vendor', {})
    sweeps = vendor.get('instrument_optimisations', {})
    checks['vendor_tools_ran'] = len(sweeps) >= 2 and any(v.get('catalog_id') == 'opentrons_flex' for v in sweeps.values()) and any(v.get('catalog_id') == 'bmg_clariostar' for v in sweeps.values())
    checks['vendor_preserves_design'] = unchanged(revision, vendor)
    return {'checks': checks, 'passed': all(checks.values()), 'scope': 'Live orchestration and model-based consistency, not real-world validation.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file', type=Path)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--resume-baseline', type=Path, help='Reuse an already saved baseline instead of charging for another baseline')
    args = parser.parse_args()
    if args.env_file:
        if not args.env_file.is_file():
            parser.error('The .env file does not exist')
        os.environ['LABFORGE_ENV_FILE'] = str(args.env_file.resolve())
    load_env()
    if not os.getenv('ANTHROPIC_API_KEY'):
        parser.error('Live gate requires Claude credentials')
    args.out.mkdir(parents=True, exist_ok=True)
    history, results = [], []
    briefs = BRIEFS
    if args.resume_baseline:
        baseline = json.loads(args.resume_baseline.read_text())
        if baseline.get('phase') != 'baseline' or not baseline.get('output', {}).get('completed'):
            parser.error('Resume file must contain a completed baseline')
        results.append(baseline)
        history = baseline['output']['history']
        (args.out / 'baseline.json').write_text(redacted_json(baseline))
        briefs = BRIEFS[1:]
    meta = {'model': os.getenv('ANTHROPIC_MODEL') or MODEL, 'started_at': datetime.now(timezone.utc).isoformat(), 'amass_configured': bool(os.getenv('AMASS_API_KEY'))}
    for phase, brief in briefs:
        print(f'Starting {phase}', flush=True)
        events = []
        def emit(event):
            events.append(event)
            if event['type'] in ('model_call', 'tool_start', 'tool_error'):
                print(phase, event['type'], event.get('name', event.get('step')), flush=True)
        try:
            out = run_turn([*history, {'role': 'user', 'content': brief}], on_event=emit, stream_text=True)
        except Exception as exc:
            (args.out / f'{phase}-error.json').write_text(redacted_json({'message': safe_error(exc), 'events': events}))
            parser.exit(1, safe_error(exc) + '\n')
        row = {'phase': phase, 'brief': brief, 'output': out, 'events': events}
        results.append(row)
        (args.out / f'{phase}.json').write_text(redacted_json(row))
        history = out.get('history', [])
        if not out.get('completed'):
            break
    summary = {**meta, **check_gate(results), 'phases': [{'name': r['phase'], 'completed': r['output'].get('completed'), 'throughput': r['output'].get('sim_result', {}).get('throughput'), 'claims': r['output'].get('claims', [])} for r in results]}
    (args.out / 'summary.json').write_text(redacted_json(summary))
    print(json.dumps(summary, indent=2), flush=True)
    return 0 if summary['passed'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
