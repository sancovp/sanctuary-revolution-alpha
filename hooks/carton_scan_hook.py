#!/usr/bin/env python3
"""
CartON Scan Hook - Auto-inject GPS coordinates on user message
"""

import json
import os
import sys
from pathlib import Path

def is_gps_enabled():
    """Check if GPS auto-injection is enabled"""
    try:
        heaven_data_dir = os.getenv('HEAVEN_DATA_DIR', '/tmp/heaven_data')
        gps_flag_file = Path(heaven_data_dir) / 'carton_gps_enabled'
        return gps_flag_file.exists()
    except:
        return False

try:
    from carton_mcp.carton_utils import CartOnUtils
except ImportError as e:
    # Skip silently if import fails
    try:
        hook_data = json.load(sys.stdin)
        print(json.dumps(hook_data))
    except:
        pass
    sys.exit(0)

def main():
    try:
        hook_data = json.load(sys.stdin)
        
        # Check if GPS is enabled
        if not is_gps_enabled():
            # GPS disabled - pass through without modification
            print(json.dumps(hook_data))
            sys.exit(0)
        
        user_message = hook_data.get('prompt', '')

        if not user_message or len(user_message) < 10:
            print(json.dumps(hook_data))
            sys.exit(0)

        # Set environment variables
        os.environ.setdefault('HEAVEN_DATA_DIR', '/tmp/heaven_data')
        os.environ.setdefault('NEO4J_URI', 'bolt://host.docker.internal:7687')
        os.environ.setdefault('NEO4J_USER', 'neo4j')
        os.environ.setdefault('NEO4J_PASSWORD', 'password')
        os.environ.setdefault('GITHUB_PAT', os.environ.get('GITHUB_PAT', ''))
        os.environ.setdefault('REPO_URL', 'https://github.com/sancovp/private_wiki')

        # Get OPENAI_API_KEY from claude config (nested in mcpServers)
        try:
            claude_config_path = '/home/GOD/.claude.json'
            with open(claude_config_path, 'r') as f:
                config = json.load(f)
                # Check mcpServers for API key
                for server_name, server_config in config.get('mcpServers', {}).items():
                    if 'env' in server_config and 'OPENAI_API_KEY' in server_config['env']:
                        os.environ['OPENAI_API_KEY'] = server_config['env']['OPENAI_API_KEY']
                        break
        except Exception as e:
            # If can't get key, skip scan
            print(json.dumps(hook_data))
            sys.exit(0)

        # Run scan
        utils = CartOnUtils()
        gps = utils.scan_carton(user_message, max_results=10)

        # Inject GPS using correct hook format
        result = {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": gps
            }
        }

        print(json.dumps(result))
        sys.exit(0)

    except Exception as e:
        # Fail silently, pass through original data
        try:
            hook_data = json.load(sys.stdin)
            print(json.dumps(hook_data))
        except:
            pass
        sys.exit(0)

if __name__ == "__main__":
    main()
