"""Landing-page facts from a recorded replay, without recomputing or upgrading it."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

CASES = {
    'chem': ('Chemistry library, QC and screening',
             'Plan an abstract two-stage 768-compound library, quality control and screening against a supplied protein target.',
             ['Timing and yield assumptions are provisional; no physical lab was operated.']),
    'fbdd': ('XChem-style fragment screening',
             'Plan protein production, crystallisation, fragment soaking and manual harvesting followed by external synchrotron diffraction.',
             ['Growth-hotel crystallisation-plate compatibility, shipper capacity and transit concurrency need confirmation.',
              'Timing and yield assumptions are provisional; no physical lab was operated.']),
}


def _imager_whatif_summary(record):
    output = record['output']
    throughput = output['sim_result']['throughput']
    verified = next((claim.get('verified_value') for claim in output['claims']
                     if claim.get('metric') == 'throughput.p50'), None)
    equipment = {e['instance_id'] for e in output['workflow']['equipment']}
    utilisation = output['sim_result']['utilisation']
    busiest = max(utilisation, key=lambda row: row['busy_fraction'])
    return {
        'planned_p50': throughput['p50'], 'verified_p50': verified, 'unit': throughput['unit'],
        'bottleneck': {'instance_id': busiest['instance_id'],
                       'kind': 'instrument' if busiest['instance_id'] in equipment else 'operator',
                       'busy_fraction': busiest['busy_fraction']},
    }


def _staffing_whatif_summary(record):
    summary = record['summary']
    return {
        'method': summary['method'],
        'verification_config': summary['verification_config'],
        'baseline_verified_p50': summary['recorded_baseline_verified_p50'],
        'changes': ['move crystal-growth residence to the existing Rock Imager',
                    'increase skilled-operator availability'],
        'attribution': ('These variants change growth residence and staffing together, so their throughput gain '
                        'cannot be attributed to either change alone.'),
        'variants': summary['variants'],
    }


def _load_imager_whatif(run):
    source = run.get('source')
    if not source:
        return None
    source_dir = ROOT / Path(source).parent
    path = source_dir / 'xchem-imager-whatif.json'
    if path.is_file():
        return json.loads(path.read_text())
    # The 50-replicate replay deliberately has no 10-replicate imager-only result beside it.
    # Its current evidence is the separately verified staffing bundle from inbox item 6.
    staffing = source_dir.parent / 'scenarios_20261004_staffing_whatifs' / 'summary.json'
    if source_dir.name == 'scenarios_20261004_resim50' and staffing.is_file():
        return {'kind': 'imager_staffing_bundle', 'summary': json.loads(staffing.read_text())}
    return None


def summarise(name, run, imager_whatif=None):
    title, brief, caveats = CASES[name]
    output = run['output']
    sim = output['sim_result']
    throughput = sim['throughput']
    workflow = output['workflow']
    equipment = {e['instance_id']: e['catalog_id'] for e in workflow['equipment']}
    utilisation = [u for u in sim['utilisation'] if u['instance_id'] in equipment]
    busiest = max(utilisation, key=lambda u: u['busy_fraction'])
    claims = {c['metric']: c for c in output['claims']}
    required_metrics = {'throughput.p50', 'bom.total_usd', 'layout.violations'}
    required_claims_pass = not any(
        claim.get('status') == 'refuted' and claim.get('metric') in required_metrics
        for claim in output['claims']
    )
    verified = claims.get('throughput.p50', {}).get('verified_value')
    limits = [f"{len(output['layout'].get('violations', []))} recorded layout violations; physical feasibility is qualified."]
    for metric in ('throughput.p50', 'bom.total_usd'):
        claim = claims.get(metric, {})
        if claim.get('status') == 'refuted':
            limits.append(f"Refuted claim: {claim['statement']} (verified value {claim.get('verified_value')}).")
    if verified is not None and verified != throughput['p50']:
        limits.append(f"Planning median {throughput['p50']} versus independent verifier {verified} {throughput['unit']}; the headline is the planning simulation, not a verified measurement.")
    limits.extend(caveats)
    if name == 'fbdd' and 'scenarios_20261003_harvesting/' in (run.get('source') or ''):
        limits.append('This historical recording predates the per-crystal catalog and batch-aware verifier fixes; its verifier restores 7200 seconds for harvesting.')
    summary = {
        'title': title, 'brief': brief, 'source': run.get('source'),
        'headline_throughput': {'p50': throughput['p50'], 'p10': throughput['p10'],
                               'p90': throughput['p90'], 'unit': throughput['unit'],
                               'basis': 'recorded planning simulation', 'verified_p50': verified,
                               'target': throughput.get('target')},
        'bottleneck': {'instance_id': busiest['instance_id'],
                       'name': busiest['instance_id'].replace('_', ' '),
                       'catalog_id': equipment[busiest['instance_id']],
                       'model': run.get('catalog', {}).get(equipment[busiest['instance_id']], {}).get('model'),
                       'busy_fraction': busiest['busy_fraction'],
                       'basis': 'busiest recorded instrument by calendar-time utilisation; operators excluded'},
        'budget_vs_bom': {'currency': 'USD',
                          'budget': output['lab_spec'].get('constraints', {}).get('budget_usd'),
                          'bom': claims.get('bom.total_usd', {}).get('verified_value'),
                          'claim_status': claims.get('bom.total_usd', {}).get('status'),
                          'basis': 'recorded checked equipment cost; excludes installation, service, consumables and building work'},
        # The scenario gate proves orchestration completed. The landing-page gate also
        # requires the checked throughput, budget and layout assertions to survive the
        # verifier, so "passed" never sits beside a refuted feasibility claim.
        'gate_passed': bool(run['gate']['passed'] and required_claims_pass),
        'limits': limits,
    }
    if name == 'fbdd' and imager_whatif:
        if imager_whatif.get('kind') == 'imager_staffing_bundle':
            summary['imager_staffing_whatifs'] = _staffing_whatif_summary(imager_whatif)
            summary['limits'].append(
                'The current imager what-ifs also add staff; they do not isolate the effect of moving growth alone.'
            )
        else:
            summary['imager_growth_whatif'] = _imager_whatif_summary(imager_whatif)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    for name in CASES:
        run = json.loads((args.directory / f'{name}.json').read_text())
        whatif = _load_imager_whatif(run) if name == 'fbdd' else None
        (args.directory / f'{name}.summary.json').write_text(json.dumps(summarise(name, run, whatif), indent=2) + '\n')


if __name__ == '__main__':
    main()
