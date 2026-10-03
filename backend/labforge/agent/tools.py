"""Strand C: tools the planner agent can call. Owner: Albert.

Each entry pairs a Claude tool definition with the Python function that runs it.
Tool functions take and return plain JSON-able dicts that follow /schemas.
"""
from labforge.catalog.store import search
from labforge.agent.validation import validate_design
from labforge.contracts import validate
from labforge.catalog.store import get as get_item
import math


def _search_catalog(capability: str | None = None, labware: str | None = None, max_price_usd: float | None = None) -> dict:
    items = search(capability, labware, max_price_usd)
    return {"items": [{k: it.get(k) for k in ("id", "vendor", "model", "capabilities", "footprint", "process",
                                                 "transport", "price_usd_estimate", "data_confidence", "access_points",
                                                 "provenance", "source_urls", "safety", "integration")} for it in items]}


def _layout_and_simulate(lab_spec: dict, workflow: dict) -> dict:
    validate_design(lab_spec, workflow)
    from labforge.layout.placer import generate_layout
    from labforge.sim.simulate import simulate

    layout = generate_layout(lab_spec, workflow)
    sim = simulate(lab_spec, workflow, layout, replicates=10)
    validate(layout, "layout")
    validate(sim, "sim_result")
    return {"layout": layout, "sim_result": sim, "capacity_checks": capacity_checks(lab_spec, workflow)}


def capacity_checks(spec: dict, workflow: dict) -> dict:
    """Simple per-step capacity bounds, explicitly limited to one-plate model flow units."""
    if spec['throughput_target']['unit'] != 'plates_per_day' or any(
        s.get('batch_size', 1) != 1 or s.get('fan_out', 1) != 1 for s in workflow['steps']
    ):
        return {'status': 'unsupported', 'note': 'Capacity arithmetic requires plates_per_day, batch_size=1 and fan_out=1.'}
    seconds = spec['throughput_target'].get('operating_hours_per_day', 24) * 3600
    if seconds <= 0:
        return {'status': 'unsupported', 'note': 'Operating hours must be positive.'}
    items = {e['instance_id']: get_item(e['catalog_id']) for e in workflow['equipment']}
    rows = []
    for s in workflow['steps']:
        if s['duration_s'] <= 0 or not s['candidate_instances']:
            continue
        slots = sum(items[i].get('process', {}).get('capacity', 1) for i in s['candidate_instances'])
        demand = spec['throughput_target']['value'] * s['duration_s']
        rows.append({'step_id': s['id'], 'parallel_slots': slots, 'duration_s_per_plate': s['duration_s'],
                     'operating_seconds_per_slot_per_day': seconds, 'target_processing_seconds_per_day': demand,
                     'upper_bound_plates_per_day': round(slots * seconds / s['duration_s'], 3),
                     'minimum_parallel_slots_for_target': math.ceil(demand / seconds)})
    return {'status': 'computed', 'steps': rows,
            'note': 'Per-step capacity ceilings ignore transfers, downtime and shared-resource interactions. They are optimistic bounds, not achieved throughput.'}


TOOLS = {
    "search_catalog": (
        {
            "name": "search_catalog",
            "description": "Search the cached vendor catalog for instruments and robots. Returns specs, prices and how confident the data is.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "capability": {"type": "string", "description": "A capability from schemas/common.schema.json, e.g. liquid_handling."},
                    "labware": {"type": "string"},
                    "max_price_usd": {"type": "number"},
                },
            },
        },
        _search_catalog,
    ),
    "layout_and_simulate": (
        {
            "name": "layout_and_simulate",
            "description": "Place the workflow's equipment in the room and run a Monte Carlo throughput simulation. "
                           "Returns the layout (with violations) and P10/P50/P90 throughput, utilisation and bottlenecks.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "lab_spec": {"type": "object", "description": "A LabSpec (schemas/lab_spec.schema.json)."},
                    "workflow": {"type": "object", "description": "A Workflow (schemas/workflow.schema.json)."},
                },
                "required": ["lab_spec", "workflow"],
            },
        },
        _layout_and_simulate,
    ),
    # TODO(Albert): cite_evidence (Amass), record_claim (schemas/claim.schema.json), update_spec.
}
