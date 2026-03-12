"""Mermaid diagram utilities — parsing, generation, and validation.

The mermaid diagram IS the program for the LLM. This module handles:
- Parsing existing mermaid text into MermaidSpec (graph-first)
- Generating mermaid specs from pipeline context
- Validating specs against tool surfaces
- Extracting tool references from prose text

MermaidSpec is GRAPH-FIRST: you build it by adding participants,
messages, and branches. The text rendering is a computed property.

From evolution_system_analysis:
    "The sequence diagrams aren't documentation — they're executable
     specifications that the LLM follows as a state machine."
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

from compoctopus.types import MermaidAlt, MermaidBranch, MermaidMessage, MermaidSpec


# =============================================================================
# Parser: text → MermaidSpec
# =============================================================================

class MermaidParser:
    """Parse mermaid sequence diagram text into a graph-first MermaidSpec.

    Supports:
    - participant declarations (with optional aliases)
    - ->> / -> / --> message arrows
    - alt/else/end blocks
    - loop/end blocks
    """

    # Regex patterns
    _RE_PARTICIPANT = re.compile(
        r"^\s*participant\s+(.+?)(?:\s+as\s+(.+))?\s*$"
    )
    _RE_MESSAGE = re.compile(
        r"^\s*(\S+?)\s*(-->>|--\>|->>|-\>)\s*(\S+?)\s*:\s*(.+?)\s*$"
    )
    _RE_ALT = re.compile(r"^\s*alt\s+(.+?)\s*$")
    _RE_ELSE = re.compile(r"^\s*else\s+(.+?)\s*$")
    _RE_LOOP = re.compile(r"^\s*loop\s+(.+?)\s*$")
    _RE_END = re.compile(r"^\s*end\s*$")

    def parse(self, diagram_text: str) -> MermaidSpec:
        """Parse mermaid sequence diagram text into a MermaidSpec.

        Args:
            diagram_text: Raw mermaid text (with or without ```mermaid fences)

        Returns:
            Graph-first MermaidSpec with participants, messages, branches.
        """
        # Strip fences
        text = diagram_text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines)

        # Skip "sequenceDiagram" header
        lines = text.strip().split("\n")
        lines = [l for l in lines if l.strip() and l.strip() != "sequenceDiagram"]

        spec = MermaidSpec()
        self._parse_lines(lines, spec)
        return spec

    def _parse_lines(self, lines: List[str], spec: MermaidSpec) -> None:
        """Parse lines into a MermaidSpec, handling nested blocks."""
        i = 0
        while i < len(lines):
            line = lines[i]

            # Participant
            m = self._RE_PARTICIPANT.match(line)
            if m:
                name = m.group(1).strip()
                alias = m.group(2).strip() if m.group(2) else None
                spec.add_participant(name, alias)
                i += 1
                continue

            # Alt block
            m = self._RE_ALT.match(line)
            if m:
                i, alt = self._parse_alt_block(lines, i)
                spec._messages.append(alt)
                continue

            # Loop block
            m = self._RE_LOOP.match(line)
            if m:
                label = m.group(1)
                i += 1
                loop_msgs = []
                while i < len(lines) and not self._RE_END.match(lines[i]):
                    msg_m = self._RE_MESSAGE.match(lines[i])
                    if msg_m:
                        loop_msgs.append((msg_m.group(1), msg_m.group(3), msg_m.group(4)))
                    i += 1
                i += 1  # skip 'end'
                spec.add_loop(label, loop_msgs)
                continue

            # Message
            m = self._RE_MESSAGE.match(line)
            if m:
                spec.add_message(m.group(1), m.group(3), m.group(4), m.group(2))
                i += 1
                continue

            # Unknown line — skip
            i += 1

    def _parse_alt_block(
        self, lines: List[str], start: int
    ) -> Tuple[int, MermaidAlt]:
        """Parse an alt/else/end block starting at `start`."""
        branches = []
        i = start

        # First 'alt' line
        m = self._RE_ALT.match(lines[i])
        current_condition = m.group(1) if m else "default"
        current_messages = []
        i += 1

        while i < len(lines):
            if self._RE_END.match(lines[i]):
                branches.append(MermaidBranch(
                    condition=current_condition,
                    messages=current_messages,
                ))
                i += 1
                break

            m = self._RE_ELSE.match(lines[i])
            if m:
                branches.append(MermaidBranch(
                    condition=current_condition,
                    messages=current_messages,
                ))
                current_condition = m.group(1)
                current_messages = []
                i += 1
                continue

            msg_m = self._RE_MESSAGE.match(lines[i])
            if msg_m:
                current_messages.append(MermaidMessage(
                    sender=msg_m.group(1),
                    receiver=msg_m.group(3),
                    label=msg_m.group(4),
                    arrow=msg_m.group(2),
                ))
            i += 1

        return i, MermaidAlt(branches=branches)


# =============================================================================
# Generator: context → MermaidSpec
# =============================================================================

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
        """Generate a standard agent operation diagram.

        Creates a sequence diagram showing:
        User → Agent → Tools (from tool_names) → Agent → User
        with optional error handling alt/else block.

        Only references the tools actually provided.
        """
        spec = MermaidSpec()
        spec.add_participant("User")
        spec.add_participant(agent_name, agent_name)

        # Add tool participants
        for tool in tool_names:
            spec.add_participant(tool)

        # Add workflow steps as messages
        for step in workflow_steps:
            spec.add_message(agent_name, agent_name, step)

        # If there are tools, show the agent calling them
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
        """Generate a pipeline/router diagram showing arm sequence.

        Used for the router's stable operational diagram.
        """
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


# =============================================================================
# Validator: MermaidSpec × ToolManifest → violations
# =============================================================================

class MermaidValidator:
    """Validate mermaid specs against tool surfaces.

    This is one half of the Capability Surface invariant check.
    The other half is checking that the system prompt CAPABILITY
    section matches the tool manifest.
    """

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
        # Phantom tools: in diagram but not equipped
        phantoms = referenced - available_tools
        for t in sorted(phantoms):
            violations.append(
                f"PHANTOM TOOL in mermaid diagram: '{t}' is referenced as a participant "
                f"but is not in the equipped tool set. The LLM will try to call '{t}' "
                f"and get an error. Currently equipped tools: {sorted(available_tools)}. "
                f"Fix: either equip '{t}' via MCPCompiler, or remove it from the diagram."
            )

        # Orphaned tools: equipped but never in diagram
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
        """Validate structural integrity of the spec.

        Checks:
        - At least one participant
        - At least one message
        - All message senders/receivers are participants
        """
        violations = []
        if not spec.participants:
            violations.append(
                "Mermaid diagram has no participants. A valid diagram needs at least "
                "the agent as a participant. Without participants, there's nothing "
                "to send or receive messages. "
                "Fix: call spec.add_participant('Agent', agent_name) before adding messages."
            )
        if not spec._messages:
            violations.append(
                "Mermaid diagram has no messages. A valid diagram needs at least "
                "one message (arrow) between participants. Without messages, the "
                "diagram describes nothing. "
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
                        f"Every sender must be a declared participant. "
                        f"Current participants: {sorted(participant_set)}. "
                        f"Fix: either add '{msg.sender}' as a participant, or correct "
                        f"the sender name in the message."
                    )
                if msg.receiver not in participant_set:
                    violations.append(
                        f"Message receiver '{msg.receiver}' is not in the participant list. "
                        f"Every receiver must be a declared participant. "
                        f"Current participants: {sorted(participant_set)}. "
                        f"Fix: either add '{msg.receiver}' as a participant, or correct "
                        f"the receiver name in the message."
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

        Returns empty list if diagram is compliant.
        Sorted by severity: ERROR first, then WARNING, then INFO.
        """
        violations: List[EvolutionSystemViolation] = []

        # Collect all messages (flat + inside alt/else branches)
        all_msgs = _flatten_messages(spec)
        participants = set(spec.participants)

        # --- V1: Participants ---
        if "User" not in participants:
            violations.append(EvolutionSystemViolation(
                rule="V1", severity="ERROR",
                message="Missing 'User' participant. Every evolution diagram needs User.",
                fix_hint="Add 'participant User' to the diagram.",
            ))

        agent_participants = participants - {"User", "Tools"}
        if not agent_participants:
            violations.append(EvolutionSystemViolation(
                rule="V1", severity="ERROR",
                message="No agent participant found. Need at least one non-User, non-Tools participant.",
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
                message="No agent-to-user message found. Cannot check task list.",
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
                    fix_hint='Agent\'s first message to User should be: '
                             '```update_task_list=["task1", "task2", ...]```',
                ))

        # --- V3: Task Completion ---
        # Extract declared tasks from update_task_list
        declared_tasks: List[str] = []
        for msg in all_msgs:
            m = re.search(r'update_task_list\s*=\s*\[([^\]]+)\]', msg.label)
            if m:
                # Parse the list items
                for item in re.findall(r'"([^"]+)"', m.group(1)):
                    declared_tasks.append(item)

        # Extract completed tasks
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
                        message=f"Task '{task}' is declared in update_task_list but never completed.",
                        fix_hint=f'Add: Agent->>User: ```complete_task={task}```',
                    ))

        # Check complete_task messages go to User
        for msg in all_msgs:
            if "complete_task" in msg.label and msg.receiver != "User":
                violations.append(EvolutionSystemViolation(
                    rule="V3", severity="ERROR",
                    message=f"complete_task message sent to '{msg.receiver}' instead of 'User'.",
                    fix_hint="complete_task messages must go from Agent to User.",
                ))

        # --- V4: GOAL ACCOMPLISHED ---
        goal_msgs = [msg for msg in all_msgs if "GOAL ACCOMPLISHED" in msg.label]
        if not goal_msgs:
            violations.append(EvolutionSystemViolation(
                rule="V4", severity="ERROR",
                message="No GOAL ACCOMPLISHED message found.",
                fix_hint='Add as final message: Agent->>User: ```GOAL ACCOMPLISHED```',
            ))
        elif len(goal_msgs) > 1:
            violations.append(EvolutionSystemViolation(
                rule="V4", severity="ERROR",
                message=f"GOAL ACCOMPLISHED appears {len(goal_msgs)} times. Must appear exactly once.",
                fix_hint="Remove duplicate GOAL ACCOMPLISHED messages.",
            ))

        # --- V5: Iteration Boundaries ---
        next_task_msgs = [msg for msg in all_msgs
                         if msg.sender == "User" and "Next task" in msg.label]
        if declared_tasks and not next_task_msgs:
            violations.append(EvolutionSystemViolation(
                rule="V5", severity="WARNING",
                message="No 'User->>Agent: Next task' iteration boundaries found.",
                fix_hint="Add 'User->>Agent: Next task' between task sections.",
            ))

        # --- V6: Tool Call Format ---
        # Real format: "ToolName: desc" or "ToolName with target X" or "ToolName(args)"
        # Just check that the label starts with a recognizable tool/action name
        tool_call_re = re.compile(
            r'^[A-Z]\w*'        # starts with capitalized word (ToolName pattern)
            r'|^\w+Tool'        # or contains "Tool" 
            r'|^\w+Util'        # or contains "Util"
        )
        for msg in all_msgs:
            if msg.receiver == "Tools" or (msg.receiver not in {"User"} and msg.receiver in participants):
                if msg.sender != "User" and msg.sender != "Tools":
                    # Agent-to-Tools message — should start with a tool/action name
                    if not tool_call_re.match(msg.label.strip()):
                        violations.append(EvolutionSystemViolation(
                            rule="V6", severity="WARNING",
                            message=f"Agent→Tools message doesn't start with a tool name: '{msg.label[:60]}'",
                            fix_hint="Start with tool name: 'ToolName: description' or 'ToolName with target X'",
                        ))

        # --- V7: Alt/Else Blocks ---
        alt_blocks = [item for item in spec._messages if isinstance(item, MermaidAlt)]
        if not alt_blocks:
            violations.append(EvolutionSystemViolation(
                rule="V7", severity="WARNING",
                message="No alt/else blocks found. Error handling is expected.",
                fix_hint="Add alt/else blocks for error paths.",
            ))
        for alt in alt_blocks:
            if len(alt.branches) < 2:
                violations.append(EvolutionSystemViolation(
                    rule="V7", severity="WARNING",
                    message=f"Alt block has only {len(alt.branches)} branch(es). Need at least 2 (alt + else).",
                    fix_hint="Add an else branch for the error/alternative case.",
                ))

        # --- V8: Response Shapes ---
        tools_to_agent = [msg for msg in all_msgs
                         if msg.sender == "Tools" or
                         (msg.sender not in {"User"} and msg.receiver in agent_participants)]
        for msg in tools_to_agent:
            if msg.sender != "User" and msg.receiver in agent_participants:
                if not msg.label.strip():
                    violations.append(EvolutionSystemViolation(
                        rule="V8", severity="INFO",
                        message=f"Empty response shape from '{msg.sender}' to '{msg.receiver}'.",
                        fix_hint="Add response shape like: {success}, {error details}, <description>",
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
                message="Error branches exist but no WriteBlockReportTool reference found.",
                fix_hint="Consider adding WriteBlockReportTool for unresolvable errors.",
            ))

        # Sort by severity: ERROR > WARNING > INFO
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
    rule: str          # V1-V9
    severity: str      # ERROR, WARNING, INFO
    message: str       # Human-readable description
    fix_hint: str      # What to do about it

    def __str__(self) -> str:
        return f"[{self.severity}] {self.rule}: {self.message}\n  Fix: {self.fix_hint}"


# =============================================================================
# Text extraction utilities
# =============================================================================

def extract_tool_references_from_text(text: str) -> Set[str]:
    """Extract tool names referenced in prose prompt text.

    Looks for patterns like:
    - "Use ToolMakerTool to..."
    - "call EvolveToolTool(...)"
    - "- tool_name" in list items
    - "mcp:name" references

    Used by alignment validators to check system prompt CAPABILITY
    sections against tool manifests.
    """
    refs = set()

    # Pattern 1: "Use XxxTool" or "call XxxTool"
    for m in re.finditer(r"\b(?:use|call|invoke)\s+(\w+Tool)\b", text, re.IGNORECASE):
        refs.add(m.group(1))

    # Pattern 2: "mcp:name" or "MCP: name"
    for m in re.finditer(r"\bmcp[:\s]+(\w+)", text, re.IGNORECASE):
        refs.add(m.group(1))

    # Pattern 3: "- tool_name" in capability lists
    for m in re.finditer(r"^[\s\-*]+(\w+)\s+(?:MCP|tool|mcp)", text, re.MULTILINE):
        refs.add(m.group(1))

    # Pattern 4: explicit "(tool_references: [...])" or similar
    for m in re.finditer(r"\b(\w+_\w+)\b", text):
        name = m.group(1)
        if any(kw in name.lower() for kw in ["tool", "mcp", "search", "query"]):
            refs.add(name)

    return refs
