"""System Prompt Compiler — builds the full XML-tagged behavioral frame.

Arm 5 in the pipeline. Takes accumulated context and produces a SystemPrompt.

This arm answers: "What should the agent's system prompt say?"
It composes XML-tagged sections (IDENTITY, WORKFLOW, CAPABILITY, CONSTRAINTS)
that precisely describe the agent's program from the behavioral/intentional angle.

Pattern source: Progenitor (Species → Settings → DNA → ProfileMaker)
Legacy source: AspectOfGod format_* methods, marker_tokens

Geometric invariants this arm is responsible for:
    1. Dual Description — system prompt must be dual to the input prompt mermaid
    4. Phase ↔ Template — SM phase configs must align with prompt sections
"""

from __future__ import annotations

from typing import List

from compoctopus.base import CompilerArm
from compoctopus.context import CompilationContext
from compoctopus.types import (
    ArmKind,
    GeometricAlignmentReport,
    MermaidSpec,
    PromptSection,
    SystemPrompt,
    ToolManifest,
    TrustLevel,
)


class SystemPromptCompiler(CompilerArm):
    """Composes the complete system prompt from compiled context.

    Input from context: ctx.task_spec, ctx.agent_profile, ctx.tool_manifest,
                       ctx.skill_bundle
    Output to context:  ctx.system_prompt

    The system prompt has mandatory XML sections:
    - IDENTITY:    Who the agent is, its role and mode
    - WORKFLOW:    How it operates (prose dual of mermaid diagram)
    - CAPABILITY:  What tools it has (must match tool_manifest)
    - CONSTRAINTS: What it cannot do (must match trust_level)

    Optional sections (from skills, domains, etc.):
    - PHILOSOPHICAL_FRAMEWORK, NETWORKING_RULES, etc.

    Key principle from Progenitor: KV-driven, every token traceable
    to a config field. No hallucinated capabilities.
    """

    @property
    def kind(self) -> ArmKind:
        return ArmKind.SYSTEM_PROMPT

    def compile(self, ctx: CompilationContext) -> None:
        """Compose system prompt from accumulated context.

        Section generation:
        1. IDENTITY -> from task_spec.description + agent_profile
        2. WORKFLOW -> from task description, must be dual to mermaid
        3. CAPABILITY -> generated from tool_manifest.all_tool_names
        4. CONSTRAINTS -> generated from task_spec.trust_level + constraints
        5. Skill sections -> from skill_bundle.injected_context
        """
        sections = []

        # IDENTITY — who the agent is
        profile = ctx.agent_profile
        identity = f"You are {profile.name if profile else 'an agent'}."
        if ctx.task_spec.description:
            identity += f" Your purpose: {ctx.task_spec.description}."
        if profile and profile.personality:
            identity += f" Personality: {profile.personality}."
        sections.append(PromptSection(tag="IDENTITY", content=identity))

        # WORKFLOW — what steps to follow (prose dual of mermaid)
        workflow_lines = []
        if ctx.chain_plan:
            for i, node in enumerate(ctx.chain_plan.nodes, 1):
                workflow_lines.append(f"{i}. {node.description or node.name}")
        else:
            workflow_lines.append(f"1. {ctx.task_spec.description}")
        sections.append(PromptSection(
            tag="WORKFLOW",
            content="\n".join(workflow_lines),
        ))

        # CAPABILITY — what tools the agent has
        tool_names = ctx.tool_manifest.all_tool_names if ctx.tool_manifest else []
        if tool_names:
            cap_lines = ["You have access to:"]
            for t in tool_names:
                cap_lines.append(f"- {t}")
            sections.append(PromptSection(
                tag="CAPABILITY",
                content="\n".join(cap_lines),
            ))
        else:
            sections.append(PromptSection(
                tag="CAPABILITY",
                content="No external tools. Use your own reasoning.",
            ))

        # CONSTRAINTS — what the agent cannot do
        trust = ctx.task_spec.trust_level
        constraint_map = {
            TrustLevel.ORCHESTRATOR: "Full access. Route and delegate as needed.",
            TrustLevel.BUILDER: "You may read, write, and debug code.",
            TrustLevel.EXECUTOR: "Execute the assigned task only. No exploration.",
            TrustLevel.OBSERVER: "Read-only operations. Do not modify anything.",
        }
        constraint_text = constraint_map.get(trust, "Follow your assignment.")
        if ctx.task_spec.constraints:
            for k, v in ctx.task_spec.constraints.items():
                constraint_text += f"\n- {k}: {v}"
        sections.append(PromptSection(tag="CONSTRAINTS", content=constraint_text))

        # SKILLS — injected skill context
        if ctx.skill_bundle and ctx.skill_bundle.injected_context.strip():
            sections.append(PromptSection(
                tag="SKILLS",
                content=ctx.skill_bundle.injected_context,
                required=False,
            ))

        ctx.system_prompt = SystemPrompt(sections=sections)

    def validate(self, ctx: CompilationContext) -> GeometricAlignmentReport:
        """Validate the system prompt (invariant 1: Dual Description).

        Checks:
        - All mandatory sections present (IDENTITY, WORKFLOW, CAPABILITY, CONSTRAINTS)
        - CAPABILITY section references all tools in tool_manifest
        - CONSTRAINTS match trust_level
        """
        from compoctopus.types import AlignmentResult, GeometricInvariant

        violations = []
        sp = ctx.system_prompt

        if not sp:
            violations.append(
                "SystemPromptCompiler produced no system prompt. "
                "The compile() step should have created a SystemPrompt with sections: "
                "IDENTITY (who the agent is), WORKFLOW (what steps to follow), "
                "CAPABILITY (what tools are available), CONSTRAINTS (what limits apply). "
                "Check that the SystemPromptCompiler arm is in the pipeline "
                "and that ctx.agent_profile, ctx.chain_plan, and ctx.tool_manifest exist."
            )
        else:
            # Check mandatory sections
            tags = {s.tag for s in sp.sections}
            for required in ["IDENTITY", "WORKFLOW", "CAPABILITY", "CONSTRAINTS"]:
                if required not in tags:
                    violations.append(
                        f"System prompt is missing required section '{required}'. "
                        f"A valid system prompt must contain all four sections: "
                        f"IDENTITY, WORKFLOW, CAPABILITY, CONSTRAINTS. "
                        f"Currently present sections: {sorted(tags)}. "
                        f"Fix: add a PromptSection(tag='{required}', content='...') "
                        f"in SystemPromptCompiler.compile()."
                    )

            # Check CAPABILITY mentions all tools
            if ctx.tool_manifest and "CAPABILITY" in tags:
                cap_section = next(s for s in sp.sections if s.tag == "CAPABILITY")
                cap_text = cap_section.content.lower()
                for tool_name in ctx.tool_manifest.all_tool_names:
                    if tool_name.lower() not in cap_text:
                        violations.append(
                            f"Tool '{tool_name}' is in the tool manifest but not mentioned "
                            f"in the system prompt CAPABILITY section. The agent won't know "
                            f"this tool exists unless it's listed in CAPABILITY. "
                            f"Fix: add '{tool_name}' to the CAPABILITY section content."
                        )

        result = AlignmentResult(
            invariant=GeometricInvariant.DUAL_DESCRIPTION,
            passed=len(violations) == 0,
            violations=violations,
            details=f"System prompt: {len(sp.sections) if sp else 0} sections",
        )
        return GeometricAlignmentReport(results=[result])

    def get_mermaid_spec(self) -> MermaidSpec:
        spec = MermaidSpec()
        spec.add_participant("Pipe", "Pipeline")
        spec.add_participant("SP", "System Prompt Compiler")
        spec.add_participant("Validator")

        spec.add_message("Pipe", "SP", "TaskSpec + AgentProfile + ToolManifest + SkillBundle")
        spec.add_message("SP", "SP", "Generate IDENTITY section")
        spec.add_message("SP", "SP", "Generate WORKFLOW section (dual of mermaid)")
        spec.add_message("SP", "SP", "Generate CAPABILITY section (from tool manifest)")
        spec.add_message("SP", "SP", "Generate CONSTRAINTS section (from trust level)")
        spec.add_message("SP", "SP", "Append skill-injected sections")
        spec.add_message("SP", "SP", "Compose final prompt")
        spec.add_message("SP", "Validator", "Validate dual description")
        spec.add_alt([
            ("Aligned", [
                ("Validator", "SP", "Prompt aligned"),
                ("SP", "Pipe", "SystemPrompt"),
            ]),
            ("Misaligned", [
                ("Validator", "SP", "Violations"),
                ("SP", "SP", "Fix sections"),
                ("SP", "Validator", "Re-validate"),
            ]),
        ])
        return spec

    def get_system_prompt_sections(self) -> List[PromptSection]:
        return [
            PromptSection(
                tag="IDENTITY",
                content=(
                    "You are the System Prompt Compiler. You compose XML-tagged "
                    "system prompts that precisely describe an agent's behavioral "
                    "frame, ensuring alignment with its tool surface and task."
                ),
            ),
            PromptSection(
                tag="WORKFLOW",
                content=(
                    "1. Read the task description and agent profile\n"
                    "2. Generate each mandatory section from context\n"
                    "3. The CAPABILITY section MUST list exactly the tools from ToolManifest\n"
                    "4. The WORKFLOW section MUST be the prose dual of the mermaid diagram\n"
                    "5. Append any skill-injected sections\n"
                    "6. Validate alignment and fix violations"
                ),
            ),
            PromptSection(
                tag="CONSTRAINTS",
                content=(
                    "- Every tool in ToolManifest must appear in CAPABILITY section\n"
                    "- Every tool in CAPABILITY must exist in ToolManifest\n"
                    "- WORKFLOW must reference the same steps as the mermaid diagram\n"
                    "- CONSTRAINTS must reflect the actual trust_level permissions"
                ),
            ),
        ]

    def get_tool_surface(self) -> ToolManifest:
        return ToolManifest(mcps={}, local_tools=[])

    # ─────────────────────────────────────────────────────────────────
    # Convenience: minimal prompt for testing
    # ─────────────────────────────────────────────────────────────────

    @staticmethod
    def minimal_prompt(
        identity: str,
        workflow: str,
        tools: List[str],
        constraints: str = "",
    ) -> SystemPrompt:
        """Create a minimal system prompt for testing."""
        sections = [
            PromptSection(tag="IDENTITY", content=identity),
            PromptSection(tag="WORKFLOW", content=workflow),
            PromptSection(
                tag="CAPABILITY",
                content="You have access to:\n" + "\n".join(f"- {t}" for t in tools),
            ),
        ]
        if constraints:
            sections.append(PromptSection(tag="CONSTRAINTS", content=constraints))
        prompt = SystemPrompt(sections=sections)
        prompt.raw = prompt.render()
        return prompt
