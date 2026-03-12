"""Generic state machine wrapper.

Extracted from the EvolutionFlow pattern in evolution_system.py.
Every compiler arm is wrapped in a deterministic state machine:
    - Python decides the phase
    - Phase determines the prompt template
    - Prompt template constrains the LLM's output space
    - Output is classified into {success, block, incomplete}
    - Classification determines next phase

The LLM never decides "what to do next" — the state machine does.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    List,
    Optional,
    TypeVar,
)

from compoctopus.types import CompilationPhase


# =============================================================================
# Phase transitions
# =============================================================================

@dataclass(frozen=True)
class PhaseTransition:
    """A single transition in the state machine.

    From evolution_system.py:
        development → (success) → complete
        development → (block)   → debug
        debug       → (success) → complete
        debug       → (block)   → debug (loop)
    """
    from_phase: CompilationPhase
    to_phase: CompilationPhase
    condition: str = "default"  # Label for the condition ("success", "block", etc.)


@dataclass
class PhaseConfig:
    """Configuration for one phase.

    Each phase maps to a different prompt template / hermes config.
    From evolution_system:
        development → tool_evolution_flow_iog_config_v2
        debug       → debug_evolution_flow_config (continuation: true)
    """
    phase: CompilationPhase
    template_name: str = ""            # Which prompt template to use
    continuation: bool = False         # Resume same conversation?
    max_retries: int = 3               # Max attempts in this phase before BLOCKED
    timeout_seconds: float = 300.0     # Timeout for this phase


# =============================================================================
# Output classification
# =============================================================================

S = TypeVar("S")  # State type


@dataclass
class PhaseOutput:
    """The result of running one phase.

    The state machine classifies this to determine the next phase.
    """
    raw_output: Any = None
    status: str = ""           # "success", "block", "incomplete", "error"
    message: str = ""          # Human-readable summary
    data: Dict[str, Any] = field(default_factory=dict)
    continuation_id: Optional[str] = None  # For resuming conversation


# =============================================================================
# State machine
# =============================================================================

class StateMachine(Generic[S]):
    """Generic deterministic state machine wrapper.

    Wraps non-deterministic LLM execution in a deterministic shell.
    Python decides phase → phase determines template → template constrains LLM.

    Usage:
        sm = StateMachine(
            initial_phase=CompilationPhase.ANALYZING,
            transitions=[
                PhaseTransition(ANALYZING, COMPILING, "analyzed"),
                PhaseTransition(COMPILING, VALIDATING, "compiled"),
                PhaseTransition(VALIDATING, COMPLETE, "valid"),
                PhaseTransition(VALIDATING, DEBUG, "invalid"),
                PhaseTransition(DEBUG, COMPILING, "fixed"),
            ],
            phase_configs={...},
        )
        while not sm.is_terminal:
            output = execute_phase(sm.current_phase, sm.current_config)
            status = classify_output(output)
            sm.transition(status)
    """

    def __init__(
        self,
        initial_phase: CompilationPhase,
        transitions: List[PhaseTransition],
        phase_configs: Optional[Dict[CompilationPhase, PhaseConfig]] = None,
        terminal_phases: Optional[List[CompilationPhase]] = None,
    ):
        self.current_phase = initial_phase
        self._transitions = transitions
        self._phase_configs = phase_configs or {}
        self._terminal_phases = terminal_phases or [
            CompilationPhase.COMPLETE,
            CompilationPhase.BLOCKED,
        ]
        self._history: List[PhaseTransition] = []
        self._retry_counts: Dict[CompilationPhase, int] = {}

    @property
    def is_terminal(self) -> bool:
        """Has the SM reached a terminal state?"""
        return self.current_phase in self._terminal_phases

    @property
    def current_config(self) -> Optional[PhaseConfig]:
        """Get the config for the current phase."""
        return self._phase_configs.get(self.current_phase)

    @property
    def history(self) -> List[PhaseTransition]:
        """Full transition history."""
        return list(self._history)

    def transition(self, condition: str) -> CompilationPhase:
        """Attempt a transition based on the condition.

        Args:
            condition: The classified output status ("success", "block", etc.)

        Returns:
            The new phase after transition.

        Raises:
            ValueError: If no valid transition exists for this phase+condition.
        """
        # Find matching transition
        for t in self._transitions:
            if t.from_phase == self.current_phase and t.condition == condition:
                self._history.append(t)
                self.current_phase = t.to_phase

                # Track retries
                count = self._retry_counts.get(self.current_phase, 0)
                self._retry_counts[self.current_phase] = count + 1

                # Check max retries
                config = self._phase_configs.get(self.current_phase)
                if config and count >= config.max_retries:
                    self.current_phase = CompilationPhase.BLOCKED

                return self.current_phase

        raise ValueError(
            f"No transition from {self.current_phase.value} "
            f"with condition '{condition}'. "
            f"Valid conditions: {self._valid_conditions()}"
        )

    def _valid_conditions(self) -> List[str]:
        """List valid conditions for current phase."""
        return [
            t.condition for t in self._transitions
            if t.from_phase == self.current_phase
        ]

    def reset(self, phase: Optional[CompilationPhase] = None):
        """Reset state machine to initial or specified phase."""
        self.current_phase = phase or self._transitions[0].from_phase
        self._history.clear()
        self._retry_counts.clear()

    def __str__(self) -> str:
        return (
            f"StateMachine(phase={self.current_phase.value}, "
            f"steps={len(self._history)}, "
            f"terminal={self.is_terminal})"
        )


# =============================================================================
# Factory for the standard compiler arm state machine
# =============================================================================

def make_compiler_sm() -> StateMachine:
    """Create the standard state machine for a compiler arm.

    Pattern:
        ANALYZING → COMPILING → VALIDATING → COMPLETE
                        ↑              │
                        └── DEBUG ←────┘ (violations → fix → revalidate)
    """
    return StateMachine(
        initial_phase=CompilationPhase.ANALYZING,
        transitions=[
            PhaseTransition(CompilationPhase.ANALYZING, CompilationPhase.COMPILING, "analyzed"),
            PhaseTransition(CompilationPhase.COMPILING, CompilationPhase.VALIDATING, "compiled"),
            PhaseTransition(CompilationPhase.VALIDATING, CompilationPhase.COMPLETE, "valid"),
            PhaseTransition(CompilationPhase.VALIDATING, CompilationPhase.DEBUG, "invalid"),
            PhaseTransition(CompilationPhase.DEBUG, CompilationPhase.COMPILING, "fixed"),
            PhaseTransition(CompilationPhase.DEBUG, CompilationPhase.BLOCKED, "unfixable"),
        ],
        phase_configs={
            CompilationPhase.ANALYZING: PhaseConfig(
                phase=CompilationPhase.ANALYZING,
                template_name="analyze",
                max_retries=1,
            ),
            CompilationPhase.COMPILING: PhaseConfig(
                phase=CompilationPhase.COMPILING,
                template_name="compile",
                max_retries=3,
            ),
            CompilationPhase.DEBUG: PhaseConfig(
                phase=CompilationPhase.DEBUG,
                template_name="debug",
                continuation=True,  # Resume same conversation
                max_retries=5,
            ),
        },
    )
