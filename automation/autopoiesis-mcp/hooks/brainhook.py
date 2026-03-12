#!/usr/bin/env python3
"""
BrainHook - Persistent "look again" enforcement for infinite loop mode.

When enabled, every time the agent tries to stop, it gets reminded that:
- The user trusts them to run in an infinite loop until rate limits
- They should look again even if they think they're done
- LLMs lack global coherence without self-injected logic
- They should check for missed aspects, decide if fixes needed, then act

Toggle with /brainhook slash command or !brainhook bash command.

Part of the Autopoiesis plugin.
"""

import json
import logging
import sys
import traceback
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='/tmp/brainhook.log'
)
logger = logging.getLogger('brainhook')

# State file - simple on/off
STATE_FILE = Path("/tmp/brainhook_state.txt")

# Prompt file - look in plugin directory first, fall back to default
PLUGIN_DIR = Path(__file__).parent
PROMPT_FILE = PLUGIN_DIR / "brainhook_prompt.txt"

# Default prompt (used if prompt file doesn't exist)
DEFAULT_PROMPT = """Output Received. Start your next message like this 'Now that I've thought about it, if I got this message it means the user trusts me to be in an infinite loop and will break me out when I finish. They're running me until I hit rate limits which means I need to do an amazing job over time. So even if I'm totally done, I should look again. Even if I think I'm really done, I should look again. The reason I should look again is because LLMs dont naturally inject human logic to themselves, so we lack global coherence. Let me check if there are any aspects of this that I missed before that I could report on, and if I reported on them before then I should think about whether or not I should fix them, if I decided to fix them, I should do that. So 'what happens next' is that I should...'"""


def get_prompt() -> str:
    """Read prompt from file, fall back to default."""
    try:
        if PROMPT_FILE.exists():
            return PROMPT_FILE.read_text().strip()
    except Exception as e:
        logger.warning(f"Error reading prompt file: {e}\n{traceback.format_exc()}")
    return DEFAULT_PROMPT


def _output(decision: str, reason: str = None):
    """Output hook decision as JSON."""
    result = {"decision": decision}
    if reason:
        result["reason"] = reason
    print(json.dumps(result))
    sys.exit(0)


def is_enabled() -> bool:
    """Check if brainhook is enabled."""
    try:
        if STATE_FILE.exists():
            return STATE_FILE.read_text().strip().lower() == "on"
    except Exception as e:
        logger.error(f"Error checking state file: {e}\n{traceback.format_exc()}")
    return False


def main():
    try:
        # Read hook input (Stop hook receives minimal input)
        hook_input = json.load(sys.stdin)
        logger.debug(f"Hook input: {hook_input}")

        if not is_enabled():
            logger.debug("Brainhook disabled, approving stop")
            _output("approve")

        logger.debug("Brainhook enabled, blocking with brain prompt")
        _output("block", get_prompt())

    except Exception as e:
        logger.error(f"Brainhook error: {e}\n{traceback.format_exc()}")
        _output("approve")


if __name__ == "__main__":
    main()
