"""Mermaid validation — tool coverage, syntax, and evolution system compliance."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Set

from compoctopus.types import MermaidAlt, MermaidMessage, MermaidSpec


class MermaidValidator:
    """Validate mermaid specs against tool surfaces and evolution system patterns."""

    def check_tool_coverage(
        self,
        spec: MermaidSpec,
        available_tools: Set[str],
    ) -> List[str]:
        """Check that every tool referenced in the diagram exists.

        Returns list of violations (empty = valid).
        """
        violations = []
        referenced = set(spec.tool_references)
        phantoms = referenced - available_tools
        for t in sorted(phantoms):
            violations.append(
                f"PHANTOM TOOL in mermaid diagram: '{t}' is referenced as a participant "
                f"but is not in the equipped tool set. The LLM will try to call '{t}' "
                f"and get an error. Currently equipped tools: {sorted(available_tools)}. "
                f"Fix: either equip '{t}' via MCPCompiler, or remove it from the diagram."
            )

        orphans = available_tools - referenced
        for t in sorted(orphans):
            violations.append(
                f"ORPHANED TOOL: '{t}' is equipped but never appears in the mermaid "
                f"diagram. The LLM won't know about this tool because the diagram "
                f"doesn't show it. Fix: add '{t}' as a participant in the diagram "
                f"with message flows, or remove it from the equipment."
            )

        return violations

    def check_syntax(self, spec: MermaidSpec) -> List[str]:
        """Validate structural integrity of the spec."""
        violations = []
        if not spec.participants:
            violations.append(
                "Mermaid diagram has no participants. A valid diagram needs at least "
                "the agent as a participant. "
                "Fix: call spec.add_participant('Agent', agent_name) before adding messages."
            )
        if not spec._messages:
            violations.append(
                "Mermaid diagram has no messages. A valid diagram needs at least "
                "one message (arrow) between participants. "
                "Fix: call spec.add_message(sender, receiver, label) to add workflow steps."
            )

        participant_set = set(spec.participants)
        for item in spec._messages:
            msgs = [item] if isinstance(item, MermaidMessage) else [
                m for b in item.branches for m in b.messages
            ]
            for msg in msgs:
                if msg.sender not in participant_set:
                    violations.append(
                        f"Message sender '{msg.sender}' is not in the participant list. "
                        f"Current participants: {sorted(participant_set)}. "
                        f"Fix: add '{msg.sender}' as a participant."
                    )
                if msg.receiver not in participant_set:
                    violations.append(
                        f"Message receiver '{msg.receiver}' is not in the participant list. "
                        f"Current participants: {sorted(participant_set)}. "
                        f"Fix: add '{msg.receiver}' as a participant."
                    )

        return violations

    def check_evolution_system_compliance(
        self,
        spec: MermaidSpec,
        expected_tools: Optional[Set[str]] = None,
    ) -> List["EvolutionSystemViolation"]:
        """Validate that a mermaid follows the evolution_system.py pattern.

        Checks 9 rules at 3 severity levels (ERROR, WARNING, INFO).
        See specs/evolution_system_validation.md for full spec.
        """
        violations: List[EvolutionSystemViolation] = []

        all_msgs = _flatten_messages(spec)
        participants = set(spec.participants)

        # --- V1: Participants ---
        if "User" not in participants:
            violations.append(EvolutionSystemViolation(
                rule="V1", severity="ERROR",
                message="Missing 'User' participant.",
                fix_hint="Add 'participant User' to the diagram.",
            ))

        agent_participants = participants - {"User", "Tools"}
        if not agent_participants:
            violations.append(EvolutionSystemViolation(
                rule="V1", severity="ERROR",
                message="No agent participant found.",
                fix_hint="Add 'participant <AgentName>' to the diagram.",
            ))

        # --- V2: Initial Task List ---
        first_agent_to_user = None
        for msg in all_msgs:
            if msg.sender != "User" and msg.receiver == "User":
                first_agent_to_user = msg
                break

        if first_agent_to_user is None:
            violations.append(EvolutionSystemViolation(
                rule="V2", severity="ERROR",
                message="No agent-to-user message found.",
                fix_hint="Agent must send first message to User with update_task_list.",
            ))
        else:
            task_list_match = re.search(
                r'update_task_list\s*=\s*\[([^\]]+)\]',
                first_agent_to_user.label,
            )
            if not task_list_match:
                violations.append(EvolutionSystemViolation(
                    rule="V2", severity="ERROR",
                    message=f"First agent-to-user message does not contain update_task_list=. "
                            f"Label: '{first_agent_to_user.label[:80]}'",
                    fix_hint='Use: ```update_task_list=["task1", "task2", ...]```',
                ))

        # --- V3: Task Completion ---
        declared_tasks: List[str] = []
        for msg in all_msgs:
            m = re.search(r'update_task_list\s*=\s*\[([^\]]+)\]', msg.label)
            if m:
                for item in re.findall(r'"([^"]+)"', m.group(1)):
                    declared_tasks.append(item)

        completed_tasks: List[str] = []
        for msg in all_msgs:
            m = re.search(r'complete_task\s*=\s*(.+?)(?:```|$)', msg.label)
            if m:
                completed_tasks.append(m.group(1).strip())

        if declared_tasks:
            for task in declared_tasks:
                if task not in completed_tasks:
                    violations.append(EvolutionSystemViolation(
                        rule="V3", severity="ERROR",
                        message=f"Task '{task}' declared but never completed.",
                        fix_hint=f'Add: Agent->>User: ```complete_task={task}```',
                    ))

        for msg in all_msgs:
            if "complete_task" in msg.label and msg.receiver != "User":
                violations.append(EvolutionSystemViolation(
                    rule="V3", severity="ERROR",
                    message=f"complete_task sent to '{msg.receiver}' instead of 'User'.",
                    fix_hint="complete_task messages must go from Agent to User.",
                ))

        # --- V4: GOAL ACCOMPLISHED ---
        goal_msgs = [msg for msg in all_msgs if "GOAL ACCOMPLISHED" in msg.label]
        if not goal_msgs:
            violations.append(EvolutionSystemViolation(
                rule="V4", severity="ERROR",
                message="No GOAL ACCOMPLISHED message found.",
                fix_hint='Add: Agent->>User: ```GOAL ACCOMPLISHED```',
            ))
        elif len(goal_msgs) > 1:
            violations.append(EvolutionSystemViolation(
                rule="V4", severity="ERROR",
                message=f"GOAL ACCOMPLISHED appears {len(goal_msgs)} times.",
                fix_hint="Remove duplicates. Must appear exactly once.",
            ))

        # --- V5: Iteration Boundaries ---
        next_task_msgs = [msg for msg in all_msgs
                         if msg.sender == "User" and "Next task" in msg.label]
        if declared_tasks and not next_task_msgs:
            violations.append(EvolutionSystemViolation(
                rule="V5", severity="WARNING",
                message="No 'User->>Agent: Next task' boundaries found.",
                fix_hint="Add 'User->>Agent: Next task' between task sections.",
            ))

        # --- V6: Tool Call Format ---
        tool_call_re = re.compile(
            r'^[A-Z]\w*'
            r'|^\w+Tool'
            r'|^\w+Util'
        )
        for msg in all_msgs:
            if msg.receiver == "Tools" or (msg.receiver not in {"User"} and msg.receiver in participants):
                if msg.sender != "User" and msg.sender != "Tools":
                    if not tool_call_re.match(msg.label.strip()):
                        violations.append(EvolutionSystemViolation(
                            rule="V6", severity="WARNING",
                            message=f"Agent→Tools message doesn't start with tool name: '{msg.label[:60]}'",
                            fix_hint="Start with: 'ToolName: description' or 'ToolName with target X'",
                        ))

        # --- V7: Alt/Else Blocks ---
        alt_blocks = [item for item in spec._messages if isinstance(item, MermaidAlt)]
        if not alt_blocks:
            violations.append(EvolutionSystemViolation(
                rule="V7", severity="WARNING",
                message="No alt/else blocks found. Error handling expected.",
                fix_hint="Add alt/else blocks for error paths.",
            ))
        for alt in alt_blocks:
            if len(alt.branches) < 2:
                violations.append(EvolutionSystemViolation(
                    rule="V7", severity="WARNING",
                    message=f"Alt block has only {len(alt.branches)} branch(es).",
                    fix_hint="Add an else branch.",
                ))

        # --- V8: Response Shapes ---
        for msg in all_msgs:
            if msg.sender != "User" and msg.receiver in agent_participants:
                if not msg.label.strip():
                    violations.append(EvolutionSystemViolation(
                        rule="V8", severity="INFO",
                        message=f"Empty response shape from '{msg.sender}'.",
                        fix_hint="Add response shape: {success}, {error details}, etc.",
                    ))

        # --- V9: WriteBlockReportTool ---
        has_error_branch = any(
            any("error" in b.condition.lower() or "fail" in b.condition.lower()
                for b in alt.branches)
            for alt in alt_blocks
        )
        has_block_report = any("BlockReport" in msg.label for msg in all_msgs)
        if has_error_branch and not has_block_report:
            violations.append(EvolutionSystemViolation(
                rule="V9", severity="INFO",
                message="Error branches exist but no WriteBlockReportTool reference.",
                fix_hint="Consider adding WriteBlockReportTool for unresolvable errors.",
            ))

        severity_order = {"ERROR": 0, "WARNING": 1, "INFO": 2}
        violations.sort(key=lambda v: severity_order.get(v.severity, 3))

        return violations


def _flatten_messages(spec: MermaidSpec) -> List[MermaidMessage]:
    """Extract all MermaidMessages from a spec, including inside alt/else blocks."""
    msgs = []
    for item in spec._messages:
        if isinstance(item, MermaidMessage):
            msgs.append(item)
        elif isinstance(item, MermaidAlt):
            for branch in item.branches:
                msgs.extend(branch.messages)
    return msgs


@dataclass
class EvolutionSystemViolation:
    """A violation of the evolution system mermaid pattern."""
    rule: str
    severity: str
    message: str
    fix_hint: str

    def __str__(self) -> str:
        return f"[{self.severity}] {self.rule}: {self.message}\n  Fix: {self.fix_hint}"


def extract_tool_references_from_text(text: str) -> Set[str]:
    """Extract tool names referenced in prose prompt text."""
    refs = set()

    for m in re.finditer(r"\b(?:use|call|invoke)\s+(\w+Tool)\b", text, re.IGNORECASE):
        refs.add(m.group(1))

    for m in re.finditer(r"\bmcp[:\s]+(\w+)", text, re.IGNORECASE):
        refs.add(m.group(1))

    for m in re.finditer(r"^[\s\-*]+(\w+)\s+(?:MCP|tool|mcp)", text, re.MULTILINE):
        refs.add(m.group(1))

    for m in re.finditer(r"\b(\w+_\w+)\b", text):
        name = m.group(1)
        if any(kw in name.lower() for kw in ["tool", "mcp", "search", "query"]):
            refs.add(name)

    return refs
