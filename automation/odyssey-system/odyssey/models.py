"""Odyssey event types and config models."""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class OdysseyEvent:
    """An event routed to OdysseyOrgan from WakingDreamer."""
    concept_ref: str
    concept_type: str = ""  # populated by dispatch from CartON is_a query
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OdysseyResult:
    """Result from any do_x method."""
    success: bool
    event_type: str  # measure_build, measure_narrative, learn_build, learn_narrative
    concept_ref: str
    concepts_created: List[str] = field(default_factory=list)
    decision: Optional[str] = None  # CONTINUE, REDO, ESCALATE (learn only)
    error: Optional[str] = None
