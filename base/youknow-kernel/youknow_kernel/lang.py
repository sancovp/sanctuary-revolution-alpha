#!/usr/bin/env python3
"""
YOUKNOW LANGUAGE: A meta-interpreter for ontological programming.

This is the LANGUAGE LAYER - how to speak patterns into existence.

Core constructs:
- DEFINE: create an entity
- IS_A: inheritance relationship
- HAS: composition relationship
- WHEN: conditional/reactive
- DO: imperative action
- VALIDATE: check against pattern_of_isa
- CODEGEN: generate code from entity

Imports patterns from codeness.py (single source of truth).
"""

import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

from .models import PIOEntity, ValidationLevel, ValidationResult
from .codeness import CODE_PATTERNS

logger = logging.getLogger(__name__)


# =============================================================================
# YOUKNOW LANGUAGE AST
# =============================================================================

class NodeType(str, Enum):
    """Types of nodes in YOUKNOW language AST."""
    DEFINE = "define"      # Define an entity
    IS_A = "is_a"          # Inheritance
    HAS = "has"            # Composition
    WHEN = "when"          # Conditional
    DO = "do"              # Action
    VALIDATE = "validate"  # Validation check
    CODEGEN = "codegen"    # Generate code
    BLOCK = "block"        # Sequence of statements
    REF = "ref"            # Reference to entity
    LITERAL = "literal"    # Literal value


@dataclass
class ASTNode:
    """A node in the YOUKNOW language AST."""
    type: NodeType
    value: Any = None
    children: List["ASTNode"] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __repr__(self):
        if self.children:
            return f"{self.type.value}({self.value}, [{len(self.children)} children])"
        return f"{self.type.value}({self.value})"


# =============================================================================
# YOUKNOW LANGUAGE PARSER
# =============================================================================

class YouknowParser:
    """
    Parse YOUKNOW language into AST.

    Syntax:
        DEFINE name IS_A parent [HAS part1, part2, ...]
        WHEN condition DO action
        VALIDATE name
        CODEGEN name AS template
    """

    def __init__(self):
        self.tokens = []
        self.pos = 0

    def parse(self, source: str) -> ASTNode:
        """Parse source into AST."""
        self.tokens = self._tokenize(source)
        self.pos = 0

        statements = []
        while self.pos < len(self.tokens):
            stmt = self._parse_statement()
            if stmt:
                statements.append(stmt)

        return ASTNode(NodeType.BLOCK, children=statements)

    def _tokenize(self, source: str) -> List[str]:
        """Simple tokenizer."""
        source = source.replace('\n', ' ; ')
        tokens = []
        current = ""
        for char in source:
            if char in ' \t':
                if current:
                    tokens.append(current)
                    current = ""
            elif char in '[]{}(),;:':
                if current:
                    tokens.append(current)
                    current = ""
                tokens.append(char)
            else:
                current += char
        if current:
            tokens.append(current)
        return [t for t in tokens if t and not t.startswith('#')]

    def _peek(self) -> Optional[str]:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def _advance(self) -> Optional[str]:
        token = self._peek()
        self.pos += 1
        return token

    def _expect(self, expected: str) -> str:
        token = self._advance()
        if token is None or token.upper() != expected.upper():
            raise SyntaxError(f"Expected '{expected}', got '{token}'")
        return token

    def _parse_statement(self) -> Optional[ASTNode]:
        """Parse a single statement."""
        token = self._peek()

        if token is None or token == ';':
            self._advance()
            return None

        token_upper = token.upper()
        if token_upper == 'DEFINE':
            return self._parse_define()
        elif token_upper == 'WHEN':
            return self._parse_when()
        elif token_upper == 'VALIDATE':
            return self._parse_validate()
        elif token_upper == 'CODEGEN':
            return self._parse_codegen()
        elif token_upper == 'DO':
            return self._parse_do()
        else:
            self._advance()
            return None

    def _parse_define(self) -> ASTNode:
        """Parse: DEFINE name IS_A parent [HAS part1, part2]"""
        self._expect('DEFINE')
        name = self._advance()

        node = ASTNode(NodeType.DEFINE, value=name)

        if self._peek() and self._peek().upper() == 'IS_A':
            self._advance()
            parent = self._advance()
            node.children.append(ASTNode(NodeType.IS_A, value=parent))

        if self._peek() and self._peek().upper() == 'HAS':
            self._advance()
            parts = self._parse_list()
            node.children.append(ASTNode(NodeType.HAS, value=parts))

        return node

    def _parse_when(self) -> ASTNode:
        """Parse: WHEN condition DO action"""
        self._expect('WHEN')
        condition = self._advance()
        self._expect('DO')
        action = self._advance()

        return ASTNode(
            NodeType.WHEN,
            children=[
                ASTNode(NodeType.REF, value=condition),
                ASTNode(NodeType.DO, value=action)
            ]
        )

    def _parse_validate(self) -> ASTNode:
        """Parse: VALIDATE name"""
        self._expect('VALIDATE')
        name = self._advance()
        return ASTNode(NodeType.VALIDATE, value=name)

    def _parse_codegen(self) -> ASTNode:
        """Parse: CODEGEN name [AS pattern]"""
        self._expect('CODEGEN')
        name = self._advance()

        pattern = None
        if self._peek() and self._peek().upper() == 'AS':
            self._advance()
            pattern = self._advance()

        return ASTNode(NodeType.CODEGEN, value=name, metadata={"pattern": pattern})

    def _parse_do(self) -> ASTNode:
        """Parse: DO action"""
        self._expect('DO')
        action = self._advance()
        return ASTNode(NodeType.DO, value=action)

    def _parse_list(self) -> List[str]:
        """Parse comma-separated list."""
        items = []
        keywords = {'DEFINE', 'WHEN', 'VALIDATE', 'CODEGEN'}
        while True:
            token = self._peek()
            if token is None or token == ';' or token.upper() in keywords:
                break
            if token == ',':
                self._advance()
                continue
            items.append(self._advance())
        return items


# =============================================================================
# YOUKNOW META-INTERPRETER
# =============================================================================

class YouknowInterpreter:
    """
    Meta-interpreter for YOUKNOW language.

    Executes YOUKNOW AST against a YOUKNOW kernel.
    """

    def __init__(self, youknow=None):
        if youknow is None:
            from .core import YOUKNOW
            self.yk = YOUKNOW()
        else:
            self.yk = youknow
        self.parser = YouknowParser()
        self.hooks: Dict[str, List[Callable]] = {}
        self.generated_code: Dict[str, str] = {}

        self._bootstrap()

    def _bootstrap(self):
        """Bootstrap the kernel with root patterns from codeness.py."""
        # Root
        self.yk.add_entity(PIOEntity(
            name="pattern_of_isa",
            description="The root of all patterns",
            is_a=[],
            validation_level=ValidationLevel.INSTANTIATES
        ))

        # Add all patterns from CODE_PATTERNS
        for name, pattern in CODE_PATTERNS.items():
            self.yk.add_entity(PIOEntity(
                name=name,
                description=pattern.description,
                is_a=["pattern_of_isa"]
            ))

        logger.debug(f"YouknowInterpreter bootstrapped with {len(CODE_PATTERNS)} patterns")

    def interpret(self, source: str) -> List[Any]:
        """Interpret YOUKNOW source code."""
        ast = self.parser.parse(source)
        return self._eval(ast)

    def _eval(self, node: ASTNode) -> Any:
        """Evaluate an AST node."""
        if node.type == NodeType.BLOCK:
            return [self._eval(child) for child in node.children]
        elif node.type == NodeType.DEFINE:
            return self._eval_define(node)
        elif node.type == NodeType.WHEN:
            return self._eval_when(node)
        elif node.type == NodeType.VALIDATE:
            return self._eval_validate(node)
        elif node.type == NodeType.CODEGEN:
            return self._eval_codegen(node)
        elif node.type == NodeType.DO:
            return self._eval_do(node)
        else:
            return node.value

    def _eval_define(self, node: ASTNode) -> str:
        """Evaluate DEFINE statement."""
        from . import utils

        name = node.value
        is_a = []
        has_parts = []

        for child in node.children:
            if child.type == NodeType.IS_A:
                is_a.append(child.value)
            elif child.type == NodeType.HAS:
                has_parts = child.value

        entity = PIOEntity(
            name=name,
            description=f"Defined via YOUKNOW language",
            is_a=is_a if is_a else ["pattern_of_isa"],
            has_parts=has_parts
        )
        self.yk.add_entity(entity)

        self._fire_hook("define", name, entity)

        result = utils.validate_pattern_of_isa(name, self.yk.entities)
        status = "✓ ONT" if result.valid else "✗ SOUP"
        chain = " → ".join(result.chain) if result.chain else "(no chain)"

        logger.info(f"DEFINED {name} {status}: {chain}")
        return f"DEFINED {name} {status}: {chain}"

    def _eval_when(self, node: ASTNode) -> str:
        """Evaluate WHEN statement - register a hook."""
        condition_node = node.children[0]
        action_node = node.children[1]

        condition = condition_node.value
        action = action_node.value

        if condition not in self.hooks:
            self.hooks[condition] = []
        self.hooks[condition].append(
            lambda name, entity: logger.debug(f"[WHEN {condition}] → {action}: {name}")
        )

        return f"REGISTERED: WHEN {condition} DO {action}"

    def _eval_validate(self, node: ASTNode) -> ValidationResult:
        """Evaluate VALIDATE statement."""
        from . import utils

        name = node.value
        result = utils.validate_pattern_of_isa(name, self.yk.entities)

        if result.valid:
            logger.info(f"✓ {name}: {' → '.join(result.chain)}")
        else:
            logger.warning(f"✗ {name}: missing {result.missing}")

        return result

    def _eval_codegen(self, node: ASTNode) -> str:
        """Evaluate CODEGEN statement - generate Python code."""
        name = node.value
        pattern = node.metadata.get("pattern")

        if name not in self.yk.entities:
            return f"ERROR: {name} not defined"

        entity = self.yk.entities[name]

        if pattern is None:
            pattern = entity.is_a[0] if entity.is_a else "DataHolder"

        code = self._generate_code(name, entity, pattern)
        self.generated_code[name] = code

        logger.info(f"Generated code for {name} as {pattern}")
        return f"GENERATED {name} as {pattern}:\n{code}"

    def _eval_do(self, node: ASTNode) -> str:
        """Evaluate DO statement."""
        from . import utils

        action = node.value

        if action == "list":
            return f"Entities: {list(self.yk.entities.keys())}"
        elif action == "status":
            ont = sum(1 for e in self.yk.entities.values()
                     if utils.validate_pattern_of_isa(e.name, self.yk.entities).valid)
            return f"ONT: {ont}/{len(self.yk.entities)}"
        else:
            return f"Unknown action: {action}"

    def _generate_code(self, name: str, entity: PIOEntity, pattern: str) -> str:
        """Generate Python code for an entity."""
        from .codeness_gen import TEMPLATES

        if pattern == "DataHolder":
            fields = "\n".join(f"    {p}: Any" for p in entity.has_parts) if entity.has_parts else "    pass"
            return f'''@dataclass
class {name}:
    """{entity.description}"""
{fields}
'''

        elif pattern == "EnumSet":
            values = "\n".join(f'    {p.upper()} = "{p.lower()}"' for p in entity.has_parts) if entity.has_parts else "    pass"
            return f'''class {name}(str, Enum):
    """{entity.description}"""
{values}
'''

        elif pattern == "SkillSpec":
            return TEMPLATES["SkillSpec"].format(
                name=name,
                description=entity.description,
                domain=entity.metadata.get("domain", "PAIAB"),
                category=entity.metadata.get("category", "understand"),
                what=entity.metadata.get("what", entity.description),
                when=entity.metadata.get("when", "When needed"),
                content=entity.metadata.get("content", ""),
            )

        elif pattern == "FlightConfig":
            waypoints = entity.has_parts or ["step1"]
            waypoint_yaml = "\n".join(f"  - {w}" for w in waypoints)
            return TEMPLATES["FlightConfig"].format(
                name=name,
                description=entity.description,
                domain=entity.metadata.get("domain", "general"),
                waypoints=waypoint_yaml,
            )

        elif pattern == "PersonaSpec":
            return TEMPLATES["PersonaSpec"].format(
                name=name,
                description=entity.description,
                domain=entity.metadata.get("domain", "PAIAB"),
                frame=entity.metadata.get("frame", ""),
                skillset=entity.metadata.get("skillset", ""),
                mcp_set=entity.metadata.get("mcp_set", ""),
                identity=entity.metadata.get("identity", ""),
            )

        else:
            # Generic
            return f'''# {name}: {pattern}
# {entity.description}
# is_a: {entity.is_a}
# has_parts: {entity.has_parts}
'''

    def _fire_hook(self, event: str, *args):
        """Fire all hooks for an event."""
        for callback in self.hooks.get(event, []):
            callback(*args)


# =============================================================================
# REPL (for testing)
# =============================================================================

def repl():
    """Interactive YOUKNOW language REPL."""
    print("=" * 60)
    print("YOUKNOW LANGUAGE REPL")
    print("=" * 60)
    print("""
Commands:
  DEFINE name IS_A parent HAS part1, part2
  VALIDATE name
  CODEGEN name [AS pattern]
  WHEN event DO action
  DO list | status

Type 'quit' to exit.
""")

    interpreter = YouknowInterpreter()

    while True:
        try:
            line = input("youknow> ").strip()
            if not line:
                continue
            if line.lower() == 'quit':
                break

            results = interpreter.interpret(line)
            for result in results:
                if result:
                    print(result)

        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    repl()
