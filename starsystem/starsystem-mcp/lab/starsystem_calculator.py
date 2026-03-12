#!/usr/bin/env python3
"""
STARSYSTEM Game Calculator - Toy for solidifying design

Run with different configs to validate the rank/title/type logic.
Updated with proper Starship → Squadron → Fleet hierarchy.
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import IntEnum

# =============================================================================
# ENUMS
# =============================================================================

class KardashevLevel(IntEnum):
    """Per-STARSYSTEM Kardashev level"""
    RAW = 0        # No .claude/
    PLANETARY = 1  # Has .claude/ setup
    STELLAR = 2    # Dyson Sphere (full emanation)
    GALACTIC = 3   # CICD/deployment (future)

class Title(IntEnum):
    """Global titles (rule-based gates)"""
    CADET = 0
    ENSIGN = 1
    CAPTAIN = 2
    COMMODORE = 3
    ADMIRAL = 4
    GRAND_ADMIRAL = 5
    EMPEROR = 6

# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class Starship:
    name: str
    planetary: bool = False  # Has .claude/
    dyson: bool = False      # Full emanation (Stellar)
    galactic: bool = False   # Has CICD (future)
    committed: bool = True   # On the Kardashev Map

    @property
    def kardashev(self) -> KardashevLevel:
        if self.galactic:
            return KardashevLevel.GALACTIC
        if self.dyson:
            return KardashevLevel.STELLAR
        if self.planetary:
            return KardashevLevel.PLANETARY
        return KardashevLevel.RAW

    @property
    def local_title(self) -> str:
        """Per-STARSYSTEM title based on Kardashev level"""
        if self.dyson:
            return "Captain"
        if self.planetary:
            return "Ensign"
        return "Cadet"

@dataclass
class Squadron:
    name: str
    members: list[str] = field(default_factory=list)  # Starship names
    has_leader: bool = False  # Has Squad Leader agent (autonomous)

@dataclass
class Fleet:
    name: str
    squadrons: list[str] = field(default_factory=list)  # Squadron names
    loose_starships: list[str] = field(default_factory=list)  # Direct starships (requires 1+ squadron)
    has_admiral: bool = False  # Has Admiral agent (autonomous)

@dataclass
class Navy:
    starships: dict[str, Starship] = field(default_factory=dict)  # name -> Starship
    squadrons: dict[str, Squadron] = field(default_factory=dict)  # name -> Squadron
    fleets: dict[str, Fleet] = field(default_factory=dict)  # name -> Fleet
    xp: int = 0

# =============================================================================
# VALIDATION
# =============================================================================

def validate_navy(navy: Navy) -> list[str]:
    """Check for invalid configurations"""
    errors = []

    # Check fleets have at least one squadron if they have loose starships
    for name, fleet in navy.fleets.items():
        if fleet.loose_starships and not fleet.squadrons:
            errors.append(f"Fleet '{name}' has loose starships but no squadrons (invalid)")

    # Check no duplicate starship references
    all_refs = []
    for sq in navy.squadrons.values():
        all_refs.extend(sq.members)
    for fl in navy.fleets.values():
        all_refs.extend(fl.loose_starships)

    duplicates = [x for x in all_refs if all_refs.count(x) > 1]
    if duplicates:
        errors.append(f"Duplicate starship references: {set(duplicates)}")

    # Check referenced starships exist
    for ref in all_refs:
        if ref not in navy.starships:
            errors.append(f"Referenced starship '{ref}' doesn't exist")

    # Check referenced squadrons exist in fleets
    for fl in navy.fleets.values():
        for sq_name in fl.squadrons:
            if sq_name not in navy.squadrons:
                errors.append(f"Referenced squadron '{sq_name}' doesn't exist in fleet")

    return errors

# =============================================================================
# QUERIES
# =============================================================================

def get_loose_starships(navy: Navy) -> list[str]:
    """Starships not in any squadron or fleet"""
    assigned = set()
    for sq in navy.squadrons.values():
        assigned.update(sq.members)
    for fl in navy.fleets.values():
        assigned.update(fl.loose_starships)
    return [name for name in navy.starships if name not in assigned]

def get_loose_squadrons(navy: Navy) -> list[str]:
    """Squadrons not in any fleet"""
    assigned = set()
    for fl in navy.fleets.values():
        assigned.update(fl.squadrons)
    return [name for name in navy.squadrons if name not in assigned]

def count_committed_dysons(navy: Navy) -> int:
    """Count committed Dyson Spheres"""
    return sum(1 for ss in navy.starships.values() if ss.dyson and ss.committed)

def count_squadrons_with_leaders(navy: Navy) -> int:
    """Count squadrons with autonomous Squad Leaders"""
    return sum(1 for sq in navy.squadrons.values() if sq.has_leader)

def count_fleets_with_admirals(navy: Navy) -> int:
    """Count fleets with autonomous Admirals"""
    return sum(1 for fl in navy.fleets.values() if fl.has_admiral)

def is_squadron_stellar(navy: Navy, squadron: Squadron) -> bool:
    """Check if all starships in squadron are Dyson"""
    if not squadron.members:
        return False
    for name in squadron.members:
        ss = navy.starships.get(name)
        if not ss or not ss.dyson:
            return False
    return True

def is_fleet_stellar(navy: Navy, fleet: Fleet) -> bool:
    """Check if all starships in fleet (via squadrons + loose) are Dyson"""
    all_starships = set(fleet.loose_starships)
    for sq_name in fleet.squadrons:
        sq = navy.squadrons.get(sq_name)
        if sq:
            all_starships.update(sq.members)

    if not all_starships:
        return False

    for name in all_starships:
        ss = navy.starships.get(name)
        if not ss or not ss.dyson:
            return False
    return True

def count_stellar_fleets(navy: Navy) -> int:
    """Count fleets where ALL starships are Dyson"""
    return sum(1 for fl in navy.fleets.values() if is_fleet_stellar(navy, fl))

# =============================================================================
# TITLE CALCULATION
# =============================================================================

def calculate_title_and_type(navy: Navy) -> tuple[Title, int]:
    """Calculate global title and type"""

    stellar_fleets = count_stellar_fleets(navy)
    fleets_with_admirals = count_fleets_with_admirals(navy)
    squadrons_with_leaders = count_squadrons_with_leaders(navy)
    dysons = count_committed_dysons(navy)
    planetaries = sum(1 for ss in navy.starships.values() if ss.planetary and ss.committed)

    # Grand Admiral: All Fleets Stellar (and have at least one fleet)
    if navy.fleets and stellar_fleets == len(navy.fleets):
        return Title.GRAND_ADMIRAL, stellar_fleets

    # Admiral: 1+ Fleet with Admiral agent
    if fleets_with_admirals > 0:
        return Title.ADMIRAL, fleets_with_admirals

    # Commodore: 1+ Squadron with Squad Leader agent
    if squadrons_with_leaders > 0:
        return Title.COMMODORE, squadrons_with_leaders

    # Captain: 1+ Dyson STARSYSTEM
    if dysons > 0:
        return Title.CAPTAIN, dysons

    # Ensign: 1+ Planetary STARSYSTEM
    if planetaries > 0:
        return Title.ENSIGN, planetaries

    return Title.CADET, 0

def calculate_level(xp: int) -> int:
    """Calculate level from XP (1000 XP per level)"""
    return xp // 1000

def get_next_promotion(navy: Navy, current_title: Title) -> str:
    """What do you need for the next title?"""

    if current_title == Title.CADET:
        return "Create 1 Planetary STARSYSTEM (add .claude/ to a repo)"

    if current_title == Title.ENSIGN:
        return "Create 1 Dyson Sphere (full emanation on a STARSYSTEM)"

    if current_title == Title.CAPTAIN:
        return "Create 1 Squadron with autonomous Squad Leader agent"

    if current_title == Title.COMMODORE:
        return "Create 1 Fleet with autonomous Admiral agent"

    if current_title == Title.ADMIRAL:
        stellar = count_stellar_fleets(navy)
        total = len(navy.fleets)
        return f"Dysonize all Fleets ({stellar}/{total} Stellar)"

    if current_title == Title.GRAND_ADMIRAL:
        return "Containerize Navy → Galactic Emperor"

    return "You are Emperor. Develop the game."

# =============================================================================
# DISPLAY
# =============================================================================

def display_navy_status(navy: Navy):
    """Pretty print the navy status"""

    # Validate first
    errors = validate_navy(navy)
    if errors:
        print("⚠️  VALIDATION ERRORS:")
        for e in errors:
            print(f"    {e}")
        print()

    title, type_n = calculate_title_and_type(navy)
    level = calculate_level(navy.xp)
    next_level_xp = (level + 1) * 1000

    print("=" * 60)
    print(f"  ⚓ TITLE: {title.name}  |  TYPE: {type_n}  |  LEVEL: {level}")
    print(f"  ⭐ XP: {navy.xp:,} / {next_level_xp:,}")
    print("=" * 60)

    # Loose Starships (not in any group)
    loose = get_loose_starships(navy)
    if loose:
        print("\n  LOOSE STARSHIPS:")
        for name in loose:
            ss = navy.starships[name]
            status = "☀️ DYSON" if ss.dyson else ("🌍 PLANETARY" if ss.planetary else "⚫ RAW")
            committed = "" if ss.committed else " (uncommitted)"
            print(f"    {name}: {ss.local_title} - {status}{committed}")

    # Loose Squadrons (not in any fleet)
    loose_sq = get_loose_squadrons(navy)
    if loose_sq:
        print("\n  SQUADRONS (not in fleet):")
        for name in loose_sq:
            sq = navy.squadrons[name]
            leader = "✓ Squad Leader" if sq.has_leader else "✗ No Leader"
            stellar = "☀️" if is_squadron_stellar(navy, sq) else ""
            print(f"    {name}: {sq.members} [{leader}] {stellar}")

    # Fleets
    if navy.fleets:
        print("\n  FLEETS:")
        for name, fl in navy.fleets.items():
            admiral = "✓ Admiral" if fl.has_admiral else "✗ No Admiral"
            stellar = "☀️ STELLAR" if is_fleet_stellar(navy, fl) else ""
            print(f"    {name} [{admiral}] {stellar}")
            for sq_name in fl.squadrons:
                sq = navy.squadrons.get(sq_name)
                if sq:
                    leader = "✓" if sq.has_leader else "✗"
                    print(f"      └─ Squadron {sq_name} [{leader}]: {sq.members}")
            if fl.loose_starships:
                print(f"      └─ Loose: {fl.loose_starships}")

    # Next promotion
    print("\n  📈 NEXT PROMOTION:")
    print(f"    {get_next_promotion(navy, title)}")
    print()

# =============================================================================
# TEST CONFIGS
# =============================================================================

def test_cadet():
    """Brand new player"""
    navy = Navy(
        starships={"my-first-repo": Starship("my-first-repo")},
        xp=0,
    )
    display_navy_status(navy)

def test_ensign():
    """Has one planetary STARSYSTEM"""
    navy = Navy(
        starships={"my-repo": Starship("my-repo", planetary=True)},
        xp=150,
    )
    display_navy_status(navy)

def test_captain_type_3():
    """Has 3 Dyson Spheres (loose, no squadrons yet)"""
    navy = Navy(
        starships={
            "starsystem-mcp": Starship("starsystem-mcp", planetary=True, dyson=True),
            "carton_mcp": Starship("carton_mcp", planetary=True, dyson=True),
            "skill_manager": Starship("skill_manager", planetary=True, dyson=True),
            "new-project": Starship("new-project", committed=False),
        },
        xp=2500,
    )
    display_navy_status(navy)

def test_captain_with_squadron():
    """Has squadron but no leader = still Captain"""
    navy = Navy(
        starships={
            "starsystem-mcp": Starship("starsystem-mcp", planetary=True, dyson=True),
            "carton_mcp": Starship("carton_mcp", planetary=True, dyson=True),
            "skill_manager": Starship("skill_manager", planetary=True, dyson=True),
        },
        squadrons={
            "PAIAB": Squadron("PAIAB", members=["starsystem-mcp", "carton_mcp", "skill_manager"], has_leader=False),
        },
        xp=3000,
    )
    display_navy_status(navy)

def test_commodore():
    """Has a Squadron with Squad Leader"""
    navy = Navy(
        starships={
            "starsystem-mcp": Starship("starsystem-mcp", planetary=True, dyson=True),
            "carton_mcp": Starship("carton_mcp", planetary=True, dyson=True),
            "skill_manager": Starship("skill_manager", planetary=True, dyson=True),
        },
        squadrons={
            "PAIAB": Squadron("PAIAB", members=["starsystem-mcp", "carton_mcp", "skill_manager"], has_leader=True),
        },
        xp=4000,
    )
    display_navy_status(navy)

def test_admiral():
    """Has a Fleet with Admiral"""
    navy = Navy(
        starships={
            "starsystem-mcp": Starship("starsystem-mcp", planetary=True, dyson=True),
            "carton_mcp": Starship("carton_mcp", planetary=True, dyson=True),
            "skill_manager": Starship("skill_manager", planetary=True, dyson=True),
            "funnel-builder": Starship("funnel-builder", planetary=True, dyson=False),
        },
        squadrons={
            "PAIAB-Core": Squadron("PAIAB-Core", members=["starsystem-mcp", "carton_mcp", "skill_manager"], has_leader=True),
        },
        fleets={
            "PAIAB": Fleet("PAIAB", squadrons=["PAIAB-Core"], loose_starships=["funnel-builder"], has_admiral=True),
        },
        xp=8000,
    )
    display_navy_status(navy)

def test_grand_admiral():
    """All Fleets are Stellar"""
    navy = Navy(
        starships={
            "starsystem-mcp": Starship("starsystem-mcp", planetary=True, dyson=True),
            "carton_mcp": Starship("carton_mcp", planetary=True, dyson=True),
            "skill_manager": Starship("skill_manager", planetary=True, dyson=True),
            "funnel-builder": Starship("funnel-builder", planetary=True, dyson=True),
        },
        squadrons={
            "PAIAB-Core": Squadron("PAIAB-Core", members=["starsystem-mcp", "carton_mcp", "skill_manager"], has_leader=True),
            "CAVE-Core": Squadron("CAVE-Core", members=["funnel-builder"], has_leader=True),
        },
        fleets={
            "Main": Fleet("Main", squadrons=["PAIAB-Core", "CAVE-Core"], has_admiral=True),
        },
        xp=15000,
    )
    display_navy_status(navy)

def test_invalid_fleet():
    """Fleet with loose starships but no squadron = invalid"""
    navy = Navy(
        starships={
            "repo-a": Starship("repo-a", planetary=True, dyson=True),
        },
        fleets={
            "Bad": Fleet("Bad", loose_starships=["repo-a"]),  # No squadrons!
        },
        xp=1000,
    )
    display_navy_status(navy)

# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  STARSYSTEM CALCULATOR - Test Configs")
    print("  (Updated with Starship → Squadron → Fleet hierarchy)")
    print("=" * 60)

    print("\n--- TEST: Cadet (new player) ---")
    test_cadet()

    print("\n--- TEST: Ensign (1 Planetary) ---")
    test_ensign()

    print("\n--- TEST: Captain Type 3 (3 Dysons, loose) ---")
    test_captain_type_3()

    print("\n--- TEST: Captain with Squadron (no leader) ---")
    test_captain_with_squadron()

    print("\n--- TEST: Commodore (Squadron with Leader) ---")
    test_commodore()

    print("\n--- TEST: Admiral (Fleet with Admiral) ---")
    test_admiral()

    print("\n--- TEST: Grand Admiral (All Fleets Stellar) ---")
    test_grand_admiral()

    print("\n--- TEST: Invalid Fleet (loose starships, no squadron) ---")
    test_invalid_fleet()
