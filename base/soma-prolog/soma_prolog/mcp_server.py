"""SOMA MCP — ONE tool. add_event. Nothing else.

SOMA exposes exactly one entrypoint: POST /event. Every operation is an
event whose observations describe what the agent wants. There is no
boot_check tool, no health tool, no query tool — submit an event and
read the result.

If you find yourself adding another @mcp.tool() here, STOP. Read
~/.claude/rules/soma-only-entrypoint-is-add-event.md
"""

import json
import logging
import urllib.request
import urllib.error
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)
mcp = FastMCP("soma-prolog")

# TRIGGERS: SOMA Prolog daemon via HTTP to localhost:8091
SOMA_URL = "http://localhost:8091"  # daemon listens on 8091


def _post_event(data: dict) -> str:
    try:
        body = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(
            f"{SOMA_URL}/event",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result.get("result", json.dumps(result))
    except urllib.error.URLError as e:
        return (
            f"SOMA daemon not running at {SOMA_URL}. "
            f"Start with: python3 -m soma_prolog.api --port 8091. "
            f"Error: {e}"
        )
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def add_event(source: str, observations: str, domain: str = "default") -> str:
    """Submit an event to SOMA. The ONLY operation SOMA supports.

    Every operation in SOMA is an event made of typed observations.
    Want to query the OWL? Submit an event whose observations say so.
    Want to set a goal? Submit an event with goal-control observations.
    Want to add a concept? Submit an event with task observations.

    Args:
        source: who/what produced this event (e.g. 'isaac', 'employee_alice')
        observations: JSON string of observation list. Each observation is
            {"key": str, "value": <primitive>, "type": str} where type is one of:
            string_value, int_value, float_value, bool_value, list_value, dict_value
            Example: '[{"key":"task","value":"invoice_processing","type":"string_value"},
                       {"key":"duration_minutes","value":90,"type":"int_value"}]'
        domain: domain namespace (default 'default'). Foundation is protected;
            user domains are isolated.

    Returns:
        Whatever the SOMA Prolog runtime decided about the event:
        what concepts were created, what partials are still unnamed,
        what dispatches the system queued, what goal violations blocked
        ingestion, etc. The return value IS the next instruction —
        the LLM reads it and acts on it.

    Goal-control observation keys (configure goals in the same event):
        set_goal           value="goal_id|description"
        deactivate_goal    value="goal_id"
        forbid_value       value="goal_id|key|value"
        forbid_key         value="goal_id|key"
        require_key        value="goal_id|key"
        require_value      value="goal_id|key|value"

    Metaprogramming observation keys (assert into Prolog runtime):
        prolog_rule        value="<rule_body_string>"
        prolog_fact        value="<fact_string>"
        add_goal           value="<goal_description>"
        capability         value="<capability_name>"
    """
    try:
        obs_list = json.loads(observations)
    except json.JSONDecodeError as e:
        return f"observations must be valid JSON: {e}"
    return _post_event({"source": source, "observations": obs_list, "domain": domain})
