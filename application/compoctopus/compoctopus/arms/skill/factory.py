"""Skill Compiler — CA that selects and injects behavioral skills.

SM: ANALYZE → SELECT → DONE
"""

from __future__ import annotations
from typing import Any, Dict, List
from compoctopus.agent import CompoctopusAgent
from compoctopus.types import ArmKind, PromptSection, SystemPrompt
from compoctopus.arms.skill.prompts import (
    SKILL_COMPILER_SYSTEM_PROMPT,
    ANALYZE_GOAL, SELECT_GOAL,
)


def make_skill_compiler() -> CompoctopusAgent:
    """Create the Skill Compiler arm.

    SM: ANALYZE → SELECT → DONE
    Queries registry for skills matching the task's behavioral needs.
    """
    from heaven_base.state_machine import KeywordBasedStateMachine, StateConfig

    sm = KeywordBasedStateMachine(
        name="skill_compiler",
        states={
            "ANALYZE": StateConfig(goal=ANALYZE_GOAL),
            "SELECT": StateConfig(goal=SELECT_GOAL),
            "DONE": StateConfig(goal="Skill selection complete. Return the skill bundle."),
        },
        initial_state="ANALYZE",
        terminal_states={"DONE"},
        transitions={"ANALYZE": ["SELECT"], "SELECT": ["DONE"]},
    )

    ariadne_elements = _build_ariadne(sm)

    try:
        from sdna.config import HermesConfig, HeavenInputs, HeavenAgentArgs
        from heaven_base.tools import BashTool
        hermes = HermesConfig(
            name="skill_compiler",
            goal="═══ STATE: {state} ═══\n{instructions}\n═══ TRANSITIONS: {valid_transitions} ═══",
            backend="heaven", model="minimax", max_turns=15,
            permission_mode="bypassPermissions",
            heaven_inputs=HeavenInputs(agent=HeavenAgentArgs(
                provider="ANTHROPIC", max_tokens=4000, tools=[BashTool],
            )),
            system_prompt=SKILL_COMPILER_SYSTEM_PROMPT,
        )
    except ImportError:
        hermes = None

    return CompoctopusAgent(
        agent_name="skill_compiler",
        state_machine=sm, hermes_config=hermes, ariadne_elements=ariadne_elements,
        arm_kind=ArmKind.SKILL,
        system_prompt=SystemPrompt(sections=[
            PromptSection(tag="IDENTITY", content="You are the Skill Compiler arm."),
        ]),
    )


def _build_ariadne(sm):
    try:
        from sdna.ariadne import InjectConfig
        return {s: [InjectConfig(source="literal", inject_as="instructions", value=c.goal)]
                for s, c in sm.states.items()}
    except ImportError:
        return {}
