"""Input Prompt Compiler — generates the final goal/spec for agent.run().

Arm 6 in the pipeline. Takes the full compilation context and produces
the InputPrompt — the actual string that triggers agent execution.

This arm answers: "What exactly should we say to start the agent?"
It produces the goal string with embedded mermaid diagram, template
variables, and all references aligned to the tool surface.

Pattern source: PIS v1 (prompt_injection_system_vX1.py) — Steps/Blocks/template_vars
Legacy source: evolution_system_request() goal construction

Geometric invariants this arm is responsible for:
    1. Dual Description — input prompt mermaid must be dual to system prompt WORKFLOW
    2. Capability Surface — mermaid tool_references must match tool_manifest
"""

from __future__ import annotations

from typing import List

from compoctopus.base import CompilerArm
from compoctopus.context import CompilationContext
from compoctopus.types import (
    ArmKind,
    GeometricAlignmentReport,
    InputPrompt,
    MermaidSpec,
    PromptSection,
    ToolManifest,
)


class InputPromptCompiler(CompilerArm):
    """Generates the final input prompt / goal for agent execution.

    Input from context: ctx.task_spec, ctx.tool_manifest, ctx.system_prompt,
                       ctx.skill_bundle
    Output to context:  ctx.input_prompt

    The input prompt is the "dovetail" — the final injection point where
    context-specific variables (file paths, IDs, task specifics) are slotted
    into a structured template.

    Key constraint from evolution_system.py:
        "The mermaid in the output ONLY references tools in the tool surface."

    The input prompt contains:
    1. Task description (from task_spec)
    2. Mermaid sequence diagram (aligned to tool_manifest)
    3. Template variables (specific file paths, IDs, etc.)
    """

    @property
    def kind(self) -> ArmKind:
        return ArmKind.INPUT_PROMPT

    def compile(self, ctx: CompilationContext) -> None:
        """Generate the input prompt from compiled context.

        Algorithm:
        1. Generate mermaid diagram referencing only equipped tools
        2. Construct goal from task description + mermaid
        3. Inject template variables from task_spec.constraints
        """
        # Build mermaid diagram aligned to tool_manifest
        mermaid = MermaidSpec()
        mermaid.add_participant("Agent", ctx.agent_profile.name if ctx.agent_profile else "Agent")

        # Add tool participants from manifest
        tool_names = ctx.tool_manifest.all_tool_names if ctx.tool_manifest else []
        for tool_name in tool_names:
            mermaid.add_participant(tool_name)

        # Add workflow steps from chain plan as messages
        if ctx.chain_plan:
            for node in ctx.chain_plan.nodes:
                # If node hints at specific MCPs, create messages to them
                if node.requires_mcps:
                    for mcp in node.requires_mcps:
                        if mcp in tool_names:
                            mermaid.add_message("Agent", mcp, node.description or node.name)
                elif tool_names:
                    # Default: message to first tool
                    mermaid.add_message("Agent", tool_names[0], node.description or node.name)
                else:
                    # No tools, self-message
                    mermaid.add_message("Agent", "Agent", node.description or node.name)

        # Build goal text
        goal = ctx.task_spec.description
        if ctx.task_spec.constraints:
            constraint_parts = [f"{k}: {v}" for k, v in ctx.task_spec.constraints.items()]
            goal += "\n\nConstraints:\n" + "\n".join(f"- {c}" for c in constraint_parts)

        ctx.input_prompt = InputPrompt(
            goal=goal,
            mermaid=mermaid,
            template_vars=dict(ctx.task_spec.constraints),
        )

    def validate(self, ctx: CompilationContext) -> GeometricAlignmentReport:
        """Validate the input prompt.

        Checks (invariants 1 + 2):
        - Mermaid tool_references ⊆ tool_manifest.all_tool_names
        - Goal text is non-empty
        - Input prompt exists
        """
        from compoctopus.types import AlignmentResult, GeometricInvariant

        violations = []
        ip = ctx.input_prompt

        if not ip:
            violations.append(
                "InputPromptCompiler produced no input prompt. "
                "The compile() step should have created an InputPrompt with "
                "a goal (task description), a mermaid diagram (workflow visualization), "
                "and template_vars (from task_spec.constraints). "
                "Check that the InputPromptCompiler arm is in the pipeline."
            )
        else:
            if not ip.goal or not ip.goal.strip():
                violations.append(
                    "Input prompt goal is empty. The goal tells the agent what to do. "
                    "It should contain the task description from ctx.task_spec.description. "
                    "Fix: ensure InputPromptCompiler.compile() sets ip.goal from ctx.task_spec."
                )

            # Check mermaid tool refs are subset of manifest
            if ip.mermaid and ctx.tool_manifest:
                manifest_names = set(ctx.tool_manifest.all_tool_names)
                mermaid_tools = ip.mermaid.tool_references
                for tool in mermaid_tools:
                    if tool not in manifest_names:
                        violations.append(
                            f"Mermaid diagram references tool '{tool}' but '{tool}' "
                            f"is not in the tool manifest. The diagram must only reference "
                            f"tools the agent actually has. Currently equipped tools: "
                            f"{sorted(manifest_names) if manifest_names else '(none)'}. "
                            f"Fix: either remove '{tool}' from the mermaid diagram, "
                            f"or add it to the tool manifest via the MCPCompiler."
                        )

        result = AlignmentResult(
            invariant=GeometricInvariant.CAPABILITY_SURFACE,
            passed=len(violations) == 0,
            violations=violations,
            details=f"Input prompt goal: {ip.goal[:50] if ip and ip.goal else 'N/A'}...",
        )
        return GeometricAlignmentReport(results=[result])

    def get_mermaid_spec(self) -> MermaidSpec:
        spec = MermaidSpec()
        spec.add_participant("Pipe", "Pipeline")
        spec.add_participant("IP", "Input Prompt Compiler")
        spec.add_participant("Mermaid", "Mermaid Generator")
        spec.add_participant("Validator")

        spec.add_message("Pipe", "IP", "TaskSpec + ToolManifest + SystemPrompt")
        spec.add_message("IP", "IP", "Extract tool list from manifest")
        spec.add_message("IP", "Mermaid", "Generate diagram with equipped tools only")
        spec.add_message("Mermaid", "IP", "Aligned MermaidSpec")
        spec.add_message("IP", "IP", "Construct goal (description + mermaid)")
        spec.add_message("IP", "IP", "Inject template variables")
        spec.add_message("IP", "Validator", "Validate alignment")
        spec.add_alt([
            ("Aligned", [
                ("Validator", "IP", "All references valid"),
                ("IP", "Pipe", "InputPrompt"),
            ]),
            ("Misaligned", [
                ("Validator", "IP", "Orphaned/phantom references"),
                ("IP", "Mermaid", "Regenerate with fixes"),
                ("IP", "Validator", "Re-validate"),
            ]),
        ])
        return spec

    def get_system_prompt_sections(self) -> List[PromptSection]:
        return [
            PromptSection(
                tag="IDENTITY",
                content=(
                    "You are the Input Prompt Compiler. You generate the final "
                    "goal string that triggers agent execution, ensuring its "
                    "embedded mermaid diagram only references equipped tools."
                ),
            ),
            PromptSection(
                tag="WORKFLOW",
                content=(
                    "1. Get the list of equipped tools from ToolManifest\n"
                    "2. Generate a mermaid sequence diagram using ONLY those tools\n"
                    "3. Construct the goal: task description + mermaid + template vars\n"
                    "4. Validate that all tool references in the mermaid exist\n"
                    "5. Validate that the task list matches system prompt WORKFLOW"
                ),
            ),
            PromptSection(
                tag="CONSTRAINTS",
                content=(
                    "- Mermaid diagram MUST only reference tools in ToolManifest\n"
                    "- No template variables may be left unfilled\n"
                    "- Goal must be specific and actionable, not vague"
                ),
            ),
        ]

    def get_tool_surface(self) -> ToolManifest:
        return ToolManifest(mcps={}, local_tools=[])

    # ─────────────────────────────────────────────────────────────────
    # Convenience: simple prompt for testing
    # ─────────────────────────────────────────────────────────────────

    @staticmethod
    def simple_prompt(task: str, tools: List[str]) -> InputPrompt:
        """Create a simple input prompt for testing."""
        spec = MermaidSpec()
        spec.add_participant("User")
        spec.add_participant("Agent")
        spec.add_message("User", "Agent", task)
        for tool in tools:
            spec.add_participant(tool)
            spec.add_message("Agent", tool, f"Use {tool}")
        return InputPrompt(
            goal=task,
            mermaid=spec,
            template_vars={},
        )
