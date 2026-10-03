"""Validate every file in examples/ against its schema. Run: python validate_examples.py"""
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

ROOT = Path(__file__).parent
schemas = {p.name: json.loads(p.read_text()) for p in (ROOT / "schemas").glob("*.schema.json")}
registry = Registry().with_resources((name, Resource.from_contents(s)) for name, s in schemas.items())

PAIRS = {
    "lab_spec.json": "lab_spec.schema.json",
    "catalog.json": "catalog_item.schema.json",  # a list of items
    "workflow.json": "workflow.schema.json",
    "layout.json": "layout.schema.json",
    "sim_result.json": "sim_result.schema.json",
}

failed = False
for example, schema_name in PAIRS.items():
    validator = Draft202012Validator(schemas[schema_name], registry=registry)
    data = json.loads((ROOT / "examples" / example).read_text())
    for item in data if isinstance(data, list) else [data]:
        for err in validator.iter_errors(item):
            failed = True
            print(f"{example}: {'/'.join(map(str, err.path))}: {err.message}")
print("FAILED" if failed else "All examples valid")
sys.exit(1 if failed else 0)
