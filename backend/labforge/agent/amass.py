"""Strand C: Amass evidence lookups. Owner: Albert.

Amass (https://platform.amass.tech) exposes BiomedCore (literature), GeneCore (targets),
DrugCore (molecules), PatentCore and more. We use it to back each workflow step's durations
and yields with citations, and to pick known ligands / building blocks for the chemistry demo.

TODO(Albert): confirm endpoints and auth from the Amass docs; read the key from AMASS_API_KEY.
Return items shaped like common.schema.json#/$defs/evidence with provider="amass".
"""
import os


def search_literature(query: str, limit: int = 5) -> list[dict]:
    if not os.environ.get("AMASS_API_KEY"):
        return []  # offline: the agent must then widen its uncertainty, not invent citations
    raise NotImplementedError("TODO(Albert): call Amass BiomedCore search")
