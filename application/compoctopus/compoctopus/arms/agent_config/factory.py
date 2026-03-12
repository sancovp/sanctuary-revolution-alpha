"""Agent Config Compiler — CA that determines model/provider/permissions.

Calls worker agents to figure out the right HermesConfig for the target agent.

SM: ANALYZE → CONFIGURE → DONE
"""

from __future__ import annotations
from typing import Any, Dict, List
from compoctopus.agent import CompoctopusAgent
from compoctopus.types import ArmKind, PromptSection, SystemPrompt
from compoctopus.arms.agent_config.prompts import (
    AGENT_CONFIG_SYSTEM_PROMPT,
    ANALYZE_GOAL, CONFIGURE_GOAL,
)


def make_agent_config_compiler() -> CompoctopusAgent:
    """Create the Agent Config Compiler arm.

    SM: ANALYZE → CONFIGURE → DONE
    Determines model, provider, permissions, max_turns for the target agent.
    """
    from heaven_base.state_machine import KeywordBasedStateMachine, StateConfig

    sm = KeywordBasedStateMachine(
        name="agent_config_compiler",
        states={
            "ANALYZE": StateConfig(goal=ANALYZE_GOAL),
            "CONFIGURE": StateConfig(goal=CONFIGURE_GOAL),
            "DONE": StateConfig(goal="Config complete. Return the HermesConfig."),
        },
        initial_state="ANALYZE",
        terminal_states={"DONE"},
        transitions={"ANALYZE": ["CONFIGURE"], "CONFIGURE": ["DONE"]},
    )

    ariadne_elements = _build_ariadne(sm)

    try:
        from sdna.config import HermesConfig, HeavenInputs, HeavenAgentArgs
        from heaven_base.tools import BashTool
        hermes = HermesConfig(
            name="agent_config_compiler",
            goal="═══ STATE: {state} ═══\n{instructions}\n═══ TRANSITIONS: {valid_transitions} ═══",
            backend="heaven", model="minimax", max_turns=15,
            permission_mode="bypassPermissions",
            heaven_inputs=HeavenInputs(agent=HeavenAgentArgs(
                provider="ANTHROPIC", max_tokens=4000, tools=[BashTool],
            )),
            system_prompt=AGENT_CONFIG_SYSTEM_PROMPT,
        )
    except ImportError:
        hermes = None

    return CompoctopusAgent(
        agent_name="agent_config_compiler",
        state_machine=sm, hermes_config=hermes, ariadne_elements=ariadne_elements,
        arm_kind=ArmKind.AGENT,
        system_prompt=SystemPrompt(sections=[
            PromptSection(tag="IDENTITY", content="You are the Agent Config Compiler arm."),
        ]),
    )


def _build_ariadne(sm):
    try:
        from sdna.ariadne import InjectConfig
        return {s: [InjectConfig(source="literal", inject_as="instructions", value=c.goal)]
                for s, c in sm.states.items()}
    except ImportError:
        return {}
