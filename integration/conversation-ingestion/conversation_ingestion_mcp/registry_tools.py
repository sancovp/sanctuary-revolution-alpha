"""
Registry tools for conversation ingestion.

Tools: add_canonical_framework, list_canonical_frameworks,
       remove_canonical_framework, add_strata
"""

from typing import Optional

from . import utils
from .models import CanonicalEntry, StrataEntry, StrataSlots


def add_canonical_framework(
    strata: str,
    slot_type: str,
    framework_name: str,
    framework_state: str
) -> str:
    """
    Add a canonical framework to the registry.

    Args:
        strata: paiab | sanctum | cave
        slot_type: reference | collection | workflow | library | operating_context
        framework_name: Name of the canonical framework
        framework_state: aspirational | actual
    """
    registry = utils.load_registry()

    # Validate strata
    if strata not in registry.strata:
        valid_strata = list(registry.strata.keys())
        return (
            f"BLOCKED: Invalid strata '{strata}'.\n"
            f"Valid strata: {valid_strata}\n"
            f"→ Use add_strata('{strata}', 'description') to add it first."
        )

    # Validate slot_type
    valid_slots = ["reference", "collection", "workflow", "library", "operating_context"]
    if slot_type not in valid_slots:
        return f"BLOCKED: Invalid slot_type '{slot_type}'.\nValid: {valid_slots}"

    # Validate framework_state
    if framework_state not in ["aspirational", "actual"]:
        return f"BLOCKED: Invalid framework_state '{framework_state}'.\nValid: aspirational | actual"

    # Check if exists
    strata_entry = registry.strata[strata]
    slot_entries = getattr(strata_entry.slots, slot_type)

    if framework_name in slot_entries:
        existing = slot_entries[framework_name]
        return (
            f"BLOCKED: Framework '{framework_name}' already exists in {strata}/{slot_type}.\n"
            f"Current state: {existing.framework_state}\n"
            f"→ Use remove_canonical_framework() first to replace."
        )

    # Add
    slot_entries[framework_name] = CanonicalEntry(framework_state=framework_state)
    utils.save_registry(registry)

    return (
        f"✓ Added canonical framework: {framework_name}\n"
        f"  Strata: {strata}\n"
        f"  Type: {slot_type}\n"
        f"  State: {framework_state}"
    )


def list_canonical_frameworks(
    strata: Optional[str] = None,
    slot_type: Optional[str] = None
) -> str:
    """
    List canonical frameworks from registry.

    Args:
        strata: Optional filter by strata
        slot_type: Optional filter by slot type
    """
    registry = utils.load_registry()

    # Validate filters
    if strata and strata not in registry.strata:
        return f"Invalid strata '{strata}'. Valid: {list(registry.strata.keys())}"

    valid_slots = ["reference", "collection", "workflow", "library", "operating_context"]
    if slot_type and slot_type not in valid_slots:
        return f"Invalid slot_type '{slot_type}'. Valid: {valid_slots}"

    output = ["=== Canonical Frameworks Registry ===", ""]

    strata_to_check = [strata] if strata else list(registry.strata.keys())
    total_count = 0

    for s in strata_to_check:
        strata_entry = registry.strata[s]
        strata_frameworks = []

        slots_to_check = [slot_type] if slot_type else valid_slots

        for slot in slots_to_check:
            slot_entries = getattr(strata_entry.slots, slot)
            for fw_name, fw_entry in slot_entries.items():
                fw_state = fw_entry.framework_state
                strata_frameworks.append(f"  [{slot}] {fw_name} ({fw_state})")
                total_count += 1

        if strata_frameworks:
            output.append(f"{strata_entry.name} ({s}):")
            output.extend(strata_frameworks)
            output.append("")

    if total_count == 0:
        output.append("No canonical frameworks found.")
    else:
        output.append(f"Total: {total_count} framework(s)")

    return "\n".join(output)


def remove_canonical_framework(
    strata: str,
    slot_type: str,
    framework_name: str
) -> str:
    """
    Remove a canonical framework from the registry.

    Args:
        strata: paiab | sanctum | cave
        slot_type: reference | collection | workflow | library | operating_context
        framework_name: Name of the framework to remove
    """
    registry = utils.load_registry()

    # Validate
    if strata not in registry.strata:
        return f"Invalid strata '{strata}'. Valid: {list(registry.strata.keys())}"

    valid_slots = ["reference", "collection", "workflow", "library", "operating_context"]
    if slot_type not in valid_slots:
        return f"Invalid slot_type '{slot_type}'. Valid: {valid_slots}"

    # Check exists
    strata_entry = registry.strata[strata]
    slot_entries = getattr(strata_entry.slots, slot_type)

    if framework_name not in slot_entries:
        return (
            f"BLOCKED: Framework '{framework_name}' not found in {strata}/{slot_type}.\n"
            f"→ Use list_canonical_frameworks('{strata}', '{slot_type}') to see what exists."
        )

    # Remove
    del slot_entries[framework_name]
    utils.save_registry(registry)

    return f"✓ Removed canonical framework: {framework_name} from {strata}/{slot_type}"


def add_strata(name: str, description: str) -> str:
    """
    Add a new strata to the registry.

    Args:
        name: Strata key (lowercase, e.g., 'paiab')
        description: Description of what this strata covers
    """
    registry = utils.load_registry()

    if name in registry.strata:
        return (
            f"BLOCKED: Strata '{name}' already exists.\n"
            f"Description: {registry.strata[name].description}"
        )

    registry.strata[name] = StrataEntry(
        name=name.upper(),
        description=description,
        slots=StrataSlots()
    )
    utils.save_registry(registry)

    return f"✓ Added strata: {name} ({description})"
