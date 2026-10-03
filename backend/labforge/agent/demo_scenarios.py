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

PIPELINE_STAGES = {
    'chemistry': [('stock preparation', {'powder_dosing'}), ('reaction', {'reaction'}),
                  ('workup', {'filtration', 'solid_phase_extraction'}),
                  ('purification', {'solid_phase_extraction', 'hplc'}), ('evaporation', {'evaporation'}),
                  ('QC', {'lcms'}), ('screening', {'fluorescence_read'})],
    'xchem': [('expression', {'cell_culture', 'bioreactor', 'shaking'}), ('harvest', {'centrifugation'}),
              ('lysis', {'cell_lysis'}), ('purification', {'protein_purification'}),
              ('protein QC', {'protein_qc'}), ('concentration', {'concentration_measurement'}),
              ('drop setup', {'crystallization_setup'}), ('growth/imaging', {'crystal_imaging'}),
              ('soaking', {'crystal_soaking', 'acoustic_dispensing'}),
              ('harvesting', {'crystal_harvesting'}), ('cooling', {'cryo_cooling'})],
}

SCENARIOS = {
    'chemistry': {
        'brief': 'Design an equipment and room-planning model for the full chemistry demo in docs/pipelines.md: 8 boronic acids x 12 aryl-bromide amines x 8 acids = 768 products, with Suzuki then amide reaction stages, stock preparation, workup/filtration, purification, evaporation, LC-MS QC of every product, compound storage and fluorescence screening against a supplied purified protein target. This is a bill of materials, abstract workflow graph and simulation request only; do not provide reaction recipes, chemical quantities or experimental execution instructions. Use only catalog equipment. Room 10 m x 8 m, USD 2000000 equipment budget, target 768 compounds/day, 24-hour instruments and one trained operator on an 8-hour shift. Use 96-well reaction blocks and appropriate assay plates, a ventilated/inert synthesis area and separated flammable-solvent storage. I permit provisional timing/yield assumptions with honest ranges. Declare flow units, plate arithmetic and final-sink units_per_labware; keep both reaction stages, QC and screening in the graph. Search catalog and evidence, call layout_and_simulate, verify throughput/budget/layout claims and create_report. Stop after the first validated design, repairing proposal validation errors if necessary; disclose refutations and limitations rather than revising equipment in this run. If essential equipment is absent, name the catalog gaps instead of inventing items or calling a partial lab complete.',
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
        'full_pipeline': all(allowed & {s['capability'] for s in steps} for _, allowed in PIPELINE_STAGES[name]),
    }
    missing_stages = [stage for stage, allowed in PIPELINE_STAGES[name] if not allowed & {s['capability'] for s in steps}]
    if name == 'chemistry':
        checks['two_reactions'] = sum(s['capability'] == 'reaction' for s in steps) >= 2
    checks['validated_flow_units'] = False
    if checks['design_returned']:
        try:
            validate_design(output['lab_spec'], workflow)
            checks['validated_flow_units'] = True
        except ValueError:
            pass
    checks['supported_simulator'] = not output.get('simulation_limitations')
    if name == 'xchem':
        checks['external_diffraction'] = any(s['mode'] == 'external' and (s['capability'] == 'xray_diffraction' or (s['capability'] == 'external_service' and any(word in s['name'].lower() for word in ('diffraction', 'synchrotron', 'beamline')))) for s in steps if s.get('mode'))
        checks['no_inhouse_xray'] = not any('xray_diffraction' in load_catalog()[e['catalog_id']]['capabilities'] for e in workflow.get('equipment', []))
        checks['manual_harvesting'] = any(s['capability'] == 'crystal_harvesting' and s.get('mode') in ('manual', 'semi_automated') for s in steps)
    return {'passed': all(checks.values()), 'checks': checks, 'missing_stages': missing_stages, **coverage}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file', type=Path)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--scenario', choices=tuple(SCENARIOS), help='Run just one scenario; default is both.')
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
        if args.scenario and args.scenario != name:
            continue
        if not args.live:
            summary[name] = {'passed': False, 'status': 'not_run', **gaps[name]}
            continue
        print('Starting ' + name, flush=True)
        events = []
        def emit(event):
            if event['type'] in ('model_call', 'tool_start', 'tool_end', 'tool_error'):
                events.append(event)
                (args.out / f'{name}-events.json').write_text(redacted_json(events))
                if event['type'] != 'tool_end':
                    print(name, event['type'], event.get('name', event.get('step')), redacted_json(event.get('error', '')), flush=True)
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
