"""Reviewer factory — make_reviewer() + ReviewerCompiler.

The Reviewer is a CA callable as an arm. It reviews other arms' outputs.
The Bandit calls the Reviewer after any CONSTRUCT.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from compoctopus.agent import CompoctopusAgent
from compoctopus.types import ArmKind, PromptSection, SystemPrompt

from compoctopus.arms.reviewer.prompts import REVIEWER_SYSTEM_PROMPT


@dataclass
class ReviewResult:
    """Result of a Reviewer evaluation."""
    passed: bool
    feedback: str = ""
    invariant_violations: List[str] = None

    def __post_init__(self):
        if self.invariant_violations is None:
            self.invariant_violations = []


def make_reviewer() -> CompoctopusAgent:
    """Create the Reviewer CA.

    SM: REVIEW → DONE
    The Reviewer takes arm output + original task, validates,
    returns pass/fail + feedback.
    """
    from heaven_base.state_machine import KeywordBasedStateMachine, StateConfig

    sm = KeywordBasedStateMachine(
        name="reviewer",
        states={
            "REVIEW": StateConfig(
                goal=(
                    "Review the following arm output:\n\n"
                    "═══ ORIGINAL TASK ═══\n"
                    "{original_task}\n\n"
                    "═══ ARM KIND ═══\n"
                    "{arm_kind}\n\n"
                    "═══ ARM OUTPUT ═══\n"
                    "{arm_output}\n\n"
                    "═══ ATTEMPT ═══\n"
                    "{attempt}\n\n"
                    "═══ PREVIOUS FEEDBACK (if retry) ═══\n"
                    "{feedback}\n\n"
                    "Validate against the geometric alignment invariants.\n"
                    "Output PASS or FAIL with specific feedback.\n"
                    "When done, transition to DONE."
                ),
            ),
            "DONE": StateConfig(
                goal="Review complete. Return the result.",
            ),
        },
        initial_state="REVIEW",
        terminal_states={"DONE"},
        transitions={
            "REVIEW": ["DONE"],
        },
    )

    ariadne_elements = _build_reviewer_ariadne_elements(sm)

    try:
        from sdna.config import HermesConfig, HeavenInputs, HeavenAgentArgs
        hermes = HermesConfig(
            name="reviewer",
            goal=(
                "═══ REVIEW ARM OUTPUT ═══\n\n"
                "{original_task}\n\n"
                "Arm: {arm_kind}\n"
                "Attempt: {attempt}\n\n"
                "Output to review:\n{arm_output}\n\n"
                "Previous feedback:\n{feedback}\n\n"
                "═══ CURRENT STATE: {state} ═══\n\n"
                "{instructions}\n\n"
                "═══ VALID TRANSITIONS: {valid_transitions} ═══\n\n"
                "Output PASS or FAIL, then transition to DONE."
            ),
            backend="heaven",
            model="minimax",
            max_turns=10,
            permission_mode="bypassPermissions",
            heaven_inputs=HeavenInputs(
                agent=HeavenAgentArgs(
                    provider="ANTHROPIC",
                    max_tokens=4000,
                    tools=[],  # Reviewer doesn't need tools — pure evaluation
                ),
            ),
            system_prompt=REVIEWER_SYSTEM_PROMPT,
        )
    except ImportError:
        hermes = None

    return CompoctopusAgent(
        agent_name="reviewer",
        state_machine=sm,
        hermes_config=hermes,
        ariadne_elements=ariadne_elements,
        arm_kind=ArmKind.REVIEWER,
        system_prompt=SystemPrompt(sections=[
            PromptSection(
                tag="IDENTITY",
                content="You are the Reviewer — the quality gate for Compoctopus.",
            ),
        ]),
    )


def _build_reviewer_ariadne_elements(sm) -> Dict[str, List]:
    """Build per-state Ariadne elements for the Reviewer."""
    try:
        from sdna.ariadne import InjectConfig
        return {
            state: [
                InjectConfig(source="literal", inject_as="instructions", value=cfg.goal),
                InjectConfig(source="context", inject_as="arm_output", key="arm_output"),
                InjectConfig(source="context", inject_as="original_task", key="original_task"),
                InjectConfig(source="context", inject_as="arm_kind", key="arm_kind"),
                InjectConfig(source="context", inject_as="attempt", key="attempt"),
                InjectConfig(source="context", inject_as="feedback", key="feedback"),
            ]
            for state, cfg in sm.states.items()
        }
    except ImportError:
        return {
            state: [{"source": "literal", "inject_as": "instructions", "value": cfg.goal}]
            for state, cfg in sm.states.items()
        }


class ReviewerCompiler:
    """Thin wrapper — the Reviewer arm callable by the Bandit."""

    def __init__(self):
        self._reviewer = None
        self.name = "reviewer_compiler"

    def _get_reviewer(self) -> CompoctopusAgent:
        if self._reviewer is None:
            self._reviewer = make_reviewer()
        return self._reviewer

    async def compile(self, ctx: dict) -> ReviewResult:
        """Run the Reviewer CA on the given context.

        ctx should contain:
            arm_output: the output to review
            original_task: what was asked
            arm_kind: which arm produced it
            attempt: retry count
            feedback: previous feedback (if retry)
        """
        reviewer = self._get_reviewer()
        result = await reviewer.execute(ctx)

        # Parse the reviewer's output for PASS/FAIL
        review_text = ""
        if hasattr(result, 'context') and isinstance(result.context, dict):
            review_text = result.context.get("text", "")

        passed = "PASS" in review_text.upper() and "FAIL" not in review_text.upper()

        return ReviewResult(
            passed=passed,
            feedback=review_text if not passed else "",
            invariant_violations=_extract_violations(review_text),
        )


def _extract_violations(text: str) -> List[str]:
    """Extract invariant violations from reviewer output."""
    violations = []
    invariant_names = [
        "Dual Description",
        "Capability Surface",
        "Trust Boundary",
        "Phase Template",  # also matches "Phase ↔ Template"
        "Polymorphic Dispatch",
    ]
    text_lower = text.lower()
    for name in invariant_names:
        if name.lower() in text_lower and "violat" in text_lower:
            violations.append(name)
    return violations
