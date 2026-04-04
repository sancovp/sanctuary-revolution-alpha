#!/usr/bin/env python3
"""Observatory MCP — research queue orchestration for Conductor.

Tools:
- queue_research: add topic to queue, ensure researcher is processing
- get_research_queue: view queue status
- research_status: check CartON for investigation results

The Researcher is an SDNAC with tools (CartON + bash for docker exec into Grug).
It processes queue items through the scientific method phases.
Conductor/user review results externally.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("observatory-mcp")
logging.basicConfig(level=logging.INFO)

mcp = FastMCP("observatory", "Observatory MCP — research queue orchestration")

QUEUE_DIR = Path("/tmp/heaven_data/observatory")
QUEUE_FILE = QUEUE_DIR / "research_queue.json"


def _load_queue() -> list:
    if QUEUE_FILE.exists():
        return json.loads(QUEUE_FILE.read_text())
    return []


def _save_queue(queue: list):
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    QUEUE_FILE.write_text(json.dumps(queue, indent=2))


# ─── Tools ─────────────────────────────────────────────────────────

@mcp.tool()
def queue_research(topic: str, domain: str, hint: str = "") -> str:
    """Queue a research topic for investigation.

    Adds topic to the research queue. The Researcher SDNAC processes
    queue items through the scientific method (observe → hypothesize →
    propose → experiment → analyze), using CartON for persistence and
    docker exec into repo-lord (Grug container) for code execution.

    Args:
        topic: What to research (natural language description)
        domain: Research domain (e.g. Sleep_Architecture, Mcp_Integration)
        hint: Optional hint or direction for the researcher

    Returns:
        Queue confirmation with investigation name
    """
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    investigation_name = "Research_Investigation_" + "_".join(
        word.capitalize() for word in topic.split()[:5]
    ) + f"_{now[:8]}"

    entry = {
        "topic": topic,
        "domain": domain,
        "hint": hint,
        "investigation_name": investigation_name,
        "queued_at": now,
        "status": "pending",
    }

    queue = _load_queue()
    queue.append(entry)
    _save_queue(queue)

    return json.dumps({
        "status": "queued",
        "investigation_name": investigation_name,
        "domain": domain,
        "topic": topic,
        "queue_position": len(queue),
    }, indent=2)


@mcp.tool()
def get_research_queue() -> str:
    """View the current research queue.

    Returns:
        List of queued research topics with status
    """
    queue = _load_queue()
    if not queue:
        return json.dumps({"status": "empty", "message": "No research queued"})
    return json.dumps({"queue": queue, "count": len(queue)}, indent=2)


@mcp.tool()
def research_status(investigation_name: str) -> str:
    """Check status of a research investigation.

    Queries CartON for all observations under the given investigation.

    Args:
        investigation_name: The investigation to check

    Returns:
        Phases completed and their observation summaries
    """
    try:
        from carton_mcp.carton_utils import CartOnUtils
        utils = CartOnUtils()

        query = """
        MATCH (n:Wiki)-[r]->(inv:Wiki {n: $investigation_name})
        WHERE type(r) = 'PART_OF'
        RETURN n.n AS name, n.d AS description
        ORDER BY n.n
        """
        result = utils.query_wiki_graph(query, parameters={"investigation_name": investigation_name})
        if not result.get("success") or not result.get("data"):
            return json.dumps({"status": "not_found", "investigation": investigation_name})

        return json.dumps({
            "investigation": investigation_name,
            "concepts": [{"name": r["name"], "description": r.get("description", "")[:200]} for r in result["data"]],
            "count": len(result["data"]),
        }, indent=2)

    except Exception as e:
        logger.error("research_status error: %s", e, exc_info=True)
        return json.dumps({"error": str(e)})


@mcp.tool()
async def run_next_research() -> str:
    """Dispatch next pending research topic to sancrev for async execution.

    POSTs to sancrev's /research/run endpoint which runs the Researcher
    SDNAC as an async task. Returns immediately — does NOT block the caller.

    Returns:
        Dispatch confirmation or error
    """
    import httpx

    sancrev_port = int(os.environ.get("CAVE_PORT", "8080"))
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"http://localhost:{sancrev_port}/research/run",
                timeout=10.0,
            )
            return json.dumps(resp.json(), indent=2)
    except Exception as e:
        logger.error("run_next_research dispatch error: %s", e, exc_info=True)
        return json.dumps({"error": f"Failed to dispatch to sancrev: {e}"})


# ─── Future: run_autoresearch ──────────────────────────────────────
#
# run_autoresearch will be a DUO that meta-researches the Researcher itself.
# The DUO pattern makes sense here because it has an OVP that observes
# how the Researcher works and optimizes it over time.
#
# This is DIFFERENT from queue_research/run_next_research which just
# processes queue items. Autoresearch is a self-improving meta-system.
#
# Not implemented yet. When ready:
# - Ariadne = Researcher (drives scientific method)
# - Poimandres = Researcher's own process (what it's improving)
# - OVP = meta-reviewer that evaluates research quality and tunes Researcher
#


if __name__ == "__main__":
    mcp.run()
