"""Odyssey core — thin facade. Onion arch middle layer.

OdysseyOrgan extends cave Organ ABC.
Single public method: process(concept_ref).
All logic delegated to utils.
"""

from dataclasses import dataclass, field
from typing import Any, Dict

from .models import OdysseyResult
from . import utils


@dataclass
class OdysseyOrgan:
    """Organ that auto-verifies GNOSYS BUILD output via adversarial SDNAC agents.

    Installed into WakingDreamer via AnatomyMixin.add_organ().
    Single public method: process(concept_ref).
    """
    name: str = "odyssey"
    enabled: bool = True
    _processing: bool = field(default=False, repr=False)
    _processed_count: int = field(default=0, repr=False)

    def start(self) -> Dict[str, Any]:
        self.enabled = True
        return {"status": "running", "organ": self.name}

    def stop(self) -> Dict[str, Any]:
        self.enabled = False
        return {"status": "stopped", "organ": self.name}

    def status(self) -> Dict[str, Any]:
        return {
            "organ": self.name,
            "enabled": self.enabled,
            "processing": self._processing,
            "processed_count": self._processed_count,
        }

    def process(self, concept_ref: str) -> OdysseyResult:
        """THE single public method. WakingDreamer calls ONLY this."""
        if not self.enabled:
            return OdysseyResult(
                success=False,
                event_type="disabled",
                concept_ref=concept_ref,
                error="OdysseyOrgan is disabled",
            )

        self._processing = True
        try:
            result = utils.dispatch(concept_ref)
            self._processed_count += 1
            return result
        finally:
            self._processing = False
