#!/usr/bin/env python3
"""
CODENESS GENERATION: From ontology specification to running code.

This module handles CODE GENERATION from patterns defined in codeness.py.
- TEMPLATES: String templates for each pattern
- OntologySpec: A specification that can become code
- spec_to_code: Natural language spec → code
- MetaInterpreter: The observe → specify → generate loop

Imports patterns from codeness.py (single source of truth).
"""

import re
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

from .models import PIOEntity, ValidationLevel
from .codeness import CODE_PATTERNS

logger = logging.getLogger(__name__)


# =============================================================================
# CODE TEMPLATES - Generation templates for each pattern
# =============================================================================

TEMPLATES = {
    "DataHolder": '''
@dataclass
class {name}:
    """{description}"""
{fields}
''',

    "EnumSet": '''
class {name}(str, Enum):
    """{description}"""
{values}
''',

    "Container": '''
    {field_name}: {container_type}[{type_params}] = field(default_factory={factory})
''',

    "Transformer": '''
    def {method_name}(self, {params}) -> {return_type}:
        """{description}"""
        {body}
''',

    "Mutator": '''
    def {method_name}(self, {params}):
        """{description}"""
        self.{target_field} = {value_expr}
''',

    "Recursive": '''
    def {method_name}(self, {params}, visited: set = None):
        """{description}"""
        if visited is None:
            visited = set()
        key = {key_expr}
        if key in visited:
            return {base_case}
        visited.add(key)
        for {item} in {collection}:
            self.{method_name}({recursive_params}, visited)
''',

    "Callback": '''
    {hook_name}: Optional[Callable[[{param_types}], {return_type}]] = None
''',

    "Graph": '''
    {nodes_field}: Dict[str, {node_type}] = field(default_factory=dict)
    {edges_field}: List[{edge_type}] = field(default_factory=list)
''',

    # Skill-ness templates
    "SkillSpec": '''---
name: {name}
domain: {domain}
category: {category}
description: {description}
---
# {name}

**WHAT**: {what}
**WHEN**: {when}

{content}
''',

    "FlightConfig": '''name: {name}
domain: {domain}
description: {description}
waypoints:
{waypoints}
''',

    "PersonaSpec": '''{
    "name": "{name}",
    "domain": "{domain}",
    "description": "{description}",
    "frame": "{frame}",
    "skillset": "{skillset}",
    "mcp_set": "{mcp_set}",
    "identity": "{identity}"
}
''',
}


# =============================================================================
# ONTOLOGY SPECIFICATION → CODE
# =============================================================================

@dataclass
class OntologySpec:
    """An ontological specification that can become code."""
    name: str
    description: str
    is_a: List[str]  # Patterns this thing uses
    has_parts: Dict[str, Any] = field(default_factory=dict)  # Fields/components

    def to_code(self) -> str:
        """Generate code from this specification."""
        code_lines = []
        imports_needed = set()

        # Determine primary pattern
        primary_pattern = self.is_a[0] if self.is_a else "DataHolder"
        logger.debug(f"Generating code for {self.name} as {primary_pattern}")

        if primary_pattern == "DataHolder":
            imports_needed.add("from dataclasses import dataclass, field")
            fields = []
            for field_name, field_spec in self.has_parts.items():
                if isinstance(field_spec, dict):
                    field_type = field_spec.get("type", "Any")
                    default = field_spec.get("default", "")
                    if default:
                        fields.append(f"    {field_name}: {field_type} = {default}")
                    else:
                        fields.append(f"    {field_name}: {field_type}")
                else:
                    fields.append(f"    {field_name}: {field_spec}")

            code = TEMPLATES["DataHolder"].format(
                name=self.name,
                description=self.description,
                fields="\n".join(fields) if fields else "    pass"
            )
            code_lines.append(code)

        elif primary_pattern == "EnumSet":
            imports_needed.add("from enum import Enum")
            values = []
            for value_name, value_val in self.has_parts.items():
                values.append(f'    {value_name} = "{value_val}"')

            code = TEMPLATES["EnumSet"].format(
                name=self.name,
                description=self.description,
                values="\n".join(values) if values else "    pass"
            )
            code_lines.append(code)

        elif primary_pattern == "SkillSpec":
            code = TEMPLATES["SkillSpec"].format(
                name=self.name,
                description=self.description,
                domain=self.has_parts.get("domain", "PAIAB"),
                category=self.has_parts.get("category", "understand"),
                what=self.has_parts.get("what", self.description),
                when=self.has_parts.get("when", "When needed"),
                content=self.has_parts.get("content", ""),
            )
            code_lines.append(code)

        elif primary_pattern == "FlightConfig":
            waypoints = self.has_parts.get("waypoints", [])
            waypoint_yaml = "\n".join(f"  - {w}" for w in waypoints) if waypoints else "  - step1"
            code = TEMPLATES["FlightConfig"].format(
                name=self.name,
                description=self.description,
                domain=self.has_parts.get("domain", "general"),
                waypoints=waypoint_yaml,
            )
            code_lines.append(code)

        elif primary_pattern == "PersonaSpec":
            code = TEMPLATES["PersonaSpec"].format(
                name=self.name,
                description=self.description,
                domain=self.has_parts.get("domain", "PAIAB"),
                frame=self.has_parts.get("frame", ""),
                skillset=self.has_parts.get("skillset", ""),
                mcp_set=self.has_parts.get("mcp_set", ""),
                identity=self.has_parts.get("identity", ""),
            )
            code_lines.append(code)

        elif primary_pattern == "Graph":
            imports_needed.add("from dataclasses import dataclass, field")
            imports_needed.add("from typing import Dict, List")

            node_type = self.has_parts.get("node_type", "Any")
            edge_type = self.has_parts.get("edge_type", "Any")

            code = f'''
@dataclass
class {self.name}:
    """{self.description}"""
    nodes: Dict[str, {node_type}] = field(default_factory=dict)
    edges: List[{edge_type}] = field(default_factory=list)

    def add_node(self, name: str, node: {node_type}):
        self.nodes[name] = node

    def add_edge(self, edge: {edge_type}):
        self.edges.append(edge)
'''
            code_lines.append(code)

        else:
            # Generic fallback
            imports_needed.add("from dataclasses import dataclass, field")
            fields = "\n".join(f"    {p}: Any" for p in self.has_parts) if self.has_parts else "    pass"
            code = f'''
@dataclass
class {self.name}:
    """{self.description}"""
{fields}
'''
            code_lines.append(code)

        # Add imports
        full_code = "\n".join(sorted(imports_needed)) + "\n\n" + "\n".join(code_lines)
        return full_code.strip()


# =============================================================================
# SPEC LANGUAGE → CODE
# =============================================================================

def spec_to_code(spec_text: str) -> str:
    """
    Parse natural ontology specification and generate code.

    Example:
      "Counter is a DataHolder with count: int, step: int"
      → @dataclass class Counter: count: int; step: int

    This is WHERE TALK BECOMES CODE.
    """
    # Pattern: "Name is a Pattern with field1: type1, field2: type2"
    match = re.match(
        r"(\w+)\s+is\s+(?:a|an)\s+(\w+)(?:\s+with\s+(.+))?",
        spec_text,
        re.IGNORECASE
    )

    if not match:
        logger.warning(f"Could not parse spec: {spec_text}")
        return f"# Could not parse: {spec_text}"

    name = match.group(1)
    pattern = match.group(2)
    fields_str = match.group(3)

    # Parse fields
    has_parts = {}
    if fields_str:
        # Handle "field: type" or "field = value" patterns
        for field_spec in fields_str.split(","):
            field_spec = field_spec.strip()
            if ":" in field_spec:
                field_name, field_type = field_spec.split(":", 1)
                has_parts[field_name.strip()] = field_type.strip()
            elif "=" in field_spec:
                field_name, field_value = field_spec.split("=", 1)
                has_parts[field_name.strip()] = field_value.strip()

    spec = OntologySpec(
        name=name,
        description=f"A {pattern} with {len(has_parts)} parts",
        is_a=[pattern],
        has_parts=has_parts
    )

    return spec.to_code()


# =============================================================================
# THE META-INTERPRETER
# =============================================================================

class MetaInterpreter:
    """
    The meta-interpreter that makes ontology DO code.

    Loop:
    1. Observe code → patterns
    2. Patterns → templates
    3. Templates → ontology
    4. Ontology spec → code
    5. Code runs
    """

    def __init__(self):
        from .core import get_youknow
        self.yk = get_youknow()  # YOUKNOW is THE singleton entry point
        self.observed_patterns: Dict[str, Dict] = {}
        self.generated_code: Dict[str, str] = {}

        # Bootstrap with code-ness patterns
        self._bootstrap()

    def _bootstrap(self):
        """Add fundamental code-ness patterns to ontology via YOUKNOW."""
        from .codeness import program_codeness

        # Add root pattern (skip_pipeline=True for bootstrap to avoid recursion)
        self.yk.add(
            name="pattern_of_isa",
            is_a=["Entity"],  # Must trace to Cat_of_Cat
            description="Root of all patterns",
            skip_pipeline=True  # Bootstrap only - avoid recursion
        )

        # Add CodePattern root
        self.yk.add(
            name="CodePattern",
            is_a=["pattern_of_isa"],
            description="A pattern that makes code DO something",
            has_part=["template", "operations", "composes_with"],
            skip_pipeline=True
        )

        # Add each pattern from CODE_PATTERNS
        for pattern_name, pattern in CODE_PATTERNS.items():
            self.yk.add(
                name=pattern_name,
                is_a=["CodePattern"],
                description=pattern.description,
                properties={"template": pattern.template},
                skip_pipeline=True
            )

        logger.info(f"MetaInterpreter bootstrapped with {len(CODE_PATTERNS)} patterns")

    def observe(self, source_code: str, name: str = "observed") -> Dict:
        """Observe code-ness in source code."""
        from .codeness import observe_codeness
        import ast

        tree = ast.parse(source_code)
        patterns = {}

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_patterns = []

                # Detect patterns
                for dec in node.decorator_list:
                    if isinstance(dec, ast.Name) and dec.id == "dataclass":
                        class_patterns.append("DataHolder")

                for base in node.bases:
                    if isinstance(base, ast.Name) and base.id == "Enum":
                        class_patterns.append("EnumSet")

                patterns[node.name] = class_patterns

                # Add to ontology via YOUKNOW
                self.yk.add(
                    name=node.name,
                    is_a=class_patterns if class_patterns else ["CodePattern"],
                    description=f"Observed class from {name}"
                )

        self.observed_patterns[name] = patterns
        logger.debug(f"Observed {len(patterns)} classes in {name}")
        return patterns

    def specify(self, spec: str) -> str:
        """
        Specify something in ontology, get code.

        This is the MAGIC: talk → code.
        """
        code = spec_to_code(spec)
        self.generated_code[spec] = code
        logger.debug(f"Generated code for spec: {spec[:50]}...")
        return code

    def validate(self, name: str) -> bool:
        """Check if concept exists and traces to Cat_of_Cat."""
        return self.yk.exists(name) and self.yk.is_valid(name)

    def get_chain(self, name: str) -> List[str]:
        """Get is_a chain back to Cat_of_Cat."""
        return self.yk.trace(name)
