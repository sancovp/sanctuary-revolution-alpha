"""Persona control via file flag.

Pattern: Class method toggles file flag, hook reads flag and injects.
"""
from pathlib import Path

PERSONA_FLAG = Path("/tmp/active_persona")


class PersonaControl:
    """Controls persona activation via file flag."""

    @staticmethod
    def activate(name: str) -> None:
        """Activate persona by writing name to flag file."""
        PERSONA_FLAG.write_text(name)

    @staticmethod
    def deactivate() -> None:
        """Deactivate persona by removing flag file."""
        PERSONA_FLAG.unlink(missing_ok=True)

    @staticmethod
    def get_active() -> str | None:
        """Get currently active persona name, or None if none active."""
        if PERSONA_FLAG.exists():
            name = PERSONA_FLAG.read_text().strip()
            return name if name else None
        return None

    @staticmethod
    def is_active() -> bool:
        """Check if any persona is active."""
        return PERSONA_FLAG.exists() and PERSONA_FLAG.read_text().strip() != ""
