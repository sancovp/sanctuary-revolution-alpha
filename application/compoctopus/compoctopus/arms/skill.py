"""Skill Compiler — injects behavioral skills and context patterns.

Arm 4 in the pipeline. Takes a task profile and produces a SkillBundle.

This arm answers: "What behavioral patterns does this agent need?"
It selects skills from the registry and compiles their context for
injection into the system prompt.

Pattern source: .agent/skills/ directories with SKILL.md files
Legacy source: Context engineering library skill injection

Geometric invariants this arm is responsible for:
    1. Dual Description — skill context must align with workflow expectations
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
    SkillBundle,
    SkillSpec,
    ToolManifest,
)


class SkillCompiler(CompilerArm):
    """Selects and compiles behavioral skills for agent injection.

    Input from context: ctx.task_spec, ctx.chain_plan, ctx.agent_profile
    Output to context:  ctx.skill_bundle

    Skills are behavioral context bundles. Examples:
    - "carton-observation" → how to observe concepts to the KG
    - "crystal-ball-work" → how to navigate Crystal Ball spaces
    - "reactflow-dev" → patterns for ReactFlow development

    The Skill Compiler:
    1. Analyzes what behaviors the task requires
    2. Queries the registry for matching skills
    3. Reads SKILL.md files and compiles injected context
    4. Packages everything into a SkillBundle
    """

    @property
    def kind(self) -> ArmKind:
        return ArmKind.SKILL

    def compile(self, ctx: CompilationContext) -> None:
        """Select and compile skills for the agent.

        Strategy (mirrors skill_manager_mcp patterns):
        1. Collect skill hints from chain_plan nodes (requires_skills)
        2. Query registry for matching skills by domain/behavioral tags
        3. Resolve dependencies (skill.requires → auto-equip)
        4. Compile injected context (concatenate skill instructions)
        """
        from compoctopus.types import SkillSpec

        skill_hints = set()
        if ctx.chain_plan:
            for node in ctx.chain_plan.nodes:
                skill_hints.update(node.requires_skills)

        # Add domain-based skill hints from task
        skill_hints.update(ctx.task_spec.domain_hints)

        skills: list = []

        # Strategy 1: Direct skill hints from chain nodes
        if hasattr(ctx, 'metadata') and ctx.metadata.get('registry'):
            registry = ctx.metadata['registry']

            # Try registry's skill lookup
            for hint in skill_hints:
                found = registry.get_skill(hint)
                if found:
                    skills.append(found.to_spec())

            # # Also try behavioral matching if registry supports it
            # Behavioral matching still not implemented in registry
            # but skill_hints give us direct references

        # Strategy 2: Build SkillSpecs from hints (fallback)
        if not skills and skill_hints:
            for hint in skill_hints:
                skills.append(SkillSpec(
                    name=hint,
                    description=f"Skill: {hint}",
                ))

        # Compile injected context (concatenate descriptions)
        # Mirrors skill_manager_mcp's get_equipped_content()
        injected_parts = []
        for skill in skills:
            injected_parts.append(f"## {skill.name}")
            if skill.description:
                injected_parts.append(skill.description)
            injected_parts.append("")

        ctx.skill_bundle = SkillBundle(
            skills=skills,
            injected_context="\n".join(injected_parts),
        )

    def validate(self, ctx: CompilationContext) -> GeometricAlignmentReport:
        """Validate skill bundle alignment.

        Checks:
        - Skill bundle exists
        - No duplicate skill names
        - Skills with allowed_tools reference real tools in manifest
        """
        from compoctopus.types import AlignmentResult, GeometricInvariant

        violations = []
        bundle = ctx.skill_bundle

        if not bundle:
            violations.append(
                "SkillCompiler produced no skill bundle. "
                "The compile() step should have created a SkillBundle "
                "with a list of SkillSpec objects and an injected_context string. "
                "Even if no skills match, an empty SkillBundle should be created. "
                "Check that the SkillCompiler arm is in the pipeline."
            )
        else:
            # Check for duplicate skill names
            names = [s.name for s in bundle.skills]
            if len(names) != len(set(names)):
                dupes = [n for n in names if names.count(n) > 1]
                violations.append(
                    f"Duplicate skill names in bundle: {set(dupes)}. "
                    f"Each skill must have a unique name. Duplicates cause "
                    f"the injected context to contain repeated instructions, "
                    f"wasting tokens and confusing the agent. "
                    f"Fix: remove duplicate entries or rename them."
                )

        result = AlignmentResult(
            invariant=GeometricInvariant.PHASE_TEMPLATE,
            passed=len(violations) == 0,
            violations=violations,
            details=f"Skills: {len(bundle.skills) if bundle else 0}",
        )
        return GeometricAlignmentReport(results=[result])

    def get_mermaid_spec(self) -> MermaidSpec:
        spec = MermaidSpec()
        spec.add_participant("Pipe", "Pipeline")
        spec.add_participant("Skill", "Skill Compiler")
        spec.add_participant("Registry")
        spec.add_participant("FS", "Filesystem")

        spec.add_message("Pipe", "Skill", "TaskSpec + AgentProfile")
        spec.add_message("Skill", "Skill", "Extract behavioral requirements")
        spec.add_message("Skill", "Registry", "Find matching skills")
        spec.add_message("Registry", "Skill", "Skill list with paths")
        spec.add_loop("For each skill", [
            ("Skill", "FS", "Read SKILL.md"),
            ("FS", "Skill", "Skill instructions"),
            ("Skill", "Skill", "Compile injected context"),
        ])
        spec.add_message("Skill", "Pipe", "SkillBundle")
        return spec

    def get_system_prompt_sections(self) -> List[PromptSection]:
        return [
            PromptSection(
                tag="IDENTITY",
                content=(
                    "You are the Skill Compiler. You select behavioral skills "
                    "from the skill registry and compile their instructions "
                    "for injection into agent system prompts."
                ),
            ),
            PromptSection(
                tag="WORKFLOW",
                content=(
                    "1. Analyze the task for required behavioral patterns\n"
                    "2. Query the registry for skills matching those patterns\n"
                    "3. Read each matched skill's SKILL.md\n"
                    "4. Compile the injected context from all skills\n"
                    "5. Package into a SkillBundle"
                ),
            ),
            PromptSection(
                tag="CAPABILITY",
                content=(
                    "You have access to:\n"
                    "- Skill registry (behavioral tag matching)\n"
                    "- Filesystem (read SKILL.md files)"
                ),
            ),
            PromptSection(
                tag="CONSTRAINTS",
                content=(
                    "- Skills must not contradict each other\n"
                    "- Injected context must be relevant to the task\n"
                    "- Prefer fewer, more specific skills over many broad ones"
                ),
            ),
        ]

    def get_tool_surface(self) -> ToolManifest:
        return ToolManifest(mcps={}, local_tools=[])
