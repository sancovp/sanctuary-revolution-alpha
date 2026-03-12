"""Input Prompt Compiler — CA that writes the goal/mermaid for agent.run().

Calls MermaidMaker to generate the operational mermaid, then assembles
the final input prompt (goal string + embedded mermaid).

SM: ANALYZE → MERMAID → ASSEMBLE → DONE
"""

from __future__ import annotations
from typing import Any, Dict, List
from compoctopus.agent import CompoctopusAgent
from compoctopus.types import ArmKind, PromptSection, SystemPrompt
from compoctopus.arms.input_prompt.prompts import (
    INPUT_PROMPT_SYSTEM_PROMPT,
    ANALYZE_GOAL, MERMAID_GOAL, ASSEMBLE_GOAL,
)


def make_input_prompt_compiler() -> CompoctopusAgent:
    """Create the Input Prompt Compiler arm.

    SM: ANALYZE → MERMAID → ASSEMBLE → DONE
    MERMAID state calls MermaidMaker CA to generate the operational mermaid.
    """
    from heaven_base.state_machine import KeywordBasedStateMachine, StateConfig

    sm = KeywordBasedStateMachine(
        name="input_prompt_compiler",
        states={
            "ANALYZE": StateConfig(goal=ANALYZE_GOAL),
            "MERMAID": StateConfig(goal=MERMAID_GOAL),
            "ASSEMBLE": StateConfig(goal=ASSEMBLE_GOAL),
            "DONE": StateConfig(goal="Input prompt assembled. Return the result."),
        },
        initial_state="ANALYZE",
        terminal_states={"DONE"},
        transitions={
            "ANALYZE": ["MERMAID"],
            "MERMAID": ["ASSEMBLE"],
            "ASSEMBLE": ["DONE"],
        },
    )

    ariadne_elements = _build_ariadne(sm)

    try:
        from sdna.config import HermesConfig, HeavenInputs, HeavenAgentArgs
        from heaven_base.tools import BashTool
        hermes = HermesConfig(
            name="input_prompt_compiler",
            goal="═══ STATE: {state} ═══\n{instructions}\n═══ TRANSITIONS: {valid_transitions} ═══",
            backend="heaven", model="minimax", max_turns=20,
            permission_mode="bypassPermissions",
            heaven_inputs=HeavenInputs(agent=HeavenAgentArgs(
                provider="ANTHROPIC", max_tokens=8000, tools=[BashTool],
            )),
            system_prompt=INPUT_PROMPT_SYSTEM_PROMPT,
        )
    except ImportError:
        hermes = None

    return CompoctopusAgent(
        agent_name="input_prompt_compiler",
        state_machine=sm, hermes_config=hermes, ariadne_elements=ariadne_elements,
        arm_kind=ArmKind.INPUT_PROMPT,
        system_prompt=SystemPrompt(sections=[
            PromptSection(tag="IDENTITY", content="You are the Input Prompt Compiler arm."),
        ]),
    )


def _build_ariadne(sm):
    try:
        from sdna.ariadne import InjectConfig
        return {s: [InjectConfig(source="literal", inject_as="instructions", value=c.goal)]
                for s, c in sm.states.items()}
    except ImportError:
        return {}
