"""Mermaid sequence diagram parser — text → MermaidSpec."""

from __future__ import annotations

import re
from typing import List, Tuple

from compoctopus.types import MermaidAlt, MermaidBranch, MermaidMessage, MermaidSpec


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
        r"^\s*(\S+?)\s*(-->>\s*|--\>|->>|-\>)\s*(\S+?)\s*:\s*(.+?)\s*$"
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
