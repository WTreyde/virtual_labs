"""Deterministic boss report: numerical facts come from backend objects, never prose."""
import math
from labforge.catalog.store import get as get_item


def cell(value):
    return str(value).replace('|', '\\|').replace('\n', ' ')


def render_report(lab_spec: dict, workflow: dict, layout: dict, sim: dict,
                  claims: list[dict] | None = None, evidence: list[dict] | None = None,
                  claim_history: list[dict] | None = None,
                  simulation_limitations: list[str] | None = None) -> str:
    t = sim['throughput']
    median = t.get('p50', t['value'])
    target = lab_spec['throughput_target']['value']
    issues = layout.get('violations', [])
    summary = f'Modelled median throughput is {median} {t["unit"]} against a requested {target} {lab_spec["throughput_target"]["unit"]}.'
    if t['unit'] != lab_spec['throughput_target']['unit']:
        summary += ' Target and result units differ; feasibility cannot be compared directly.'
    elif median < target:
        summary += ' The median prediction falls below the requested target.'
    if issues:
        summary += f' There are {len(issues)} layout issues; feasibility is qualified.'
    lines = [f'# {lab_spec["name"]}: automated lab proposal', '', '## Executive summary', '', summary,
             '', 'These are model-based predictions, not measured throughput or safety certification.',
             '', lab_spec.get('description', ''), '', '## Bill of materials', '',
             '| Instance | Vendor | Model | Est. price (USD) | Data confidence |', '|---|---|---|---|---|']
    total, unknown = 0, []
    for e in workflow['equipment']:
        item = get_item(e['catalog_id'])
        price = item.get('price_usd_estimate')
        if isinstance(price, (int, float)) and math.isfinite(price) and price >= 0:
            total += price
            cost = f'{price:,.0f}'
        else:
            unknown.append(e['instance_id'])
            cost = 'Unknown'
        lines.append('| ' + ' | '.join(cell(v) for v in [e['instance_id'], item['vendor'], item['model'], cost, item.get('data_confidence', 'estimated')]) + ' |')
    lines += [f'| **Known-price subtotal** | | | **{total:,.0f}** | |', '']
    budget = lab_spec.get('constraints', {}).get('budget_usd')
    if unknown:
        lines += ['Unknown prices: ' + ', '.join(unknown) + '. The subtotal is incomplete; total affordability is unverified.', '']
    if budget is not None:
        lines += [f'Equipment budget: USD {budget:,.0f}. Known-price subtotal: USD {total:,.0f}.', '']
        if total > budget:
            lines += ['The known-price subtotal exceeds the budget.', '']
    if simulation_limitations:
        lines += ['## Simulator limitations', '', *['- ' + note for note in simulation_limitations], '']
    lines += ['Costs are catalog estimates and exclude installation, service, consumables and building work.', '',
              '## Throughput', '', f'Median {median} {t["unit"]}; P10 {t.get("p10", "unavailable")}; P90 {t.get("p90", "unavailable")}.',
              f'Probability of meeting the simulated target: {t.get("prob_meets_target", "unavailable")}.',
              'This probability describes duration sampling under the model; it is not confidence that the design is correct in reality.', '',
              '## Checked claims', '', '| Claim | Confidence | Status | Observed value | Note |', '|---|---|---|---|---|']
    for c in claims or []:
        lines.append('| ' + ' | '.join(cell(c.get(k, '')) for k in ('statement', 'confidence', 'status', 'verified_value', 'verifier_note')) + ' |')
    if not claims:
        lines += ['| No claims checked | | unverified | | |']
    refutations = [(h.get('workflow_id', '?'), c) for h in claim_history or [] for c in h['claims'] if c.get('status') == 'refuted']
    if refutations:
        lines += ['', '## Refutation history', '', 'These are historical checks; a later revision may supersede the design or assertion.']
        for workflow_id, c in refutations:
            lines.append(f'- {workflow_id}: {c["statement"]} — refuted; observed {c.get("verified_value", "unknown")}.')
    observed = sorted({c['verified_value'] for c in claims or []
                       if c.get('metric') == 'throughput.p50' and 'verified_value' in c})
    if observed and any(not math.isclose(value, median, rel_tol=0.01, abs_tol=0.01) for value in observed):
        lines += ['', '## Independent verifier comparison', '',
                  f'The planning simulation reports P50 {median}; the verifier observed {observed}. '
                  'These are different model runs/assumptions. Use the verifier notes to identify restored catalog durations; '
                  'do not present the planning number as independently confirmed.']
    lines += ['', '## Bottlenecks and risks', '']
    lines += [f'- **{b["severity"]}**: {b["message"]} {b.get("suggestion", "")}' for b in sim.get('bottlenecks', [])] or ['- None reported by the model.']
    lines += ['', '## Layout issues', '']
    lines += [f'- {v["message"]}' for v in issues] or ['- None reported by the layout engine.']
    lines += ['', '## Assumptions and unknowns', '']
    for step in workflow['steps']:
        u = step.get('duration_uncertainty') or {}
        lines.append(f'- {step["name"]}: {step["duration_s"]} seconds; range {u.get("low", "unspecified")}–{u.get("high", "unspecified")}; source {u.get("source", "agent_estimate")}; basis {u.get("confidence", "estimated")}.')
    lines += ['- Duration ranges are modelling assumptions unless supported by relevant measurements.',
              '- Batch/fan-out, operator shifts and external queues depend on simulator support; check these before interpreting complex workflows.',
              '- Verification checks consistency with catalog and simulation results; it does not validate the physical lab.']
    lines += ['', '## Evidence', '']
    sources = set()
    for step in workflow['steps']:
        for e in step.get('evidence', []):
            sources.add(e['source'])
            lines.append(f'- {e["claim"]} — {e["source"]}')
    for lookup in evidence or []:
        lines.append(f'- Literature search `{lookup["query"]}`: {lookup["status"]}.')
        for item in lookup.get('reviewed_items', []):
            source = item['evidence']['source']
            if source not in sources:
                sources.add(source)
                lines.append(f'- Reviewed public reference (not Amass): {item["title"]} — {source}')
        for item in lookup.get('items', []):
            source = item['evidence']['source']
            if source not in sources:
                sources.add(source)
                lines.append(f'- Candidate (relevance requires review): {item["title"]} — {source}')
    if not sources:
        lines.append('- No retrieved literature cited; processing times remain estimates.')
    return '\n'.join(lines) + '\n'
