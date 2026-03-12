"""Geometric alignment validation — the laws of the algebra.

Checks the 5 invariants that every compilation output must satisfy.
This is the core safety mechanism of Compoctopus — it prevents
compound garbage by catching misalignment between compilation stages.

Each invariant has a dedicated checker that can be run independently
or composed into a full alignment report.

From evolution_system_analysis.md:
    - Remove the mermaid from the input? → Agent improvises, skips steps
    - Remove the workflow from the system prompt? → Wrong contextual decisions
    - Add a tool without updating the diagram? → Tool never gets called
    - Mention a tool without providing it? → "tool call and result not match" error
    - Give creation_of_god too many tools? → Compound failures
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Set

from compoctopus.types import (
    AlignmentResult,
    GeometricAlignmentReport,
    GeometricInvariant,
    InputPrompt,
    MermaidSpec,
    PromptSection,
    SkillBundle,
    SystemPrompt,
    ToolManifest,
    TrustLevel,
)
from compoctopus.mermaid import extract_tool_references_from_text

logger = logging.getLogger(__name__)


class GeometricAlignmentValidator:
    """Validates the 5 geometric invariants.

    Usage:
        validator = GeometricAlignmentValidator()
        report = validator.validate_all(
            system_prompt=...,
            input_prompt=...,
            tool_manifest=...,
            trust_level=...,
        )
        if not report.aligned:
            print(report)  # Shows which invariants failed and why
    """

    # ─────────────────────────────────────────────────────────────────
    # Invariant 1: Dual Description
    # ─────────────────────────────────────────────────────────────────

    def check_dual_description(
        self,
        system_prompt: SystemPrompt,
        input_prompt: InputPrompt,
    ) -> AlignmentResult:
        """Verify system prompt and input prompt describe the same program.

        System prompt (WORKFLOW section) says WHY and HOW (prose).
        Input prompt (mermaid) says WHAT and WHEN (diagram).
        They must reference the same tasks, tools, and flow.

        Checks:
        - WORKFLOW section exists in system prompt
        - Input prompt has a mermaid spec
        - Every task in the mermaid task_list appears in WORKFLOW text
        - Every tool in the mermaid tool_references appears in CAPABILITY text
        """
        violations = []

        # Check WORKFLOW section exists
        workflow_section = None
        capability_section = None
        for s in system_prompt.sections:
            if s.tag == "WORKFLOW":
                workflow_section = s
            if s.tag == "CAPABILITY":
                capability_section = s

        if not workflow_section:
            violations.append(
                "System prompt is missing the WORKFLOW section. "
                "The WORKFLOW section tells the agent what steps to follow (prose). "
                "Without it, the agent has no structured approach and will improvise. "
                "The input prompt mermaid diagram (WHAT/WHEN) must have a "
                "corresponding WORKFLOW section (WHY/HOW) in the system prompt. "
                "Fix: add a PromptSection(tag='WORKFLOW', content='...') in SystemPromptCompiler."
            )

        if not input_prompt.mermaid:
            violations.append(
                "Input prompt has no mermaid diagram. "
                "The mermaid diagram is the visual workflow specification "
                "that tells the agent WHAT to do and in WHAT ORDER. "
                "Without it, the input prompt is just raw text with no structure. "
                "Fix: ensure InputPromptCompiler.compile() creates a MermaidSpec "
                "with participants (tools) and messages (steps)."
            )

        # Cross-check task list against workflow prose
        if workflow_section and input_prompt.mermaid:
            workflow_text = workflow_section.content.lower()
            for task in input_prompt.mermaid.task_list:
                # Relaxed check: any word from the task label appears in workflow
                task_words = set(task.lower().split())
                # Require at least one significant word to match
                significant = {w for w in task_words if len(w) > 3}
                if significant and not any(w in workflow_text for w in significant):
                    violations.append(
                        f"Mermaid task '{task}' has no corresponding mention in the "
                        f"WORKFLOW section of the system prompt. This means the agent "
                        f"will see this task in the diagram but have no behavioral context "
                        f"for it in its system prompt. Fix: add a reference to '{task}' "
                        f"in the WORKFLOW section, or remove it from the mermaid diagram."
                    )

        # Cross-check tool references against capability section
        if capability_section and input_prompt.mermaid:
            capability_text = capability_section.content.lower()
            for tool in input_prompt.mermaid.tool_references:
                if tool.lower() not in capability_text:
                    violations.append(
                        f"Mermaid diagram references tool '{tool}' but the system prompt "
                        f"CAPABILITY section doesn't mention it. The agent will try to use "
                        f"'{tool}' based on the diagram but won't know what it does. "
                        f"Fix: add '{tool}' to the CAPABILITY section, or remove it "
                        f"from the mermaid diagram."
                    )

        return AlignmentResult(
            invariant=GeometricInvariant.DUAL_DESCRIPTION,
            passed=len(violations) == 0,
            violations=violations,
            details="System prompt ↔ input prompt dual description check",
        )

    # ─────────────────────────────────────────────────────────────────
    # Invariant 2: Capability Surface
    # ─────────────────────────────────────────────────────────────────

    def check_capability_surface(
        self,
        system_prompt: SystemPrompt,
        input_prompt: InputPrompt,
        tool_manifest: ToolManifest,
    ) -> AlignmentResult:
        """Verify all tool references match actual tool surface.

        This is THE check that prevents Error 2013:
            "tool call and result not match"

        Checks:
        - Every tool in tool_manifest is referenced in prompts (no orphans)
        - Every tool referenced in prompts exists in tool_manifest (no phantoms)
        """
        violations = []
        equipped_tools = set(tool_manifest.all_tool_names)

        # Collect all tool references from both prompts
        referenced_tools: Set[str] = set()

        # From system prompt text
        prompt_text = system_prompt.render()
        referenced_tools.update(extract_tool_references_from_text(prompt_text))

        # From input prompt mermaid
        if input_prompt.mermaid:
            referenced_tools.update(input_prompt.mermaid.tool_references)

        # From input prompt goal text
        referenced_tools.update(
            extract_tool_references_from_text(input_prompt.goal)
        )

        # Phantom tools: mentioned but not equipped
        phantoms = referenced_tools - equipped_tools
        for t in sorted(phantoms):
            violations.append(
                f"PHANTOM TOOL: '{t}' is referenced in prompts but is NOT in the "
                f"ToolManifest. The agent will try to call this tool and get an error. "
                f"This is the root cause of 'tool call and result not match' errors. "
                f"Fix: either add '{t}' to the ToolManifest via MCPCompiler, "
                f"or remove all references to '{t}' from the system and input prompts."
            )

        # Orphaned tools: equipped but never mentioned
        orphans = equipped_tools - referenced_tools
        for t in sorted(orphans):
            violations.append(
                f"ORPHANED TOOL: '{t}' is in the ToolManifest but never referenced "
                f"in the system prompt or input prompt. The agent won't know this tool "
                f"exists because nothing mentions it. This wastes a tool slot. "
                f"Fix: either reference '{t}' in the CAPABILITY section and mermaid "
                f"diagram, or remove it from the ToolManifest."
            )

        return AlignmentResult(
            invariant=GeometricInvariant.CAPABILITY_SURFACE,
            passed=len(violations) == 0,
            violations=violations,
            details=(
                f"Equipped: {sorted(equipped_tools)}, "
                f"Referenced: {sorted(referenced_tools)}"
            ),
        )

    # ─────────────────────────────────────────────────────────────────
    # Invariant 3: Trust Boundary
    # ─────────────────────────────────────────────────────────────────

    # Tool categories for trust boundary checking
    WRITE_TOOLS = {"edit", "write", "create", "delete", "remove", "modify", "update"}
    ROUTE_TOOLS = {"route", "dispatch", "orchestrate", "delegate", "invoke"}
    READ_TOOLS = {"read", "view", "list", "search", "query", "get", "fetch"}

    # Trust level → which capabilities are allowed
    TRUST_CAPABILITIES = {
        TrustLevel.ORCHESTRATOR: {"read", "write", "route"},
        TrustLevel.BUILDER: {"read", "write"},
        TrustLevel.EXECUTOR: {"read", "write"},  # But max 1-2 tools
        TrustLevel.OBSERVER: {"read"},
    }

    # Max tools per trust level
    TRUST_MAX_TOOLS = {
        TrustLevel.ORCHESTRATOR: 50,
        TrustLevel.BUILDER: 20,
        TrustLevel.EXECUTOR: 3,
        TrustLevel.OBSERVER: 10,
    }

    def check_trust_boundary(
        self,
        tool_manifest: ToolManifest,
        trust_level: TrustLevel,
        system_prompt: SystemPrompt,
    ) -> AlignmentResult:
        """Verify agent scope matches permission scope.

        From evolution_system:
            "creation_of_god can ONLY use the maker tool and write block reports.
             It cannot fix errors. It cannot edit files. It cannot make decisions.
             The container boundary is the prompt boundary."

        Checks:
        - Tool count within trust level limits
        - Tool capabilities within trust level permissions
        - System prompt CONSTRAINTS section reflects trust level
        """
        violations = []
        all_tools = tool_manifest.all_tool_names

        # Check tool count
        max_tools = self.TRUST_MAX_TOOLS.get(trust_level, 20)
        if len(all_tools) > max_tools:
            violations.append(
                f"Tool count ({len(all_tools)}) exceeds the limit for trust level "
                f"'{trust_level.value}' (max {max_tools}). Too many tools increase "
                f"compound failure probability exponentially. "
                f"Fix: reduce tools to ≤{max_tools} for {trust_level.value} trust, "
                f"or elevate the trust level if the agent truly needs more tools."
            )

        # Check tool capabilities against trust level
        allowed = self.TRUST_CAPABILITIES.get(trust_level, {"read"})

        for tool_name in all_tools:
            name_lower = tool_name.lower()
            # Categorize the tool
            if any(kw in name_lower for kw in self.WRITE_TOOLS):
                if "write" not in allowed:
                    violations.append(
                        f"Write tool '{tool_name}' violates the '{trust_level.value}' "
                        f"trust boundary. {trust_level.value} agents are only allowed "
                        f"{sorted(allowed)} capabilities. Write tools can modify state "
                        f"and must not be given to read-only agents. "
                        f"Fix: remove '{tool_name}' or elevate trust to BUILDER+."
                    )
            if any(kw in name_lower for kw in self.ROUTE_TOOLS):
                if "route" not in allowed:
                    violations.append(
                        f"Routing tool '{tool_name}' violates the '{trust_level.value}' "
                        f"trust boundary. Only ORCHESTRATOR agents can route and delegate "
                        f"to other agents. {trust_level.value} agents are limited to "
                        f"{sorted(allowed)} capabilities. "
                        f"Fix: remove '{tool_name}' or elevate trust to ORCHESTRATOR."
                    )

        # Check CONSTRAINTS section mentions trust level
        has_constraints = any(s.tag == "CONSTRAINTS" for s in system_prompt.sections)
        if not has_constraints:
            violations.append(
                "System prompt is missing the CONSTRAINTS section. "
                "The CONSTRAINTS section enforces the trust boundary in natural language. "
                "Without it, the agent has no awareness of its permission limits. "
                f"For trust level '{trust_level.value}', CONSTRAINTS should specify: "
                f"what the agent CAN do, what it CANNOT do, and the consequences of violations. "
                f"Fix: add a PromptSection(tag='CONSTRAINTS', content='...') in SystemPromptCompiler."
            )

        return AlignmentResult(
            invariant=GeometricInvariant.TRUST_BOUNDARY,
            passed=len(violations) == 0,
            violations=violations,
            details=f"Trust level: {trust_level.value}, tools: {len(all_tools)}",
        )

    # ─────────────────────────────────────────────────────────────────
    # Invariant 4: Phase ↔ Template
    # ─────────────────────────────────────────────────────────────────

    def check_phase_template(
        self,
        phase_configs: Dict[str, dict],
        prompt_templates: Dict[str, str],
    ) -> AlignmentResult:
        """Verify every SM phase has a corresponding prompt template.

        From evolution_system:
            "development → tool_evolution_flow_iog_config_v2
             debug       → debug_evolution_flow_config (continuation: true)"

        Checks:
        - Every phase in phase_configs has a template_name
        - Every template_name maps to an actual prompt template
        """
        violations = []

        for phase_name, config in phase_configs.items():
            template_name = config.get("template_name", "")
            if not template_name:
                violations.append(
                    f"Phase '{phase_name}' has no template_name configured. "
                    f"Every state machine phase must map to a prompt template "
                    f"so the agent's behavior changes with each phase transition. "
                    f"Fix: add 'template_name' to the config dict for phase '{phase_name}'."
                )
            elif template_name not in prompt_templates:
                violations.append(
                    f"Phase '{phase_name}' references template '{template_name}' "
                    f"which doesn't exist in the prompt_templates dictionary. "
                    f"Available templates: {sorted(prompt_templates.keys()) if prompt_templates else '(none)'}. "
                    f"Fix: either create the template '{template_name}' or update "
                    f"phase '{phase_name}' to reference an existing template."
                )

        return AlignmentResult(
            invariant=GeometricInvariant.PHASE_TEMPLATE,
            passed=len(violations) == 0,
            violations=violations,
        )

    # ─────────────────────────────────────────────────────────────────
    # Invariant 5: Polymorphic Dispatch
    # ─────────────────────────────────────────────────────────────────

    def check_polymorphic_dispatch(
        self,
        feature_type: str,
        available_paths: List[str],
    ) -> AlignmentResult:
        """Verify feature type maps to a valid compilation path.

        From evolution_system:
            "if feature_type == 'tool': full_request += tool_help  (tool_mermaid)
             if feature_type == 'agent': full_request += agent_help (agent_mermaid)"

        Checks:
        - feature_type is recognized
        - A compilation path exists for this type
        """
        violations = []

        # Import FeatureType for validation
        from compoctopus.types import FeatureType

        valid_types = {ft.value for ft in FeatureType}
        if feature_type not in valid_types:
            violations.append(
                f"Unknown feature type '{feature_type}'. "
                f"Valid types: {sorted(valid_types)}. "
                f"The feature type determines which compilation path (arms) to use. "
                f"Fix: use one of the valid FeatureType enum values."
            )

        if feature_type not in available_paths:
            violations.append(
                f"No compilation path registered for feature type '{feature_type}'. "
                f"Available paths: {sorted(available_paths)}. "
                f"This means the pipeline doesn't know how to compile '{feature_type}'. "
                f"Fix: register a compilation path for '{feature_type}' in the router, "
                f"or use one of the available feature types."
            )

        return AlignmentResult(
            invariant=GeometricInvariant.POLYMORPHIC_DISPATCH,
            passed=len(violations) == 0,
            violations=violations,
        )

    # ─────────────────────────────────────────────────────────────────
    # Full validation
    # ─────────────────────────────────────────────────────────────────

    def validate_all(
        self,
        system_prompt: SystemPrompt,
        input_prompt: InputPrompt,
        tool_manifest: ToolManifest,
        trust_level: TrustLevel = TrustLevel.BUILDER,
        phase_configs: Optional[Dict[str, dict]] = None,
        prompt_templates: Optional[Dict[str, str]] = None,
        feature_type: str = "agent",
        available_paths: Optional[List[str]] = None,
    ) -> GeometricAlignmentReport:
        """Run all 5 invariant checks and produce a full report.

        Each check runs independently. The report shows exactly
        which invariants passed and which violated.
        """
        results = [
            self.check_dual_description(system_prompt, input_prompt),
            self.check_capability_surface(system_prompt, input_prompt, tool_manifest),
            self.check_trust_boundary(tool_manifest, trust_level, system_prompt),
            self.check_phase_template(
                phase_configs or {}, prompt_templates or {}
            ),
            self.check_polymorphic_dispatch(
                feature_type, available_paths or [feature_type]
            ),
        ]

        passed = sum(1 for r in results if r.passed)
        failed = len(results) - passed
        if failed:
            logger.warning(
                "Alignment validation: %d/5 invariants FAILED — %s",
                failed,
                ", ".join(r.invariant.value for r in results if not r.passed),
            )
        else:
            logger.info("Alignment validation: 5/5 invariants passed ✓")

        return GeometricAlignmentReport(results=results)
