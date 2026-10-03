"""Validated planner boundary for the deterministic shared-lab portfolio engine."""
import copy
import math
import re

from labforge.agent.validation import validate_design
from labforge.contracts import validate

PROJECT_TOOL = {
    'name': 'plan_projects',
    'description': 'Compare project orders and interleaved release policies on a shared lab. Supply validated workflows, labware unit counts, and optional priority weights and deadlines in hours from start. Mean durations only; excludes transfers and operator shifts. Batch/fan-out workflows are unsupported. Confirm with Monte Carlo before commitment.',
    'input_schema': {
        'type': 'object',
        'properties': {
            'lab_spec': {'type': 'object', 'description': 'Shared LabSpec; every workflow must refer to its ID.'},
            'projects': {'type': 'array', 'minItems': 1, 'maxItems': 6, 'items': {
                'type': 'object', 'properties': {
                    'id': {'type': 'string', 'pattern': '^[a-z0-9_]+$'},
                    'workflow': {'type': 'object', 'description': 'Workflow using shared physical equipment instance IDs.'},
                    'units': {'type': 'integer', 'minimum': 1, 'maximum': 1000},
                    'weight': {'type': 'number', 'exclusiveMinimum': 0},
                    'deadline_h': {'type': 'number', 'minimum': 0},
                }, 'required': ['id', 'workflow', 'units'], 'additionalProperties': False}},
        }, 'required': ['lab_spec', 'projects'], 'additionalProperties': False,
    },
}


def plan_projects(lab_spec, projects):
    if not isinstance(projects, list) or not 1 <= len(projects) <= 6:
        raise ValueError('Supply 1–6 projects; exhaustive ordering is limited to six.')
    ids, hardware = set(), {}
    total_units = 0
    for project in projects:
        pid = project.get('id')
        if not isinstance(pid, str) or not re.fullmatch('[a-z0-9_]+', pid) or pid in ids:
            raise ValueError('Project IDs must be unique snake_case identifiers.')
        ids.add(pid)
        units = project.get('units')
        if type(units) is not int or not 1 <= units <= 1000:
            raise ValueError('Project units must be positive integers, at most 1000.')
        total_units += units
        for key in ('weight', 'deadline_h'):
            if key in project:
                value = project[key]
                if type(value) not in (int, float) or not math.isfinite(value) or value < 0 or (key == 'weight' and value == 0):
                    raise ValueError('Weights must be positive and deadlines nonnegative; all numbers must be finite.')
        workflow = project['workflow']
        validate_design(lab_spec, workflow)
        for step in workflow['steps']:
            if step.get('batch_size', 1) != 1 or step.get('fan_out', 1) != 1:
                raise ValueError('Portfolio engine does not model batch_size/fan_out; both must be 1.')
        for equipment in workflow['equipment']:
            instance, catalog = equipment['instance_id'], equipment['catalog_id']
            if instance in hardware and hardware[instance] != catalog:
                raise ValueError('A shared equipment instance must use the same catalog item in every project.')
            hardware[instance] = catalog
    if total_units > 1000:
        raise ValueError('Limit the interactive schedule to 1000 total labware units.')
    from labforge.sim.portfolio import prioritise
    # Keep hypothetical scheduling separate from the current lab design and checked claims.
    schedule = prioritise(copy.deepcopy(projects), lab_id=lab_spec['id'])
    validate(schedule, 'project_schedule')
    return {'project_schedule': schedule,
            'scope': 'Deterministic mean-duration scheduling; not verified physical feasibility. Transfers, operator shifts and stochastic failures are omitted. Confirm with Monte Carlo before commitment.'}
