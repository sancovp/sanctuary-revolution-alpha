"""MCP Compiler — selects and configures required tool surfaces.

Arm 3 in the pipeline. Takes agent requirements and produces a ToolManifest.

This arm answers: "Given this agent's task, which MCPs and tools does it need?"
It queries the registry for available MCPs, matches them to task requirements,
and produces a validated tool manifest.

Pattern source: evolution_system.py format_tools() + mcp_servers dict
Legacy source: HermesConfig mcp_servers dictionary construction

Geometric invariants this arm is responsible for:
    2. Capability Surface — every tool it equips must be used; every tool
       referenced must be equipped. This is THE arm that prevents Error 2013.
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
    ToolManifest,
)


class MCPCompiler(CompilerArm):
    """Resolves required MCPs and assembles the tool manifest.

    Input from context: ctx.task_spec, ctx.chain_plan, ctx.agent_profile
    Output to context:  ctx.tool_manifest

    The MCP Compiler is the primary defense against Error 2013:
    "tool call and result not match" — which happens when a prompt
    references a tool that isn't equipped, or vice versa.

    Resolution strategy:
    1. Parse task description for tool requirements
    2. Include MCPs hinted by chain nodes (requires_mcps)
    3. Query registry for MCPs matching domain hints
    4. Resolve tool surfaces from MCP configs
    5. Validate no orphaned or phantom tools
    """

    @property
    def kind(self) -> ArmKind:
        return ArmKind.MCP

    def compile(self, ctx: CompilationContext) -> None:
        """Resolve MCPs and build tool manifest.

        Algorithm:
        1. Collect tool hints from chain_plan nodes
        2. Collect domain hints from task_spec
        3. Query registry for matching MCPs
        4. If no registry, build from hints using mock generation
        5. Build ToolManifest
        """
        from compoctopus.types import MCPConfig, ToolSpec

        # Gather tool hints from chain nodes
        tool_hints = set()
        if ctx.chain_plan:
            for node in ctx.chain_plan.nodes:
                tool_hints.update(node.requires_mcps)

        # Add domain hints from task
        tool_hints.update(ctx.task_spec.domain_hints)

        if not tool_hints:
            # No hints → empty manifest (agent needs no tools)
            ctx.tool_manifest = ToolManifest()
            return

        # Try registry first
        if hasattr(ctx, 'metadata') and ctx.metadata.get('registry'):
            registry = ctx.metadata['registry']
            matched = registry.find_mcps_for_tools(list(tool_hints))
            mcps = {}
            for reg_mcp in matched:
                mcps[reg_mcp.name] = reg_mcp.to_config()
            ctx.tool_manifest = ToolManifest(mcps=mcps)
        else:
            # No registry → create minimal configs from hints
            mcps = {}
            for hint in tool_hints:
                mcps[hint] = MCPConfig(
                    name=hint,
                    tools=[ToolSpec(name=hint, description=f"Tool: {hint}")],
                )
            ctx.tool_manifest = ToolManifest(mcps=mcps)

    def validate(self, ctx: CompilationContext) -> GeometricAlignmentReport:
        """Validate the tool manifest (invariant 2: Capability Surface).

        Checks:
        - Tool manifest exists
        - Every chain node hint is satisfied
        - No empty MCPs (MCPs with zero tools)
        """
        from compoctopus.types import AlignmentResult, GeometricInvariant

        violations = []
        manifest = ctx.tool_manifest

        if not manifest:
            violations.append(
                "MCPCompiler produced no tool manifest. "
                "The compile() step should have created a ToolManifest "
                "mapping MCP names to MCPConfig objects, each with a list of ToolSpecs. "
                "This can happen if compile() was never called, or if an exception "
                "was swallowed. Check that the MCPCompiler arm is in the pipeline."
            )
        else:
            equipped_names = set(manifest.all_tool_names)

            # Check chain node hints are satisfied
            if ctx.chain_plan:
                for node in ctx.chain_plan.nodes:
                    for needed in node.requires_mcps:
                        if needed not in equipped_names:
                            violations.append(
                                f"Chain node '{node.name}' requires MCP tool '{needed}' "
                                f"but '{needed}' is not in the tool manifest. "
                                f"Currently equipped tools: {sorted(equipped_names) if equipped_names else '(none)'}. "
                                f"Fix: either register an MCP that provides '{needed}' "
                                f"in the Registry, or add '{needed}' to task_spec.domain_hints "
                                f"so the MCPCompiler can auto-generate a config for it."
                            )

            # Check no empty MCPs
            for name, mcp_config in manifest.mcps.items():
                if not mcp_config.tools:
                    violations.append(
                        f"MCP '{name}' is registered but has zero tools. "
                        f"An MCP with no tools wastes a connection and provides nothing. "
                        f"Fix: either add ToolSpec entries to this MCP's config, "
                        f"or remove the MCP from the manifest entirely."
                    )

        result = AlignmentResult(
            invariant=GeometricInvariant.CAPABILITY_SURFACE,
            passed=len(violations) == 0,
            violations=violations,
            details=f"Manifest: {len(manifest.all_tool_names) if manifest else 0} tools",
        )
        return GeometricAlignmentReport(results=[result])

    def get_mermaid_spec(self) -> MermaidSpec:
        spec = MermaidSpec()
        spec.add_participant("Pipe", "Pipeline")
        spec.add_participant("MCP", "MCP Compiler")
        spec.add_participant("Registry")
        spec.add_participant("Validator")

        spec.add_message("Pipe", "MCP", "TaskSpec + ChainPlan + AgentProfile")
        spec.add_message("MCP", "MCP", "Collect tool hints from chain nodes")
        spec.add_message("MCP", "Registry", "Query MCPs for domain")
        spec.add_message("Registry", "MCP", "Available MCPs with tool surfaces")
        spec.add_message("MCP", "MCP", "Select required MCPs")
        spec.add_message("MCP", "MCP", "Build ToolManifest")
        spec.add_message("MCP", "Validator", "Check capability surface")
        spec.add_alt([
            ("All tools accounted for", [
                ("Validator", "MCP", "No orphans or phantoms"),
                ("MCP", "Pipe", "ToolManifest"),
            ]),
            ("Mismatch found", [
                ("Validator", "MCP", "Orphaned/phantom tool list"),
                ("MCP", "MCP", "Add missing MCPs or remove unused"),
                ("MCP", "Validator", "Re-check"),
            ]),
        ])
        return spec

    def get_system_prompt_sections(self) -> List[PromptSection]:
        return [
            PromptSection(
                tag="IDENTITY",
                content=(
                    "You are the MCP Compiler. You resolve which MCP servers "
                    "and tools an agent needs, ensuring perfect alignment between "
                    "the tool surface and the prompt surface."
                ),
            ),
            PromptSection(
                tag="WORKFLOW",
                content=(
                    "1. Collect tool hints from chain plan nodes\n"
                    "2. Query the registry for MCPs matching the domain\n"
                    "3. Select the minimal set of MCPs needed\n"
                    "4. Build the ToolManifest\n"
                    "5. Validate: no orphaned tools, no phantom tools\n"
                    "6. Fix any mismatches and re-validate"
                ),
            ),
            PromptSection(
                tag="CAPABILITY",
                content=(
                    "You have access to:\n"
                    "- Registry (query available MCPs and their tool surfaces)\n"
                    "- Alignment validator (check capability surface invariant)"
                ),
            ),
            PromptSection(
                tag="CONSTRAINTS",
                content=(
                    "- CRITICAL: Every tool you include MUST be referenced in "
                    "the system prompt or input prompt\n"
                    "- CRITICAL: Every tool referenced in prompts MUST be in "
                    "the tool manifest\n"
                    "- Prefer minimal tool surfaces — don't include MCPs 'just in case'\n"
                    "- Error 2013 ('tool call and result not match') means this "
                    "arm's validation failed"
                ),
            ),
        ]

    def get_tool_surface(self) -> ToolManifest:
        return ToolManifest(
            mcps={},  # TODO Phase 2: carton MCP for registry queries
            local_tools=[],  # TODO: alignment_validator local tool
        )
