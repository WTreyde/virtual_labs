"""Planner-side checks before handing a design to other strands."""
import math
from labforge.catalog.store import load_catalog
from labforge.contracts import validate


def validate_design(spec: dict, workflow: dict) -> None:
    def finite(value):
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError('Design numbers must be finite')
        if isinstance(value, dict):
            for child in value.values():
                finite(child)
        elif isinstance(value, list):
            for child in value:
                finite(child)
    finite(spec)
    finite(workflow)
    validate(spec, "lab_spec")
    validate(workflow, "workflow")
    if workflow["lab_spec_id"] != spec["id"]:
        raise ValueError("workflow.lab_spec_id must match lab_spec.id")
    catalog = load_catalog()
    equipment = workflow["equipment"]
    instances = {e["instance_id"]: e for e in equipment}
    if len(instances) != len(equipment):
        raise ValueError("Equipment instance IDs must be unique")
    for e in equipment:
        if e["catalog_id"] not in catalog:
            raise ValueError(f"Unknown catalog_id: {e['catalog_id']}; search_catalog first")
    steps = {s["id"]: s for s in workflow["steps"]}
    if len(steps) != len(workflow["steps"]):
        raise ValueError("Step IDs must be unique")
    if not any(step['duration_s'] > 0 for step in steps.values()):
        raise ValueError('At least one step must have a positive duration to avoid a zero-time simulation loop')
    if workflow.get('labware') and workflow['labware'] not in spec.get('labware', []):
        raise ValueError('Workflow labware must be permitted by LabSpec.labware')
    for step in steps.values():
        for parent in step.get("after", []):
            if parent not in steps:
                raise ValueError(f"{step['id']}: unknown dependency {parent}")
        if step['capability'] == 'crystal_harvesting' and step.get('mode') != 'manual':
            raise ValueError('Crystal harvesting needs mode=manual: an operator performs the entire harvesting run, including with the Shifter. Setup-only semi_automated would undercount human work.')
        candidates = step["candidate_instances"]
        if len(candidates) != len(set(candidates)):
            raise ValueError(f"{step['id']}: candidate instance IDs must be unique")
        if not candidates and step.get("mode", "automated") not in ("external", "in_silico"):
            raise ValueError(f"{step['id']}: physical step needs candidate_instances")
        for instance in candidates:
            if instance not in instances:
                raise ValueError(f"{step['id']}: unknown instance {instance}")
            item = catalog[instances[instance]["catalog_id"]]
            if step["capability"] not in item["capabilities"]:
                raise ValueError(f"{instance} does not support {step['capability']}")
        u = step.get("duration_uncertainty")
        if u:
            value = step["duration_s"]
            if u["value"] != value or not 0 <= u.get("low", value) <= value <= u.get("high", value):
                raise ValueError(f"{step['id']}: duration range must satisfy 0 <= low <= duration_s == value <= high")
        if step.get("fan_out", 1) <= 0:
            raise ValueError(f"{step['id']}: fan_out must be positive")
    if spec['throughput_target']['unit'] != 'plates_per_day':
        parents = {parent for step in steps.values() for parent in step.get('after', [])}
        sinks = [step for sid, step in steps.items() if sid not in parents]
        counting = [step for step in sinks if step.get('params', {}).get('count_throughput') is True]
        if len(counting) != 1:
            raise ValueError('Non-plate throughput needs exactly one sink with params.count_throughput=true and explicit params.units_per_labware.')
        units = counting[0].get('params', {}).get('units_per_labware')
        if type(units) not in (int, float) or not math.isfinite(units) or units <= 0:
            raise ValueError('Counting sink units_per_labware must be finite and positive; do not relabel plate counts as compounds/crystals.')
    done = set()
    while len(done) < len(steps):
        ready = {sid for sid, step in steps.items() if sid not in done and set(step.get("after", [])) <= done}
        if not ready:
            raise ValueError("Workflow dependency cycle")
        done.update(ready)
