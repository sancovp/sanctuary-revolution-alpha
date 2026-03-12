"""Core game wrapper components.

Runtime control (harness, hooks, events, output watcher, terminal UI,
self-commands) is now provided by cave-harness. Import from cave.core.

Sancrev-specific components remain here:
- PersonaControl: file-flag persona activation
- CodeAgent/PAIAAgent: agent definitions (PAIA level)
"""
from .persona_control import PersonaControl, PERSONA_FLAG

__all__ = [
    "PersonaControl",
    "PERSONA_FLAG",
]
