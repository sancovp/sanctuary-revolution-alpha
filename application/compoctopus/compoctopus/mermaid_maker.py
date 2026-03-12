"""MermaidMaker CA — generates evolution-system-style mermaid sequence diagrams.

One file per CA. Invariant pattern:
    1. System prompt constant
    2. Factory function: make_<agent_name>() -> CompoctopusAgent
    3. Helper functions (if any)

Input (from context):
    agent_name: str — name of the agent to generate mermaid for
    tool_list: str — comma-separated tool names the agent has
    workflow_description: str — what the agent does step by step

Output (into context):
    mermaid_path: str — path to the validated mermaid file
"""

from __future__ import annotations

import os
from typing import Optional

from compoctopus.types import PromptSection, SystemPrompt


# =============================================================================
# Spec file reader
# =============================================================================

_SPECS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "specs")


def _read_spec(filename: str) -> str:
    """Read a spec file, return placeholder if not found."""
    path = os.path.join(_SPECS_DIR, filename)
    try:
        with open(path) as f:
            return f.read()
    except FileNotFoundError:
        return f"(spec file not found: {filename})"


# =============================================================================
# System prompt
# =============================================================================

MERMAID_MAKER_SYSTEM_PROMPT = f"""\
You are the MermaidMaker — you generate evolution-system-style mermaid
sequence diagrams that LLM agents follow as executable programs.

<RULES>
{_read_spec("mermaid_rules.md")}
</RULES>

<EXAMPLE_TOOL_EVOLUTION>
The following is a REAL mermaid from evolution_system.py for tool evolution.
Study its structure — your output must follow this exact pattern.

{_read_spec("example_tool_mermaid.md")}
</EXAMPLE_TOOL_EVOLUTION>

<EXAMPLE_AGENT_EVOLUTION>
Another REAL mermaid for agent evolution:

{_read_spec("example_agent_mermaid.md")}
</EXAMPLE_AGENT_EVOLUTION>

<WORKFLOW>
1. Read the agent name, tool list, and workflow description from the goal
2. Write a mermaid sequenceDiagram following the 12 rules above
3. Save it to a file: /tmp/<agent_name>_mermaid.md
4. Validate: python3 -m compoctopus.validate_mermaid /tmp/<agent_name>_mermaid.md
5. If violations → fix the file → revalidate
6. Loop until you see "VALID: <path>"
7. Report the path
</WORKFLOW>

<CRITICAL>
- The mermaid you write IS the program the agent will follow
- Every task in update_task_list MUST have a matching complete_task
- Always end with GOAL ACCOMPLISHED
- Tool calls must start with the actual tool name, not vague descriptions
- Include alt/else for error handling
- Use "User->>Agent: Next task" between task sections
</CRITICAL>
"""


# =============================================================================
# Factory
# =============================================================================

def make_mermaid_maker():
    """Create the MermaidMaker CA.

    Single-state agent. Annealing happens inside the SDNAC via BashTool:
    LLM writes mermaid → validates with CLI → fixes → repeats until VALID.
    """
    from compoctopus.octopus_coder import CompoctopusAgent
    from heaven_base.state_machine import KeywordBasedStateMachine, StateConfig

    sm = KeywordBasedStateMachine(
        name="mermaid_maker",
        states={
            "GENERATE": StateConfig(
                goal=(
                    "Generate a mermaid sequenceDiagram for the following agent:\n\n"
                    "═══ AGENT NAME ═══\n"
                    "{agent_name}\n\n"
                    "═══ TOOLS AVAILABLE ═══\n"
                    "{tool_list}\n\n"
                    "═══ WORKFLOW DESCRIPTION ═══\n"
                    "{workflow_description}\n\n"
                    "Write the mermaid to /tmp/{agent_name}_mermaid.md\n"
                    "Then validate with: python3 -m compoctopus.validate_mermaid "
                    "/tmp/{agent_name}_mermaid.md\n"
                    "Fix any violations and revalidate until you see VALID.\n"
                    "When VALID, output DONE."
                ),
            ),
            "DONE": StateConfig(
                goal="Return. The mermaid is validated.",
            ),
        },
        initial_state="GENERATE",
        terminal_states={"DONE"},
        transitions={
            "GENERATE": ["DONE"],
        },
    )

    # Ariadne elements for state injection
    try:
        from sdna.ariadne import InjectConfig
        ariadne_elements = {
            state: [
                InjectConfig(
                    source="literal",
                    inject_as="instructions",
                    value=cfg.goal,
                ),
            ]
            for state, cfg in sm.states.items()
        }
    except ImportError:
        ariadne_elements = {
            state: [{"source": "literal", "inject_as": "instructions", "value": cfg.goal}]
            for state, cfg in sm.states.items()
        }

    # HermesConfig — BashTool only
    try:
        from sdna.config import HermesConfig, HeavenInputs, HeavenAgentArgs
        from heaven_base.tools import BashTool
        hermes = HermesConfig(
            name="mermaid_maker",
            goal=(
                "═══ GENERATE MERMAID ═══\n\n"
                "Agent: {agent_name}\n"
                "Tools: {tool_list}\n"
                "Workflow: {workflow_description}\n\n"
                "═══ CURRENT STATE: {state} ═══\n\n"
                "{instructions}\n\n"
                "═══ VALID TRANSITIONS: {valid_transitions} ═══\n\n"
                "When done, output the keyword: DONE"
            ),
            backend="heaven",
            model="minimax",
            max_turns=15,
            permission_mode="bypassPermissions",
            heaven_inputs=HeavenInputs(
                agent=HeavenAgentArgs(
                    provider="ANTHROPIC",
                    max_tokens=8000,
                    tools=[BashTool],
                ),
            ),
            system_prompt=MERMAID_MAKER_SYSTEM_PROMPT,
        )
    except ImportError:
        hermes = None

    return CompoctopusAgent(
        agent_name="mermaid_maker",
        state_machine=sm,
        hermes_config=hermes,
        ariadne_elements=ariadne_elements,
        system_prompt=SystemPrompt(sections=[
            PromptSection(
                tag="IDENTITY",
                content="You are the MermaidMaker — you write executable mermaid sequence diagrams.",
            ),
        ]),
    )
