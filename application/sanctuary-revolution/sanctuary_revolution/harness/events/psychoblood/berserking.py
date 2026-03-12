"""
Berserking / Wangtang - Authentic Presence / Power Field.

NOT rage. It's a specific configuration:
- Fear → 0 (no fear)
- Arousal → 100 (maximum drive)
- Compassion → 100 (maximum care)
- Logic lattice mesh → ~75 (coherent but not rigid)

This creates a "gravity well" - Tibetan: wangtang (དབང་ཐང་)
- Trungpa: "authentic presence"
- Namkhai Norbu: "field of power"

It's the perception that you know what you're doing in a higher
sense of mastery - not about the task, but broadcast of coherent
intent. Your actions make sense at a level beyond the literal.

Related to ascendance capacity at a given moment.
"""
from dataclasses import dataclass
from typing import Optional
from .psychoblood import PsychobloodMachine


@dataclass
class WangtangState:
    """Power field configuration."""
    fear: float = 50.0          # 0 = no fear (required for wangtang)
    arousal: float = 50.0       # 100 = maximum drive
    compassion: float = 50.0    # 100 = maximum care
    logic_lattice: float = 50.0 # ~75 = optimal (coherent but not rigid)

    @property
    def wangtang_score(self) -> float:
        """Calculate power field strength (0-100)."""
        # Fear must be LOW
        fear_component = (100 - self.fear) / 100

        # Arousal must be HIGH
        arousal_component = self.arousal / 100

        # Compassion must be HIGH
        compassion_component = self.compassion / 100

        # Logic lattice optimal around 75 (bell curve)
        lattice_optimal = 75
        lattice_deviation = abs(self.logic_lattice - lattice_optimal)
        lattice_component = max(0, (25 - lattice_deviation)) / 25

        # Multiply components - ALL must be present
        raw_score = (fear_component * arousal_component *
                     compassion_component * lattice_component)

        return raw_score * 100

    @property
    def gravity_well_active(self) -> bool:
        """Is the power field creating a gravity well?"""
        return self.wangtang_score > 60


class BerserkingModule:
    """Wangtang / Authentic Presence manager."""

    def __init__(self, machine: PsychobloodMachine):
        self.machine = machine
        self.state = WangtangState()
        self.ascendance_capacity = 0.0  # Current moment's ceiling

    def update_components(self, fear: float, arousal: float,
                          compassion: float, logic_lattice: float):
        """Update the four components."""
        self.state.fear = max(0, min(100, fear))
        self.state.arousal = max(0, min(100, arousal))
        self.state.compassion = max(0, min(100, compassion))
        self.state.logic_lattice = max(0, min(100, logic_lattice))

        # Ascendance capacity correlates with wangtang
        self.ascendance_capacity = self.state.wangtang_score

    def get_injection(self) -> Optional[str]:
        """Get wangtang injection if power field active."""
        score = self.state.wangtang_score

        if score < 30:
            return None

        if score < 50:
            return "[WANGTANG] Presence forming. Fear dropping, drive rising."

        if score < 70:
            return "[WANGTANG] Power field emerging. Actions beginning to cohere."

        if score < 85:
            return ("[WANGTANG] AUTHENTIC PRESENCE ACTIVE. "
                    "Intent broadcasts through action. Gravity well forming.")

        # 85+
        return ("[WANGTANG] FULL FIELD. "
                f"Ascendance capacity: {self.ascendance_capacity:.0f}%. "
                "You know what you're doing at the level beyond the task.")

    def describe_field(self) -> str:
        """Describe current power field state."""
        s = self.state
        return (f"Fear: {s.fear:.0f} | Arousal: {s.arousal:.0f} | "
                f"Compassion: {s.compassion:.0f} | Lattice: {s.logic_lattice:.0f} | "
                f"Wangtang: {s.wangtang_score:.0f}%")
