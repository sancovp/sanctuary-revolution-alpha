"""
Console script entry point for conversation-ingestion MCP server
"""
from .mcp_server import mcp


def main():
    """Start the MCP server"""
    mcp.run()


if __name__ == "__main__":
    main()
