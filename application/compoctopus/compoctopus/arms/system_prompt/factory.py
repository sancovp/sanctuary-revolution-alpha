"""System Prompt Compiler — CA that calls worker agents to write each section.

Arm that produces a complete XML-tagged system prompt. Calls worker CAs
to generate each section (IDENTITY, WORKFLOW, CAPABILITY, CONSTRAINTS).

SM: IDENTITY → WORKFLOW → CAPABILITY → CONSTRAINTS → DONE
Each state calls a worker agent to write that section.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from compoctopus.agent import CompoctopusAgent
from compoctopus.types import ArmKind, PromptSection, SystemPrompt
from compoctopus.arms.system_prompt.prompts import (
    SYSTEM_PROMPT_COMPILER_SYSTEM_PROMPT,
    IDENTITY_STATE_GOAL,
    WORKFLOW_STATE_GOAL,
    CAPABILITY_STATE_GOAL,
    CONSTRAINTS_STATE_GOAL,
)


def make_system_prompt_compiler() -> CompoctopusAgent:
    """Create the System Prompt Compiler arm.

    SM: IDENTITY → WORKFLOW → CAPABILITY → CONSTRAINTS → DONE

    Each state calls a worker CA to generate that section of the
    target agent's system prompt. The WORKFLOW state calls MermaidMaker
    to generate the operational mermaid for the EVOLUTION_WORKFLOW section.
    """
    from heaven_base.state_machine import KeywordBasedStateMachine, StateConfig

    sm = KeywordBasedStateMachine(
        name="system_prompt_compiler",
        states={
            "IDENTITY": StateConfig(goal=IDENTITY_STATE_GOAL),
            "WORKFLOW": StateConfig(goal=WORKFLOW_STATE_GOAL),
            "CAPABILITY": StateConfig(goal=CAPABILITY_STATE_GOAL),
            "CONSTRAINTS": StateConfig(goal=CONSTRAINTS_STATE_GOAL),
            "DONE": StateConfig(goal="All sections written. Return the assembled system prompt."),
        },
        initial_state="IDENTITY",
        terminal_states={"DONE"},
        transitions={
            "IDENTITY": ["WORKFLOW"],
            "WORKFLOW": ["CAPABILITY"],
            "CAPABILITY": ["CONSTRAINTS"],
            "CONSTRAINTS": ["DONE"],
        },
    )

    ariadne_elements = _build_ariadne_elements(sm)

    try:
        from sdna.config import HermesConfig, HeavenInputs, HeavenAgentArgs
        from heaven_base.tools import BashTool

        hermes = HermesConfig(
            name="system_prompt_compiler",
            goal=(
                "═══ COMPILING SYSTEM PROMPT ═══\n\n"
                "Task: {original_task}\n\n"
                "═══ STATE: {state} ═══\n\n"
                "{instructions}\n\n"
                "═══ CONTEXT SO FAR ═══\n"
                "{compiled_sections}\n\n"
                "═══ VALID TRANSITIONS: {valid_transitions} ═══"
            ),
            backend="heaven",
            model="minimax",
            max_turns=30,
            permission_mode="bypassPermissions",
            heaven_inputs=HeavenInputs(
                agent=HeavenAgentArgs(
                    provider="ANTHROPIC",
                    max_tokens=8000,
                    tools=[BashTool],
                ),
            ),
            system_prompt=SYSTEM_PROMPT_COMPILER_SYSTEM_PROMPT,
        )
    except ImportError:
        hermes = None

    return CompoctopusAgent(
        agent_name="system_prompt_compiler",
        state_machine=sm,
        hermes_config=hermes,
        ariadne_elements=ariadne_elements,
        arm_kind=ArmKind.SYSTEM_PROMPT,
        system_prompt=SystemPrompt(sections=[
            PromptSection(
                tag="IDENTITY",
                content="You are the System Prompt Compiler arm of Compoctopus.",
            ),
        ]),
    )


def _build_ariadne_elements(sm) -> Dict[str, List]:
    """Build per-state Ariadne elements."""
    try:
        from sdna.ariadne import InjectConfig
        return {
            state: [
                InjectConfig(source="literal", inject_as="instructions", value=cfg.goal),
                InjectConfig(source="context", inject_as="original_task", key="original_task"),
                InjectConfig(source="context", inject_as="compiled_sections", key="compiled_sections"),
            ]
            for state, cfg in sm.states.items()
        }
    except ImportError:
        return {}
