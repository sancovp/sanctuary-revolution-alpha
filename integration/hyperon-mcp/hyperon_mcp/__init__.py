"""Hyperon MCP - Persistent MeTTa/Atomspace integration with MCP interface"""

__version__ = "0.1.0"

from .core.persistent_metta import PersistentMeTTa, get_metta_instance
from .core.atomspace_registry import AtomspaceRegistry

__all__ = [
    "PersistentMeTTa",
    "get_metta_instance",
    "AtomspaceRegistry"
]
