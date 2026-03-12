"""Bandit — Select/Construct decision agent for Compoctopus.

The Bandit implements the Select/Construct decision: given a task, either
reuse a known-good "golden chain" (Select) or build a new pipeline via
the OctoCoder (Construct).
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
import re

from compoctopus.types import CompiledAgent, TaskSpec

# Import KeywordBasedStateMachine from heaven_patch
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'heaven_patch'))
from keyword_state_machine import KeywordBasedStateMachine, StateConfig


@dataclass
class GoldenChain:
    """A cached success configuration that can be reused."""
    name: str
    task_pattern: str
    config: Dict[str, Any]
    success_count: int = 0
    last_used: Optional[str] = None


@dataclass
class BanditOutcome:
    """Recorded execution outcome."""
    task_description: str
    strategy: str
    config_used: Dict[str, Any]
    success: bool
    timestamp: str


class Bandit:
    """The Bandit head of Compoctopus - Select vs Construct decision.
    
    State Machine:
        LOOKUP → SELECT|CONSTRUCT → RECORD → DONE
    
    Attributes:
        golden_chains: Dict[str, GoldenChain] — cached success configs
        outcomes: List[BanditOutcome] — recorded execution history
    """
    
    def __init__(self) -> None:
        """Initialize Bandit with empty golden chains and outcomes."""
        self.golden_chains: Dict[str, GoldenChain] = {}
        self.outcomes: List[BanditOutcome] = []
        self.name = "bandit"
        self.state_machine = self._make_state_machine()
    
    def _make_state_machine(self) -> KeywordBasedStateMachine:
        """Create the KeywordBasedStateMachine for the bandit."""
        states = {
            "LOOKUP": StateConfig(
                goal="Check golden_chains for a matching config",
                tools=[],
                prompt_suffix="Looking up golden chain...",
            ),
            "SELECT": StateConfig(
                goal="Match found — load and return the golden chain",
                tools=[],
                prompt_suffix="Selecting golden chain...",
            ),
            "CONSTRUCT": StateConfig(
                goal="No match — invoke construction pipeline",
                tools=[],
                prompt_suffix="Building new pipeline...",
            ),
            "RECORD": StateConfig(
                goal="Store the outcome (success/fail, config used)",
                tools=[],
                prompt_suffix="Recording outcome...",
            ),
            "DONE": StateConfig(
                goal="Return result",
                tools=[],
                prompt_suffix="Complete.",
            ),
        }
        transitions = {
            "LOOKUP": ["SELECT", "CONSTRUCT"],
            "SELECT": ["RECORD"],
            "CONSTRUCT": ["RECORD"],
            "RECORD": ["DONE"],
        }
        return KeywordBasedStateMachine(
            name="bandit_sm",
            states=states,
            initial_state="LOOKUP",
            terminal_states={"DONE"},
            transitions=transitions,
        )
    
    def lookup(self, task_description: str) -> Optional[GoldenChain]:
        """Search golden_chains for a matching task pattern.
        
        Args:
            task_description: The task to match against patterns.
            
        Returns:
            The best matching GoldenChain or None if no match.
        """
        best_match = None
        for chain in self.golden_chains.values():
            # Match by checking if task_pattern appears in task_description
            try:
                if re.search(chain.task_pattern, task_description):
                    # Prefer chains with higher success_count
                    if best_match is None or chain.success_count > best_match.success_count:
                        best_match = chain
            except re.error:
                # If regex is invalid, treat as literal substring
                if chain.task_pattern in task_description:
                    if best_match is None or chain.success_count > best_match.success_count:
                        best_match = chain
        return best_match
    
    def select(self, chain: GoldenChain) -> Dict[str, Any]:
        """Return the chain's config for execution.
        
        Increments success_count and updates last_used timestamp.
        
        Args:
            chain: The GoldenChain to select.
            
        Returns:
            The config dict from the chain.
        """
        chain.success_count += 1
        chain.last_used = datetime.utcnow().isoformat()
        return chain.config
    
    def construct(self, task_description: str) -> Dict[str, Any]:
        """Return a default construction config for a new task.
        
        The actual pipeline invocation happens externally.
        
        Args:
            task_description: Description of the task to construct for.
            
        Returns:
            A default config dict with task_description.
        """
        return {
            "task_description": task_description,
            "strategy": "construct",
        }
    
    def record(
        self,
        task_description: str,
        strategy: str,
        config: Dict[str, Any],
        success: bool,
    ) -> BanditOutcome:
        """Record the execution outcome.
        
        If success and strategy was "construct", graduate the config
        to a golden chain.
        
        Args:
            task_description: Description of the task.
            strategy: "select" or "construct".
            config: The config that was used.
            success: Whether the execution succeeded.
            
        Returns:
            The BanditOutcome that was recorded.
        """
        timestamp = datetime.utcnow().isoformat()
        outcome = BanditOutcome(
            task_description=task_description,
            strategy=strategy,
            config_used=config,
            success=success,
            timestamp=timestamp,
        )
        self.outcomes.append(outcome)
        # Graduate successful constructs to golden chains
        if success and strategy == "construct":
            self.graduate(task_description, config)
        return outcome
    
    def graduate(self, task_description: str, config: Dict[str, Any]) -> GoldenChain:
        """Create a new GoldenChain from a successful construction.
        
        Derives task_pattern from the task_description keywords.
        
        Args:
            task_description: The task description.
            config: The config that succeeded.
            
        Returns:
            The newly created GoldenChain.
        """
        # Derive task_pattern from task_description keywords
        # Use a simple pattern: replace spaces with .* for flexible matching
        words = task_description.split()
        if len(words) >= 2:
            # Create pattern from first two significant words
            pattern_words = [w for w in words if len(w) > 2][:2]
            task_pattern = ".*".join(pattern_words)
        else:
            task_pattern = words[0] if words else ".*"
        
        # Generate unique name
        base_name = task_description[:20].replace(" ", "_")
        name = f"{base_name}_{len(self.golden_chains)}"
        
        chain = GoldenChain(
            name=name,
            task_pattern=task_pattern,
            config=config,
            success_count=1,
            last_used=datetime.utcnow().isoformat(),
        )
        self.golden_chains[name] = chain
        return chain
    
    def transition(self, new_state: str) -> None:
        """Transition to a new state in the state machine.
        
        Args:
            new_state: The state to transition to.
            
        Raises:
            ValueError: If the transition is invalid.
        """
        current = self.state_machine.current_state
        valid = self.state_machine.valid_transitions
        if new_state not in valid:
            raise ValueError(
                f"Invalid transition: {current} -> {new_state}. "
                f"Valid transitions from {current}: {valid}"
            )
        self.state_machine.current_state = new_state


def make_bandit() -> Bandit:
    """Factory function to create a Bandit agent.
    
    Creates the Bandit with:
    - KeywordBasedStateMachine with the states/transitions
    - StateConfig goals for each state
    - System prompt describing the select/construct decision
    
    Returns:
        A configured Bandit instance.
    """
    return Bandit()
