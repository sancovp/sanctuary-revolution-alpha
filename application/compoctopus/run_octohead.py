#!/usr/bin/env python3
"""OctoHead CLI — Compoctopus chat entrypoint.

Uses exec_completion_style (agent_mode=False hermes) + conversation utils
from heaven_base. Same pattern as conversation_chat_app.py but as a CLI.
"""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional

from heaven_base.baseheavenagent import HeavenAgentConfig
from heaven_base.tool_utils.completion_runners import exec_completion_style
from heaven_base.utils.heaven_conversation_utils import start_chat, continue_chat, get_latest_history
from heaven_base.utils.get_env_value import EnvConfigUtil

# Force-load env vars from system_config.sh
EnvConfigUtil._update_env_val()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(name)-30s %(levelname)-8s %(message)s',
)
logger = logging.getLogger(__name__)

import json as _json
_ro_cfg_path = HEAVEN_DATA / "conductor_agent_config.json"
_ro_cfg = {}
if _ro_cfg_path.exists():
    try:
        _ro_cfg = _json.loads(_ro_cfg_path.read_text())
    except (ValueError, OSError):
        pass
MINIMAX_BASE_URL = _ro_cfg.get("extra_model_kwargs", {}).get("anthropic_api_url", "")
HEAVEN_DATA = Path(os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data"))
STATE_FILE = HEAVEN_DATA / "octohead_conversation.json"


def _build_agent_config():
    """Build OctoHead HeavenAgentConfig."""
    from compoctopus.octohead import make_octohead
    return make_octohead()



def _load_state() -> dict:
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except Exception:
        pass
    return {"conversation_id": None}


def _save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state))


def _extract_response(result: dict) -> str:
    """Extract text response from exec_completion_style result, including tool usage."""
    msgs = result.get("messages", [])
    if not msgs:
        return ""

    parts = []

    # Show tool calls from all messages
    for msg in msgs:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role == "assistant" and isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    tool_name = block.get("name", "unknown")
                    parts.append(f"🔧 {tool_name}")

    # Extract final text from last message
    last = msgs[-1]
    content = last.get("content", "")
    if isinstance(content, list):
        text_parts = [b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"]
        text = "\n".join(text_parts)
    else:
        text = str(content)

    if parts:
        return "\n".join(parts) + "\n\n" + text
    return text


async def start_new_chat(message: str, config: HeavenAgentConfig) -> Dict[str, Any]:
    """Start a new conversation. Returns response + conversation state."""
    result = await exec_completion_style(
        prompt=message,
        agent=config,
    )

    history_id = result.get("history_id")
    response = _extract_response(result)

    if not history_id:
        return {"response": response or "(no response)", "error": "No history_id returned"}

    conv = start_chat(
        title="OctoHead — Compoctopus",
        first_history_id=history_id,
        agent_name="octohead",
        tags=["compoctopus", "octohead"],
    )

    state = {"conversation_id": conv["conversation_id"]}
    _save_state(state)

    return {"response": response, "conversation_id": conv["conversation_id"]}


async def continue_existing_chat(message: str, conversation_id: str, config: HeavenAgentConfig) -> Dict[str, Any]:
    """Continue an existing conversation."""
    latest_history_id = get_latest_history(conversation_id)

    result = await exec_completion_style(
        prompt=message,
        agent=config,
        history_id=latest_history_id,
    )

    history_id = result.get("history_id")
    response = _extract_response(result)

    if history_id:
        continue_chat(conversation_id, history_id)

    return {"response": response, "conversation_id": conversation_id}


async def interactive_loop():
    """Interactive CLI chat loop."""
    config = _build_agent_config()
    state = _load_state()
    conversation_id = state.get("conversation_id")

    print(f"\n{'='*60}")
    print(f"🐙 OctoHead — Compoctopus")
    print(f"{'='*60}")
    if conversation_id:
        print(f"Resuming: {conversation_id[:16]}...")
    else:
        print(f"New conversation")
    print(f"Commands: 'quit', 'new'")
    print(f"{'='*60}\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n👋 Bye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit"):
            break
        if user_input.lower() == "new":
            conversation_id = None
            _save_state({"conversation_id": None})
            print("🔄 New conversation.\n")
            continue

        try:
            if conversation_id:
                result = await continue_existing_chat(user_input, conversation_id, config)
            else:
                result = await start_new_chat(user_input, config)

            conversation_id = result.get("conversation_id")
            response = result.get("response", "")
            print(f"\n🐙 {response}\n" if response else "\n🐙 (tool output only)\n")

        except Exception as e:
            logger.error("Error: %s", e, exc_info=True)
            print(f"\n❌ {e}\n")


async def one_shot(message: str):
    """Non-interactive single message."""
    config = _build_agent_config()
    state = _load_state()
    conversation_id = state.get("conversation_id")

    if conversation_id:
        result = await continue_existing_chat(message, conversation_id, config)
    else:
        result = await start_new_chat(message, config)

    print(result.get("response", ""))


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="OctoHead — Compoctopus chat")
    parser.add_argument("--message", "-m", help="Non-interactive: send one message")
    parser.add_argument("--new", action="store_true", help="Start fresh conversation")
    args = parser.parse_args()

    if args.new:
        _save_state({"conversation_id": None})

    if args.message:
        asyncio.run(one_shot(args.message))
    else:
        asyncio.run(interactive_loop())
