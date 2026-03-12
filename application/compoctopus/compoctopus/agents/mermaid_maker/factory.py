"""MermaidMaker factory — make_mermaid_maker() + helpers.

Invariant: every CA package has factory.py with the make_<name>() function.
"""

from __future__ import annotations

from typing import Dict, List

from compoctopus.agent import CompoctopusAgent
from compoctopus.types import PromptSection, SystemPrompt

from compoctopus.agents.mermaid_maker.prompts import MERMAID_MAKER_SYSTEM_PROMPT


def make_mermaid_maker() -> CompoctopusAgent:
    """Create the MermaidMaker CA.

    Single-state agent. Annealing happens inside the SDNAC via BashTool:
    LLM writes mermaid → validates with CLI → fixes → repeats until VALID.
    """
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
                    "Then validate with: python3 -m compoctopus.mermaid.cli "
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

    ariadne_elements = _build_mermaid_maker_ariadne_elements(sm)

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


def _build_mermaid_maker_ariadne_elements(sm) -> Dict[str, List]:
    """Build per-state Ariadne elements for the MermaidMaker."""
    try:
        from sdna.ariadne import InjectConfig
        return {
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
        return {
            state: [{"source": "literal", "inject_as": "instructions", "value": cfg.goal}]
            for state, cfg in sm.states.items()
        }
