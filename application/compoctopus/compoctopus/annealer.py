"""Compoctopus Annealer — compile .🐙 / .octo files to any target language.

This is the core of the Annealing Protocol. A .🐙 file is target-language
code with annealing markers that delineate stub/pseudocode regions. The
annealer unwraps these markers into executable code.

The .🐙 format is NOT a new language. It's a WAY of writing that makes
the annealing phases explicit via markers. The markers are comment-style
so the file is valid in its target language (just with wrapped stubs).

File extensions:
    .🐙   — canonical (LLM-native, no humans allowed)
    .octo — alias for environments that can't handle emoji paths

════════════════════════════════════════════════════════════════════════
.octo File Format
════════════════════════════════════════════════════════════════════════

A .octo file uses three marker types:

    #>> STUB                   Opens a stub block
    #| actual_code_here        Wrapped pseudocode (the | is the "pipe" state)
    #<< STUB                   Closes the stub block

Between STUB markers, ONLY #| lines and blank lines are allowed.
The #| prefix is stripped during unwrap, producing executable code.

Example .octo file:

    from compoctopus.types import TaskSpec
    from compoctopus.context import CompilationContext

    class MyCompiler:
        def compile(self, ctx: CompilationContext) -> None:
            \"\"\"Compile the thing.\"\"\"
            #>> STUB
            #| task = ctx.task_spec
            #| result = self._process(task)
            #| ctx.output = result
            #<< STUB

        def validate(self, ctx: CompilationContext) -> bool:
            #>> STUB
            #| return ctx.output is not None
            #<< STUB

After anneal:

    from compoctopus.types import TaskSpec
    from compoctopus.context import CompilationContext

    class MyCompiler:
        def compile(self, ctx: CompilationContext) -> None:
            \"\"\"Compile the thing.\"\"\"
            task = ctx.task_spec
            result = self._process(task)
            ctx.output = result

        def validate(self, ctx: CompilationContext) -> bool:
            return ctx.output is not None

════════════════════════════════════════════════════════════════════════
Language-Agnostic Syntax Matchers
════════════════════════════════════════════════════════════════════════

The markers adapt to target language comment style:

    Python:     #>> STUB    #| code    #<< STUB
    JS/TS:      //>> STUB   //| code   //<< STUB
    Rust/C:     //>> STUB   //| code   //<< STUB
    Ruby:       #>> STUB    #| code    #<< STUB

The SyntaxMatcher dataclass defines the pattern for each language.

════════════════════════════════════════════════════════════════════════
Bootstrap Sequence
════════════════════════════════════════════════════════════════════════

1. Human writes annealer.py (this file) by hand — the bootstrap kernel
2. First .🐙 file: PlannerAgent — compiled by following template
3. PlannerAgent writes SpecialistAgent.🐙 — the arm factory
4. SpecialistAgent compiles all default arms from .🐙 specs
5. System is self-compiling — D:D→D fixed point reached
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Syntax Matchers — one per target language
# =============================================================================

@dataclass(frozen=True)
class SyntaxMatcher:
    """Defines the annealing markers for a target language.

    The markers are comment-style in the target language so that
    .octo files are syntactically valid (just with stub blocks).
    """
    name: str
    stub_open: str     # e.g. "#>> STUB"
    stub_close: str    # e.g. "#<< STUB"
    pipe_prefix: str   # e.g. "#| "
    comment_char: str  # e.g. "#"
    file_ext: str      # e.g. ".py"


# Built-in matchers for common languages
PYTHON_SYNTAX = SyntaxMatcher(
    name="python",
    stub_open="#>> STUB",
    stub_close="#<< STUB",
    pipe_prefix="#| ",
    comment_char="#",
    file_ext=".py",
)

JAVASCRIPT_SYNTAX = SyntaxMatcher(
    name="javascript",
    stub_open="//>> STUB",
    stub_close="//<< STUB",
    pipe_prefix="//| ",
    comment_char="//",
    file_ext=".js",
)

TYPESCRIPT_SYNTAX = SyntaxMatcher(
    name="typescript",
    stub_open="//>> STUB",
    stub_close="//<< STUB",
    pipe_prefix="//| ",
    comment_char="//",
    file_ext=".ts",
)

RUST_SYNTAX = SyntaxMatcher(
    name="rust",
    stub_open="//>> STUB",
    stub_close="//<< STUB",
    pipe_prefix="//| ",
    comment_char="//",
    file_ext=".rs",
)

SYNTAX_REGISTRY: Dict[str, SyntaxMatcher] = {
    "python": PYTHON_SYNTAX,
    "javascript": JAVASCRIPT_SYNTAX,
    "typescript": TYPESCRIPT_SYNTAX,
    "rust": RUST_SYNTAX,
}


def get_syntax_for_ext(ext: str) -> SyntaxMatcher:
    """Infer syntax matcher from file extension."""
    ext_map = {
        ".py": PYTHON_SYNTAX,
        ".js": JAVASCRIPT_SYNTAX,
        ".ts": TYPESCRIPT_SYNTAX,
        ".tsx": TYPESCRIPT_SYNTAX,
        ".rs": RUST_SYNTAX,
    }
    if ext not in ext_map:
        raise ValueError(
            f"No syntax matcher for extension '{ext}'. "
            f"Supported: {list(ext_map.keys())}. "
            f"Register a custom SyntaxMatcher with SYNTAX_REGISTRY for new languages."
        )
    return ext_map[ext]


# =============================================================================
# Annealing Phases — what state is each stub block in?
# =============================================================================

class StubPhase(Enum):
    """The annealing phase of a stub block."""
    EMPTY = "empty"       # #>> STUB / #<< STUB with nothing inside
    PSEUDO = "pseudo"     # Has #| lines (pseudocode ready to unwrap)
    ANNEALED = "annealed" # Already unwrapped (no stub markers left)


@dataclass
class StubBlock:
    """A single stub block found in an .octo file."""
    start_line: int        # 0-indexed line of #>> STUB
    end_line: int          # 0-indexed line of #<< STUB
    indent: str            # Whitespace before the #>> marker
    pipe_lines: List[str]  # The #| content lines (with pipe stripped)
    phase: StubPhase       # Current phase
    raw_lines: List[str]   # Original lines including markers


@dataclass
class AnnealReport:
    """Report from an anneal operation."""
    source_path: str
    target_path: str
    syntax: str
    stubs_found: int
    stubs_annealed: int
    stubs_empty: int
    errors: List[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return len(self.errors) == 0

    def __repr__(self) -> str:
        status = "✅" if self.success else "❌"
        return (
            f"{status} AnnealReport({self.source_path} → {self.target_path}, "
            f"stubs={self.stubs_found}, annealed={self.stubs_annealed}, "
            f"empty={self.stubs_empty}, errors={len(self.errors)})"
        )


# =============================================================================
# Core Annealer
# =============================================================================

class Annealer:
    """Compiles .octo files to target language by unwrapping stub blocks.

    Usage:
        annealer = Annealer()

        # Anneal a single file
        report = annealer.anneal("my_compiler.octo", "my_compiler.py")

        # Anneal with explicit syntax
        report = annealer.anneal("router.octo", "router.py",
                                 syntax=PYTHON_SYNTAX)

        # Scan without annealing (just report stub status)
        stubs = annealer.scan("my_file.octo")

        # Anneal in-memory (string → string)
        output = annealer.anneal_source(source_code, syntax=PYTHON_SYNTAX)
    """

    def scan(
        self,
        source: str,
        syntax: Optional[SyntaxMatcher] = None,
    ) -> List[StubBlock]:
        """Find all stub blocks in source code.

        Args:
            source: Source code string (contents of .octo file)
            syntax: Syntax matcher. If None, uses Python.

        Returns:
            List of StubBlock objects describing each stub region.
        """
        if syntax is None:
            syntax = PYTHON_SYNTAX

        lines = source.split("\n")
        stubs = []
        i = 0

        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            if stripped == syntax.stub_open:
                # Found stub open marker
                indent = line[:len(line) - len(line.lstrip())]
                start = i
                pipe_lines = []
                raw_lines = [line]
                i += 1

                # Consume until stub close
                while i < len(lines):
                    inner = lines[i]
                    inner_stripped = inner.strip()
                    raw_lines.append(inner)

                    if inner_stripped == syntax.stub_close:
                        # Found close marker
                        phase = StubPhase.PSEUDO if pipe_lines else StubPhase.EMPTY
                        stubs.append(StubBlock(
                            start_line=start,
                            end_line=i,
                            indent=indent,
                            pipe_lines=pipe_lines,
                            phase=phase,
                            raw_lines=raw_lines,
                        ))
                        break
                    elif inner_stripped.startswith(syntax.pipe_prefix.strip()):
                        # Extract content after pipe prefix
                        # Handle the prefix carefully — preserve internal indentation
                        after_comment = inner.lstrip()
                        if after_comment.startswith(syntax.pipe_prefix):
                            content = after_comment[len(syntax.pipe_prefix):]
                        elif after_comment.startswith(syntax.pipe_prefix.rstrip()):
                            # Handle #| with no trailing space (empty line)
                            content = after_comment[len(syntax.pipe_prefix.rstrip()):]
                            if content.startswith(" "):
                                content = content[1:]
                        else:
                            content = after_comment

                        pipe_lines.append(indent + content)
                    elif inner_stripped == "":
                        # Blank line inside stub — preserve as blank
                        pipe_lines.append("")

                    i += 1
                else:
                    # Never found close marker
                    logger.warning(
                        "Unclosed stub block starting at line %d. "
                        "Expected '%s' but reached end of file.",
                        start + 1, syntax.stub_close,
                    )
            i += 1

        return stubs

    def anneal_source(
        self,
        source: str,
        syntax: Optional[SyntaxMatcher] = None,
    ) -> Tuple[str, AnnealReport]:
        """Anneal source code in-memory.

        Args:
            source: Source code with stub markers.
            syntax: Syntax matcher. If None, uses Python.

        Returns:
            Tuple of (annealed source code, report).
        """
        if syntax is None:
            syntax = PYTHON_SYNTAX

        stubs = self.scan(source, syntax)
        lines = source.split("\n")

        report = AnnealReport(
            source_path="<string>",
            target_path="<string>",
            syntax=syntax.name,
            stubs_found=len(stubs),
            stubs_annealed=0,
            stubs_empty=0,
        )

        if not stubs:
            return source, report

        # Process stubs in REVERSE order so line numbers stay valid
        for stub in reversed(stubs):
            if stub.phase == StubPhase.EMPTY:
                report.stubs_empty += 1
                # Remove the empty stub markers entirely
                # Replace with a NotImplementedError so it's still callable
                nie_line = f"{stub.indent}raise NotImplementedError(\"Stub not yet filled\")"
                lines[stub.start_line:stub.end_line + 1] = [nie_line]
            elif stub.phase == StubPhase.PSEUDO:
                report.stubs_annealed += 1
                # Replace stub block with unwrapped pipe lines
                lines[stub.start_line:stub.end_line + 1] = stub.pipe_lines

        output = "\n".join(lines)
        return output, report

    def anneal(
        self,
        source_path: str,
        target_path: Optional[str] = None,
        syntax: Optional[SyntaxMatcher] = None,
    ) -> AnnealReport:
        """Anneal an .octo file to its target language.

        Args:
            source_path: Path to .octo file.
            target_path: Path to output file. If None, infers from syntax.
            syntax: Syntax matcher. If None, infers from target extension
                   or defaults to Python.

        Returns:
            AnnealReport with results.
        """
        source_path = Path(source_path)

        if not source_path.exists():
            return AnnealReport(
                source_path=str(source_path),
                target_path=str(target_path or ""),
                syntax="unknown",
                stubs_found=0,
                stubs_annealed=0,
                stubs_empty=0,
                errors=[f"Source file not found: {source_path}"],
            )

        # Determine target path
        if target_path is None:
            if syntax:
                target_path = source_path.with_suffix(syntax.file_ext)
            else:
                target_path = source_path.with_suffix(".py")

        target_path = Path(target_path)

        # Determine syntax
        if syntax is None:
            syntax = get_syntax_for_ext(target_path.suffix)

        # Read, anneal, write
        source_code = source_path.read_text()
        output, report = self.anneal_source(source_code, syntax)

        report.source_path = str(source_path)
        report.target_path = str(target_path)

        if report.errors:
            return report

        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(output)

        logger.info(
            "Annealed %s → %s (%d stubs unwrapped, %d empty)",
            source_path.name, target_path.name,
            report.stubs_annealed, report.stubs_empty,
        )

        return report

    def anneal_directory(
        self,
        source_dir: str,
        target_dir: Optional[str] = None,
        syntax: Optional[SyntaxMatcher] = None,
    ) -> List[AnnealReport]:
        """Anneal all .🐙 / .octo files in a directory.

        Args:
            source_dir: Directory containing .🐙 or .octo files.
            target_dir: Output directory. If None, same as source_dir.
            syntax: Syntax matcher. If None, defaults to Python.

        Returns:
            List of AnnealReport for each file.
        """
        source_dir = Path(source_dir)
        target_dir = Path(target_dir) if target_dir else source_dir

        if syntax is None:
            syntax = PYTHON_SYNTAX

        reports = []
        # Collect both .🐙 and .octo files
        octo_files = sorted(
            list(source_dir.glob("*.🐙")) + list(source_dir.glob("*.octo"))
        )
        for octo_file in octo_files:
            target_file = target_dir / octo_file.with_suffix(syntax.file_ext).name
            report = self.anneal(str(octo_file), str(target_file), syntax)
            reports.append(report)

        return reports


# =============================================================================
# Convenience functions
# =============================================================================

def anneal(source_path: str, target_path: Optional[str] = None, **kwargs) -> AnnealReport:
    """Anneal a single file. See Annealer.anneal() for details."""
    return Annealer().anneal(source_path, target_path, **kwargs)


def anneal_source(source: str, syntax: Optional[SyntaxMatcher] = None) -> str:
    """Anneal source code in-memory. Returns annealed source."""
    output, _ = Annealer().anneal_source(source, syntax)
    return output


def scan(source: str, syntax: Optional[SyntaxMatcher] = None) -> List[StubBlock]:
    """Scan source for stub blocks. See Annealer.scan() for details."""
    return Annealer().scan(source, syntax)
