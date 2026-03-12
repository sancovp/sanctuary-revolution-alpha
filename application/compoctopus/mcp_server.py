#!/usr/bin/env python3
"""Compoctopus MCP — chat with OctoHead via MCP.

Single tool: compoctopus(message) → sends message to OctoHead and returns response.
"""

from __future__ import annotations

import asyncio
import json
import logging

from mcp.server.fastmcp import FastMCP

from run_octohead import (
    _build_agent_config,
    _load_state,
    _save_state,
    start_new_chat,
    continue_existing_chat,
)

# ─── Setup ─────────────────────────────────────────────────────────

logger = logging.getLogger("compoctopus-mcp")
logging.basicConfig(level=logging.INFO)

mcp = FastMCP("compoctopus", "Compoctopus OctoHead — the self-compiling agent compiler")

_config = _build_agent_config()

# ─── Tool ──────────────────────────────────────────────────────────

@mcp.tool()
async def compoctopus(message: str) -> str:
    """Talk to OctoHead — the Compoctopus chat interface.

    OctoHead is the self-compiling agent compiler. It guides you through
    designing, specifying, and building agents via PRDs (Product Requirement
    Documents). It operates in phases:

      1. Talk about system/design
      2. Conceptualize PRD
      3. Refine PRD
      4. Queue PRD (CreatePRD → BuildPRD)
      5. Review results / Go Auto

    Conversations persist across calls automatically.

    Args:
        message: Your message to OctoHead (natural language)

    Returns:
        OctoHead's response
    """
    if not message or not message.strip():
        return json.dumps({"error": "Empty message", "hint": "Send a message to OctoHead"})

    state = _load_state()
    conversation_id = state.get("conversation_id")

    try:
        if conversation_id:
            result = await continue_existing_chat(message.strip(), conversation_id, _config)
        else:
            result = await start_new_chat(message.strip(), _config)

        return json.dumps({
            "response": result.get("response", ""),
            "conversation_id": result.get("conversation_id"),
        }, indent=2)

    except Exception as e:
        logger.error("OctoHead error: %s", e, exc_info=True)
        return json.dumps({"error": str(e)})


@mcp.tool()
async def compoctopus_new_chat() -> str:
    """Start a fresh OctoHead conversation.

    Resets the conversation state so the next compoctopus() call
    begins a new session instead of continuing the previous one.

    Returns:
        Confirmation message
    """
    _save_state({"conversation_id": None})
    return json.dumps({"status": "ok", "message": "New conversation started"})


# ─── Main ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
