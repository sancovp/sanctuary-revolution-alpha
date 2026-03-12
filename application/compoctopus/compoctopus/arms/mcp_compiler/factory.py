"""MCP Compiler — CA that selects and configures required tool surfaces.

Calls worker agents to determine which MCPs the target agent needs.

SM: ANALYZE → SELECT → DONE
"""

from __future__ import annotations
from typing import Any, Dict, List
from compoctopus.agent import CompoctopusAgent
from compoctopus.types import ArmKind, PromptSection, SystemPrompt
from compoctopus.arms.mcp_compiler.prompts import (
    MCP_COMPILER_SYSTEM_PROMPT,
    ANALYZE_GOAL, SELECT_GOAL,
)


def make_mcp_compiler() -> CompoctopusAgent:
    """Create the MCP Compiler arm.

    SM: ANALYZE → SELECT → DONE
    Queries the registry to find MCPs matching the task's tool needs.
    """
    from heaven_base.state_machine import KeywordBasedStateMachine, StateConfig

    sm = KeywordBasedStateMachine(
        name="mcp_compiler",
        states={
            "ANALYZE": StateConfig(goal=ANALYZE_GOAL),
            "SELECT": StateConfig(goal=SELECT_GOAL),
            "DONE": StateConfig(goal="MCP selection complete. Return the tool manifest."),
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
            name="mcp_compiler",
            goal="═══ STATE: {state} ═══\n{instructions}\n═══ TRANSITIONS: {valid_transitions} ═══",
            backend="heaven", model="minimax", max_turns=15,
            permission_mode="bypassPermissions",
            heaven_inputs=HeavenInputs(agent=HeavenAgentArgs(
                provider="ANTHROPIC", max_tokens=4000, tools=[BashTool],
            )),
            system_prompt=MCP_COMPILER_SYSTEM_PROMPT,
        )
    except ImportError:
        hermes = None

    return CompoctopusAgent(
        agent_name="mcp_compiler",
        state_machine=sm, hermes_config=hermes, ariadne_elements=ariadne_elements,
        arm_kind=ArmKind.MCP,
        system_prompt=SystemPrompt(sections=[
            PromptSection(tag="IDENTITY", content="You are the MCP Compiler arm."),
        ]),
    )


def _build_ariadne(sm):
    try:
        from sdna.ariadne import InjectConfig
        return {s: [InjectConfig(source="literal", inject_as="instructions", value=c.goal)]
                for s, c in sm.states.items()}
    except ImportError:
        return {}
