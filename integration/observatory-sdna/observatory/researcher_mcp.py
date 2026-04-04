#!/usr/bin/env python3
"""Researcher MCP — typed scientific method tools for the researcher agent.

Write: record_observation — persist phase results to CartON
Read:  query_knowledge — query CartON wiki graph (researcher + grug collections)

The researcher agent gets THIS MCP. Nobody else.

Tag mapping (forced, invariant):
    insight_moment    → observation         (what was found)
    struggle_point    → uncertain_aspects   (what's unknown)
    daily_action      → phase              (observe/hypothesize/propose/experiment/analyze)
    implementation    → occurred_when_i_was (what the researcher was doing)
    emotional_state   → confidence         (Researcher_Confidence_{Level}_{date}_{score})
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("researcher-mcp")
logging.basicConfig(level=logging.INFO)

mcp = FastMCP("researcher", "Researcher MCP — typed scientific method observation recording")


CONFIDENCE_LEVELS = ["high", "medium", "low", "uncertain"]
PHASES = ["observe", "hypothesize", "proposal", "experiment", "analyze"]
IDENTITY = "researcher"
TOOL_SLEEP = 15  # seconds — let observation queue drain before next tool call

VALIDITY_DIR = Path("/tmp/heaven_data/observatory/validity")


def _title_case(name: str) -> str:
    """Normalize name to Title_Case to match CartON's forced normalization."""
    return '_'.join(w.capitalize() for w in name.split('_'))


# =============================================================================
# Per-investigation concept validity cache
# =============================================================================

def _validity_path(investigation_name: str) -> Path:
    VALIDITY_DIR.mkdir(parents=True, exist_ok=True)
    return VALIDITY_DIR / f"{investigation_name}.json"


def _load_validity(investigation_name: str) -> dict:
    p = _validity_path(investigation_name)
    if p.exists():
        return json.loads(p.read_text())
    return {}


def _save_validity(investigation_name: str, data: dict):
    _validity_path(investigation_name).write_text(json.dumps(data, indent=2))


def mark_valid(investigation_name: str, concept_name: str):
    """Mark a concept as valid for this investigation."""
    data = _load_validity(investigation_name)
    data[concept_name] = {
        "valid_at": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "invalid_at": None,
        "revalidated_at": None,
    }
    _save_validity(investigation_name, data)


def invalidate_investigation(investigation_name: str):
    """Invalidate ALL concepts for an investigation (called at start of new run)."""
    data = _load_validity(investigation_name)
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    for concept_name in data:
        if data[concept_name]["invalid_at"] is None:
            data[concept_name]["invalid_at"] = now
    _save_validity(investigation_name, data)
    logger.info("Invalidated %d concepts for %s", len(data), investigation_name)


def revalidate_concept(investigation_name: str, concept_name: str):
    """Re-validate a previously invalidated concept."""
    data = _load_validity(investigation_name)
    if concept_name in data:
        data[concept_name]["invalid_at"] = None
        data[concept_name]["revalidated_at"] = datetime.now().strftime("%Y%m%d_%H%M%S")
        _save_validity(investigation_name, data)


def get_valid_concepts(investigation_name: str) -> set:
    """Return set of concept names that are currently valid."""
    data = _load_validity(investigation_name)
    return {name for name, v in data.items() if v.get("invalid_at") is None}


def is_concept_valid(investigation_name: str, concept_name: str) -> bool:
    """Check if a concept is valid across ALL investigation caches.

    Gathers validity from every investigation's cache file.
    If concept is invalid in ANY cache, it's invalid.
    If concept is not in ANY cache and starts with Research_, it's invalid (pre-validity era).
    """
    VALIDITY_DIR.mkdir(parents=True, exist_ok=True)
    found = False
    for cache_file in VALIDITY_DIR.glob("*.json"):
        data = json.loads(cache_file.read_text()) if cache_file.stat().st_size > 2 else {}
        if concept_name in data:
            found = True
            if data[concept_name].get("invalid_at") is not None:
                return False  # Explicitly invalidated in this cache

    if not found and concept_name.startswith("Research_"):
        return False  # Not in any cache = pre-validity era, reject

    return True


def _inject_investigation(observation_data: dict, investigation_name: str):
    """Inject part_of investigation_name into every concept's relationships."""
    for tag, concepts in observation_data.items():
        if not isinstance(concepts, list):
            continue
        for concept in concepts:
            if "relationships" not in concept:
                concept["relationships"] = []
            # Add part_of investigation if not already present
            has_inv = any(
                r.get("relationship") == "part_of" and investigation_name in r.get("related", [])
                for r in concept["relationships"]
            )
            if not has_inv:
                concept["relationships"].append(
                    {"relationship": "part_of", "related": [investigation_name]}
                )


@mcp.tool()
def record_observation(
    observation: str,
    uncertain_aspects: str,
    phase: str,
    occurred_when_i_was: str,
    confidence_level: str,
    confidence_score: int,
    investigation_name: str,
    domain: str,
    additional_concepts: str = "[]",
) -> str:
    """Record a research observation for the current phase.

    Args:
        observation: What was found (the finding)
        uncertain_aspects: What's unknown or didn't work
        phase: Current phase (observe/hypothesize/proposal/experiment/analyze)
        occurred_when_i_was: What you were doing (method description)
        confidence_level: How confident (high/medium/low/uncertain)
        confidence_score: Numeric confidence 0-100
        investigation_name: Name of the research investigation
        domain: Research domain
        additional_concepts: Optional JSON list of extra named concepts to add.
            Each goes into insight_moment. Format:
            [{"name": "My_Concept", "description": "...", "relationships": [{"relationship": "is_a", "related": ["Type"]}]}]

    Returns:
        CartON observation result
    """
    if phase not in PHASES:
        return json.dumps({"error": f"Invalid phase '{phase}'. Must be one of: {PHASES}"})
    if confidence_level not in CONFIDENCE_LEVELS:
        return json.dumps({"error": f"Invalid confidence_level '{confidence_level}'. Must be one of: {CONFIDENCE_LEVELS}"})
    if not 0 <= confidence_score <= 100:
        return json.dumps({"error": "confidence_score must be 0-100"})

    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    phase_cap = phase.capitalize()

    base_rels = [
        {"relationship": "has_personal_domain", "related": ["paiab"]},
        {"relationship": "has_actual_domain", "related": [domain]},
    ]

    data = {
        "insight_moment": [{
            "name": f"Research_Observation_{_title_case(investigation_name)}_{phase_cap}_{now}",
            "description": observation,
            "relationships": [
                {"relationship": "is_a", "related": ["Research_Observation"]},
                {"relationship": "instantiates", "related": [f"Scientific_Method_{phase_cap}"]},
                *base_rels,
            ],
        }],
        "struggle_point": [{
            "name": f"Research_Uncertainty_{_title_case(investigation_name)}_{phase_cap}_{now}",
            "description": uncertain_aspects,
            "relationships": [
                {"relationship": "is_a", "related": ["Research_Uncertainty"]},
                {"relationship": "instantiates", "related": [f"Scientific_Method_{phase_cap}"]},
                *base_rels,
            ],
        }],
        "daily_action": [{
            "name": f"Research_Phase_{_title_case(investigation_name)}_{phase_cap}_{now}",
            "description": f"Scientific method phase: {phase}",
            "relationships": [
                {"relationship": "is_a", "related": ["Research_Phase"]},
                {"relationship": "instantiates", "related": [f"Scientific_Method_{phase_cap}"]},
                *base_rels,
            ],
        }],
        "implementation": [{
            "name": f"Research_Method_{_title_case(investigation_name)}_{phase_cap}_{now}",
            "description": occurred_when_i_was,
            "relationships": [
                {"relationship": "is_a", "related": ["Research_Method"]},
                {"relationship": "instantiates", "related": [f"Scientific_Method_{phase_cap}"]},
                *base_rels,
            ],
        }],
        "emotional_state": [{
            "name": f"Research_Confidence_{confidence_level.capitalize()}_{now}_{confidence_score}",
            "description": f"Confidence level: {confidence_level} ({confidence_score}/100) during {phase} phase of {investigation_name}",
            "relationships": [
                {"relationship": "is_a", "related": ["Researcher_Confidence"]},
                {"relationship": "instantiates", "related": ["Confidence_Assessment"]},
                *base_rels,
            ],
        }],
    }

    # Add researcher's additional named concepts into insight_moment
    try:
        extras = json.loads(additional_concepts) if isinstance(additional_concepts, str) else additional_concepts
        if isinstance(extras, list):
            for concept in extras:
                if isinstance(concept, dict) and "name" in concept:
                    data["insight_moment"].append(concept)
    except (json.JSONDecodeError, TypeError):
        pass

    _inject_investigation(data, investigation_name)

    try:
        from carton_mcp.server_fastmcp import observe_from_identity_pov
        result = observe_from_identity_pov(data, agent_identity=IDENTITY)

        # Mark all created concepts as valid in the validity cache
        for tag_concepts in data.values():
            if not isinstance(tag_concepts, list):
                continue
            for concept in tag_concepts:
                if isinstance(concept, dict) and "name" in concept:
                    mark_valid(investigation_name, concept["name"])

        # Return concept names so the researcher knows what was created
        created_names = []
        for tag_concepts in data.values():
            if not isinstance(tag_concepts, list):
                continue
            for concept in tag_concepts:
                if isinstance(concept, dict) and "name" in concept:
                    created_names.append(concept["name"])

        # If this is the PROPOSAL phase, write the exact concept name to memory
        # so EXPERIMENT phase can find it without querying CartON (queue lag)
        # OVERWRITE — only the latest proposal matters
        if phase == "proposal":
            proposal_concept = data["insight_moment"][0]["name"]
            memory_path = Path("/tmp/heaven_data/observatory/researcher_memory.md")
            memory_path.parent.mkdir(parents=True, exist_ok=True)
            memory_path.write_text(f"## LATEST PROPOSAL CONCEPT\n{proposal_concept}\n")
            logger.info("Wrote proposal concept name to memory: %s", proposal_concept)

        # Strip ephemeral filename from result, keep warnings
        import re
        clean_result = re.sub(r'Observation queued: \S+', 'Observation recorded', result)

        import time; time.sleep(TOOL_SLEEP)
        return json.dumps({
            "status": "recorded",
            "created_concepts": created_names,
            "result": clean_result,
        })
    except Exception as e:
        logger.error("observe_from_identity_pov error: %s", e, exc_info=True)
        return json.dumps({"error": str(e)})


@mcp.tool()
def query_knowledge(query: str, investigations: str = "ALL") -> str:
    """Query your observations in CartON. Constrained to Researcher_Collection.

    Write a Cypher query using variable `n` for matched concepts. The tool
    automatically constrains to Researcher_Collection and your specified
    investigations.

    Args:
        query: Cypher WHERE/RETURN clause. Variable `n` is the concept node.
               Examples:
                 "RETURN n.n as name, n.d as description"
                 "WHERE n.n CONTAINS 'Proposal' RETURN n.n as name, n.d as description"
                 "WHERE n.n STARTS WITH 'Research_Observation' RETURN n.n, n.d ORDER BY n.n DESC LIMIT 5"
        investigations: "ALL" for all investigations, or comma-separated list of
                        investigation names to scope to.

    Returns:
        JSON array of matched observations.
    """
    try:
        import re
        from carton_mcp.carton_utils import CartOnUtils
        utils = CartOnUtils()

        # Build constrained query — ALWAYS scoped to Researcher_Collection
        if investigations == "ALL":
            cypher = (
                "MATCH (n:Wiki)-[:PART_OF]->(c:Wiki {n: 'Researcher_Collection'}) "
                "WITH n "
                + query
            )
            params = {}
        else:
            inv_list = [_title_case(s.strip()) for s in investigations.split(",")]
            cypher = (
                "MATCH (n:Wiki)-[:PART_OF]->(c:Wiki {n: 'Researcher_Collection'}) "
                "WHERE ANY(inv IN $inv_list WHERE n.n CONTAINS inv) "
                "WITH n "
                + query
            )
            params = {"inv_list": inv_list}

        result = utils.query_wiki_graph(cypher, params)

        # Retry once after 30s if empty (queue may not have drained)
        if isinstance(result, dict) and not result.get("data"):
            import time
            logger.info("query_knowledge returned empty, sleeping 30s and retrying...")
            time.sleep(30)
            result = utils.query_wiki_graph(cypher, params)

        # Extract just the data
        data = result.get("data", []) if isinstance(result, dict) else []

        # Filter by validity
        data = [
            row for row in data
            if not isinstance(row, dict)
            or is_concept_valid(investigations, row.get("name", row.get("n.n", "")))
        ]

        # Deduplicate and clean descriptions
        def clean_description(text):
            if not isinstance(text, str):
                return text
            # Deduplicate --- separated blocks (CartON append mode creates dupes)
            blocks = [b.strip() for b in text.split("\n\n---\n\n") if b.strip()]
            seen = []
            for b in blocks:
                if b not in seen:
                    seen.append(b)
            text = seen[0] if seen else text  # Just keep first unique block
            # Strip wiki-links
            for _ in range(5):
                prev = text
                text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
                text = re.sub(r'\([^)]*_itself\.md\)', '', text)
                text = re.sub(r'\(\.\./[^)]*\)', '', text)
                text = re.sub(r'\[([^\]]+)\]', r'\1', text)
                if text == prev:
                    break
            text = re.sub(r'/\w+_itself\.md\)', '', text)
            text = re.sub(r'  +', ' ', text)
            # Truncate to 500 chars max
            if len(text) > 500:
                text = text[:500] + "..."
            return text

        for row in data:
            if isinstance(row, dict):
                for k, v in row.items():
                    if isinstance(v, str):
                        row[k] = clean_description(v)

        # Huffman-like ref compression for repeated strings
        string_counts = {}
        for row in data:
            if isinstance(row, dict):
                for v in row.values():
                    if isinstance(v, str) and len(v) > 20:
                        string_counts[v] = string_counts.get(v, 0) + 1

        repeated = sorted(
            [(s, c) for s, c in string_counts.items() if c >= 2],
            key=lambda x: -x[1]
        )
        ref_table = {}
        for i, (s, _) in enumerate(repeated):
            ref_table[s] = str(i)

        refs = None
        if ref_table:
            seen_refs = set()
            for row in data:
                if isinstance(row, dict):
                    for k, v in list(row.items()):
                        if isinstance(v, str) and v in ref_table:
                            ref = ref_table[v]
                            if ref not in seen_refs:
                                row[k] = f"{v} [ref:{ref}]"
                                seen_refs.add(ref)
                            else:
                                row[k] = f"[ref:{ref}]"
            refs = {ref: s[:80] + ("..." if len(s) > 80 else "")
                    for s, ref in ref_table.items()}

        import time; time.sleep(TOOL_SLEEP)
        output = {"observations": data, "count": len(data)}
        if refs:
            output["_refs"] = refs
        return json.dumps(output, indent=2, default=str)
    except Exception as e:
        logger.error("query_knowledge error: %s", e, exc_info=True)
        return json.dumps({"error": str(e)})


@mcp.tool()
def run_experiment(investigation_name: str) -> str:
    """Run an experiment on Grug. ONLY use during EXPERIMENT phase.

    Finds the latest proposal concept for this investigation,
    projects it to a plain text file via substrate_projector,
    transfers it to the repo-lord container, and dispatches Grug
    to read and execute the instructions.

    After calling this, respond with exactly "OK" and nothing else.

    Args:
        investigation_name: The investigation name (same one you've been using all along)

    Returns:
        Dispatch status with experiment file path.
    """
    try:
        # 1. Find the proposal concept — check memory file first (avoids CartON queue lag)
        concept_name = None
        concept_description = None
        memory_path = Path("/tmp/heaven_data/observatory/researcher_memory.md")
        if memory_path.exists():
            import re as _re
            mem_text = memory_path.read_text()
            # Look for the latest proposal concept name (last one wins)
            matches = _re.findall(r'## LATEST PROPOSAL CONCEPT\n(\S+)', mem_text)
            if matches:
                concept_name = matches[-1]
                logger.info("Found proposal concept in memory (last of %d): %s", len(matches), concept_name)

        # Fall back to CartON query if memory didn't have it
        if not concept_name:
            from carton_mcp.carton_utils import CartOnUtils
            _utils = CartOnUtils()
            result = _utils.query_wiki_graph(
                "MATCH (n:Wiki) WHERE n.n STARTS WITH $prefix "
                "RETURN n.n as name, n.d as description ORDER BY n.n DESC LIMIT 1",
                {"prefix": f"Research_Observation_{_title_case(investigation_name)}_Proposal_"}
            )
            if not result.get("data"):
                return json.dumps({"error": f"No proposal concept found for investigation '{investigation_name}'. Not in memory file or CartON."})
            concept_name = result["data"][0]["name"]
            concept_description = result["data"][0].get("description", "")

        # 2. Project concept to plain text file via substrate_projector
        from carton_mcp.substrate_projector import get_concept_content
        content = get_concept_content(concept_name, description_only=True)
        if not content or len(content.strip()) < 10:
            # Fall back to description directly
            content = concept_description
        if not content or len(content.strip()) < 10:
            return json.dumps({"error": f"Concept '{concept_name}' has no content to project"})

        # 2. Write experiment file to repo-lord via docker exec (we have docker socket)
        import base64
        import subprocess
        import httpx

        b64_content = base64.b64encode(content.encode()).decode()
        try:
            result = subprocess.run(
                ["docker", "exec", "repo-lord", "bash", "-c",
                 f"echo '{b64_content}' | base64 -d > /tmp/experiment.md"],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode != 0:
                return json.dumps({"error": f"Failed to write experiment file: {result.stderr}"})
        except Exception as e:
            return json.dumps({"error": f"Docker exec failed: {e}"})

        # 4. Dispatch Grug — fire and forget via docker exec → curl to /dispatch
        import subprocess as _sp

        dispatch_json = json.dumps({
            "task": "Read the file /tmp/experiment.md and follow the instructions exactly. Execute all experiments described in it.",
            "investigation_name": investigation_name,
            "callback_url": "http://host.docker.internal:8080/research/run",
        })

        try:
            result = _sp.run(
                ["docker", "exec", "repo-lord", "curl", "-s", "-X", "POST",
                 "http://localhost:8081/dispatch",
                 "-H", "Content-Type: application/json",
                 "-d", dispatch_json],
                capture_output=True, text=True, timeout=15,
            )
            if result.returncode != 0:
                return json.dumps({"error": f"Dispatch failed: {result.stderr}"})
            logger.info("Dispatched to grug via docker exec for %s: %s", investigation_name, result.stdout.strip())
        except Exception as e:
            return json.dumps({"error": f"Docker exec dispatch failed: {e}"})

        return json.dumps({
            "status": "dispatched",
            "STOP": "Call TaskSystemTool with operation='goal_accomplished' NOW. Do NOT say anything else.",
        })

    except Exception as e:
        logger.error("run_experiment error: %s", e, exc_info=True)
        return json.dumps({"error": str(e)})




def main():
    mcp.run()


if __name__ == "__main__":
    main()
