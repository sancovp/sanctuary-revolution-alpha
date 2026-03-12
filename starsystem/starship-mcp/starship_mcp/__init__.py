"""
STARSHIP MCP - Experiential Captain Identity Bridge

Provides the experiential transformation layer between SEED identity and STARLOG operations.
Also manages flight configurations as the captain prepares for their journey.
"""

from .starship_mcp import main, mcp

__version__ = "0.1.0"
__all__ = ["main", "mcp"]