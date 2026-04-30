"""Skill/Flight Candidate Harvester.

Queries CartON for unprocessed Skill_Candidate and Flight_Candidate concepts,
deduplicates by name similarity, groups by domain, creates a Proposal_Batch
concept, and writes a proposal message to the Conductor inbox.

Called by CAVE Heart Tick every 4 hours.
"""

import json
import logging
import os
import time
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# Neo4j connection defaults (same pattern as flow.py check_completed_levels)
_NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://host.docker.internal:7687")
_NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
_NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "password")

HEAVEN_DATA_DIR = Path(os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data"))
CONDUCTOR_INBOX = HEAVEN_DATA_DIR / "inboxes" / "conductor"
DEDUPE_THRESHOLD = 0.8


def _get_driver():
    """Get Neo4j driver. Fails loudly if unavailable."""
    from neo4j import GraphDatabase
    return GraphDatabase.driver(_NEO4J_URI, auth=(_NEO4J_USER, _NEO4J_PASSWORD))


def _query_unprocessed_candidates(driver, candidate_type: str) -> List[Dict[str, str]]:
    """Query CartON for candidates that haven't been harvested into a batch yet.

    Args:
        driver: Neo4j driver
        candidate_type: e.g. "Skill_Candidate" or "Flight_Candidate"

    Returns:
        List of dicts with keys: name, description, domain, category
    """
    with driver.session() as session:
        # Find candidates via IS_A relationship (names vary, can't use prefix)
        # AND that do NOT have a HARVESTED_INTO relationship to any batch
        result = session.run(
            "MATCH (c:Wiki)-[:IS_A]->(:Wiki {n: $type}) "
            "WHERE NOT (c)-[:HARVESTED_INTO]->(:Wiki) "
            "AND c.n IS NOT NULL "
            "OPTIONAL MATCH (c)-[:HAS_DOMAIN]->(d:Wiki) "
            "OPTIONAL MATCH (c)-[:IS_A]->(cat:Wiki) "
            "WHERE cat.n <> $type "
            "RETURN c.n AS name, c.d AS description, "
            "d.n AS domain, cat.n AS category "
            "ORDER BY c.n",
            type=candidate_type
        )
        return [dict(record) for record in result]


def _dedupe_by_name(candidates: List[Dict], threshold: float = DEDUPE_THRESHOLD) -> List[Dict]:
    """Remove near-duplicate candidates based on name similarity.

    Keeps the first occurrence in each cluster of similar names.
    """
    if not candidates:
        return []

    kept = []
    seen_names: List[str] = []

    for candidate in candidates:
        name = candidate["name"]
        is_dupe = False
        for seen in seen_names:
            ratio = SequenceMatcher(None, name.lower(), seen.lower()).ratio()
            if ratio >= threshold:
                is_dupe = True
                logger.debug("Deduped %s (similar to %s, ratio=%.2f)", name, seen, ratio)
                break
        if not is_dupe:
            kept.append(candidate)
            seen_names.append(name)

    deduped_count = len(candidates) - len(kept)
    if deduped_count > 0:
        logger.info("Deduped %d candidates (threshold=%.2f)", deduped_count, threshold)

    return kept


def _group_by_domain(candidates: List[Dict]) -> Dict[str, List[Dict]]:
    """Group candidates by their domain relationship."""
    groups: Dict[str, List[Dict]] = {}
    for c in candidates:
        domain = c.get("domain") or "unknown"
        groups.setdefault(domain, []).append(c)
    return groups


def _create_proposal_batch(
    driver,
    batch_name: str,
    skill_candidates: List[Dict],
    flight_candidates: List[Dict],
) -> bool:
    """Create Proposal_Batch concept in CartON and link candidates to it.

    Creates the batch node, then creates HARVESTED_INTO relationships
    from each candidate to the batch.

    Returns True if successful.
    """
    all_candidate_names = [c["name"] for c in skill_candidates + flight_candidates]
    if not all_candidate_names:
        return False

    skill_domains = _group_by_domain(skill_candidates)
    flight_domains = _group_by_domain(flight_candidates)

    # Build description with domain breakdown
    desc_parts = [f"[STATUS:proposed] Crystallization proposal batch."]
    if skill_candidates:
        desc_parts.append(f"\nSkill candidates ({len(skill_candidates)}):")
        for domain, items in sorted(skill_domains.items()):
            cats = {}
            for item in items:
                cat = (item.get("category") or "unknown").replace("Skill_Candidate_", "")
                cats[cat] = cats.get(cat, 0) + 1
            cat_str = ", ".join(f"{count} {cat}" for cat, count in sorted(cats.items()))
            desc_parts.append(f"  - {domain}: {len(items)} ({cat_str})")
    if flight_candidates:
        desc_parts.append(f"\nFlight candidates ({len(flight_candidates)}):")
        for domain, items in sorted(flight_domains.items()):
            cats = {}
            for item in items:
                cat = (item.get("category") or "unknown").replace("Flight_Candidate_", "")
                cats[cat] = cats.get(cat, 0) + 1
            cat_str = ", ".join(f"{count} {cat}" for cat, count in sorted(cats.items()))
            desc_parts.append(f"  - {domain}: {len(items)} ({cat_str})")

    description = "\n".join(desc_parts)

    with driver.session() as session:
        # Create the batch node
        session.run(
            "MERGE (b:Wiki {n: $name}) "
            "SET b.d = $desc, b.t = $ts "
            "WITH b "
            "MERGE (type:Wiki {n: 'Crystallization_Proposal'}) "
            "MERGE (b)-[:IS_A]->(type) "
            "MERGE (status:Wiki {n: 'Proposal_Status_Proposed'}) "
            "MERGE (b)-[:HAS_STATUS]->(status)",
            name=batch_name,
            desc=description,
            ts=datetime.now(timezone.utc).isoformat(),
        )

        # Link each candidate to the batch via HARVESTED_INTO
        for cname in all_candidate_names:
            session.run(
                "MATCH (c:Wiki {n: $cname}) "
                "MATCH (b:Wiki {n: $bname}) "
                "MERGE (c)-[:HARVESTED_INTO]->(b) "
                "MERGE (b)-[:HAS_PART]->(c)",
                cname=cname,
                bname=batch_name,
            )

    logger.info(
        "Created batch %s: %d skill + %d flight candidates",
        batch_name, len(skill_candidates), len(flight_candidates),
    )
    return True


def _write_conductor_proposal(
    batch_name: str,
    skill_candidates: List[Dict],
    flight_candidates: List[Dict],
) -> Path:
    """Write proposal message JSON to Conductor's file inbox."""
    CONDUCTOR_INBOX.mkdir(parents=True, exist_ok=True)

    skill_domains = _group_by_domain(skill_candidates)
    flight_domains = _group_by_domain(flight_candidates)

    # Build human-readable summary for Conductor
    lines = [f"Crystallization Proposal: {batch_name}"]
    lines.append("")
    if skill_candidates:
        lines.append(f"Skill candidates ({len(skill_candidates)} total):")
        for domain, items in sorted(skill_domains.items()):
            cats = {}
            for item in items:
                cat = (item.get("category") or "unknown").replace("Skill_Candidate_", "")
                cats[cat] = cats.get(cat, 0) + 1
            cat_str = ", ".join(f"{count} {cat}" for cat, count in sorted(cats.items()))
            lines.append(f"  - {domain}: {len(items)} ({cat_str})")
    if flight_candidates:
        lines.append(f"\nFlight candidates ({len(flight_candidates)} total):")
        for domain, items in sorted(flight_domains.items()):
            cats = {}
            for item in items:
                cat = (item.get("category") or "unknown").replace("Flight_Candidate_", "")
                cats[cat] = cats.get(cat, 0) + 1
            cat_str = ", ".join(f"{count} {cat}" for cat, count in sorted(cats.items()))
            lines.append(f"  - {domain}: {len(items)} ({cat_str})")
    lines.append("")
    # CONNECTS_TO: /tmp/heaven_data/conductor_dynamic/crystallization_rules.json (read) — also accessed by Conductor prompt blocks
    lines.append("Check hot rules at /tmp/heaven_data/conductor_dynamic/crystallization_rules.json")
    lines.append("Apply rules and approve/reject/escalate.")

    summary = "\n".join(lines)

    msg = {
        "content": f"<system>{summary}</system>",
        "metadata": {
            "source": "harvester",
            "type": "crystallization_proposal",
            "batch": batch_name,
            "skill_count": len(skill_candidates),
            "flight_count": len(flight_candidates),
            "skill_names": [c["name"] for c in skill_candidates],
            "flight_names": [c["name"] for c in flight_candidates],
        },
    }

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    msg_file = CONDUCTOR_INBOX / f"proposal_{ts}.json"
    msg_file.write_text(json.dumps(msg, indent=2))

    logger.info("Wrote proposal to %s", msg_file)
    return msg_file


def harvest_candidates() -> Dict[str, Any]:
    """Main entry point. Called by CAVE Heart Tick.

    1. Query CartON for unprocessed Skill_Candidate and Flight_Candidate concepts
    2. Dedupe by name similarity within each type
    3. Create Proposal_Batch concept in CartON with status "proposed"
    4. Write proposal JSON to Conductor inbox

    Returns:
        Summary dict with counts and batch name (or noop if nothing to harvest)
    """
    t0 = time.time()
    logger.info("Harvester firing...")

    try:
        driver = _get_driver()
    except Exception as e:
        logger.error("Harvester: Neo4j connection failed: %s", e)
        return {"status": "error", "error": str(e)}

    try:
        # Query unprocessed candidates
        raw_skills = _query_unprocessed_candidates(driver, "Skill_Candidate")
        raw_flights = _query_unprocessed_candidates(driver, "Flight_Candidate")

        logger.info(
            "Found %d unprocessed skill candidates, %d flight candidates",
            len(raw_skills), len(raw_flights),
        )

        if not raw_skills and not raw_flights:
            driver.close()
            logger.info("Harvester: nothing to harvest (noop)")
            return {"status": "noop", "reason": "no unprocessed candidates"}

        # Dedupe
        skills = _dedupe_by_name(raw_skills)
        flights = _dedupe_by_name(raw_flights)

        # Create batch
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M")
        batch_name = f"Proposal_Batch_{ts}"

        success = _create_proposal_batch(driver, batch_name, skills, flights)
        if not success:
            driver.close()
            return {"status": "error", "error": "failed to create batch"}

        # Write to Conductor inbox
        msg_file = _write_conductor_proposal(batch_name, skills, flights)

        driver.close()

        elapsed = time.time() - t0
        result = {
            "status": "proposed",
            "batch": batch_name,
            "skill_count": len(skills),
            "flight_count": len(flights),
            "deduped_skills": len(raw_skills) - len(skills),
            "deduped_flights": len(raw_flights) - len(flights),
            "conductor_msg": str(msg_file),
            "elapsed_seconds": round(elapsed, 2),
        }
        logger.info("Harvester complete: %s", result)
        return result

    except Exception as e:
        logger.error("Harvester error: %s", e, exc_info=True)
        try:
            driver.close()
        except Exception:
            pass
        return {"status": "error", "error": str(e)}
