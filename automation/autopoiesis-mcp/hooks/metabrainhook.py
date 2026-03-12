#!/usr/bin/env python3
"""
MetaBrainHook - Remote control daemon for orchestration mode.

Reads a JSON config file that the user can edit from anywhere.
Injects orchestration context on every prompt submission.

The agent CANNOT turn this off - only the user can by:
- Running `metabrainhook off`
- Deleting the state file
- Setting enabled: false in config

Config file: /tmp/heaven_data/metabrainhook_config.json
State file: /tmp/metabrainhook_state.txt

Part of the Autopoiesis plugin.
"""

import json
import logging
import os
import sys
import traceback
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='/tmp/metabrainhook.log'
)
logger = logging.getLogger('metabrainhook')

# Paths
HEAVEN_DATA_DIR = Path(os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data"))
CONFIG_FILE = HEAVEN_DATA_DIR / "metabrainhook_config.json"
STATE_FILE = Path("/tmp/metabrainhook_state.txt")

# Brainhook prompt file (to append at end)
PLUGIN_DIR = Path(__file__).parent
BRAINHOOK_PROMPT_FILE = PLUGIN_DIR / "brainhook_prompt.txt"



def _output(result: str):
    """Output hook result as JSON."""
    print(json.dumps({"result": result}))
    sys.exit(0)


def is_enabled() -> bool:
    """Check if metabrainhook is enabled."""
    try:
        if STATE_FILE.exists():
            return STATE_FILE.read_text().strip().lower() == "on"
    except Exception as e:
        logger.error(f"Error checking state file: {e}\n{traceback.format_exc()}")
    return False


def load_config_text() -> str:
    """Load config file as raw text. No parsing, just inject."""
    try:
        if CONFIG_FILE.exists():
            return CONFIG_FILE.read_text().strip()
    except Exception as e:
        logger.warning(f"Error reading config: {e}\n{traceback.format_exc()}")
    return ""


def get_brainhook_prompt() -> str:
    """Get brainhook prompt text to append."""
    try:
        if BRAINHOOK_PROMPT_FILE.exists():
            return BRAINHOOK_PROMPT_FILE.read_text().strip()
    except Exception as e:
        logger.warning(f"Error reading brainhook prompt: {e}\n{traceback.format_exc()}")
    return ""


def format_orchestration_context(config_text: str) -> str:
    """Wrap raw config text with header. That's it."""
    if not config_text:
        return ""
    return f"ORCHESTRATION MODE ACTIVE\n{'=' * 40}\n{config_text}\n{'=' * 40}"


def _build_injection_context(config_text: str) -> str:
    """Build full injection context from raw config text + brainhook."""
    context = format_orchestration_context(config_text)
    brainhook_prompt = get_brainhook_prompt()
    if brainhook_prompt:
        context = f"{context}\n\n{brainhook_prompt}"
    return context


def _process_hook() -> str:
    """Process hook logic, return injection string (empty if disabled)."""
    if not is_enabled():
        logger.debug("MetaBrainHook disabled, no injection")
        return ""

    config_text = load_config_text()
    logger.debug(f"Config loaded: {len(config_text)} chars")

    return _build_injection_context(config_text)


def main():
    try:
        hook_input = json.load(sys.stdin)
        logger.debug(f"Hook input keys: {list(hook_input.keys())}")

        context = _process_hook()
        logger.debug(f"Injecting context ({len(context)} chars)")
        _output(context)

    except Exception as e:
        logger.error(f"MetaBrainHook error: {e}\n{traceback.format_exc()}")
        _output("")


if __name__ == "__main__":
    main()
