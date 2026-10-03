"""Orchestrating-agent export: turn a designed and simulated lab into instructions for an LLM that runs it.

`build_orchestrator(...)` returns a SKILL.md for the orchestrating agent and a device/tool manifest
(instrument tools, their limits, safety, run order, escalation rules). See `skills.py`.
"""
from labforge.orchestrator.skills import build_orchestrator, from_replay

__all__ = ["build_orchestrator", "from_replay"]
