"""Chain Compiler — CA that decomposes goals into SDNAC node sequences.

SM: ANALYZE → DECOMPOSE → DONE
"""

from __future__ import annotations
from typing import Any, Dict, List
from compoctopus.agent import CompoctopusAgent
from compoctopus.types import ArmKind, PromptSection, SystemPrompt
from compoctopus.arms.chain_compiler.prompts import (
    CHAIN_COMPILER_SYSTEM_PROMPT,
    ANALYZE_GOAL, DECOMPOSE_GOAL,
)


def make_chain_compiler() -> CompoctopusAgent:
    """Create the Chain Compiler arm.

    SM: ANALYZE → DECOMPOSE → DONE
    Decomposes complex goals into ordered sequences of SDNAC nodes.
    """
    from heaven_base.state_machine import KeywordBasedStateMachine, StateConfig

    sm = KeywordBasedStateMachine(
        name="chain_compiler",
        states={
            "ANALYZE": StateConfig(goal=ANALYZE_GOAL),
            "DECOMPOSE": StateConfig(goal=DECOMPOSE_GOAL),
            "DONE": StateConfig(goal="Chain plan complete. Return the node sequence."),
        },
        initial_state="ANALYZE",
        terminal_states={"DONE"},
        transitions={"ANALYZE": ["DECOMPOSE"], "DECOMPOSE": ["DONE"]},
    )

    ariadne_elements = _build_ariadne(sm)

    try:
        from sdna.config import HermesConfig, HeavenInputs, HeavenAgentArgs
        from heaven_base.tools import BashTool
        hermes = HermesConfig(
            name="chain_compiler",
            goal="═══ STATE: {state} ═══\n{instructions}\n═══ TRANSITIONS: {valid_transitions} ═══",
            backend="heaven", model="minimax", max_turns=15,
            permission_mode="bypassPermissions",
            heaven_inputs=HeavenInputs(agent=HeavenAgentArgs(
                provider="ANTHROPIC", max_tokens=8000, tools=[BashTool],
            )),
            system_prompt=CHAIN_COMPILER_SYSTEM_PROMPT,
        )
    except ImportError:
        hermes = None

    return CompoctopusAgent(
        agent_name="chain_compiler",
        state_machine=sm, hermes_config=hermes, ariadne_elements=ariadne_elements,
        arm_kind=ArmKind.CHAIN,
        system_prompt=SystemPrompt(sections=[
            PromptSection(tag="IDENTITY", content="You are the Chain Compiler arm."),
        ]),
    )


def _build_ariadne(sm):
    try:
        from sdna.ariadne import InjectConfig
        return {s: [InjectConfig(source="literal", inject_as="instructions", value=c.goal)]
                for s, c in sm.states.items()}
    except ImportError:
        return {}
