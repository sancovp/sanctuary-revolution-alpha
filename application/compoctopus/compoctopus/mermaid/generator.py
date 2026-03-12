"""Mermaid sequence diagram generator — context → MermaidSpec."""

from __future__ import annotations

from typing import List

from compoctopus.types import MermaidSpec


class MermaidGenerator:
    """Generate MermaidSpec from pipeline context.

    This is how output mermaid becomes reactive: the generator reads
    the compilation context and builds a spec that only references
    tools actually equipped in the ToolManifest.
    """

    def for_agent(
        self,
        agent_name: str,
        tool_names: List[str],
        workflow_steps: List[str],
        error_handling: bool = True,
    ) -> MermaidSpec:
        """Generate a standard agent operation diagram."""
        spec = MermaidSpec()
        spec.add_participant("User")
        spec.add_participant(agent_name, agent_name)

        for tool in tool_names:
            spec.add_participant(tool)

        for step in workflow_steps:
            spec.add_message(agent_name, agent_name, step)

        for tool in tool_names:
            spec.add_message(agent_name, tool, f"Use {tool}")
            spec.add_message(tool, agent_name, f"{tool} result")

        if error_handling:
            spec.add_alt([
                ("Success", [(agent_name, "User", "Result")]),
                ("Error", [
                    (agent_name, agent_name, "Handle error"),
                    (agent_name, "User", "Error report"),
                ]),
            ])
        else:
            spec.add_message(agent_name, "User", "Result")

        return spec

    def for_pipeline(
        self,
        arm_names: List[str],
        task_label: str = "TaskSpec",
    ) -> MermaidSpec:
        """Generate a pipeline/router diagram showing arm sequence."""
        spec = MermaidSpec()
        spec.add_participant("User")
        spec.add_participant("Router", "Compoctopus")

        spec.add_message("User", "Router", task_label)
        spec.add_message("Router", "Router", "Select pipeline arms")

        for arm in arm_names:
            spec.add_message("Router", "Router", f"Run {arm}")

        spec.add_message("Router", "Router", "Validate alignment")
        spec.add_alt([
            ("Aligned", [("Router", "User", "CompiledAgent")]),
            ("Not Aligned", [("Router", "Router", "Fix violations and retry")]),
        ])

        return spec
