"""
Reality Validation State Machine

The lifecycle of a concept as it moves toward consensus reality.

States:
1. SOUP - raw, LLM generated, no validation
2. VIEWED - user has seen it, aware it exists
3. ONT_LOCAL - user approved + UARL valid (TheirReality)
4. PENDING_CONSENSUS - published, awaiting others
5. ONT_CONSENSUS - others agree (SharedReality)
6. REJECTED - disagreement, back to SOUP with new rules

The feedback loop: disagreement generates new validation rules
for that Cat type, which become part of UARL for future attempts.
"""

from enum import Enum, auto
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from pydantic import BaseModel


class ValidationState(str, Enum):
    """States in the reality validation lifecycle."""
    
    SOUP = "soup"                      # Raw, LLM generated
    VIEWED = "viewed"                  # User has seen it
    ONT_LOCAL = "ont_local"            # User approved + UARL valid
    PENDING_CONSENSUS = "pending"      # Published, awaiting others
    ONT_CONSENSUS = "ont_consensus"    # Others agree (SharedReality)
    REJECTED = "rejected"              # Disagreement, with feedback rules


class RejectionReason(BaseModel):
    """Why a concept was rejected from consensus."""
    
    reason: str
    rejector_id: str
    timestamp: datetime = datetime.now()
    
    # What validation should mean for this Cat type
    suggested_rules: List[str] = []
    
    # The Cat type this applies to
    applies_to_cat: Optional[str] = None


class ValidationTransition(BaseModel):
    """A transition in the validation state machine."""
    
    from_state: ValidationState
    to_state: ValidationState
    timestamp: datetime = datetime.now()
    actor: str  # who initiated this transition
    reason: Optional[str] = None
    metadata: Dict[str, Any] = {}


class ConceptLifecycle(BaseModel):
    """Tracks a concept's journey through reality validation."""
    
    concept_name: str
    current_state: ValidationState = ValidationState.SOUP
    
    # UARL validation status
    uarl_valid: bool = False
    ses_layer: int = 0
    
    # The three ENOUGH conditions
    constructible_enough: bool = False  # Can instantiate beyond strings
    inferable_enough: bool = False      # Membership hooks exist
    closed_enough: bool = False         # Morphisms map cleanly
    
    # Transition history
    transitions: List[ValidationTransition] = []
    
    # Rejection feedback (accumulates rules over time)
    rejection_history: List[RejectionReason] = []
    
    # Derived validation rules from rejections
    derived_rules: List[str] = []
    
    # Owner (for ONT_LOCAL)
    owner_id: Optional[str] = None
    
    # Timestamps
    created_at: datetime = datetime.now()
    last_viewed_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    consensus_at: Optional[datetime] = None


class ValidationStateMachine:
    """State machine for concept reality validation."""
    
    # Valid transitions
    VALID_TRANSITIONS = {
        ValidationState.SOUP: [ValidationState.VIEWED],
        ValidationState.VIEWED: [ValidationState.ONT_LOCAL, ValidationState.SOUP],
        ValidationState.ONT_LOCAL: [ValidationState.PENDING_CONSENSUS, ValidationState.SOUP],
        ValidationState.PENDING_CONSENSUS: [ValidationState.ONT_CONSENSUS, ValidationState.REJECTED],
        ValidationState.ONT_CONSENSUS: [ValidationState.REJECTED],  # Can always be challenged
        ValidationState.REJECTED: [ValidationState.SOUP],  # Goes back with new rules
    }
    
    def __init__(self, concept: ConceptLifecycle):
        self.concept = concept
        self._transition_hooks: Dict[str, List[Callable]] = {}
    
    def can_transition(self, to_state: ValidationState) -> tuple:
        """Check if transition is valid and return (can_transition, reason)."""
        current = self.concept.current_state
        
        # Check if transition is allowed
        if to_state not in self.VALID_TRANSITIONS.get(current, []):
            return (False, f"Cannot transition from {current} to {to_state}")
        
        # Additional checks based on target state
        if to_state == ValidationState.ONT_LOCAL:
            # Must meet UARL requirements
            if not self.concept.uarl_valid:
                return (False, "UARL validation required for ONT_LOCAL")
            if self.concept.ses_layer < 1:
                return (False, "Must have at least SES layer 1 for ONT_LOCAL")
        
        if to_state == ValidationState.ONT_CONSENSUS:
            # Must have been validated by others (placeholder for voting logic)
            pass
        
        return (True, None)
    
    def transition(
        self, 
        to_state: ValidationState, 
        actor: str,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ValidationTransition:
        """Execute a state transition."""
        can, err = self.can_transition(to_state)
        if not can:
            raise ValueError(err)
        
        # Create transition record
        transition = ValidationTransition(
            from_state=self.concept.current_state,
            to_state=to_state,
            actor=actor,
            reason=reason,
            metadata=metadata or {}
        )
        
        # Update state
        old_state = self.concept.current_state
        self.concept.current_state = to_state
        self.concept.transitions.append(transition)
        
        # Update timestamps
        if to_state == ValidationState.VIEWED:
            self.concept.last_viewed_at = datetime.now()
        elif to_state == ValidationState.ONT_LOCAL:
            self.concept.approved_at = datetime.now()
            self.concept.owner_id = actor
        elif to_state == ValidationState.PENDING_CONSENSUS:
            self.concept.published_at = datetime.now()
        elif to_state == ValidationState.ONT_CONSENSUS:
            self.concept.consensus_at = datetime.now()
        
        # Execute hooks
        hook_key = f"{old_state}_{to_state}"
        for hook in self._transition_hooks.get(hook_key, []):
            hook(self.concept, transition)
        
        return transition
    
    def view(self, actor: str) -> ValidationTransition:
        """Mark concept as viewed by user."""
        return self.transition(ValidationState.VIEWED, actor, "User viewed concept")
    
    def approve(self, actor: str) -> ValidationTransition:
        """User approves concept for their local ontology."""
        return self.transition(
            ValidationState.ONT_LOCAL, 
            actor, 
            "User approved + UARL valid"
        )
    
    def publish(self, actor: str) -> ValidationTransition:
        """Publish concept for consensus validation."""
        return self.transition(
            ValidationState.PENDING_CONSENSUS,
            actor,
            "Published for consensus"
        )
    
    def achieve_consensus(self, actor: str, voters: List[str]) -> ValidationTransition:
        """Concept achieves consensus."""
        return self.transition(
            ValidationState.ONT_CONSENSUS,
            actor,
            f"Consensus achieved with {len(voters)} voters",
            {"voters": voters}
        )
    
    def reject(
        self, 
        actor: str, 
        reason: str,
        suggested_rules: Optional[List[str]] = None,
        applies_to_cat: Optional[str] = None
    ) -> ValidationTransition:
        """Reject concept with feedback."""
        # Record rejection with rules
        rejection = RejectionReason(
            reason=reason,
            rejector_id=actor,
            suggested_rules=suggested_rules or [],
            applies_to_cat=applies_to_cat
        )
        self.concept.rejection_history.append(rejection)
        
        # Accumulate derived rules
        if suggested_rules:
            self.concept.derived_rules.extend(suggested_rules)
        
        return self.transition(
            ValidationState.REJECTED,
            actor,
            reason,
            {"suggested_rules": suggested_rules, "applies_to_cat": applies_to_cat}
        )
    
    def return_to_soup(self, actor: str) -> ValidationTransition:
        """Return rejected concept to SOUP with accumulated rules."""
        return self.transition(
            ValidationState.SOUP,
            actor,
            f"Returned to SOUP with {len(self.concept.derived_rules)} derived rules"
        )
    
    def on_transition(self, from_state: ValidationState, to_state: ValidationState, hook: Callable):
        """Register a hook for a specific transition."""
        key = f"{from_state}_{to_state}"
        if key not in self._transition_hooks:
            self._transition_hooks[key] = []
        self._transition_hooks[key].append(hook)
    
    def update_uarl_status(
        self,
        uarl_valid: bool,
        ses_layer: int,
        constructible: bool = False,
        inferable: bool = False,
        closed: bool = False
    ):
        """Update UARL validation status."""
        self.concept.uarl_valid = uarl_valid
        self.concept.ses_layer = ses_layer
        self.concept.constructible_enough = constructible
        self.concept.inferable_enough = inferable
        self.concept.closed_enough = closed
    
    def get_status_summary(self) -> Dict[str, Any]:
        """Get a summary of the concept's validation status."""
        return {
            "name": self.concept.concept_name,
            "state": self.concept.current_state.value,
            "uarl_valid": self.concept.uarl_valid,
            "ses_layer": self.concept.ses_layer,
            "enough": {
                "constructible": self.concept.constructible_enough,
                "inferable": self.concept.inferable_enough,
                "closed": self.concept.closed_enough,
            },
            "transitions_count": len(self.concept.transitions),
            "rejections_count": len(self.concept.rejection_history),
            "derived_rules": self.concept.derived_rules,
            "owner": self.concept.owner_id,
        }


# Global registry of concept lifecycles
_concept_lifecycles: Dict[str, ConceptLifecycle] = {}


def get_or_create_lifecycle(concept_name: str) -> ValidationStateMachine:
    """Get or create a lifecycle for a concept."""
    if concept_name not in _concept_lifecycles:
        _concept_lifecycles[concept_name] = ConceptLifecycle(concept_name=concept_name)
    return ValidationStateMachine(_concept_lifecycles[concept_name])


def get_lifecycle(concept_name: str) -> Optional[ValidationStateMachine]:
    """Get lifecycle for a concept if it exists."""
    if concept_name in _concept_lifecycles:
        return ValidationStateMachine(_concept_lifecycles[concept_name])
    return None


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    # Create a concept lifecycle
    lifecycle = get_or_create_lifecycle("Dog")
    
    print("=== Dog's Journey Through Reality ===\n")
    
    # Initial state
    print(f"Initial: {lifecycle.get_status_summary()}")
    
    # LLM generates, user views
    lifecycle.view("user_123")
    print(f"\nAfter VIEW: {lifecycle.concept.current_state}")
    
    # Update UARL status (simulating validation)
    lifecycle.update_uarl_status(
        uarl_valid=True,
        ses_layer=2,
        constructible=True,
        inferable=True,
        closed=True
    )
    
    # User approves
    lifecycle.approve("user_123")
    print(f"After APPROVE: {lifecycle.concept.current_state}")
    
    # Publish for consensus
    lifecycle.publish("user_123")
    print(f"After PUBLISH: {lifecycle.concept.current_state}")
    
    # Someone rejects with feedback
    lifecycle.reject(
        actor="user_456",
        reason="Dog definition too vague for simulation",
        suggested_rules=[
            "Dog must have action_propensities defined",
            "Dog must have fetch_response behavioral hook"
        ],
        applies_to_cat="SimulatableAgent"
    )
    print(f"\nAfter REJECT: {lifecycle.concept.current_state}")
    print(f"Derived rules: {lifecycle.concept.derived_rules}")
    
    # Return to SOUP with new rules
    lifecycle.return_to_soup("system")
    print(f"\nAfter RETURN_TO_SOUP: {lifecycle.concept.current_state}")
    
    # Final summary
    print(f"\n=== Final Status ===")
    print(lifecycle.get_status_summary())
