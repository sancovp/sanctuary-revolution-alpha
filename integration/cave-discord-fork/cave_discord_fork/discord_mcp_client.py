"""
Python client for saseq/discord-mcp container.

Wraps the MCP container via subprocess, communicating via JSON-RPC over stdio.
"""

import subprocess
import json
import os
import re
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
        return self.call_tool("list_channels", {})

    def find_channel(self, name: str) -> Dict[str, Any]:
        """Find a channel by name."""
        return self.call_tool("find_channel", {"channelName": name})

    def create_category(self, name: str) -> Dict[str, Any]:
        """Create a category."""
        return self.call_tool("create_category", {"name": name})

    def find_category(self, name: str) -> Dict[str, Any]:
        """Find a category by name."""
        return self.call_tool("find_category", {"categoryName": name})

    def create_text_channel(
        self,
        name: str,
        category_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a text channel."""
        args = {"name": name}
        if category_id:
            args["categoryId"] = category_id
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

    def _get_or_create_channel(self, domain: str, channel_type: str) -> Optional[str]:
        """Get channel ID, creating domain structure if needed."""
        cache_key = f"{domain}_{channel_type}"
        if cache_key in self._channel_cache:
            return self._channel_cache[cache_key]

        channel_name = f"{domain.lower()}-{channel_type}"
        result = self.client.find_channel(channel_name)

        channel_id = self._extract_id(result)

        if not channel_id:
            # Channel doesn't exist - create domain structure
            # create_category doesn't return ID, so we find it after
            self.client.create_category(domain)
            cat_find = self.client.find_category(domain)
            category_id = self._extract_id(cat_find)

            ch_result = self.client.create_text_channel(
                channel_name,
                category_id=category_id
            )
            channel_id = self._extract_id(ch_result)

        if channel_id:
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

        # Get or create the journeys channel for this domain
        channel_id = self._get_or_create_channel(core.domain, "journeys")

        if not channel_id:
            return {"error": f"Could not find or create channel for {core.domain}"}

        return self.client.send_message(channel_id, content)

    def post_domain_overview(
        self,
        domain: str,
        pain_herald: str,
        inciting_incident: str,
        first_framework_discovery: str,
        domain_mission: str,
        pain_point: str,
        prerequisites: List[str],
        system_name: str,
        dream_achieved: str,
        benefits: List[str]
    ) -> Dict[str, Any]:
        """
        Post the main domain overview narrative to #overview channel.

        This should be the first/pinned post in the overview channel.
        """
        from renderers import DomainOverviewPost

        post = DomainOverviewPost(
            domain=domain,
            pain_herald=pain_herald,
            inciting_incident=inciting_incident,
            first_framework_discovery=first_framework_discovery,
            domain_mission=domain_mission,
            pain_point=pain_point,
            prerequisites=prerequisites,
            system_name=system_name,
            dream_achieved=dream_achieved,
            benefits=benefits
        )
        content = post.render()

        # Get or create the overview channel for this domain
        channel_id = self._get_or_create_channel(domain, "overview")

        if not channel_id:
            return {"error": f"Could not find or create overview channel for {domain}"}

        return self.client.send_message(channel_id, content)

    def post_journey_summary(self, core: 'JourneyCore') -> Dict[str, Any]:
        """
        Post a journey/framework summary to #overview channel.

        Call this after posting to #journeys to add the summary to overview.
        """
        from core import JourneyCore
        from renderers import JourneySummaryPost

        post = JourneySummaryPost.from_core(core)
        content = post.render()

        # Get or create the overview channel for this domain
        channel_id = self._get_or_create_channel(core.domain, "overview")

        if not channel_id:
            return {"error": f"Could not find or create overview channel for {core.domain}"}

        return self.client.send_message(channel_id, content)

    def _extract_id(self, result: Dict[str, Any]) -> Optional[str]:
        """
        Extract ID from MCP tool response.

        Response formats from saseq/discord-mcp:
        - find_channel: "Retrieved TEXT channel: name (ID: 123456789)"
        - create_text_channel: "Created new text channel: name (ID: 123456789)"
        - find_category: "Retrieved category: name, with ID: 123456789"
        - create_category: "Created new category: name" (NO ID - need find_category after)
        """
        content = result.get("content", [])
        if content and isinstance(content, list):
            text = content[0].get("text", "")
            # Try (ID: xxx) format first (channels)
            match = re.search(r'\(ID:\s*(\d+)\)', text)
            if match:
                return match.group(1)
            # Try "with ID: xxx" format (categories)
            match = re.search(r'with ID:\s*(\d+)', text)
            if match:
                return match.group(1)
        return None

    def setup_domain_structure(self, domain: str) -> Dict[str, Any]:
        """
        Create the full domain structure:

        📂 DOMAIN
        ├── #overview
        ├── #journeys
        └── #frameworks (locked)

        Returns dict with category_id and channel_ids.
        """
        results = {"domain": domain}

        # Create category (doesn't return ID, so we find it after)
        self.client.create_category(domain)
        cat_find = self.client.find_category(domain)
        category_id = self._extract_id(cat_find)
        results["category_id"] = category_id

        # Create channels under category
        channel_ids = {}
        for channel in ["overview", "journeys", "frameworks"]:
            channel_name = f"{domain.lower()}-{channel}"
            ch_result = self.client.create_text_channel(
                channel_name,
                category_id=category_id,
            )
            channel_id = self._extract_id(ch_result)
            channel_ids[channel] = channel_id

            # Cache for later use
            self._channel_cache[f"{domain}_{channel}"] = channel_id

        results["channels"] = channel_ids
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
