#!/usr/bin/env python3

import logging
from mcp.server.fastmcp import FastMCP
from .client import OBSWebSocketClient

# Setup logging
logger = logging.getLogger("obs_server")

# Create FastMCP instance - let it manage its own event loop
mcp = FastMCP("obs_mcp")

# Create client without custom loop - will use running loop when called
obs_client = OBSWebSocketClient()

logger.debug("OBS MCP server created")