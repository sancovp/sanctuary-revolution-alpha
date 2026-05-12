#!/usr/bin/env python3
"""
CODENESS: The pattern library - defines HOW code IS code.

This is the SINGLE SOURCE OF TRUTH for code patterns.
Other modules (codeness_v2, lang, recognizer) import from here.

The insight: You OBSERVE the WAY code IS code. That programs code-ness into
the ontology. Now YOUKNOW's talk level applies to the code. You can specify
things and they become code... because the ontology knows how to BE code.

What IS "code-ness"?
- Patterns: dataclass, enum, composition, callbacks, recursion
- Templates: how those patterns become actual code
- Operations: what you can DO with each pattern
- Composition: how patterns combine
"""

import ast
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

from .models import PIOEntity, ValidationLevel


# =============================================================================
# THE PATTERNS OF CODE-NESS
# =============================================================================

@dataclass
class CodePattern:
    """A pattern that makes code DO something."""
    name: str
    description: str
    template: str  # How to generate this pattern
    recognizer: str  # AST pattern that identifies this
    operations: List[str]  # What you can DO with this pattern
    composes_with: List[str]  # Other patterns this combines with

    def to_entity(self, is_a: List[str]) -> PIOEntity:
        """Convert pattern to YOUKNOW entity."""
        return PIOEntity(
            name=self.name,
            description=self.description,
            is_a=is_a,
            has_parts=self.operations,
            metadata={
                "template": self.template,
                "recognizer": self.recognizer,
                "composes_with": self.composes_with,
            }
        )


# The fundamental code patterns
CODE_PATTERNS: Dict[str, CodePattern] = {
    # ==========================================================================
    # STRUCTURAL PATTERNS - How code IS structured
    # ==========================================================================
    "DataHolder": CodePattern(
        name="DataHolder",
        description="A structure that holds named fields with types",
        template="""
@dataclass
class {name}:
    \"\"\"{description}\"\"\"
{fields}
""",
        recognizer="ClassDef with @dataclass decorator",
        operations=["create", "access_field", "update_field", "compare"],
        composes_with=["Container", "Validator"],
    ),

    "EnumSet": CodePattern(
        name="EnumSet",
        description="A finite set of named values",
        template="""
class {name}(str, Enum):
    \"\"\"{description}\"\"\"
{values}
""",
        recognizer="ClassDef inheriting from Enum",
        operations=["iterate", "compare", "switch"],
        composes_with=["Validator", "Router"],
    ),

    "Container": CodePattern(
        name="Container",
        description="Holds other things (Dict, List, Set)",
        template="{container_type}[{key_type}, {value_type}]",
        recognizer="Subscript with Dict/List/Set",
        operations=["add", "remove", "lookup", "iterate"],
        composes_with=["DataHolder", "Graph"],
    ),

    # ==========================================================================
    # BEHAVIORAL PATTERNS - How code DOES things
    # ==========================================================================
    "Transformer": CodePattern(
        name="Transformer",
        description="Takes input, produces output (pure function)",
        template="""
def {name}(self, {inputs}) -> {output_type}:
    \"\"\"{description}\"\"\"
    {body}
""",
        recognizer="FunctionDef with return annotation",
        operations=["call", "compose", "map"],
        composes_with=["Validator", "Pipeline"],
    ),

    "Mutator": CodePattern(
        name="Mutator",
        description="Changes state (method that modifies self)",
        template="""
def {name}(self, {inputs}):
    \"\"\"{description}\"\"\"
    self.{field} = {new_value}
""",
        recognizer="FunctionDef with self.x = assignment",
        operations=["call", "chain", "undo"],
        composes_with=["DataHolder", "EventEmitter"],
    ),

    "Callback": CodePattern(
        name="Callback",
        description="Hook that fires when something happens",
        template="on_{event}: Optional[Callable[[{args}], {result}]] = None",
        recognizer="Attribute with Optional[Callable]",
        operations=["register", "fire", "unregister"],
        composes_with=["EventEmitter", "Observer"],
    ),

    "Recursive": CodePattern(
        name="Recursive",
        description="Calls itself to process nested structures",
        template="""
def {name}(self, {inputs}, visited: Set = None):
    if visited is None:
        visited = set()
    if {base_case}:
        return {base_result}
    visited.add({key})
    for {item} in {collection}:
        self.{name}({recursive_args}, visited)
""",
        recognizer="FunctionDef that calls itself",
        operations=["call", "memoize", "parallelize"],
        composes_with=["Graph", "Tree"],
    ),

    # ==========================================================================
    # COMPOSITION PATTERNS - How code COMBINES
    # ==========================================================================
    "Pipeline": CodePattern(
        name="Pipeline",
        description="Chain of transformations",
        template="""
def process(self, input):
    result = input
    for step in self.steps:
        result = step(result)
    return result
""",
        recognizer="Loop with accumulator pattern",
        operations=["add_step", "remove_step", "run"],
        composes_with=["Transformer", "Validator"],
    ),

    "Graph": CodePattern(
        name="Graph",
        description="Nodes connected by edges",
        template="""
nodes: Dict[str, Node] = field(default_factory=dict)
edges: List[Edge] = field(default_factory=list)
""",
        recognizer="Dict of nodes + List of edges",
        operations=["add_node", "add_edge", "traverse", "find_path"],
        composes_with=["Recursive", "Propagator"],
    ),

    "Propagator": CodePattern(
        name="Propagator",
        description="Spreads activation/values through a graph",
        template="""
def propagate(self, source, value, visited=None):
    if visited is None:
        visited = set()
    if source in visited:
        return
    visited.add(source)
    for neighbor in self.get_neighbors(source):
        neighbor.value = combine(neighbor.value, value * weight)
        self.propagate(neighbor, neighbor.value, visited)
""",
        recognizer="Recursive + neighbor iteration + value combination",
        operations=["propagate", "decay", "threshold"],
        composes_with=["Graph", "Callback"],
    ),

    # ==========================================================================
    # SKILL-NESS PATTERNS - How skills/flights/personas ARE structured
    # ==========================================================================
    "SkillSpec": CodePattern(
        name="SkillSpec",
        description="A skill package with domain, category, and content",
        template="""---
name: {name}
domain: {domain}
category: {category}
description: {description}
---
# {name}

**WHAT**: {what}
**WHEN**: {when}

{content}
""",
        recognizer="Directory with SKILL.md",
        operations=["equip", "unequip", "search"],
        composes_with=["FlightConfig", "PersonaSpec"],
    ),

    "FlightConfig": CodePattern(
        name="FlightConfig",
        description="A replayable workflow template with waypoints",
        template="""name: {name}
domain: {domain}
description: {description}
waypoints:
{waypoints}
""",
        recognizer="YAML with waypoints list",
        operations=["start", "navigate", "complete"],
        composes_with=["SkillSpec"],
    ),

    "PersonaSpec": CodePattern(
        name="PersonaSpec",
        description="Bundles frame + skillset + MCP set + identity",
        template="""{
    "name": "{name}",
    "domain": "{domain}",
    "description": "{description}",
    "frame": "{frame}",
    "skillset": "{skillset}",
    "mcp_set": "{mcp_set}",
    "identity": "{identity}"
}
""",
        recognizer="JSON with persona fields",
        operations=["equip", "deactivate"],
        composes_with=["SkillSpec", "FlightConfig"],
    ),
}


# =============================================================================
# OBSERVE CODE-NESS
# =============================================================================

def observe_codeness(source_code: str, filename: str = "unknown") -> Dict[str, Any]:
    """
    Observe HOW code IS code.

    Returns the patterns that make this code do what it does.
    """
    tree = ast.parse(source_code)
    observations = {
        "filename": filename,
        "patterns_found": [],
        "classes": {},
        "templates": {},  # How to regenerate this code
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            class_patterns = []

            # Check for dataclass
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Name) and decorator.id == "dataclass":
                    class_patterns.append("DataHolder")

            # Check for Enum
            for base in node.bases:
                if isinstance(base, ast.Name) and base.id == "Enum":
                    class_patterns.append("EnumSet")

            # Check methods
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    # Recursive?
                    for subnode in ast.walk(item):
                        if isinstance(subnode, ast.Call):
                            if isinstance(subnode.func, ast.Attribute):
                                if subnode.func.attr == item.name:
                                    class_patterns.append("Recursive")

                    # Mutator?
                    for subnode in ast.walk(item):
                        if isinstance(subnode, ast.Assign):
                            for target in subnode.targets:
                                if isinstance(target, ast.Attribute):
                                    if isinstance(target.value, ast.Name) and target.value.id == "self":
                                        class_patterns.append("Mutator")
                                        break

                    # Transformer?
                    if item.returns is not None:
                        class_patterns.append("Transformer")

                # Callback?
                if isinstance(item, ast.AnnAssign):
                    if item.annotation:
                        ann_str = ast.unparse(item.annotation) if hasattr(ast, 'unparse') else str(item.annotation)
                        if "Callable" in ann_str:
                            class_patterns.append("Callback")

            # Check for Container patterns in type hints
            for item in node.body:
                if isinstance(item, ast.AnnAssign) and item.annotation:
                    ann_str = ast.unparse(item.annotation) if hasattr(ast, 'unparse') else str(item.annotation)
                    if "Dict" in ann_str or "List" in ann_str or "Set" in ann_str:
                        class_patterns.append("Container")

            # Extract base classes (inheritance)
            bases = []
            for base in node.bases:
                if isinstance(base, ast.Name):
                    bases.append(base.id)
                elif isinstance(base, ast.Attribute):
                    bases.append(ast.unparse(base) if hasattr(ast, 'unparse') else str(base))

            # Extract constructor args with types
            constructor_args = {}
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == "__init__":
                    for arg in item.args.args:
                        if arg.arg == "self":
                            continue
                        arg_type = ast.unparse(arg.annotation) if arg.annotation and hasattr(ast, 'unparse') else "Any"
                        constructor_args[arg.arg] = arg_type

            # Extract dataclass fields with types (class-level annotations)
            fields = {}
            for item in node.body:
                if isinstance(item, ast.AnnAssign) and item.target and isinstance(item.target, ast.Name):
                    field_name = item.target.id
                    field_type = ast.unparse(item.annotation) if hasattr(ast, 'unparse') else "Any"
                    has_default = item.value is not None
                    fields[field_name] = {"type": field_type, "optional": has_default}

            # Extract method signatures (public only + __init__)
            methods = {}
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if item.name.startswith("_") and item.name != "__init__":
                        continue
                    args = {}
                    for arg in item.args.args:
                        if arg.arg == "self":
                            continue
                        arg_type = ast.unparse(arg.annotation) if arg.annotation and hasattr(ast, 'unparse') else "Any"
                        args[arg.arg] = arg_type
                    return_type = ast.unparse(item.returns) if item.returns and hasattr(ast, 'unparse') else "None"
                    methods[item.name] = {
                        "args": args,
                        "return_type": return_type,
                        "is_async": isinstance(item, ast.AsyncFunctionDef),
                    }

            observations["classes"][node.name] = {
                "patterns": list(set(class_patterns)),
                "line": node.lineno,
                "bases": bases,
                "constructor_args": constructor_args,
                "fields": fields,
                "methods": methods,
            }
            observations["patterns_found"].extend(class_patterns)

    observations["patterns_found"] = list(set(observations["patterns_found"]))
    return observations


# =============================================================================
# PROGRAM CODE-NESS INTO ONTOLOGY
# =============================================================================

def program_codeness(observations: Dict[str, Any], yk: "YOUKNOW") -> None:
    """
    Program the observed code-ness into YOUKNOW.

    Takes output from observe_codeness() and feeds it into the YOUKNOW ontology
    via yk.add(). Each class becomes an ontology entity with its full runtime spec:
    constructor args, method signatures, inheritance, fields, patterns.
    """
    # Ensure CodePattern root exists
    if not yk.exists("CodePattern"):
        yk.add(
            name="CodePattern",
            is_a=["Entity"],
            description="A pattern that makes code DO something",
            skip_pipeline=True,
        )

    # Add each observed pattern type
    for pat_name, pattern in CODE_PATTERNS.items():
        if not yk.exists(pat_name):
            yk.add(
                name=pat_name,
                is_a=["CodePattern"],
                description=pattern.description,
                properties={"template": pattern.template},
                skip_pipeline=True,
            )

    # Add each observed class with full runtime spec
    for class_name, class_info in observations["classes"].items():
        is_a = class_info.get("bases", []) or class_info.get("patterns", ["CodePattern"])
        if not is_a:
            is_a = ["CodePattern"]

        # Build properties dict with full runtime spec
        properties = {
            "source_file": observations["filename"],
            "line": class_info["line"],
            "patterns": class_info.get("patterns", []),
            "constructor_args": class_info.get("constructor_args", {}),
            "fields": class_info.get("fields", {}),
            "methods": class_info.get("methods", {}),
        }

        # Build description with calling convention
        desc_parts = [f"Class from {observations['filename']} line {class_info['line']}"]
        if class_info.get("bases"):
            desc_parts.append(f"Inherits: {', '.join(class_info['bases'])}")
        if class_info.get("constructor_args"):
            args_str = ", ".join(f"{k}: {v}" for k, v in class_info["constructor_args"].items())
            desc_parts.append(f"Constructor: {class_name}({args_str})")
        if class_info.get("fields"):
            fields_str = ", ".join(f"{k}: {v['type']}" for k, v in class_info["fields"].items())
            desc_parts.append(f"Fields: {fields_str}")
        if class_info.get("methods"):
            for mname, minfo in class_info["methods"].items():
                if mname == "__init__":
                    continue
                args_str = ", ".join(f"{k}: {v}" for k, v in minfo["args"].items())
                async_prefix = "async " if minfo.get("is_async") else ""
                desc_parts.append(f"Method: {async_prefix}{mname}({args_str}) -> {minfo['return_type']}")

        yk.add(
            name=class_name,
            is_a=is_a,
            description="\n".join(desc_parts),
            properties=properties,
        )


# =============================================================================
# TALK → CODE (simple keyword-based)
# =============================================================================

def talk_to_code(description: str, yk: "YOUKNOW" = None) -> str:
    """
    TODO: This function only returns COMMENTS about patterns, not actual code.
    For real code generation, use:
    - OntologySpec.to_code() in codeness_gen.py
    - spec_to_code() in codeness_gen.py
    - MetaInterpreter.specify() in codeness_gen.py

    This is a STUB that shows pattern detection, not code generation.
    """
    # Find patterns mentioned in description
    patterns_used = []
    for pattern_name in CODE_PATTERNS:
        if pattern_name.lower() in description.lower():
            patterns_used.append(pattern_name)

    # If no explicit patterns, infer from keywords
    if not patterns_used:
        if "holds" in description or "contains" in description:
            patterns_used.append("DataHolder")
        if "enum" in description or "finite set" in description:
            patterns_used.append("EnumSet")
        if "transform" in description or "convert" in description:
            patterns_used.append("Transformer")
        if "recursive" in description or "nested" in description:
            patterns_used.append("Recursive")
        if "propagate" in description or "spread" in description:
            patterns_used.append("Propagator")
        if "skill" in description:
            patterns_used.append("SkillSpec")
        if "flight" in description or "workflow" in description:
            patterns_used.append("FlightConfig")
        if "persona" in description:
            patterns_used.append("PersonaSpec")

    # Generate code from templates
    code_parts = []
    for pattern_name in patterns_used:
        pattern = CODE_PATTERNS.get(pattern_name)
        if pattern:
            code_parts.append(f"# Pattern: {pattern_name}")
            code_parts.append(f"# Template: {pattern.template[:100]}...")
            code_parts.append(f"# Operations: {', '.join(pattern.operations)}")
            code_parts.append("")

    return "\n".join(code_parts) if code_parts else "# No patterns recognized"
