"""Mermaid diagram utilities — parsing, generation, and validation.

The mermaid diagram IS the program for the LLM. This package handles:
- parser: parsing existing mermaid text into MermaidSpec (graph-first)
- generator: generating mermaid specs from pipeline context
- validator: validating specs against tool surfaces + evolution system
- cli: command-line validation entrypoint
"""

from compoctopus.mermaid.parser import MermaidParser
from compoctopus.mermaid.generator import MermaidGenerator
from compoctopus.mermaid.validator import (
    MermaidValidator,
    EvolutionSystemViolation,
    extract_tool_references_from_text,
)

__all__ = [
    "MermaidParser",
    "MermaidGenerator",
    "MermaidValidator",
    "EvolutionSystemViolation",
    "extract_tool_references_from_text",
]
