"""Typed PRD — the canonical input to any Compoctopus compiler arm.

The PRD declares everything the coder needs WITHOUT having to think.
Behavioral assertions become tests directly. The coder implements, not invents.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class BehavioralAssertion:
    """One thing execute() MUST do, expressed as a test case."""
    description: str              # "agent writes request file to disk"
    setup: str                    # python code to create agent
    call: str                     # python code to call execute()
    assertions: List[str]         # python assert statements

    def to_test_code(self, test_name: str) -> str:
        """Generate a pytest async test from this assertion."""
        asserts = "\n        ".join(self.assertions)
        return (
            f"    @pytest.mark.asyncio\n"
            f"    async def {test_name}(self):\n"
            f'        """{self.description}"""\n'
            f"        {self.setup}\n"
            f"        {self.call}\n"
            f"        {asserts}\n"
        )

    def to_dict(self) -> dict:
        return {
            "description": self.description,
            "setup": self.setup,
            "call": self.call,
            "assertions": self.assertions,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "BehavioralAssertion":
        return cls(
            description=d["description"],
            setup=d["setup"],
            call=d["call"],
            assertions=d["assertions"],
        )


@dataclass
class LinkSpec:
    """Specification for one link in the agent's chain."""
    name: str                     # "tag"
    kind: str                     # "SDNAC" or "FunctionLink"
    description: str              # "LLM generates tags from task"
    inputs: List[str] = field(default_factory=list)   # ["ctx['task']"]
    outputs: List[str] = field(default_factory=list)   # ["ctx['tags']"]

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "kind": self.kind,
            "description": self.description,
            "inputs": self.inputs,
            "outputs": self.outputs,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "LinkSpec":
        return cls(
            name=d["name"],
            kind=d["kind"],
            description=d["description"],
            inputs=d.get("inputs", []),
            outputs=d.get("outputs", []),
        )


@dataclass
class TypeSpec:
    """Specification for a data type the agent needs."""
    name: str                     # "PlanHierarchy"
    kind: str                     # "dataclass" | "enum" | "TypedDict"
    fields: Dict[str, str] = field(default_factory=dict)
    description: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "kind": self.kind,
            "fields": self.fields,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "TypeSpec":
        return cls(
            name=d["name"],
            kind=d["kind"],
            fields=d.get("fields", {}),
            description=d.get("description", ""),
        )


@dataclass
class PRD:
    """Typed Product Requirements Document — input to Compoctopus."""
    name: str                     # "bandit"
    description: str              # "Select/construct decision layer"
    architecture: str             # "Chain" | "EvalChain"
    links: List[LinkSpec]         # what the chain does
    types: List[TypeSpec] = field(default_factory=list)
    behavioral_assertions: List[BehavioralAssertion] = field(default_factory=list)
    imports_available: List[str] = field(default_factory=list)
    system_prompt_identity: str = ""
    file_structure: Dict[str, str] = field(default_factory=dict)  # path -> description
    project_id: str = ""          # GIINT project ID — links coral to existing project

    def to_dict(self) -> dict:
        """Serialize to dict for JSON storage."""
        d = {
            "name": self.name,
            "description": self.description,
            "architecture": self.architecture,
            "links": [l.to_dict() for l in self.links],
            "types": [t.to_dict() for t in self.types],
            "behavioral_assertions": [ba.to_dict() for ba in self.behavioral_assertions],
            "imports_available": self.imports_available,
            "system_prompt_identity": self.system_prompt_identity,
            "file_structure": self.file_structure,
        }
        if self.project_id:
            d["project_id"] = self.project_id
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "PRD":
        """Deserialize from dict. Validates every slot."""
        # Required fields
        for req in ("name", "description", "architecture", "links"):
            if req not in d:
                raise ValueError(f"PRD missing required field: {req}")

        return cls(
            name=d["name"],
            description=d["description"],
            architecture=d["architecture"],
            links=[LinkSpec.from_dict(l) for l in d["links"]],
            types=[TypeSpec.from_dict(t) for t in d.get("types", [])],
            behavioral_assertions=[
                BehavioralAssertion.from_dict(ba)
                for ba in d.get("behavioral_assertions", [])
            ],
            imports_available=d.get("imports_available", []),
            system_prompt_identity=d.get("system_prompt_identity", ""),
            file_structure=d.get("file_structure", {}),
            project_id=d.get("project_id", ""),
        )

    def save_to_queue(self, queue_dir: Optional[str] = None) -> str:
        """Save this PRD as a .🪸 (coral) file. Returns path."""
        import json
        import os
        from datetime import datetime
        from pathlib import Path

        qdir = Path(queue_dir or os.environ.get("COMPOCTOPUS_QUEUE", "/tmp/compoctopus_queue"))
        qdir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = self.name.replace(" ", "_").lower()
        path = qdir / f"prd_{safe_name}_{timestamp}.🪸"

        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

        return str(path)

    def to_spec_string(self) -> str:
        """Render PRD as the spec string the OctoCoder consumes."""
        lines = [
            f"# {self.name} — {self.description}\n",
            f"## Architecture: {self.architecture}\n",
        ]

        if self.system_prompt_identity:
            lines.append(f"## Identity\n{self.system_prompt_identity}\n")

        # Links
        lines.append("## Chain Links\n")
        for i, link in enumerate(self.links, 1):
            lines.append(f"{i}. `{link.name}` {link.kind} — {link.description}")
            if link.inputs:
                lines.append(f"   Inputs: {', '.join(link.inputs)}")
            if link.outputs:
                lines.append(f"   Outputs: {', '.join(link.outputs)}")
            lines.append("")

        # Types
        if self.types:
            lines.append("## Types\n")
            for t in self.types:
                lines.append(f"### {t.name} ({t.kind})")
                if t.description:
                    lines.append(t.description)
                for fname, ftype in t.fields.items():
                    lines.append(f"  - {fname}: {ftype}")
                lines.append("")

        # File structure
        if self.file_structure:
            lines.append("## File Structure\n```")
            for path, desc in self.file_structure.items():
                lines.append(f"  {path}  # {desc}")
            lines.append("```\n")

        # Imports
        if self.imports_available:
            lines.append("## Imports Available\n```python")
            for imp in self.imports_available:
                lines.append(imp)
            lines.append("```\n")

        # Behavioral assertions — THE KEY PART
        if self.behavioral_assertions:
            lines.append("## BEHAVIORAL TESTS (MANDATORY)\n")
            lines.append("These are NOT optional. TESTS phase MUST implement ALL of them.\n")
            lines.append("Each assertion calls execute() with real LLM calls.\n")
            for i, ba in enumerate(self.behavioral_assertions, 1):
                lines.append(f"### BT-{i}: {ba.description}\n")
                lines.append(f"Setup: `{ba.setup}`")
                lines.append(f"Call: `{ba.call}`")
                lines.append("Assertions:")
                for a in ba.assertions:
                    lines.append(f"  - `{a}`")
                lines.append("")

        return "\n".join(lines)

    def assertion_signatures(self) -> List[str]:
        """Return the test function names VERIFY should check for."""
        return [
            f"test_behavioral_{i}"
            for i in range(1, len(self.behavioral_assertions) + 1)
        ]

