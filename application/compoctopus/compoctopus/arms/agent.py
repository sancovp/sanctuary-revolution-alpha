"""Agent Config Compiler — determines the specific "who" for each agent.

Arm 2 in the pipeline. Takes a ChainPlan and produces an AgentProfile.

This arm answers: "Given this task node, what model/provider/personality?"
It maps SDNAC nodes to HermesConfig-compatible agent profiles.

Pattern source: Acolyte v2 (heaven_base/acolyte_v2/)
Legacy source: HermesConfig generation in SDNA

Geometric invariants this arm is responsible for:
    3. Trust Boundary — the model/permission selection must match scope
"""

from __future__ import annotations

from typing import List

from compoctopus.base import CompilerArm
from compoctopus.context import CompilationContext
from compoctopus.types import (
    AgentProfile,
    ArmKind,
    GeometricAlignmentReport,
    MermaidSpec,
    PermissionMode,
    PromptSection,
    ToolManifest,
    TrustLevel,
)


class AgentConfigCompiler(CompilerArm):
    """Maps task nodes to agent execution profiles.

    Input from context: ctx.task_spec, ctx.chain_plan
    Output to context:  ctx.agent_profile

    Decision axes:
    - Model selection:   complexity → model capability tier
    - Provider selection: cost/latency tradeoff
    - Permission mode:    trust level → permission_mode
    - Temperature:        task type → creativity dial
    - Max turns:          task complexity → conversation budget
    """

    @property
    def kind(self) -> ArmKind:
        return ArmKind.AGENT

    def compile(self, ctx: CompilationContext) -> None:
        """Generate agent profile from task spec and chain plan.

        Decision tree:
        1. Trust level → permission_mode mapping
        2. Task complexity → model tier (minimax, claude, etc.)
        3. Feature type → temperature (creative=0.8, deterministic=0.3)
        4. Chain depth → max_turns budget
        """
        task = ctx.task_spec

        # Permission mode from trust level
        permission_map = {
            TrustLevel.ORCHESTRATOR: PermissionMode.BYPASS,
            TrustLevel.BUILDER: PermissionMode.BYPASS,
            TrustLevel.EXECUTOR: PermissionMode.RESTRICTED,
            TrustLevel.OBSERVER: PermissionMode.READ_ONLY,
        }
        permission_mode = permission_map.get(task.trust_level, PermissionMode.BYPASS)

        # Model tier from chain depth (more nodes = harder task = better model)
        chain_depth = len(ctx.chain_plan.nodes) if ctx.chain_plan else 1
        if chain_depth >= 4 or task.trust_level == TrustLevel.ORCHESTRATOR:
            model = "claude-sonnet"
        elif chain_depth >= 2:
            model = "minimax"
        else:
            model = "minimax"

        # Temperature from feature type
        from compoctopus.types import FeatureType
        temp_map = {
            FeatureType.TOOL: 0.3,    # Deterministic coding
            FeatureType.AGENT: 0.5,   # Moderate creativity
            FeatureType.CHAIN: 0.3,   # Deterministic decomposition
            FeatureType.DOMAIN: 0.5,  # Moderate
            FeatureType.SKILL: 0.7,   # Creative behavioral design
        }
        temperature = temp_map.get(task.feature_type, 0.7)

        # Max turns from trust level + chain depth
        turn_map = {
            TrustLevel.ORCHESTRATOR: 30,
            TrustLevel.BUILDER: 15,
            TrustLevel.EXECUTOR: 5,
            TrustLevel.OBSERVER: 3,
        }
        max_turns = turn_map.get(task.trust_level, 15)

        ctx.agent_profile = AgentProfile(
            name=ctx.chain_plan.nodes[0].name if ctx.chain_plan and ctx.chain_plan.nodes else "agent",
            model=model,
            provider="openrouter",
            temperature=temperature,
            max_turns=max_turns,
            permission_mode=permission_mode,
            backend="heaven",
        )

    def validate(self, ctx: CompilationContext) -> GeometricAlignmentReport:
        """Validate the agent profile (invariant 3: Trust Boundary).

        Checks:
        - EXECUTOR trust → max_turns ≤ 5, permission_mode restricted
        - OBSERVER trust → no write permissions
        - Profile exists and has valid fields
        """
        from compoctopus.types import AlignmentResult, GeometricInvariant

        violations = []
        profile = ctx.agent_profile

        if not profile:
            violations.append(
                "AgentConfigCompiler produced no agent profile. "
                "The compile() step should have created an AgentProfile with "
                "model, provider, temperature, max_turns, and permission_mode. "
                "Check that ctx.task_spec exists and has a valid feature_type."
            )
        else:
            trust = ctx.task_spec.trust_level

            if trust == TrustLevel.EXECUTOR:
                if profile.max_turns > 5:
                    violations.append(
                        f"EXECUTOR trust requires max_turns ≤ 5 to prevent runaway execution, "
                        f"but the agent profile has max_turns={profile.max_turns}. "
                        f"Fix: set profile.max_turns to 5 or less for EXECUTOR trust level."
                    )
                if profile.permission_mode != PermissionMode.RESTRICTED:
                    violations.append(
                        f"EXECUTOR trust requires permission_mode=RESTRICTED "
                        f"to prevent unauthorized actions, but the agent profile has "
                        f"permission_mode={profile.permission_mode}. "
                        f"Fix: set profile.permission_mode to PermissionMode.RESTRICTED."
                    )

            if trust == TrustLevel.OBSERVER:
                if profile.permission_mode != PermissionMode.READ_ONLY:
                    violations.append(
                        f"OBSERVER trust requires permission_mode=READ_ONLY to prevent "
                        f"any write operations, but the agent profile has "
                        f"permission_mode={profile.permission_mode}. "
                        f"Fix: set profile.permission_mode to PermissionMode.READ_ONLY."
                    )

            if not profile.model:
                violations.append(
                    "Agent profile has no model specified. "
                    "Every agent needs a model (e.g. 'minimax', 'claude-sonnet'). "
                    "The AgentConfigCompiler should set model based on task complexity "
                    "and chain depth (≥4 nodes → claude-sonnet, else minimax)."
                )

        result = AlignmentResult(
            invariant=GeometricInvariant.TRUST_BOUNDARY,
            passed=len(violations) == 0,
            violations=violations,
            details=f"Profile: model={profile.model if profile else 'N/A'}",
        )
        return GeometricAlignmentReport(results=[result])

    def get_mermaid_spec(self) -> MermaidSpec:
        spec = MermaidSpec()
        spec.add_participant("Pipe", "Pipeline")
        spec.add_participant("Agent", "Agent Compiler")
        spec.add_participant("Registry")

        spec.add_message("Pipe", "Agent", "TaskSpec + ChainPlan")
        spec.add_message("Agent", "Agent", "Analyze trust level")
        spec.add_message("Agent", "Agent", "Determine model tier")
        spec.add_message("Agent", "Registry", "Query available models")
        spec.add_message("Registry", "Agent", "Model capabilities")
        spec.add_message("Agent", "Agent", "Set temperature, max_turns")
        spec.add_message("Agent", "Agent", "Generate AgentProfile")
        spec.add_message("Agent", "Pipe", "AgentProfile")
        return spec

    def get_system_prompt_sections(self) -> List[PromptSection]:
        return [
            PromptSection(
                tag="IDENTITY",
                content=(
                    "You are the Agent Config Compiler. You determine the "
                    "optimal model, provider, and behavioral parameters for "
                    "SDNA agent execution profiles."
                ),
            ),
            PromptSection(
                tag="WORKFLOW",
                content=(
                    "1. Analyze the task's trust level and complexity\n"
                    "2. Map trust level to permission mode\n"
                    "3. Select model tier based on task requirements\n"
                    "4. Set temperature based on task type\n"
                    "5. Calculate max_turns budget\n"
                    "6. Output AgentProfile"
                ),
            ),
            PromptSection(
                tag="CAPABILITY",
                content="You have access to: model registry, trust level definitions",
            ),
            PromptSection(
                tag="CONSTRAINTS",
                content=(
                    "- Trust boundary must match permission mode\n"
                    "- EXECUTOR agents get max 5 turns\n"
                    "- Temperature must be ≤ 0.3 for deterministic tasks"
                ),
            ),
        ]

    def get_tool_surface(self) -> ToolManifest:
        return ToolManifest(mcps={}, local_tools=[])

    # ─────────────────────────────────────────────────────────────────
    # Convenience defaults
    # ─────────────────────────────────────────────────────────────────

    @staticmethod
    def default_profile(trust: TrustLevel = TrustLevel.BUILDER) -> AgentProfile:
        """Create a default agent profile for testing."""
        permission_map = {
            TrustLevel.ORCHESTRATOR: PermissionMode.BYPASS,
            TrustLevel.BUILDER: PermissionMode.BYPASS,
            TrustLevel.EXECUTOR: PermissionMode.RESTRICTED,
            TrustLevel.OBSERVER: PermissionMode.READ_ONLY,
        }
        turn_map = {
            TrustLevel.ORCHESTRATOR: 30,
            TrustLevel.BUILDER: 15,
            TrustLevel.EXECUTOR: 5,
            TrustLevel.OBSERVER: 3,
        }
        return AgentProfile(
            model="minimax",
            provider="openrouter",
            temperature=0.7,
            max_turns=turn_map.get(trust, 15),
            permission_mode=permission_map.get(trust, PermissionMode.BYPASS),
            backend="heaven",
        )
