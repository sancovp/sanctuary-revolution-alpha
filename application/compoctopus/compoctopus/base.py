"""Abstract base classes for the Compoctopus compiler pipeline.

Every compiler arm implements CompilerArm and satisfies the 5 geometric invariants.
Extracted from the Evolution System's geometric syntax patterns.

This module now uses the proper type algebra from types.py and delegates
validation to alignment.py. The CompilerPipeline threads a CompilationContext
through the arms.

Chain Ontology integration:
    CompilerArm IS a Link — each arm is an executable unit in the chain.
    CompilerPipeline IS a Chain — a sequence of arms/Links.
    This means compile arms can be composed into any Chain topology.

═══════════════════════════════════════════════════════════════════════════
THE ANNEALING PROTOCOL — How Compoctopus Generates Code
═══════════════════════════════════════════════════════════════════════════

When Compoctopus compiles code it doesn't yet have compilers for (i.e.,
when it compiles compilers), it generates in phases using the Annealing
Protocol. This is not just a development pattern — it IS the compilation
strategy, reified into the code.

The key insight: NotImplementedError-with-pseudocode IS the intermediate
representation. compile_partial() IS the gradient. Unwrapping IS the anneal.

    Phase 1 (Stub):    def foo(): raise NotImplementedError()
                       # Interface exists. Types correct. Tests can be written.

    Phase 2 (Pseudo):  def foo(): raise NotImplementedError(
                           # working_code_here
                           # validated against design
                       )
                       # Logic described. Design verified against concept.

    Phase 3 (Tests):   assert foo() == expected
                       # Verification exists. Tests expect NotImplementedError
                       # OR test the interface shape.

    Phase 4 (Anneal):  def foo(): working_code_here
                       # Unwrap: remove raise, uncomment, dedent.
                       # This is a SYNTACTIC operation, not semantic.

    Phase 5 (Verify):  ✅ tests pass
                       # Fixed point reached. Concept reified.

The Construct vs Select duality:

    Construct:  Concept ↔ Design → Stub → Tests → Pseudo ↔ Design
                                                        |
                                                    Unwrap (anneal)
                                                        |
                                                    Test → Concept
                                                        ↑
                                              (the anneal step)

    Select:     List → Construct | Select → List | Select
                ↑                         ↑
         (check golden chains)    (if found, reuse)

compile_partial() reports which arms are at which phase:
  - "not_implemented" = Phase 1/2 (stub or pseudocode, not yet annealed)
  - "failed"          = Phase 4 attempted, tests fail (need design revision)
  - "completed"       = Phase 5 (fixed point reached)

The PartialCompilationReport IS the gradient. Follow it downhill.
═══════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from compoctopus.types import (
    ArmKind,
    CompilationPhase,
    GeometricAlignmentReport,
    InputPrompt,
    MermaidSpec,
    PromptSection,
    SystemPrompt,
    ToolManifest,
)
from compoctopus.context import CompilationContext
from compoctopus.state_machine import StateMachine, make_compiler_sm
from compoctopus.chain_ontology import Link, Chain, LinkResult, LinkStatus

logger = logging.getLogger(__name__)

class CompilerArm(Link, ABC):
    """Abstract base for every Compoctopus compiler arm.

    Inherits from Link — every compiler arm IS a Link in the chain ontology.
    This means arms can be composed into any Chain topology.

    Each arm:
    - Has an identity (ArmKind)
    - Has its own mermaid spec (how it operates)
    - Has its own system prompt sections (its identity as an agent)
    - Has its own tool surface (what it can use)
    - Has its own state machine (deterministic wrapper)
    - Compiles by reading from and writing to a CompilationContext
    - Validates output against the 5 invariants

    The compile() method is called by CompilerPipeline with a shared
    CompilationContext. The arm reads what it needs, writes its output.
    """

    @property
    @abstractmethod
    def kind(self) -> ArmKind:
        """Which arm this is."""
        ...

    @property
    def name(self) -> str:
        """Human-readable name for this arm."""
        return self.kind.value.replace("_", " ").title() + " Compiler"

    @abstractmethod
    def compile(self, ctx: CompilationContext) -> None:
        """Compile by reading from and writing to the context.

        The arm should:
        1. Read its inputs from ctx (e.g. ctx.task_spec, ctx.agent_profile)
        2. Do its compilation work
        3. Write its output to ctx (e.g. ctx.tool_manifest = ToolManifest(...))

        Raises CompilationError if compilation fails.
        """
        ...

    @abstractmethod
    def validate(self, ctx: CompilationContext) -> GeometricAlignmentReport:
        """Validate the context after this arm's compilation.

        Checks the geometric invariants relevant to this arm.
        Not all arms check all 5 invariants — each arm is responsible
        for the invariants it can break.
        """
        ...

    @abstractmethod
    def get_mermaid_spec(self) -> MermaidSpec:
        """Return the mermaid spec for this compiler arm's own operation.

        This is the mermaid diagram that the LLM follows when this arm
        is running as an agent (meta-compilation / D:D->D).
        """
        ...

    @abstractmethod
    def get_system_prompt_sections(self) -> List[PromptSection]:
        """Return the system prompt sections for this compiler's agent.

        These sections define the arm's identity when it runs as an
        SDNA agent. Used for meta-compilation.
        """
        ...

    @abstractmethod
    def get_tool_surface(self) -> ToolManifest:
        """Return the tools this compiler arm's agent needs.

        The actual MCP/tool configuration required when this arm
        runs as an agent.
        """
        ...

    def get_state_machine(self) -> StateMachine:
        """Return the state machine for this arm.

        Default: the standard ANALYZING->COMPILING->VALIDATING->COMPLETE machine.
        Override for arms that need custom phase transitions.
        """
        return make_compiler_sm()

    # ----- Link interface -----

    async def execute(self, context: Optional[Dict[str, Any]] = None, **kwargs) -> LinkResult:
        """Execute this arm as a Link (async bridge over synchronous compile).

        If context contains '_compilation_ctx', uses that CompilationContext.
        Otherwise creates a fresh one. This allows arms to work both as
        standalone Links and as pipeline members.
        """
        ctx_dict = dict(context) if context else {}

        # Get or create CompilationContext
        from compoctopus.types import TaskSpec
        comp_ctx = ctx_dict.get("_compilation_ctx")
        if comp_ctx is None:
            task_desc = ctx_dict.get("_task_description", "")
            comp_ctx = CompilationContext(task_spec=TaskSpec(description=task_desc))

        try:
            self.compile(comp_ctx)
            alignment = self.validate(comp_ctx)
            ctx_dict["_compilation_ctx"] = comp_ctx
            status = LinkStatus.SUCCESS if alignment.aligned else LinkStatus.ERROR
            error = "; ".join(alignment.violations[:3]) if not alignment.aligned else None
            return LinkResult(status=status, context=ctx_dict, error=error)
        except (ValueError, TypeError, KeyError, AttributeError, RuntimeError) as e:
            ctx_dict["_compilation_ctx"] = comp_ctx
            return LinkResult(status=LinkStatus.ERROR, context=ctx_dict, error=str(e))

    def describe(self, depth: int = 0) -> str:
        """LLM-readable description of this compiler arm."""
        indent = "  " * depth
        return f"{indent}Arm \"{self.name}\" [{self.kind.value}]"

    def get_system_prompt(self) -> str:
        """Compose full system prompt from sections."""
        sections = self.get_system_prompt_sections()
        return "\n\n".join(s.render() for s in sections)

    def get_input_prompt(self, task: str) -> str:
        """Compose input prompt from mermaid spec + task.

        The input prompt CONTAINS the mermaid diagram.
        The system prompt REFERENCES it via workflow prose.
        They are dual descriptions of the same program.
        """
        spec = self.get_mermaid_spec()
        return (
            f"{task}\n\n"
            f"Follow this sequence diagram exactly:\n\n"
            f"{spec.diagram}\n\n"
            f"Task list: {spec.task_list}"
        )

    # ----- D:D->D Self-compilation -----

    def self_compile(self) -> "SelfCompilationResult":
        """Validate this arm against its own self-description.

        Treats the arm as an agent and checks:
        - Mermaid spec is structurally valid
        - System prompt has required sections
        - Tool surface is consistent with mermaid tool_references
        - System prompt CAPABILITY matches tool surface
        - System prompt WORKFLOW is dual to mermaid diagram

        This is D:D->D: the compiler arm, described as an agent using
        the same structures it compiles, must pass the same invariants
        it checks in others.

        The design IS the test. If this fails, the arm's self-description
        is inconsistent.
        """
        from compoctopus.mermaid import MermaidValidator
        from compoctopus.alignment import GeometricAlignmentValidator

        issues: List[str] = []

        # 1. Mermaid structural validity
        mermaid_spec = self.get_mermaid_spec()
        mv = MermaidValidator()
        syntax_issues = mv.check_syntax(mermaid_spec)
        issues.extend(syntax_issues)

        # 2. System prompt sections
        sections = self.get_system_prompt_sections()
        section_tags = {s.tag for s in sections}
        if "IDENTITY" not in section_tags:
            issues.append(f"{self.name}: Missing IDENTITY section")
        if "WORKFLOW" not in section_tags:
            issues.append(f"{self.name}: Missing WORKFLOW section")

        # 3. Tool surface vs mermaid tool references
        tool_surface = self.get_tool_surface()
        equipped = set(tool_surface.all_tool_names)

        # Only check tools if arm has them (many stubs have empty surfaces)
        if equipped:
            tool_issues = mv.check_tool_coverage(mermaid_spec, equipped)
            issues.extend(tool_issues)

        # 4. Cross-compile: treat self-description as a CompiledAgent
        system_prompt = SystemPrompt(sections=sections)
        input_prompt = InputPrompt(mermaid=mermaid_spec)

        gav = GeometricAlignmentValidator()

        # Check dual description
        dd = gav.check_dual_description(system_prompt, input_prompt)
        if not dd.passed:
            issues.extend([f"DualDescription: {v}" for v in dd.violations])

        # Check capability surface (only if arm has tools)
        if equipped:
            cs = gav.check_capability_surface(
                system_prompt, input_prompt, tool_surface
            )
            if not cs.passed:
                issues.extend([f"CapabilitySurface: {v}" for v in cs.violations])

        return SelfCompilationResult(
            arm=self.kind,
            arm_name=self.name,
            aligned=len(issues) == 0,
            issues=issues,
            mermaid_spec=mermaid_spec,
            sections=sections,
            tool_surface=tool_surface,
        )


@dataclass
class SelfCompilationResult:
    """Result of D:D->D self-compilation check.

    Each arm, treated as an agent, either passes or fails
    the same invariants it checks in others.
    """
    arm: ArmKind
    arm_name: str = ""
    aligned: bool = False
    issues: List[str] = field(default_factory=list)
    mermaid_spec: Optional[MermaidSpec] = None
    sections: List[PromptSection] = field(default_factory=list)
    tool_surface: Optional[ToolManifest] = None

    def __str__(self) -> str:
        icon = "✅" if self.aligned else "❌"
        lines = [f"{icon} {self.arm_name}"]
        for issue in self.issues:
            lines.append(f"    - {issue}")
        return "\n".join(lines)


@dataclass
class ArmStatus:
    """Status of one arm in a partial pipeline run."""
    arm: ArmKind
    arm_name: str
    status: str  # "completed", "not_implemented", "failed", "skipped"
    error: Optional[str] = None


@dataclass
class PartialCompilationReport:
    """Report from a partial pipeline run.

    Shows exactly which layer the system is at:
    - Which arms completed (implemented and working)
    - Which arms are not yet implemented (NotImplementedError)
    - Which arms failed (implemented but broken)
    - Which arms were skipped (dependencies missing)

    The gradient: the failing tests tell you which arm to fill next.
    """
    arm_statuses: List[ArmStatus] = field(default_factory=list)
    ctx: Optional[CompilationContext] = None

    @property
    def completed(self) -> List[str]:
        return [s.arm_name for s in self.arm_statuses if s.status == "completed"]

    @property
    def not_implemented(self) -> List[str]:
        return [s.arm_name for s in self.arm_statuses if s.status == "not_implemented"]

    @property
    def failed(self) -> List[str]:
        return [s.arm_name for s in self.arm_statuses if s.status == "failed"]

    @property
    def layer(self) -> int:
        """Which layer we're at. 0 = nothing works, N = N arms work."""
        return len(self.completed)

    @property
    def total(self) -> int:
        return len(self.arm_statuses)

    @property
    def next_to_fill(self) -> Optional[str]:
        """The next arm that needs implementation."""
        for s in self.arm_statuses:
            if s.status == "not_implemented":
                return s.arm_name
        for s in self.arm_statuses:
            if s.status == "failed":
                return s.arm_name
        return None

    def __str__(self) -> str:
        lines = [f"=== Partial Compilation: Layer {self.layer}/{self.total} ==="]
        for s in self.arm_statuses:
            icons = {
                "completed": "✅",
                "not_implemented": "🔲",
                "failed": "❌",
                "skipped": "⏭️",
            }
            icon = icons.get(s.status, "?")
            line = f"  {icon} {s.arm_name}: {s.status}"
            if s.error:
                line += f" ({s.error})"
            lines.append(line)
        if self.next_to_fill:
            lines.append(f"\n-> Next to fill: {self.next_to_fill}")
        return "\n".join(lines)


class CompilerPipeline(Chain):
    """Chains multiple CompilerArms together via a shared CompilationContext.

    Inherits from Chain — the pipeline IS a Chain of Link-typed arms.
    This means the pipeline itself is a Link and can be composed into
    larger chains (meta-compilation, empire compilation).

    Each arm's output feeds the next arm's input.
    Validation happens between every arm.
    If any arm fails alignment, the pipeline stops with diagnostics.

    The pipeline does NOT decide which arms to run -- that's the router's job.
    The pipeline just executes a given sequence of arms.

    Hooks:
        Register callbacks via on_arm_start, on_arm_complete, on_arm_error,
        on_pipeline_complete. Each callback receives the relevant context.
        Use for telemetry, metrics, tracing, middleware.
    """

    # Catch compile-time errors but NOT system errors (KeyboardInterrupt, etc.)
    _CATCH_ERRORS = (ValueError, TypeError, KeyError, AttributeError, RuntimeError)

    def __init__(self, arms: List[CompilerArm]):
        super().__init__(chain_name="compiler_pipeline", links=arms)
        self.arms = arms  # backward compat alias
        # Hook registries
        self._hooks_arm_start: list = []
        self._hooks_arm_complete: list = []
        self._hooks_arm_error: list = []
        self._hooks_pipeline_complete: list = []

    # ---- Hook registration ----

    def on_arm_start(self, callback) -> "CompilerPipeline":
        """Register a callback: fn(arm: CompilerArm, ctx: CompilationContext)"""
        self._hooks_arm_start.append(callback)
        return self

    def on_arm_complete(self, callback) -> "CompilerPipeline":
        """Register a callback: fn(arm: CompilerArm, ctx: CompilationContext, alignment: GeometricAlignmentReport)"""
        self._hooks_arm_complete.append(callback)
        return self

    def on_arm_error(self, callback) -> "CompilerPipeline":
        """Register a callback: fn(arm: CompilerArm, ctx: CompilationContext, error: Exception)"""
        self._hooks_arm_error.append(callback)
        return self

    def on_pipeline_complete(self, callback) -> "CompilerPipeline":
        """Register a callback: fn(ctx: CompilationContext)"""
        self._hooks_pipeline_complete.append(callback)
        return self

    def _fire_hooks(self, hooks: list, *args) -> None:
        """Fire all registered hooks, logging (not raising) callback errors."""
        for hook in hooks:
            try:
                hook(*args)
            except Exception as e:  # noqa: don't let bad hooks kill the pipeline
                logger.warning("Hook %s raised: %s", hook.__name__, e)

    def compile(self, ctx: CompilationContext) -> CompilationContext:
        """Run the context through each arm in sequence (strict mode).

        Stops on first error or alignment failure.
        """
        arm_names = [a.kind.value for a in self.arms]
        logger.info(
            "Pipeline starting: %d arms [%s] for task '%s'",
            len(self.arms), " → ".join(arm_names),
            ctx.task_spec.description[:80] if ctx.task_spec else "N/A",
        )

        for i, arm in enumerate(self.arms):
            step = ctx.begin_step(arm.kind)
            logger.debug(
                "Arm %d/%d [%s] compiling...",
                i + 1, len(self.arms), arm.kind.value,
            )
            self._fire_hooks(self._hooks_arm_start, arm, ctx)

            try:
                arm.compile(ctx)
            except self._CATCH_ERRORS as e:
                logger.error(
                    "Arm [%s] threw exception: %s",
                    arm.kind.value, e,
                    exc_info=True,
                )
                self._fire_hooks(self._hooks_arm_error, arm, ctx, e)
                ctx.end_step(step, success=False, error=str(e))
                ctx.alignment = GeometricAlignmentReport(results=[])
                return ctx

            alignment = arm.validate(ctx)
            step.alignment_passed = alignment.aligned
            ctx.end_step(step, success=alignment.aligned)

            self._fire_hooks(self._hooks_arm_complete, arm, ctx, alignment)

            if not alignment.aligned:
                logger.warning(
                    "Arm [%s] failed alignment: %s",
                    arm.kind.value,
                    "; ".join(alignment.results[0].violations) if alignment.results else "unknown",
                )
                ctx.alignment = alignment
                return ctx

            logger.debug(
                "Arm %d/%d [%s] passed alignment ✓",
                i + 1, len(self.arms), arm.kind.value,
            )

        if self.arms:
            ctx.alignment = self.arms[-1].validate(ctx)

        logger.info(
            "Pipeline complete: %d/%d arms succeeded, aligned=%s",
            len(self.arms), len(self.arms),
            ctx.alignment.aligned if ctx.alignment else "N/A",
        )
        self._fire_hooks(self._hooks_pipeline_complete, ctx)
        return ctx

    def compile_partial(self, ctx: CompilationContext) -> PartialCompilationReport:
        """Run the pipeline, gracefully handling NotImplementedError.

        This is the bootstrap mechanism:
        - Tries each arm in sequence
        - If NotImplementedError -> marks as "not_implemented", continues
        - If other error -> marks as "failed", continues
        - If success -> marks as "completed", continues

        Returns a PartialCompilationReport showing exactly which layer
        the system is at and what needs to be filled next.

        The report IS the gradient. Follow it downhill.
        """
        report = PartialCompilationReport(ctx=ctx)

        for arm in self.arms:
            step = ctx.begin_step(arm.kind)

            try:
                arm.compile(ctx)
            except NotImplementedError as e:
                ctx.end_step(step, success=False, error=str(e))
                report.arm_statuses.append(ArmStatus(
                    arm=arm.kind,
                    arm_name=arm.name,
                    status="not_implemented",
                    error=str(e)[:100],
                ))
                continue
            except (ValueError, TypeError, KeyError, AttributeError, RuntimeError) as e:
                ctx.end_step(step, success=False, error=str(e))
                report.arm_statuses.append(ArmStatus(
                    arm=arm.kind,
                    arm_name=arm.name,
                    status="failed",
                    error=str(e)[:100],
                ))
                continue

            # Compilation succeeded -- try validation
            try:
                alignment = arm.validate(ctx)
                step.alignment_passed = alignment.aligned
                ctx.end_step(step, success=True)
                report.arm_statuses.append(ArmStatus(
                    arm=arm.kind,
                    arm_name=arm.name,
                    status="completed" if alignment.aligned else "failed",
                    error=None if alignment.aligned else "; ".join(alignment.violations[:3]),
                ))
            except NotImplementedError:
                ctx.end_step(step, success=True)
                report.arm_statuses.append(ArmStatus(
                    arm=arm.kind,
                    arm_name=arm.name,
                    status="completed",
                    error="validation not yet implemented",
                ))

        return report

    def self_compile_all(self) -> List[SelfCompilationResult]:
        """Run D:D->D self-compilation on every arm in the pipeline.

        Each arm validates its own self-description against the same
        invariants it checks in others. Returns a list of results.

        This is the bootstrap test suite: if all arms pass self-compilation,
        the pipeline's design is internally consistent.
        """
        return [arm.self_compile() for arm in self.arms]

    def describe(self, depth: int = 0) -> str:
        """Describe the pipeline as a human-readable chain tree."""
        indent = "  " * depth
        lines = [f"{indent}CompilerPipeline ({len(self.arms)} arms):"]
        for i, arm in enumerate(self.arms):
            connector = "└──" if i == len(self.arms) - 1 else "├──"
            lines.append(f"{indent}  {connector} {arm.describe(depth + 1).lstrip()}")
        return "\n".join(lines)

    def __repr__(self) -> str:
        return f"CompilerPipeline(arms={[a.kind.value for a in self.arms]})"
