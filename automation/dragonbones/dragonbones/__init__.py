"""Dragonbones v2 — Modular Chain Type Compiler.

Dragonbones is the ontological compilation syntax for the compound intelligence system.
Parses entity chains from agent output and compiles them to CartON (Neo4j + ChromaDB).

Modules:
    constants: Chain types, UARL relationships, paths, markers
    parser: Chain parsing (claims, PIO operators, entity chains)
    giint_types: GIINT hierarchy type injection and validation
    logs: *Log persistence and validation (CogLog, SkillLog, DeliverableLog)
    compiler: CartON compilation loop
    transcript: Transcript reading utilities
    main: Hook entry point
"""

from dragonbones.main import main

__all__ = ["main"]
