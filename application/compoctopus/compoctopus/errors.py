"""Compoctopus error hierarchy.

All errors are typed so that the pipeline can give diagnostic information
about WHERE the failure occurred and WHICH invariant was violated.

Error hierarchy:
    CompoctopusError
    ├── CompilationError          — arm failed to compile
    │   ├── ChainCompilationError
    │   ├── AgentCompilationError
    │   ├── MCPCompilationError
    │   ├── SkillCompilationError
    │   ├── SystemPromptCompilationError
    │   └── InputPromptCompilationError
    ├── AlignmentError            — geometric invariant violated
    │   ├── DualDescriptionError
    │   ├── CapabilitySurfaceError
    │   ├── TrustBoundaryError
    │   ├── PhaseTemplateError
    │   └── PolymorphicDispatchError
    ├── RegistryError             — Carton registry lookup failed
    ├── RoutingError              — Router/onionmorph routing failed
    └── BridgeError               — SDNA/Heaven execution failed
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from compoctopus.types import ArmKind, GeometricInvariant


class CompoctopusError(Exception):
    """Base error for all Compoctopus failures."""

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.context = context or {}


# =============================================================================
# Compilation errors (arm-specific)
# =============================================================================

class CompilationError(CompoctopusError):
    """A compiler arm failed to produce output.

    This means one of the 6 arms (Chain, Agent, MCP, Skill, SystemPrompt,
    InputPrompt) threw an exception during its compile() step. The `arm`
    field tells you which one. Check `input_spec` for what went in and
    `partial_output` for what came out before the failure.
    """

    def __init__(
        self,
        message: str,
        arm: ArmKind,
        input_spec: Optional[Dict[str, Any]] = None,
        partial_output: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        super().__init__(message, **kwargs)
        self.arm = arm
        self.input_spec = input_spec
        self.partial_output = partial_output


class ChainCompilationError(CompilationError):
    def __init__(self, message: str, **kwargs):
        super().__init__(message, arm=ArmKind.CHAIN, **kwargs)


class AgentCompilationError(CompilationError):
    def __init__(self, message: str, **kwargs):
        super().__init__(message, arm=ArmKind.AGENT, **kwargs)


class MCPCompilationError(CompilationError):
    def __init__(self, message: str, **kwargs):
        super().__init__(message, arm=ArmKind.MCP, **kwargs)


class SkillCompilationError(CompilationError):
    def __init__(self, message: str, **kwargs):
        super().__init__(message, arm=ArmKind.SKILL, **kwargs)


class SystemPromptCompilationError(CompilationError):
    def __init__(self, message: str, **kwargs):
        super().__init__(message, arm=ArmKind.SYSTEM_PROMPT, **kwargs)


class InputPromptCompilationError(CompilationError):
    def __init__(self, message: str, **kwargs):
        super().__init__(message, arm=ArmKind.INPUT_PROMPT, **kwargs)


# =============================================================================
# Alignment errors (invariant-specific)
# =============================================================================

class AlignmentError(CompoctopusError):
    """A geometric invariant was violated.

    Compoctopus enforces 5 geometric invariants on every compilation output.
    When any invariant fails, the compiled agent would be unsafe or broken
    if deployed. The `invariant` field tells you which of the 5 was violated.
    The `violations` list gives the specific failures with fix instructions.

    Invariants:
        1. DUAL_DESCRIPTION   - system prompt and input prompt must describe the same program
        2. CAPABILITY_SURFACE  - every tool referenced must exist, and vice versa
        3. TRUST_BOUNDARY      - agent scope must match permission scope
        4. PHASE_TEMPLATE      - every SM phase must map to a prompt template
        5. POLYMORPHIC_DISPATCH - feature type must map to a compilation path
    """

    def __init__(
        self,
        message: str,
        invariant: GeometricInvariant,
        violations: Optional[List[str]] = None,
        **kwargs,
    ):
        super().__init__(message, **kwargs)
        self.invariant = invariant
        self.violations = violations or []


class DualDescriptionError(AlignmentError):
    """Invariant 1: System prompt and input prompt are not dual descriptions of the same program.

    The system prompt WORKFLOW section (prose) and the input prompt mermaid diagram (visual)
    must reference the same tasks, tools, and flow. When they diverge, the agent gets
    contradictory instructions and improvises incorrectly.
    Fix: ensure SystemPromptCompiler and InputPromptCompiler produce aligned content.
    """
    def __init__(self, message: str, **kwargs):
        super().__init__(message, invariant=GeometricInvariant.DUAL_DESCRIPTION, **kwargs)


class CapabilitySurfaceError(AlignmentError):
    """Invariant 2: Tool references in prompts don't match actual tool surface.

    Every tool mentioned in prompts MUST exist in the ToolManifest (no phantoms),
    and every tool in the ToolManifest SHOULD be referenced in prompts (no orphans).
    Phantom tools cause 'tool call and result not match' errors at runtime.
    Orphaned tools waste connection slots and confuse the agent.
    Fix: sync MCPCompiler output with SystemPromptCompiler and InputPromptCompiler.
    """
    def __init__(self, message: str, **kwargs):
        super().__init__(message, invariant=GeometricInvariant.CAPABILITY_SURFACE, **kwargs)


class TrustBoundaryError(AlignmentError):
    """Invariant 3: Agent scope doesn't match container/permission scope.

    Each trust level (ORCHESTRATOR, BUILDER, EXECUTOR, OBSERVER) has limits
    on what tools the agent can use, how many turns it can take, and what
    permissions it has. Violating this means an agent could escalate beyond
    its intended scope.
    Fix: reduce tools/turns/permissions to match the trust level, or elevate trust.
    """
    def __init__(self, message: str, **kwargs):
        super().__init__(message, invariant=GeometricInvariant.TRUST_BOUNDARY, **kwargs)


class PhaseTemplateError(AlignmentError):
    """Invariant 4: State machine phase does not map to a prompt template.

    Every state machine phase must have a corresponding prompt template so the
    agent's behavior changes appropriately with each phase transition. Without
    this mapping, phases run with wrong or missing prompts.
    Fix: ensure every phase_config has a template_name that exists in prompt_templates.
    """
    def __init__(self, message: str, **kwargs):
        super().__init__(message, invariant=GeometricInvariant.PHASE_TEMPLATE, **kwargs)


class PolymorphicDispatchError(AlignmentError):
    """Invariant 5: Feature type does not map to a valid compilation path.

    The feature type (TOOL, AGENT, CHAIN, DOMAIN, SKILL) determines which arms
    run and in what order. If the feature type isn't recognized or has no registered
    compilation path, the pipeline doesn't know how to compile it.
    Fix: use a valid FeatureType enum value, or register a path for the new type.
    """
    def __init__(self, message: str, **kwargs):
        super().__init__(message, invariant=GeometricInvariant.POLYMORPHIC_DISPATCH, **kwargs)


# =============================================================================
# Infrastructure errors
# =============================================================================

class RegistryError(CompoctopusError):
    """Carton registry lookup failed.

    The Registry tried to find an MCP, skill, or domain in Carton (the knowledge graph)
    but the lookup returned nothing or failed. This usually means the concept hasn't
    been registered in Carton yet, or the Carton connection is down.
    Fix: ensure the MCP/skill/domain is registered in Carton, or provide fallback hints.
    """
    pass


class RoutingError(CompoctopusError):
    """Router or onionmorph routing failed.

    The Bandit couldn't determine which compilation path (ChainSelect vs ChainConstruct)
    to use, or the OnionmorphRouter couldn't determine which domain handles this task.
    This usually means the TaskSpec has insufficient domain_hints or the Registry
    has no domains registered that match the task description.
    Fix: add domain_hints to the TaskSpec, or register domains in the Registry.
    """
    pass


class BridgeError(CompoctopusError):
    """SDNA/Heaven bridge execution failed.

    The compiled Link was sent to SDNA for execution (via AriadneChain + HermesConfig)
    but the execution failed. This could be a model error, a tool error, or a
    Heaven runner error. Check the SDNA logs for the specific failure.
    Fix: verify the LinkConfig has valid model/provider, check Heaven is running.
    """
    pass
