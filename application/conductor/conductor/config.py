"""Shared constants and configuration."""
import json
import os
from pathlib import Path

PHASES = ["observe", "hypothesize", "proposal", "experiment", "analyze"]

# Models read from conductor_agent_config.json — no hardcoded values
_CFG_PATH = Path(os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data")) / "conductor_agent_config.json"
_CFG = {}
if _CFG_PATH.exists():
    try:
        _CFG = json.loads(_CFG_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        pass

GRUG_MODEL = _CFG.get("model", "")
RESEARCHER_MODEL = _CFG.get("model", "")
