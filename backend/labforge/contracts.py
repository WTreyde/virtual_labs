"""Shared JSON contracts. Every strand validates what it produces with `validate()`.

The schemas in /schemas are the source of truth; only the integrator changes them.
"""
import json
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = REPO_ROOT / "schemas"
EXAMPLE_DIR = REPO_ROOT / "examples"


@lru_cache
def _registry() -> tuple[Registry, dict]:
    schemas = {p.name: json.loads(p.read_text()) for p in SCHEMA_DIR.glob("*.schema.json")}
    registry = Registry().with_resources((n, Resource.from_contents(s)) for n, s in schemas.items())
    return registry, schemas


def errors(obj: dict, schema: str) -> list[str]:
    """Return human-readable validation errors; `schema` is e.g. "layout" or "sim_result"."""
    registry, schemas = _registry()
    validator = Draft202012Validator(schemas[f"{schema}.schema.json"], registry=registry)
    return [f"{'/'.join(map(str, e.path)) or '<root>'}: {e.message}" for e in validator.iter_errors(obj)]


def validate(obj: dict, schema: str) -> dict:
    """Raise ValueError if `obj` breaks the contract, else return it unchanged."""
    errs = errors(obj, schema)
    if errs:
        raise ValueError(f"{schema} contract violated:\n  " + "\n  ".join(errs[:10]))
    return obj


def load_example(name: str):
    """Load examples/<name>.json (lab_spec, catalog, workflow, layout, sim_result)."""
    return json.loads((EXAMPLE_DIR / f"{name}.json").read_text())
