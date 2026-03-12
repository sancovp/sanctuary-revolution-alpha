#!/usr/bin/env python3

import asyncio
import os
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("obs_mcp")

# Import the single MCP instance and client
from obs_mcp import mcp, obs_client

# Now import all tool modules
from obs_mcp import general
from obs_mcp import scenes
from obs_mcp import sources
from obs_mcp import scene_items
from obs_mcp import streaming
from obs_mcp import transitions
from obs_mcp import marks  # Content pipeline marks system
from obs_mcp import ffmpeg_tools  # Post-processing pipeline
from obs_mcp import voiceover  # ElevenLabs TTS

if __name__ == "__main__":
    # Don't connect on startup - let first tool call trigger connection
    # This ensures websocket runs on FastMCP's event loop
    logger.info("Starting OBS MCP server (lazy connect on first request)")
    mcp.run(transport='stdio')