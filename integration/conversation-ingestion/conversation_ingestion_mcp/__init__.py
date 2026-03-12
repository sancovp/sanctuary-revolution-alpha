"""
Conversation Ingestion MCP
Semi-automated ingestion system for OpenAI conversation exports
"""
from . import utils
from . import core
from .mcp_server import mcp

__version__ = "0.1.0"

__all__ = ["utils", "core", "mcp"]
