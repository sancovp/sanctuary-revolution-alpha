#!/usr/bin/env python3
"""
CogLog Hook - Extract semantic addresses from assistant responses and log to CartON

PreCompact hook that fires before context compaction, extracts ALL 🧠 lines
from the entire conversation, and queues observations to CartON Timeline.
"""

try:
    with open('/tmp/coglog_hook_debug.log', 'a') as f:
        f.write("SCRIPT STARTED\n")
except:
    pass

import json
import sys
import re
from datetime import datetime
from pathlib import Path

# Debug at module load time
with open('/tmp/coglog_hook_debug.log', 'a') as f:
    f.write(f"{datetime.now()}: Module loaded\n")

def main():
    try:
        # Debug: log that hook was called
        with open('/tmp/coglog_hook_debug.log', 'a') as f:
            f.write(f"{datetime.now()}: Hook called\n")

        # Read hook input from stdin
        hook_data = json.load(sys.stdin)

        # Check if this is a stop hook continuation (prevent infinite loops)
        if hook_data.get('stop_hook_active'):
            sys.exit(0)

        transcript_path = hook_data.get('transcript_path')
        if not transcript_path:
            sys.exit(0)

        # Read transcript JSONL
        transcript_file = Path(transcript_path)
        if not transcript_file.exists():
            sys.exit(0)

        # Collect ALL assistant messages from entire conversation
        all_assistant_content = []
        with open(transcript_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if entry.get('type') == 'assistant':
                        # Get the message content
                        message = entry.get('message', {})
                        content = message.get('content', [])
                        # Extract text from content blocks
                        for block in content:
                            if isinstance(block, dict) and block.get('type') == 'text':
                                all_assistant_content.append(block.get('text', ''))
                            elif isinstance(block, str):
                                all_assistant_content.append(block)
                except json.JSONDecodeError:
                    continue

        if not all_assistant_content:
            sys.exit(0)

        # Extract 🧠 lines (semantic addresses) from ALL messages
        brain_pattern = re.compile(r'🧠\s*(.+?)(?:\n|$)')
        full_text = '\n'.join(all_assistant_content)
        matches = brain_pattern.findall(full_text)

        # Deduplicate while preserving order
        seen = set()
        unique_matches = []
        for m in matches:
            if m not in seen:
                seen.add(m)
                unique_matches.append(m)
        matches = unique_matches

        if not matches:
            sys.exit(0)

        # Import carton observation function
        try:
            from carton_mcp.add_concept_tool import add_observation
        except ImportError:
            # If can't import, skip silently
            sys.exit(0)

        # Set required environment variables
        import os
        os.environ.setdefault('HEAVEN_DATA_DIR', '/tmp/heaven_data')
        os.environ.setdefault('NEO4J_URI', 'bolt://host.docker.internal:7687')
        os.environ.setdefault('NEO4J_USER', 'neo4j')
        os.environ.setdefault('NEO4J_PASSWORD', 'password')
        os.environ.setdefault('GITHUB_PAT', os.environ.get('GITHUB_PAT', ''))
        os.environ.setdefault('REPO_URL', 'https://github.com/sancovp/private_wiki')

        # Process each semantic address
        timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")

        for i, semantic_addr in enumerate(matches):
            semantic_addr = semantic_addr.strip()
            if not semantic_addr:
                continue

            # Parse semantic address to extract domain info
            # Format: domain/subdomain/topic/phase
            parts = semantic_addr.split('/')
            domain = parts[0] if len(parts) > 0 else "unknown"

            # Map domain to personal_domain enum
            personal_domain_map = {
                'funnel': 'funnel',
                'potential_offers': 'potential_offers',
                'discord': 'discord',
                'frameworks': 'frameworks',
                'misc_ideas': 'misc_ideas',
                'personal_life_stuff': 'personal_life_stuff',
                'real_job_stuff': 'real_job_stuff',
                'gnosys_kit': 'frameworks',
                'carton': 'frameworks',
                'starship': 'frameworks',
                'starlog': 'frameworks',
                'twi': 'frameworks',
                'paiab': 'frameworks',
                'sanctum': 'frameworks',
                'cave': 'funnel',
            }
            personal_domain = personal_domain_map.get(domain.lower(), 'misc_ideas')

            # Create unique entry name
            entry_name = f"{timestamp}_Cog_Log_Entry" if i == 0 else f"{timestamp}_Cog_Log_Entry_{i}"

            # Build observation with all 5 required tags
            observation_data = {
                "insight_moment": [],
                "struggle_point": [],
                "daily_action": [{
                    "name": entry_name,
                    "description": f"Cognitive log entry: {semantic_addr}",
                    "relationships": [
                        {"relationship": "is_a", "related": ["Cog_Log_Entry"]},
                        {"relationship": "part_of", "related": ["IO_Pairs"]},
                        {"relationship": "has_personal_domain", "related": [personal_domain]},
                        {"relationship": "has_actual_domain", "related": ["Cognitive_Tracking"]}
                    ]
                }],
                "implementation": [],
                "emotional_state": [],
                "confidence": 0.8
            }

            # Queue the observation (non-blocking)
            add_observation(observation_data)

        sys.exit(0)

    except Exception as e:
        # Fail silently - don't block Claude
        sys.exit(0)

if __name__ == "__main__":
    main()
