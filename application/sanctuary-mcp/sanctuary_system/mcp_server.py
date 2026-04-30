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

# Carton integration — enabled by default. Set SANCTUARY_CARTON_ENABLED=false to disable.
CARTON_ENABLED = os.environ.get("SANCTUARY_CARTON_ENABLED", "true").lower() not in ("false", "0", "no")

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
                {"relationship": "part_of", "related": [f"Day_{date_str}", "User_Autobiography_Timeline"]},
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
# TRIGGERS: WakingDreamer journal_completion_watcher via file write to /tmp/heaven_data/sanctuary/journals/
JOURNALS_MARKER_DIR = Path(os.environ.get("SANCTUARY_JOURNALS_DIR", "/tmp/heaven_data/sanctuary/journals"))


@mcp.tool()
def journal_entry(
    entry_text: str,
    entry_type: Literal["opening", "closing", "friendship"],
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


@mcp.tool()
def friendship_journal(
    reflection_text: str,
    status: Literal["continue", "pivot"],
    engagement: int,
    emotion: int,
    mechanics: int,
    progression: int,
    immersion: int,
    agency: int,
    invalidated_twis: Optional[list] = None,
    new_twis: Optional[list] = None,
    deliverables: Optional[list] = None,
) -> str:
    """Weekly Friendship ritual journal — executive BML on the whole system.

    Emits: sanctuary degree scores, journal entry, TWI changes, deliverables to backlog.
    The human + system review the week's odyssey output and steer via TWIs.

    Args:
        reflection_text: The friendship reflection/journal text
        status: "continue" (TWIs holding) or "pivot" (changes needed)
        engagement: Weekly system experience score 1-10
        emotion: Weekly emotional quality score 1-10
        mechanics: Weekly technical execution score 1-10
        progression: Weekly forward movement score 1-10
        immersion: Weekly depth of focus score 1-10
        agency: Weekly sense of control score 1-10
        invalidated_twis: List of {"twi": "the TWI text", "reason": "why it failed"}
        new_twis: List of {"twi": "new TWI text max 150 chars", "hypothesis": "I predict...", "evidence": "episodes that support"}
        deliverables: List of {"name": "deliverable name", "description": "what needs to be built"}

    Returns:
        Confirmation with all emitted concepts
    """
    today = datetime.now()
    date_str = today.strftime("%Y_%m_%d")
    timestamp_str = today.strftime("%Y%m%d")

    invalidated_twis = invalidated_twis or []
    new_twis = new_twis or []
    deliverables = deliverables or []

    results = []

    # 1. Journal entry + sanctuary degree (same as regular journal)
    observation_data, journal_name, degree_name = _build_observation_batch(
        reflection_text, "friendship", today,
        engagement, emotion, mechanics, progression, immersion, agency
    )

    # Add status to journal description
    observation_data["daily_action"][0]["description"] += f"\n\n## Friendship Status: {status.upper()}"
    observation_data["daily_action"][0]["relationships"].append(
        {"relationship": "has_status", "related": [f"Friendship_Status_{status.capitalize()}"]}
    )

    # Write marker file
    marker_filename = f"{date_str}_friendship.json"
    marker_path = JOURNALS_MARKER_DIR / marker_filename
    try:
        marker_path.parent.mkdir(parents=True, exist_ok=True)
        marker_path.write_text(json.dumps({
            "entry_type": "friendship",
            "status": status,
            "date": today.strftime('%Y-%m-%d'),
            "timestamp": today.isoformat(),
            "invalidated_count": len(invalidated_twis),
            "new_twi_count": len(new_twis),
            "deliverable_count": len(deliverables),
        }, indent=2))
    except Exception as e:
        logger.warning(f"Failed to write friendship marker: {e}")

    if CARTON_ENABLED:
        try:
            from carton_mcp.add_concept_tool import add_observation, get_observation_queue_dir
            import uuid

            # Queue the journal observation
            carton_result = add_observation(observation_data)
            results.append(f"Journal: {journal_name}")

            queue_dir = get_observation_queue_dir()

            # 2. Invalidate TWIs — create record, will be removed from global intents by daemon
            for inv in invalidated_twis:
                inv_name = f"Twi_Invalidated_{timestamp_str}_{uuid.uuid4().hex[:6]}"
                inv_data = {
                    "raw_concept": True,
                    "concept_name": inv_name,
                    "description": f"TWI invalidated during Friendship {date_str}: {inv.get('twi', '')} | Reason: {inv.get('reason', '')}",
                    "relationships": [
                        {"relationship": "is_a", "related": ["Twi_Invalidated"]},
                        {"relationship": "part_of", "related": [journal_name]},
                        {"relationship": "invalidates", "related": ["Claude_Code_Rule_Twi_Global_Intents"]},
                    ],
                    "source": "friendship",
                }
                queue_file = queue_dir / f"{today.strftime('%Y%m%d_%H%M%S%f')}_{uuid.uuid4().hex[:8]}.json"
                with open(queue_file, 'w') as f:
                    json.dump(inv_data, f)
                results.append(f"Invalidated: {inv.get('twi', '')[:50]}...")

            # 3. New TWIs — create hypothesis + append to global intents
            for twi in new_twis:
                # Hypothesis concept
                hyp_name = f"Twi_Hypothesis_{timestamp_str}_{uuid.uuid4().hex[:6]}"
                hyp_data = {
                    "raw_concept": True,
                    "concept_name": hyp_name,
                    "description": f"theme: {twi.get('twi', '')} | hypothesis: {twi.get('hypothesis', '')} | evidence: {twi.get('evidence', '')}",
                    "relationships": [
                        {"relationship": "is_a", "related": ["Twi_Hypothesis"]},
                        {"relationship": "part_of", "related": [journal_name]},
                    ],
                    "source": "friendship",
                }
                queue_file = queue_dir / f"{today.strftime('%Y%m%d_%H%M%S%f')}_{uuid.uuid4().hex[:8]}.json"
                with open(queue_file, 'w') as f:
                    json.dump(hyp_data, f)

                # Append TWI to global intents
                twi_text = twi.get("twi", "")[:150]
                append_data = {
                    "raw_concept": True,
                    "concept_name": "Claude_Code_Rule_Twi_Global_Intents",
                    "description": f"\n- {twi_text}",
                    "relationships": [
                        {"relationship": "is_a", "related": ["Claude_Code_Rule"]},
                        {"relationship": "has_scope", "related": ["global"]},
                    ],
                    "desc_update_mode": "append",
                    "source": "friendship",
                }
                queue_file = queue_dir / f"{today.strftime('%Y%m%d_%H%M%S%f')}_{uuid.uuid4().hex[:8]}.json"
                with open(queue_file, 'w') as f:
                    json.dump(append_data, f)
                results.append(f"New TWI: {twi_text[:50]}...")

            # 4. Deliverables — emit as Friendship_Deliverable for daemon to create TK cards
            for deliv in deliverables:
                deliv_name = f"Friendship_Deliverable_{timestamp_str}_{uuid.uuid4().hex[:6]}"
                deliv_data = {
                    "raw_concept": True,
                    "concept_name": deliv_name,
                    "description": deliv.get("description", ""),
                    "relationships": [
                        {"relationship": "is_a", "related": ["Friendship_Deliverable"]},
                        {"relationship": "part_of", "related": [journal_name]},
                    ],
                    "source": "friendship",
                }
                queue_file = queue_dir / f"{today.strftime('%Y%m%d_%H%M%S%f')}_{uuid.uuid4().hex[:8]}.json"
                with open(queue_file, 'w') as f:
                    json.dump(deliv_data, f)
                results.append(f"Deliverable: {deliv.get('name', '')}")

            return json.dumps({
                "success": True,
                "journal": journal_name,
                "degree": degree_name,
                "status": status,
                "emitted": results,
                "message": f"Friendship journal complete: {len(invalidated_twis)} invalidated, {len(new_twis)} new TWIs, {len(deliverables)} deliverables"
            }, indent=2)

        except Exception as e:
            logger.error(f"Friendship journal error: {e}", exc_info=True)
            return json.dumps({"success": False, "error": str(e)}, indent=2)
    else:
        return json.dumps({
            "success": True,
            "journal": journal_name,
            "status": status,
            "message": "Friendship assessed (Carton disabled)",
            "note": "Set SANCTUARY_CARTON_ENABLED=true to persist"
        }, indent=2)


@mcp.tool()
def deposit_memory(
    memory_name: str,
    description: str,
    domain: str,
    location: str,
    feeling: str,
    source: str = "chat",
    date: str = "",
    estimated_daterange: str = "",
    people_and_entities: str = "",
) -> str:
    """Deposit a biographical memory onto the User Autobiography Timeline.

    Extract from the user's natural speech: WHEN it happened, WHERE, WHAT happened,
    HOW they felt, and WHO/WHAT was involved. Then call this tool.

    The user says things like "Back in 93, at grandma's house, Dad showed me BASIC.
    I felt like I discovered a superpower." You extract the structured fields from that.

    Args:
        memory_name: Short descriptive name for this memory. Use Title_Case_With_Underscores.
            Examples: "Learned_Basic", "Met_Tara", "Started_Gnosys", "Christina_Left"
        description: The actual memory content — what happened, in the user's words.
            Preserve their phrasing. This is the biographical record.
        domain: EXACTLY ONE OF: health, wealth, relationships, purpose, growth, environment.
            Pick the life domain this memory most belongs to.
        location: Where this happened. Can be specific ("NYC", "grandmother's house")
            or general ("at home", "online", "at school"). Always provide something.
        feeling: How the user felt about this memory. Can be one word ("grateful")
            or a phrase ("like I discovered a superpower"). Capture their actual words.
        source: How this memory was captured. ONE OF: chat, journal_morning,
            journal_evening, friendship, ritual. Default: "chat"
        date: Exact date if known, format YYYY-MM-DD. Leave empty string if uncertain.
            Example: "2026-04-20"
        estimated_daterange: Fuzzy time range if exact date unknown. Can be a year ("1993"),
            a month ("2026-03"), a range ("2020-2023"), or a period ("childhood").
            At least one of date or estimated_daterange REQUIRED.
        people_and_entities: JSON list of people, events, and topics mentioned in the memory.
            NOT locations or feelings (those have their own fields).
            Format: ["Dad", "Christina", "BASIC_Programming", "College_Graduation"]
            Each becomes a CartON concept (created if it doesn't exist) linked to this memory.
            These are the retrieval anchors — future mentions of "Dad" find all Dad memories.

    Returns:
        Confirmation with concept name and what was deposited.
    """
    today = datetime.now()

    if not date and not estimated_daterange:
        return json.dumps({
            "success": False,
            "error": "At least one of date or estimated_daterange is required."
        })

    # Determine timeline placement
    timeline_parents = ["User_Autobiography_Timeline"]
    if date:
        # Exact date → Day → Month → Year
        try:
            dt = datetime.strptime(date, "%Y-%m-%d")
            year_str = dt.strftime("%Y")
            month_str = dt.strftime("%Y_%m")
            day_str = dt.strftime("%Y_%m_%d")
            timeline_parents.append(f"Day_{day_str}")
        except ValueError:
            return json.dumps({"success": False, "error": f"Invalid date format: {date}. Use YYYY-MM-DD."})
    elif estimated_daterange:
        # Fuzzy — attach to most specific container we can
        dr = estimated_daterange.strip()
        if len(dr) == 4 and dr.isdigit():
            # Just a year: "1993"
            timeline_parents.append(f"Year_{dr}")
        elif len(dr) == 7 and dr[4] == "-" and dr[:4].isdigit():
            # Year-month: "2026-03"
            timeline_parents.append(f"Month_{dr.replace('-', '_')}")
        else:
            # Range or period: "2020-2023", "childhood"
            timeline_parents.append(f"Period_{dr.replace(' ', '_').replace('-', '_')}")

    # Build concept name
    timestamp_str = today.strftime("%Y%m%d_%H%M%S")
    concept_name = f"Biographical_Memory_{memory_name}_{timestamp_str}"

    # Build relationships
    relationships = [
        {"relationship": "is_a", "related": ["Biographical_Memory"]},
        {"relationship": "part_of", "related": timeline_parents},
        {"relationship": "has_domain", "related": [f"Domain_{domain.capitalize()}"]},
        {"relationship": "has_location", "related": [location]},
        {"relationship": "has_feeling", "related": [feeling]},
        {"relationship": "has_source", "related": [f"Source_{source}"]},
    ]

    if date:
        relationships.append({"relationship": "has_date", "related": [date]})
    if estimated_daterange:
        relationships.append({"relationship": "has_estimated_daterange", "related": [estimated_daterange]})

    # Parse people/entities and add as relates_to
    entities = []
    if people_and_entities:
        try:
            entities = json.loads(people_and_entities) if isinstance(people_and_entities, str) else people_and_entities
        except json.JSONDecodeError:
            # Treat as comma-separated fallback
            entities = [e.strip() for e in people_and_entities.split(",") if e.strip()]

    if entities:
        relationships.append({"relationship": "relates_to", "related": entities})

    # Build full description with metadata header
    full_description = (
        f"**Biographical Memory** — {memory_name.replace('_', ' ')}\n"
        f"**When**: {date or estimated_daterange}\n"
        f"**Where**: {location}\n"
        f"**Feeling**: {feeling}\n"
        f"**Domain**: {domain}\n\n"
        f"{description}"
    )

    if not CARTON_ENABLED:
        return json.dumps({
            "success": False,
            "error": "Carton disabled. Set SANCTUARY_CARTON_ENABLED=true to deposit memories.",
        })

    try:
        from carton_mcp.add_concept_tool import add_observation, get_observation_queue_dir
        import uuid

        queue_dir = get_observation_queue_dir()

        # Queue the memory concept
        memory_data = {
            "raw_concept": True,
            "concept_name": concept_name,
            "description": full_description,
            "relationships": relationships,
            "source": "autobiographer",
        }
        queue_file = queue_dir / f"{today.strftime('%Y%m%d_%H%M%S%f')}_{uuid.uuid4().hex[:8]}.json"
        with open(queue_file, 'w') as f:
            json.dump(memory_data, f)

        # Queue entity concepts (created if they don't exist)
        created_entities = []
        for entity in entities:
            entity_data = {
                "raw_concept": True,
                "concept_name": entity,
                "description": f"Person, event, or topic from Isaac's biographical memory. First referenced in: {concept_name}",
                "relationships": [
                    {"relationship": "is_a", "related": ["Biographical_Entity"]},
                    {"relationship": "part_of", "related": ["User_Autobiography_Timeline"]},
                    {"relationship": "relates_to", "related": [concept_name]},
                ],
                "source": "autobiographer",
                "desc_update_mode": "append",
            }
            queue_file = queue_dir / f"{today.strftime('%Y%m%d_%H%M%S%f')}_{uuid.uuid4().hex[:8]}.json"
            with open(queue_file, 'w') as f:
                json.dump(entity_data, f)
            created_entities.append(entity)

        return json.dumps({
            "success": True,
            "concept_name": concept_name,
            "timeline_parents": timeline_parents,
            "entities_linked": created_entities,
            "domain": domain,
            "message": f"Memory deposited: {concept_name} → {', '.join(timeline_parents)}",
        }, indent=2)

    except Exception as e:
        logger.error(f"deposit_memory error: {e}", exc_info=True)
        return json.dumps({"success": False, "error": str(e)})


def main():
    """Run Sanctuary System MCP server"""
    mcp.run()


if __name__ == "__main__":
    main()
