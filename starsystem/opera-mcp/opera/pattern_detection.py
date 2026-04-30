#!/usr/bin/env python3
"""
OPERA Pattern Detection - Analyzes operadic_ledger to detect workflow patterns

Runs automatically after each Canopy completion to detect repeated sequences.
"""

import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)

# PARALLEL: uses heaven_base.registry — should migrate to CartON/YOUKNOW
try:
    from heaven_base.tools.registry_tool import registry_util_func
except ImportError:
    logger.warning("heaven_base not available - pattern detection will not persist", exc_info=True)
    def registry_util_func(*args, **kwargs):
        return "Registry not available"

# Registry names
OPERADIC_LEDGER_REGISTRY = "operadic_ledger"
CANOPY_PATTERN_REGISTRY = "opera_canopy_patterns"
PATTERN_STATE_REGISTRY = "opera_pattern_state"


def detect_patterns(min_occurrences: int = 2, sequence_length: int = 2) -> Dict[str, Any]:
    """
    Analyze operadic_ledger to detect repeated workflow sequences.

    Primary detection: Analyzes source_type='freestyle' items only
    (Skips opera-sourced to prevent re-detecting patterns from their own execution)

    Args:
        min_occurrences: Minimum times a sequence must appear (default 2)
        sequence_length: Length of sequences to detect (default 2)

    Returns:
        Detection results with patterns found
    """
    try:
        # Get all completed items from ledger (organized by date)
        all_items = _read_operadic_ledger()

        # Filter to freestyle only (primary detection)
        freestyle_items = [
            item for item in all_items
            if item.get("source_type") == "freestyle"
        ]

        logger.info(f"Analyzing {len(freestyle_items)} freestyle items for patterns")

        # Extract sequences
        sequences = _extract_sequences(freestyle_items, sequence_length)

        # Find repeated sequences
        patterns = _find_repeated_sequences(sequences, min_occurrences)

        # Store detected patterns in quarantine
        stored_count = 0
        for pattern in patterns:
            if _store_pattern(pattern):
                stored_count += 1

        return {
            "success": True,
            "analyzed_items": len(freestyle_items),
            "detected_patterns": len(patterns),
            "stored_patterns": stored_count,
            "patterns": patterns
        }

    except Exception as e:
        logger.error(f"Error detecting patterns: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


def _read_operadic_ledger() -> List[Dict[str, Any]]:
    """
    Read all completed items from operadic_ledger (all dates).

    Returns:
        List of completed schedule items sorted by completion time
    """
    items = []

    try:
        # operadic_ledger is organized as operadic_ledger/YYYY-MM-DD/
        # We need to read all date registries

        # For now, read last 30 days (TODO: optimize with last_checked_date tracking)
        from datetime import timedelta

        today = datetime.now()
        for days_ago in range(30):
            date = (today - timedelta(days=days_ago)).strftime('%Y-%m-%d')
            registry_name = f"{OPERADIC_LEDGER_REGISTRY}/{date}"

            result = registry_util_func("get_all", registry_name=registry_name)

            # Parse registry result
            if "Items in registry" in result:
                try:
                    start_idx = result.find("{")
                    if start_idx != -1:
                        dict_str = result[start_idx:]
                        dict_str = dict_str.replace("None", "null").replace("True", "true").replace("False", "false")
                        date_items = json.loads(dict_str.replace("'", '"'))
                        items.extend(date_items.values())
                except Exception:
                    logger.debug(f"No items for date {date}")

        # Sort by completed_at
        items.sort(key=lambda x: x.get("completed_at", ""))

        return items

    except Exception as e:
        logger.error(f"Error reading operadic_ledger: {e}", exc_info=True)
        return []


def _extract_sequences(items: List[Dict[str, Any]], length: int) -> List[List[Dict[str, Any]]]:
    """
    Extract sequences of item steps from completed items.

    Args:
        items: Completed schedule items
        length: Length of sequences to extract

    Returns:
        List of sequences, each sequence is list of step dicts with item data
    """
    # Create step representations for each item (keep essential fields)
    steps = []
    for item in items:
        step = {
            "item_type": item.get("item_type"),
            "execution_type": item.get("execution_type"),
            "mission_type": item.get("mission_type"),
            "mission_type_domain": item.get("mission_type_domain"),
            "human_capability": item.get("human_capability"),
            "priority": item.get("priority", 5),
            "description": item.get("description", ""),
            "variables": item.get("variables", {}),
            "metadata": item.get("metadata", {})
        }
        steps.append(step)

    # Extract sliding window sequences
    sequences = []
    for i in range(len(steps) - length + 1):
        sequence = steps[i:i+length]
        sequences.append(sequence)

    return sequences


def _find_repeated_sequences(
    sequences: List[List[Dict[str, Any]]],
    min_occurrences: int
) -> List[Dict[str, Any]]:
    """
    Find sequences that appear multiple times.

    Args:
        sequences: List of sequences (each sequence is list of step dicts)
        min_occurrences: Minimum occurrences to be considered a pattern

    Returns:
        List of detected patterns
    """
    # Count sequence occurrences (use capability signature as key)
    sequence_map = {}  # signature -> full sequence
    sequence_counts = defaultdict(int)

    for seq in sequences:
        # Create signature from capabilities only (for matching)
        signature = tuple([
            f"{step.get('mission_type') or step.get('human_capability')}"
            for step in seq
        ])

        # Store full sequence data
        if signature not in sequence_map:
            sequence_map[signature] = seq

        sequence_counts[signature] += 1

    # Find patterns (sequences with enough occurrences)
    patterns = []
    for signature, count in sequence_counts.items():
        if count >= min_occurrences:
            pattern = {
                "sequence": sequence_map[signature],  # Full step data
                "occurrences": count,
                "detected_at": datetime.now().isoformat()
            }
            patterns.append(pattern)

    return patterns


def _mirror_pattern_to_carton(pattern_id: str, pattern_data: Dict[str, Any]) -> None:
    """Mirror detected Opera pattern to CartON via carton_queue."""
    try:
        import os
        import uuid
        from pathlib import Path

        heaven_data = os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data")
        queue_dir = Path(heaven_data) / "carton_queue"
        queue_dir.mkdir(parents=True, exist_ok=True)

        # Build description from pattern sequence
        steps = pattern_data.get("sequence", [])
        step_names = [s.get("mission_type") or s.get("human_capability") or "unknown" for s in steps]
        occurrences = pattern_data.get("occurrences", 0)
        desc = f"[QUARANTINE] Opera pattern: {' → '.join(step_names)} ({occurrences} occurrences)"

        queue_data = {
            "raw_concept": True,
            "concept_name": f"Opera_Pattern_{pattern_id}",
            "description": desc,
            "relationships": [
                {"relationship": "is_a", "related": ["Opera_Canopy_Flow_Pattern"]},
                {"relationship": "part_of", "related": ["Opera_Pattern_Quarantine"]},
                {"relationship": "instantiates", "related": ["Opera_Pattern_Template"]},
            ],
            "desc_update_mode": "replace",
            "hide_youknow": True,
            "is_soup": False,
            "soup_reason": None,
            "source": "opera_pattern_detection_mirror",
        }

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        queue_file = queue_dir / f"{timestamp}_{unique_id}_opera.json"

        with open(queue_file, "w") as f:
            json.dump(queue_data, f, indent=2)

        logger.info(f"Mirrored Opera pattern {pattern_id} to CartON")

    except Exception as e:
        logger.warning(f"Failed to mirror Opera pattern to CartON: {e}")


def _store_pattern(pattern: Dict[str, Any]) -> bool:
    """
    Store detected pattern in CanopyFlowPattern quarantine.

    Args:
        pattern: Detected pattern with full sequence data

    Returns:
        True if stored successfully
    """
    try:
        # Generate pattern ID from capability signature
        capability_names = []
        for step in pattern["sequence"]:
            cap = step.get("mission_type") or step.get("human_capability") or "unknown"
            capability_names.append(cap)

        seq_str = "_".join(capability_names)
        pattern_id = f"canopy_pattern_{seq_str}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Create CanopyFlowPattern
        canopy_pattern = {
            "pattern_id": pattern_id,
            "sequence": pattern["sequence"],  # Full step objects
            "occurrences": pattern["occurrences"],
            "detected_at": pattern["detected_at"],
            "status": "quarantine",
            "source": "primary_detection"
        }

        # Store in quarantine
        registry_util_func(
            "add",
            registry_name=CANOPY_PATTERN_REGISTRY,
            key=pattern_id,
            value_dict=canopy_pattern
        )

        # Mirror to CartON via carton_queue
        _mirror_pattern_to_carton(pattern_id, canopy_pattern)

        logger.info(f"Stored pattern: {pattern_id} ({pattern['occurrences']} occurrences)")
        return True

    except Exception as e:
        logger.error(f"Error storing pattern: {e}", exc_info=True)
        return False
