"""
Python client for saseq/discord-mcp container.

Wraps the MCP container via subprocess, communicating via JSON-RPC over stdio.
"""

import subprocess
import json
import os
from typing import Optional, Dict, Any, List


class DiscordMCPClient:
    """Client to call Discord MCP container via subprocess."""
    
    def __init__(
        self,
        token: str,
        guild_id: str,
        image: str = "saseq/discord-mcp:latest"
    ):
        self.token = token
        self.guild_id = guild_id
        self.image = image
        self.process: Optional[subprocess.Popen] = None
        self._request_id = 0
    
    def _get_request_id(self) -> int:
        self._request_id += 1
        return self._request_id
    
    def start(self):
        """Start the MCP container."""
        self.process = subprocess.Popen(
            [
                "docker", "run", "--rm", "-i",
                "-e", f"DISCORD_TOKEN={self.token}",
                "-e", f"DISCORD_GUILD_ID={self.guild_id}",
                self.image
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        # Initialize MCP connection
        self._send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "cave-discord-client", "version": "0.1.0"}
        })
        # Send initialized notification
        self._send_notification("notifications/initialized", {})
        # Wait for Discord bot to connect to gateway
        import time
        time.sleep(5)
    
    def stop(self):
        """Stop the MCP container."""
        if self.process:
            self.process.terminate()
            self.process.wait()
            self.process = None
    
    def _send_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Send JSON-RPC request and get response."""
        if not self.process:
            raise RuntimeError("Client not started")
        
        request = {
            "jsonrpc": "2.0",
            "id": self._get_request_id(),
            "method": method,
            "params": params
        }
        
        self.process.stdin.write(json.dumps(request) + "\n")
        self.process.stdin.flush()
        
        response_line = self.process.stdout.readline()
        if not response_line:
            raise RuntimeError("No response from MCP")
        
        return json.loads(response_line)
    
    def _send_notification(self, method: str, params: Dict[str, Any]):
        """Send JSON-RPC notification (no response expected)."""
        if not self.process:
            raise RuntimeError("Client not started")
        
        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params
        }
        
        self.process.stdin.write(json.dumps(notification) + "\n")
        self.process.stdin.flush()
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools from the MCP."""
        response = self._send_request("tools/list", {})
        return response.get("result", {}).get("tools", [])
    
    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on the MCP."""
        response = self._send_request("tools/call", {
            "name": name,
            "arguments": arguments
        })
        return response.get("result", {})
    
    # Convenience methods for Discord operations
    def send_message(self, channel_id: str, content: str) -> Dict[str, Any]:
        """Send a message to a Discord channel."""
        return self.call_tool("send_message", {
            "channelId": channel_id,
            "message": content
        })
    
    def create_channel(
        self,
        name: str,
        channel_type: int = 0,  # 0 = text, 2 = voice, 4 = category
        parent_id: Optional[str] = None,
        topic: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new channel."""
        args = {"name": name, "type": channel_type}
        if parent_id:
            args["parent_id"] = parent_id
        if topic:
            args["topic"] = topic
        return self.call_tool("create_channel", args)
    
    def list_channels(self) -> Dict[str, Any]:
        """List all channels in the guild."""
        return self.call_tool("list_channels", {"guildId": self.guild_id})

    def find_channel(self, name: str) -> Dict[str, Any]:
        """Find a channel by name."""
        return self.call_tool("find_channel", {"guildId": self.guild_id, "channelName": name})

    def create_category(self, name: str) -> Dict[str, Any]:
        """Create a category."""
        return self.call_tool("create_category", {"guildId": self.guild_id, "name": name})

    def create_text_channel(
        self,
        name: str,
        category_id: Optional[str] = None,
        topic: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a text channel."""
        args = {"guildId": self.guild_id, "name": name}
        if category_id:
            args["categoryId"] = category_id
        if topic:
            args["topic"] = topic
        return self.call_tool("create_text_channel", args)


class CAVEDiscordPoster:
    """
    Posts CAVE content to Discord using templates.

    Integrates JourneyCore → ContentSuite → Discord channels.
    """

    def __init__(self, client: DiscordMCPClient):
        self.client = client
        # Channel IDs get cached after first lookup
        self._channel_cache: Dict[str, str] = {}

    def _get_or_create_channel(self, domain: str, channel_type: str) -> str:
        """Get channel ID, creating domain structure if needed."""
        cache_key = f"{domain}_{channel_type}"
        if cache_key in self._channel_cache:
            return self._channel_cache[cache_key]

        channel_name = f"{domain.lower()}-{channel_type}"
        result = self.client.find_channel(channel_name)

        if result.get("isError"):
            # Create the domain category and channel
            cat_result = self.client.create_category(domain)
            # Extract category ID from result and create channel
            # For now, just create the channel
            ch_result = self.client.create_text_channel(channel_name)
            # Would extract channel_id from ch_result
            channel_id = "TODO"  # Parse from result
        else:
            channel_id = "TODO"  # Parse from result

        self._channel_cache[cache_key] = channel_id
        return channel_id

    def post_journey(self, core: 'JourneyCore') -> Dict[str, Any]:
        """
        Post a journey to the appropriate Discord channel.

        Creates: DOMAIN → #journeys channel → formatted post
        """
        from core import JourneyCore
        from renderers import DiscordJourneyPost

        # Render the content
        post = DiscordJourneyPost.from_core(core)
        content = post.render()

        # Find or create the journeys channel for this domain
        channel_name = f"{core.domain.lower()}-journeys"

        # Try to find existing channel
        find_result = self.client.find_channel(channel_name)

        if find_result.get("isError"):
            # Channel doesn't exist - would need to create domain structure
            return {"error": f"Channel {channel_name} not found. Create domain structure first."}

        # Extract channel_id from find_result and post
        # The actual structure depends on the MCP's response format
        channel_id = self._extract_channel_id(find_result)

        if not channel_id:
            return {"error": "Could not extract channel_id from find_channel result"}

        return self.client.send_message(channel_id, content)

    def _extract_channel_id(self, find_result: Dict[str, Any]) -> Optional[str]:
        """Extract channel ID from find_channel response."""
        # MCP returns: {"content": [{"type": "text", "text": "..."}]}
        # Need to parse the text to get channel ID
        content = find_result.get("content", [])
        if content and isinstance(content, list):
            text = content[0].get("text", "")
            # Parse channel ID from text - format TBD based on actual response
            # For now return the raw text for debugging
            return text if text and not "not found" in text.lower() else None
        return None

    def setup_domain_structure(self, domain: str) -> Dict[str, Any]:
        """
        Create the full domain structure:

        📂 DOMAIN
        ├── #overview
        ├── #journeys
        └── #frameworks (locked)
        """
        results = {}

        # Create category
        cat_result = self.client.create_category(domain)
        results["category"] = cat_result

        # Create channels
        for channel in ["overview", "journeys", "frameworks"]:
            ch_result = self.client.create_text_channel(
                f"{domain.lower()}-{channel}",
                topic=f"{domain} {channel}"
            )
            results[channel] = ch_result

        return results


# Test it
if __name__ == "__main__":
    # These would come from env in production
    TOKEN = os.environ.get("DISCORD_TOKEN", "")
    GUILD_ID = os.environ.get("DISCORD_GUILD_ID", "")
    
    if not TOKEN or not GUILD_ID:
        print("Set DISCORD_TOKEN and DISCORD_GUILD_ID env vars")
        exit(1)
    
    client = DiscordMCPClient(TOKEN, GUILD_ID)
    try:
        client.start()
        print("Connected to Discord MCP")
        
        # List available tools
        tools = client.list_tools()
        print(f"\nAvailable tools: {[t['name'] for t in tools]}")
        
        # List channels
        channels = client.list_channels()
        print(f"\nChannels: {channels}")
        
    finally:
        client.stop()
