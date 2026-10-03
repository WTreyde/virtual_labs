"""Repeatable chemistry/XChem acceptance run; catalog gaps are failures, not fixture passes."""
import argparse
import json
import os
from pathlib import Path

from labforge.agent.config import load_env
from labforge.agent.errors import redacted_json, safe_error
from labforge.agent.planner import MODEL, run_turn
from labforge.agent.validation import validate_design
from labforge.catalog.store import load_catalog

SCENARIOS = {
    'chemistry': {
        'brief': 'Design the full combinatorial chemistry demo: 8 boronic acids x 12 aryl-bromide amines x 8 acids = 768 products, using Suzuki coupling then amide coupling. Include stock preparation, both reaction setups and runs, workup/filtration, purification, evaporation, LC-MS QC, compound storage and biochemical fluorescence screening against a supplied purified BRD4 protein target. Target 768 compounds/day in a 10 m x 8 m room, USD 2000000 equipment budget, instruments operating 24 h/day, one skilled operator on an 8 h shift. Use 96-well reaction blocks and appropriate assay plates. Flammable solvents and toxic reagents require ventilated/inert synthesis and separated storage. Estimate durations/yields only with explicit uncertainty; I permit a provisional planning model. Search catalog and evidence, preserve library/plate arithmetic, then simulate, verify throughput/budget/layout claims and report. If any essential equipment is missing, list it and stop rather than substituting unrelated equipment or producing a partial lab as an end-to-end design.',
        'required': ['liquid_handling', 'powder_dosing', 'reaction', 'heating_stirring', 'filtration', 'solid_phase_extraction', 'evaporation', 'lcms', 'compound_storage', 'inert_atmosphere', 'ventilated_enclosure', 'fluorescence_read', 'manual_bench'],
    },
    'xchem': {
        'brief': 'Design the full XChem-style fragment-screening demo: express a soluble E. coli target protein, harvest cells, lyse/clarify, purify, QC/concentrate, set crystallisation drops, grow and image crystals, select drops, soak fragments, manually harvest crystals, cryo-cool/load pucks and ship to an external synchrotron for diffraction followed by in-silico hit analysis. No in-house X-ray instrument. Target 300 crystals/day in a steady-state 10 m x 8 m room, USD 2000000 equipment budget, instruments operating 24 h/day with two skilled operators on 8 h shifts. BSL1, high-g centrifuges and cryogens require separated work areas and ventilation/O2 monitoring. Use appropriate flasks, columns, crystallisation plates and pucks. State protein-yield and crystal-success assumptions explicitly; I permit provisional estimates with wide uncertainty. Preserve manual harvesting, crystal growth and the external shipping/beamline queue. Search catalog and evidence, then simulate, verify throughput/budget/layout claims and report. If essential equipment is absent, list it and stop; do not invent catalog entries or call a partial workflow end to end.',
        'required': ['cell_culture', 'shaking', 'centrifugation', 'cell_lysis', 'protein_purification', 'protein_qc', 'concentration_measurement', 'crystallization_setup', 'crystal_imaging', 'crystal_soaking', 'crystal_harvesting', 'cryo_cooling', 'cold_storage', 'manual_bench'],
    },
}


def catalog_gaps():
    items = load_catalog()
    available = {cap for item in items.values() for cap in item['capabilities']}
    return {name: {'missing_capabilities': sorted(set(case['required']) - available),
                   'catalog_ids': sorted(items)} for name, case in SCENARIOS.items()}


def check_scenario(name, output, coverage):
    workflow = output.get('workflow', {})
    steps = workflow.get('steps', [])
    checks = {
        'catalog_complete': not coverage['missing_capabilities'],
        'design_returned': bool(output.get('lab_spec') and workflow and output.get('sim_result')),
        'turn_complete': bool(output.get('completed')),
        'claims_checked': bool(output.get('verification_complete')),
        'report_created': bool(output.get('report_markdown')),
        'full_pipeline': (set(SCENARIOS[name]['required']) - {'inert_atmosphere', 'ventilated_enclosure', 'cold_storage', 'manual_bench'}) <= {s['capability'] for s in steps},
    }
    if checks['design_returned']:
        validate_design(output['lab_spec'], workflow)
    if name == 'xchem':
        checks['external_diffraction'] = any(s['mode'] == 'external' and s['capability'] in ('xray_diffraction', 'external_service') for s in steps if s.get('mode'))
        checks['no_inhouse_xray'] = not any('xray_diffraction' in load_catalog()[e['catalog_id']]['capabilities'] for e in workflow.get('equipment', []))
        checks['manual_harvesting'] = any(s['capability'] == 'crystal_harvesting' and s.get('mode') in ('manual', 'semi_automated') for s in steps)
    return {'passed': all(checks.values()), 'checks': checks, **coverage}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file', type=Path)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--live', action='store_true', help='Make chargeable planner calls for both scenarios.')
    args = parser.parse_args()
    if args.env_file:
        if not args.env_file.is_file(): parser.error('Environment file does not exist')
        os.environ['LABFORGE_ENV_FILE'] = str(args.env_file.resolve())
    load_env()
    if args.live and not os.getenv('ANTHROPIC_API_KEY'):
        parser.error('Live demos require credentials; offline fixtures cannot satisfy these gates.')
    args.out.mkdir(parents=True, exist_ok=True)
    gaps = catalog_gaps()
    (args.out / 'catalog_gaps.json').write_text(redacted_json(gaps))
    summary = {}
    for name, case in SCENARIOS.items():
        if not args.live:
            summary[name] = {'passed': False, 'status': 'not_run', **gaps[name]}
            continue
        print('Starting ' + name, flush=True)
        events = []
        def emit(event):
            if event['type'] in ('model_call', 'tool_start', 'tool_error'):
                events.append(event)
                print(name, event['type'], event.get('name', event.get('step')), flush=True)
        try:
            output = run_turn([{'role': 'user', 'content': case['brief']}], on_event=emit, stream_text=True)
            summary[name] = check_scenario(name, output, gaps[name])
        except Exception as exc:
            output = {'error': safe_error(exc)}
            summary[name] = {'passed': False, 'error': safe_error(exc), **gaps[name]}
        output.pop('history', None)
        output.get('sim_result', {}).pop('timeline', None)
        (args.out / f'{name}.json').write_text(redacted_json({'brief': case['brief'], 'model': os.getenv('ANTHROPIC_MODEL') or MODEL, 'output': output, 'events': events, 'gate': summary[name]}))
    (args.out / 'summary.json').write_text(redacted_json(summary))
    print(json.dumps(summary, indent=2), flush=True)
    return 0 if all(r['passed'] for r in summary.values()) else 2


if __name__ == '__main__':
    raise SystemExit(main())
