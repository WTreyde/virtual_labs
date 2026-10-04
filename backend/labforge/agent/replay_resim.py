"""Refresh only the stochastic simulation in a recorded design; never call a model.

The recorded LabSpec, workflow and layout stay byte-for-byte equivalent as Python
objects. The refreshed run keeps the original live answer for audit, appends an
explicit deterministic resimulation note, regenerates the report, and reruns the
scenario gate against the larger Monte Carlo sample.
"""
import argparse
import copy
import json
from pathlib import Path

from labforge.agent.demo_scenarios import MIN_PLANNER_REPLICATES, catalog_gaps, check_scenario
from labforge.agent.errors import redacted_json
from labforge.agent.report import render_report
from labforge.agent.replay_summary import ROOT, summarise
from labforge.agent.tools import PLANNER_REPLICATES
from labforge.catalog.store import load_catalog
from labforge.sim.simulate import simulate


def resimulate_record(record: dict, replicates: int = PLANNER_REPLICATES, seed: int = 0) -> dict:
    """Return a copy with a fresh simulation and gate, preserving the recorded design."""
    if replicates < MIN_PLANNER_REPLICATES:
        raise ValueError(f'Resimulation requires at least {MIN_PLANNER_REPLICATES} replicates.')
    run = copy.deepcopy(record)
    output = run.get('output') or {}
    required = ('lab_spec', 'workflow', 'layout', 'sim_result')
    if any(not output.get(key) for key in required):
        raise ValueError('Recording must contain a completed lab_spec, workflow, layout and sim_result.')

    lab_spec = output['lab_spec']
    workflow = output['workflow']
    layout = output['layout']
    before = copy.deepcopy(output['sim_result'])
    refreshed = simulate(lab_spec, workflow, layout, replicates=replicates, seed=seed)
    output['sim_result'] = refreshed
    output['report_markdown'] = render_report(
        lab_spec, workflow, layout, refreshed,
        claims=output.get('claims'), evidence=output.get('evidence_searches'),
        claim_history=output.get('claim_history'),
        simulation_limitations=output.get('simulation_limitations'),
    )

    throughput = refreshed['throughput']
    verified = next((claim.get('verified_value') for claim in output.get('claims', [])
                     if claim.get('metric') == 'throughput.p50'
                     and 'recomputed by the verifier' in claim.get('verifier_note', '')), None)
    output.setdefault('messages', []).append({
        'role': 'assistant',
        'content': (
            'Deterministic replay refresh; no new agent/model run was made. The recorded design was '
            f're-simulated with {replicates} Monte Carlo replicates (seed {seed}). Planned '
            f'P10/P50/P90 is {throughput["p10"]} / {throughput["p50"]} / '
            f'{throughput["p90"]} {throughput["unit"]}. The independent verifier value from '
            f'the recorded checked claims is {verified}. LabSpec, workflow and layout are unchanged.'
        ),
    })

    for event in run.get('events', []):
        if event.get('type') == 'tool_end' and event.get('name') == 'layout_and_simulate':
            event.setdefault('output', {})['sim_result'] = copy.deepcopy(refreshed)
            event['summary'] = (f'Simulated {replicates} replicates at p50 {throughput["p50"]} '
                                f'{throughput["unit"]}; {len(layout.get("violations", []))} layout violations.')

    run['gate'] = check_scenario('xchem', output, catalog_gaps()['xchem'])
    catalog = load_catalog()
    run['catalog'] = {item['catalog_id']: catalog[item['catalog_id']]
                      for item in workflow['equipment'] if item['catalog_id'] in catalog}
    run['resimulation'] = {
        'method': 'deterministic recorded-design simulation; no model call',
        'seed': seed,
        'original_replicates': before.get('replicates'),
        'replicates': refreshed.get('replicates'),
        'original_throughput': before.get('throughput'),
        'lab_spec_unchanged': output['lab_spec'] == record['output']['lab_spec'],
        'workflow_unchanged': output['workflow'] == record['output']['workflow'],
        'layout_unchanged': output['layout'] == record['output']['layout'],
    }
    return run


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('recording', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--summary-output', type=Path,
                        help='Also write a baseline-only fbdd landing summary for the frontend owner.')
    parser.add_argument('--replicates', type=int, default=PLANNER_REPLICATES)
    parser.add_argument('--seed', type=int, default=0)
    args = parser.parse_args()
    record = json.loads(args.recording.read_text())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    run = resimulate_record(record, args.replicates, args.seed)
    try:
        run['source'] = str(args.output.resolve().relative_to(ROOT))
    except ValueError:
        pass
    args.output.write_text(redacted_json(run))
    if args.summary_output:
        args.summary_output.parent.mkdir(parents=True, exist_ok=True)
        args.summary_output.write_text(json.dumps(summarise('fbdd', run), indent=2) + '\n')


if __name__ == '__main__':
    main()
