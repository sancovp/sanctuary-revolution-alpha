"""
Sanctuary System MCP Server

Provides:
- assess_sanctuary_degree() - Interactive survey for evaluating work quality
- view_sanctuary_history() - Trend analysis over time
- declare_system_state() - Current Wasteland/Sanctuary classification
- journal_entry() - Create daily journal entries with Carton integration

Future:
- Automated metrics integration (codenose, test coverage, etc.)
- PIO/SANC_Fractal holographic evaluation
- Narrative context generation
"""

import logging
import json
import os
from datetime import datetime
from typing import Literal, Optional
from pathlib import Path
from fastmcp import FastMCP

logger = logging.getLogger(__name__)

# Carton integration is optional - set SANCTUARY_CARTON_ENABLED=true to enable
CARTON_ENABLED = os.environ.get("SANCTUARY_CARTON_ENABLED", "").lower() in ("true", "1", "yes")

# Initialize MCP server
mcp = FastMCP("Sanctuary System")


# Dimension weights (can be tuned later)
DIMENSION_WEIGHTS = {
    "engagement": 1.0,
    "emotion": 1.0,
    "mechanics": 1.0,
    "progression": 1.0,
    "immersion": 1.0,
    "agency": 1.0
}

def _calculate_sanctuary_score(
    engagement: int,
    emotion: int,
    mechanics: int,
    progression: int,
    immersion: int,
    agency: int
) -> tuple:
    """Calculate weighted sanctuary score and classification."""
    scores = {
        "engagement": engagement,
        "emotion": emotion,
        "mechanics": mechanics,
        "progression": progression,
        "immersion": immersion,
        "agency": agency
    }

    # Normalize to 0-1 and apply weights
    weighted_sum = sum(
        (scores[dim] / 10.0) * DIMENSION_WEIGHTS[dim]
        for dim in scores
    )
    total_weight = sum(DIMENSION_WEIGHTS.values())
    composite = weighted_sum / total_weight

    # Classify
    classification = "Sanctuary" if composite >= 0.75 else "Wasteland"

    return composite, classification, scores


@mcp.tool()
def assess_sanctuary_degree(
    engagement: int,
    emotion: int,
    mechanics: int,
    progression: int,
    immersion: int,
    agency: int
) -> str:
    """
    Calculate composite sanctuary degree from 6 dimension scores.

    Evaluates 6 dimensions (each scored 1-10):
    - Engagement ⚡️ - How engaged/present were you
    - Emotion ❤️ - Emotional quality of the experience
    - Mechanics 🏆 - Technical execution quality
    - Progression 🚀 - Forward movement/progress
    - Immersion 🌍 - Depth of focus/flow state
    - Agency 🔑 - Sense of control/autonomy

    Args:
        engagement: Score 1-10
        emotion: Score 1-10
        mechanics: Score 1-10
        progression: Score 1-10
        immersion: Score 1-10
        agency: Score 1-10

    Returns:
        Composite sanctuary degree score and breakdown
    """
    composite, classification, scores = _calculate_sanctuary_score(
        engagement, emotion, mechanics, progression, immersion, agency
    )

    # Build result
    result_parts = [
        f"**{classification}**: {composite:.2f}",
        "",
        "**Dimension Breakdown:**",
        f"- Engagement ⚡️: {scores['engagement']}/10",
        f"- Emotion ❤️: {scores['emotion']}/10",
        f"- Mechanics 🏆: {scores['mechanics']}/10",
        f"- Progression 🚀: {scores['progression']}/10",
        f"- Immersion 🌍: {scores['immersion']}/10",
        f"- Agency 🔑: {scores['agency']}/10"
    ]

    return "\n".join(result_parts)


@mcp.tool()
def view_sanctuary_history() -> str:
    """
    View sanctuary degree history and trends.

    Placeholder - to be implemented next conversation.

    Returns:
        Historical sanctuary scores and trend analysis
    """
    return "Placeholder: Sanctuary history viewer"


@mcp.tool()
def declare_system_state() -> str:
    """
    Declare current system state: Wasteland or Sanctuary.

    Placeholder - to be implemented next conversation.

    Returns:
        System state classification and reasoning
    """
    return "Placeholder: System state declaration"


def _build_observation_batch(
    entry_text: str,
    entry_type: str,
    today: datetime,
    engagement: int,
    emotion: int,
    mechanics: int,
    progression: int,
    immersion: int,
    agency: int
) -> tuple:
    """Build observation batch with journal entry and sanctuary degree."""
    date_str = today.strftime("%Y_%m_%d")
    timestamp_str = today.strftime("%Y_%m_%d_%H_%M_%S")
    entry_type_capitalized = entry_type.capitalize()

    # Calculate sanctuary score
    composite, classification, scores = _calculate_sanctuary_score(
        engagement, emotion, mechanics, progression, immersion, agency
    )

    # Build assessment text
    assessment_parts = [
        "",
        "## Sanctuary Assessment",
        f"**{classification}**: {composite:.2f}",
        "",
        "**Dimension Scores:**",
        f"- Engagement ⚡️: {scores['engagement']}/10",
        f"- Emotion ❤️: {scores['emotion']}/10",
        f"- Mechanics 🏆: {scores['mechanics']}/10",
        f"- Progression 🚀: {scores['progression']}/10",
        f"- Immersion 🌍: {scores['immersion']}/10",
        f"- Agency 🔑: {scores['agency']}/10"
    ]
    assessment_text = "\n".join(assessment_parts)

    # Journal entry concept
    journal_name = f"Journal_Entry_{date_str}_{entry_type_capitalized}"
    journal_description = f"""**Journal Entry - {entry_type_capitalized}**
**Date**: {today.strftime('%Y-%m-%d')}

## Entry
{entry_text}{assessment_text}"""

    # Sanctuary degree concept
    degree_name = f"Sanctuary_Degree_{timestamp_str}"
    degree_description = f"""**{classification}**: {composite:.2f}
**Timestamp**: {today.isoformat()}

**Dimension Scores:**
- Engagement ⚡️: {scores['engagement']}/10
- Emotion ❤️: {scores['emotion']}/10
- Mechanics 🏆: {scores['mechanics']}/10
- Progression 🚀: {scores['progression']}/10
- Immersion 🌍: {scores['immersion']}/10
- Agency 🔑: {scores['agency']}/10"""

    # Build observation batch
    observation_data = {
        "daily_action": [{
            "name": journal_name,
            "description": journal_description,
            "relationships": [
                {"relationship": "is_a", "related": ["Journal_Entry"]},
                {"relationship": "part_of", "related": [f"Day_{date_str}"]},
                {"relationship": "has_sanctuary_degree", "related": [degree_name]},
                {"relationship": "has_personal_domain", "related": ["personal_life_stuff"]},
                {"relationship": "has_actual_domain", "related": ["Historical_Sanctuary_Degrees"]}
            ]
        }],
        "implementation": [{
            "name": degree_name,
            "description": degree_description,
            "relationships": [
                {"relationship": "is_a", "related": ["Sanctuary_Degree"]},
                {"relationship": "part_of", "related": [journal_name]},
                {"relationship": "has_personal_domain", "related": ["personal_life_stuff"]},
                {"relationship": "has_actual_domain", "related": ["Historical_Sanctuary_Degrees"]}
            ]
        }],
        "confidence": 0.9
    }

    return observation_data, journal_name, degree_name


# Default path for local journal marker files (for hook sync)
JOURNALS_MARKER_DIR = Path(os.environ.get("SANCTUARY_JOURNALS_DIR", "/tmp/heaven_data/sanctuary/journals"))


@mcp.tool()
def journal_entry(
    entry_text: str,
    entry_type: Literal["opening", "closing"],
    engagement: int,
    emotion: int,
    mechanics: int,
    progression: int,
    immersion: int,
    agency: int,
    user_explicitly_authorized: bool = False,
    entry_file_path: Optional[str] = None
) -> str:
    """
    Create a journal entry and save it as a Carton concept.

    Each day can have an opening entry (morning) and closing entry (evening).
    The entry is assessed for sanctuary degree and stored in the knowledge graph.

    Args:
        entry_text: The journal entry content
        entry_type: Type of entry - "opening" or "closing"
        engagement: Engagement score 1-10
        emotion: Emotion score 1-10
        mechanics: Mechanics score 1-10
        progression: Progression score 1-10
        immersion: Immersion score 1-10
        agency: Agency score 1-10
        user_explicitly_authorized: Whether the user explicitly authorized this journal entry
        entry_file_path: Optional custom path to write the journal marker file

    Returns:
        Confirmation of journal entry creation with sanctuary assessment
    """
    today = datetime.now()

    # Build observation batch with journal and degree concepts
    observation_data, journal_name, degree_name = _build_observation_batch(
        entry_text, entry_type, today,
        engagement, emotion, mechanics, progression, immersion, agency
    )

    # Calculate score for response
    composite, classification, scores = _calculate_sanctuary_score(
        engagement, emotion, mechanics, progression, immersion, agency
    )

    result_base = {
        "concept_name": journal_name,
        "degree_concept_name": degree_name,
        "entry_type": entry_type,
        "date": today.strftime('%Y-%m-%d'),
        "classification": classification,
        "composite_score": composite,
        "user_explicitly_authorized": user_explicitly_authorized
    }

    # Write local marker file for hook sync
    date_str = today.strftime("%Y_%m_%d")
    marker_filename = f"{date_str}_{entry_type}.json"
    marker_path = Path(entry_file_path) if entry_file_path else JOURNALS_MARKER_DIR / marker_filename

    try:
        marker_path.parent.mkdir(parents=True, exist_ok=True)
        marker_data = {
            **result_base,
            "timestamp": today.isoformat(),
            "entry_text_preview": entry_text[:200] if len(entry_text) > 200 else entry_text
        }
        marker_path.write_text(json.dumps(marker_data, indent=2))
        result_base["marker_file"] = str(marker_path)
    except Exception as e:
        logger.warning(f"Failed to write marker file: {e}")
        result_base["marker_file_error"] = str(e)

    if CARTON_ENABLED:
        try:
            from carton_mcp.add_concept_tool import add_observation

            # Submit to Carton observation queue
            carton_result = add_observation(observation_data)

            return json.dumps({
                "success": True,
                **result_base,
                "message": f"Journal entry created and saved to Carton: {journal_name}",
                "carton_result": carton_result
            }, indent=2)

        except ImportError as e:
            logger.error(f"Carton tools not available: {e}", exc_info=True)
            return json.dumps({
                "success": False,
                **result_base,
                "error": f"SANCTUARY_CARTON_ENABLED=true but Carton import failed: {str(e)}"
            }, indent=2)

        except Exception as e:
            logger.error(f"Error saving to Carton: {e}", exc_info=True)
            return json.dumps({
                "success": False,
                **result_base,
                "error": f"Carton save failed: {str(e)}"
            }, indent=2)
    else:
        # Carton disabled - just return the assessment
        return json.dumps({
            "success": True,
            **result_base,
            "message": f"Journal entry assessed (Carton disabled): {journal_name}",
            "note": "Set SANCTUARY_CARTON_ENABLED=true to persist to knowledge graph"
        }, indent=2)


def main():
    """Run Sanctuary System MCP server"""
    mcp.run()


if __name__ == "__main__":
    main()
