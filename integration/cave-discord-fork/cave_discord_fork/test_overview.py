#!/usr/bin/env python3
"""
Test the overview posting functionality.
"""

import os
import sys
sys.path.insert(0, '/Users/isaacwr/Desktop/claude_code/cave_discord_fork')

from discord_mcp_client import DiscordMCPClient, CAVEDiscordPoster
from core import JourneyCore

# Example: Post domain overview
def test_domain_overview():
    TOKEN = os.environ.get("DISCORD_TOKEN", "")
    GUILD_ID = os.environ.get("DISCORD_GUILD_ID", "")

    if not TOKEN or not GUILD_ID:
        print("Set DISCORD_TOKEN and DISCORD_GUILD_ID env vars")
        return

    client = DiscordMCPClient(TOKEN, GUILD_ID)
    poster = CAVEDiscordPoster(client)

    try:
        client.start()
        print("Connected to Discord MCP")

        # Post the domain overview
        result = poster.post_domain_overview(
            domain="PAIAB",
            pain_herald="my AI kept going in circles",
            inciting_incident="I realized context windows weren't the problem",
            first_framework_discovery=(
                "The first breakthrough was understanding that AI doesn't need "
                "bigger context - it needs explicit typing. Once I built the first "
                "typed workflow, everything clicked. The agent stopped hallucinating "
                "capabilities and started executing reliably."
            ),
            domain_mission="build AI that compounds",
            pain_point="context loss and capability amnesia",
            prerequisites=[
                "use Claude Code daily",
                "write good prompts",
                "understand agent architecture"
            ],
            system_name="PAIA",
            dream_achieved="agents that extend themselves",
            benefits=[
                "no more context rot",
                "workflows that persist",
                "compound intelligence"
            ]
        )

        print(f"\nPosted overview: {result}")

    finally:
        client.stop()


# Example: Post journey summary
def test_journey_summary():
    TOKEN = os.environ.get("DISCORD_TOKEN", "")
    GUILD_ID = os.environ.get("DISCORD_GUILD_ID", "")

    if not TOKEN or not GUILD_ID:
        print("Set DISCORD_TOKEN and DISCORD_GUILD_ID env vars")
        return

    client = DiscordMCPClient(TOKEN, GUILD_ID)
    poster = CAVEDiscordPoster(client)

    try:
        client.start()
        print("Connected to Discord MCP")

        # Create example journey
        journey = JourneyCore(
            journey_name="Understanding MCP Architecture",
            domain="PAIAB",
            status_quo="I was manually writing tool wrappers for every integration",
            obstacle="Each new service meant rebuilding the integration layer",
            overcome="I discovered MCP and realized tools could be composable",
            accomplishment="Now services plug in via MCP and the agent discovers them automatically",
            the_boon="MCP = composable tool interfaces. Agents discover capabilities at runtime."
        )

        # Post journey summary to #overview
        result = poster.post_journey_summary(journey)

        print(f"\nPosted journey summary: {result}")

    finally:
        client.stop()


if __name__ == "__main__":
    print("Test 1: Domain Overview")
    test_domain_overview()

    print("\n" + "="*60)
    print("Test 2: Journey Summary")
    test_journey_summary()
