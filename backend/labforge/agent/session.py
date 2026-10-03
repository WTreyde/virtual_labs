"""Per-turn tools. Verifier inputs are held here, never supplied in the claim call."""
import copy
import math

from labforge.agent.amass import retrieve_literature
from labforge.agent.report import render_report
from labforge.catalog.store import get as get_item
from labforge.contracts import validate
from labforge.verify.verifier import verify_claims, brier_score


class ToolSession:
    def __init__(self, base_tools, history):
        self.design = None
        self.previous_input = None
        self.claims = []
        self.claim_history = []
        self.optimisations = {}
        self.evidence = []
        self.known_sources = set()
        self.base_tools = base_tools
        # Restore only a proposal, never user-provided simulator/verifier results.
        for message in history:
            if message.get('role') == 'assistant' and isinstance(message.get('content'), list):
                for block in message['content']:
                    if block.get('type') == 'tool_use' and block.get('name') == 'layout_and_simulate':
                        self.previous_input = copy.deepcopy(block.get('input'))
        self.tools = dict(base_tools)
        if 'layout_and_simulate' in self.tools:
            definition, _ = self.tools['layout_and_simulate']
            self.tools['layout_and_simulate'] = (definition, self.simulate)
        if 'search_catalog' in self.tools:
            definition, _ = self.tools['search_catalog']
            self.tools['search_catalog'] = (definition, self.search_catalog)
        self.tools.update({
            'search_evidence': ({'name': 'search_evidence', 'description': 'Retrieve cached Amass literature candidates. A paper title is not evidence of a numerical duration or yield. Missing access is returned explicitly.',
                'input_schema': {'type': 'object', 'properties': {'query': {'type': 'string'}, 'limit': {'type': 'integer', 'minimum': 1, 'maximum': 10}}, 'required': ['query'], 'additionalProperties': False}}, self.search_evidence),
            'verify_claims': ({'name': 'verify_claims', 'description': 'Check structured claims against the last successful backend simulation and catalog. Accepts claims only, never simulator outputs. Refuted claims must be retracted. Checks model-based consistency, not real-world correctness.',
                'input_schema': {'type': 'object', 'properties': {'claims': {'type': 'array', 'minItems': 1, 'maxItems': 20, 'items': {'type': 'object', 'properties': {'id': {'type': 'string'}, 'statement': {'type': 'string'}, 'metric': {'type': 'string'}, 'comparator': {'type': 'string', 'enum': ['>=', '<=', '==']}, 'predicted_value': {'type': 'number'}, 'confidence': {'type': 'number', 'minimum': 0, 'maximum': 1}}, 'required': ['id', 'statement', 'metric', 'comparator', 'predicted_value', 'confidence'], 'additionalProperties': False}}}, 'required': ['claims'], 'additionalProperties': False}}, self.verify),
            'create_report': ({'name': 'create_report', 'description': 'Render a deterministic report from the last design and checked claims. Includes costs, unknowns, assumptions, evidence and simulation limitations.',
                'input_schema': {'type': 'object', 'properties': {}, 'additionalProperties': False}}, self.report),
            'optimise_instrument': ({'name': 'optimise_instrument', 'description': 'Use the vendor what-if engine on the backend-held design. Sweep cycle time and capacity for an existing instrument; return throughput bands, elasticity, headroom and the next bottleneck. This is hypothetical analysis, not a physical equipment upgrade.',
                'input_schema': {'type': 'object', 'properties': {'instance_id': {'type': 'string'}}, 'required': ['instance_id'], 'additionalProperties': False}}, self.optimise),
        })

    def search_catalog(self, **kwargs):
        result = self.base_tools['search_catalog'][1](**kwargs)
        for item in result.get('items', []):
            self.known_sources.update(item.get('source_urls') or [])
        return result

    def search_evidence(self, query, limit=5):
        result = retrieve_literature(query, limit)
        self.evidence.append({'query': query, **result})
        for item in result['items']:
            self.known_sources.add(item['evidence']['source'])
        return result

    def simulate(self, lab_spec, workflow):
        # Numerical source claims require sources discovered in this turn. Prior turns may
        # re-search them. Retrieval alone is not proof of relevance; that remains disclosed.
        for step in workflow.get('steps', []):
            source = (step.get('duration_uncertainty') or {}).get('source')
            if source and source != 'agent_estimate' and source not in self.known_sources:
                raise ValueError('Search evidence/catalog before attributing a duration to: ' + str(source))
            for evidence in step.get('evidence', []):
                if evidence.get('provider') != 'agent' and evidence.get('source') not in self.known_sources:
                    raise ValueError('Search evidence/catalog before citing a source: ' + str(evidence.get('source')))
        self.design = None
        self.claims = []
        self.optimisations = {}
        result = self.base_tools['layout_and_simulate'][1](lab_spec=lab_spec, workflow=workflow)
        self.design = copy.deepcopy({'lab_spec': lab_spec, 'workflow': workflow, **result})
        self.previous_input = copy.deepcopy({'lab_spec': lab_spec, 'workflow': workflow})
        return result

    def ensure_design(self):
        if self.design is None:
            if not self.previous_input:
                raise ValueError('Run layout_and_simulate successfully before verifying claims or creating a report')
            # Recompute across turns instead of trusting serialized tool results.
            result = self.base_tools['layout_and_simulate'][1](**self.previous_input)
            self.design = copy.deepcopy({**self.previous_input, **result})

    def verify(self, claims):
        if not isinstance(claims, list) or not 1 <= len(claims) <= 20:
            raise ValueError('Submit between 1 and 20 claims')
        pending = []
        ids = set()
        for claim in claims:
            c = {k: v for k, v in claim.items() if k in ('id', 'statement', 'metric', 'comparator', 'predicted_value', 'confidence')}
            c['status'] = 'unverified'
            validate(c, 'claim')
            if c['id'] in ids or c.get('comparator') not in ('>=', '<=', '==') or 'predicted_value' not in c:
                raise ValueError('Claims need unique IDs, a numeric prediction and a supported comparator')
            if any(not math.isfinite(c[k]) for k in ('confidence', 'predicted_value')):
                raise ValueError('Claim numbers must be finite')
            ids.add(c['id'])
            pending.append(c)
        self.ensure_design()
        d = self.design
        # The existing verifier assumes all prices are numeric. Mark BOM unknown if any
        # cost is missing instead of allowing absent costs to become a zero-price claim.
        unknown_cost = any(get_item(e['catalog_id']).get('price_usd_estimate') is None for e in d['workflow']['equipment'])
        ordinary = [c for c in pending if not (unknown_cost and c.get('metric') == 'bom.total_usd')]
        if unknown_cost:
            # Avoid the existing verifier's eager BOM computation when a price is null.
            from labforge.verify.verifier import OPS
            t = d['sim_result']['throughput']
            seen = {'throughput.p50': t.get('p50', t['value']), 'throughput.p10': t.get('p10', t['value']),
                    'throughput.prob_meets_target': t.get('prob_meets_target', float(t.get('meets_target', False))),
                    'layout.violations': len(d['layout'].get('violations', []))}
            checked = []
            for c in pending:
                c = dict(c)
                if c.get('metric') in seen:
                    c['verified_value'] = seen[c['metric']]
                    c['status'] = 'supported' if OPS[c['comparator']](c['verified_value'], c['predicted_value']) else 'refuted'
                else:
                    c.update(status='unverifiable', verifier_note='Unknown equipment price or unsupported metric; cannot verify.')
                checked.append(c)
        else:
            checked = verify_claims(ordinary, d['workflow'], d['layout'], d['sim_result'])
        checked = [validate(c, 'claim') for c in checked]
        self.claim_history.append({'workflow_id': d['workflow']['id'], 'claims': copy.deepcopy(checked)})
        # A second batch (e.g. BOM/layout) must not erase a throughput refutation.
        current = {c['id']: c for c in self.claims}
        current.update({c['id']: c for c in checked})
        self.claims = list(current.values())
        return {'claims': self.claims, 'brier': brier_score(self.claims),
                'scope': 'Consistency with backend model outputs; confidence is not empirically calibrated.',
                'recompute': 'Prior-turn designs are recomputed before checks; model-supplied results are ignored.'}

    def report(self):
        self.ensure_design()
        d = self.design
        return {'report_markdown': render_report(d['lab_spec'], d['workflow'], d['layout'], d['sim_result'],
                                                claims=self.claims, evidence=self.evidence, claim_history=self.claim_history)}

    def optimise(self, instance_id):
        self.ensure_design()
        d = self.design
        if instance_id not in {e['instance_id'] for e in d['workflow']['equipment']}:
            raise ValueError('Optimise an instance ID from the current design, not a catalog ID')
        from labforge.sim.whatif import optimise_instrument
        result = optimise_instrument(d['lab_spec'], d['workflow'], d['layout'], instance_id)
        validate(result, 'instrument_optimisation')
        self.optimisations[instance_id] = result
        return {'instrument_optimisation': result,
                'scope': 'Hypothetical spec sensitivity; layout, catalog prices and actual design are unchanged.',
                'simulation_config': {'hours': 48, 'replicates': 8, 'seed': 0},
                'cycle_time_scope': [{'step_id': s['id'], 'candidate_instances': s['candidate_instances']}
                                     for s in d['workflow']['steps'] if instance_id in s['candidate_instances']],
                'limitation': 'Cycle-time sweeps scale the whole affected step, including every parallel candidate. Capacity sweeps change only the selected instance. The sweep baseline uses 48 hours and 8 replicates and may differ from the design simulation.'}
