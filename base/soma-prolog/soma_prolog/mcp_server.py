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
from typing import List
from pydantic import BaseModel, Field
from mcp.server.fastmcp import FastMCP


class ConceptRelationship(BaseModel):
    relationship: str = Field(..., description="Predicate name (e.g. has_deduction_premise, has_steps, has_agent)")
    related: List[str] = Field(..., description="List of target concept names or values")


class Observation(BaseModel):
    concept_name: str = Field(..., description="Concept name (lowercase_with_underscores)")
    is_a: List[str] = Field(..., description="What category/type is this? e.g. ['deduction_chain'], ['domain']")
    part_of: List[str] = Field(..., description="What contains this? e.g. ['weather_house'], ['soma_projects']")
    instantiates: List[str] = Field(..., description="What pattern does this realize? e.g. ['cor_validation_pattern']")
    produces: List[str] = Field(..., description="What does this produce? e.g. ['unmet_requirement'], ['compiled_code']")
    concept: str = Field(..., description="Full conceptual content explaining what this is")
    relationships: List[ConceptRelationship] = Field(default=None, description="Additional custom relationships beyond the required four. Use for has_deduction_premise, has_deduction_conclusion, has_endeavor, has_steps, etc.")

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
def add_event(source: str, observations: List[Observation], domain: str) -> str:
    """Submit an event to SOMA. The ONLY operation SOMA supports.

    Every operation in SOMA is an event made of typed observations.
    Want to query the OWL? Submit an event whose observations say so.
    Want to set a goal? Submit an event with goal-control observations.
    Want to add a concept? Submit an event with task observations.

    Args:
        source: who/what produced this event (e.g. 'isaac', 'employee_alice')
        observations: List of observations. Each observation is a fully typed concept
            with required fields. Submit as many concepts as needed in one event —
            entire domain models, full relationship webs, N concepts with N webs.
        domain: Domain namespace for isolation (e.g. 'weather_api', 'soma_development')

    Returns:
        Whatever the SOMA Prolog runtime decided about the event:
        what concepts were created, what partials are still unnamed,
        what dispatches the system queued, what goal violations blocked
        ingestion, etc. The return value IS the next instruction —
        the LLM reads it and acts on it.
    """
    obs_list = []
    for obs in observations:
        if isinstance(obs, dict):
            o = obs
        else:
            o = obs.model_dump()
        rels = [
            {"relationship": "is_a", "related": o["is_a"]},
            {"relationship": "part_of", "related": o["part_of"]},
            {"relationship": "instantiates", "related": o["instantiates"]},
            {"relationship": "produces", "related": o["produces"]},
        ]
        if o.get("relationships"):
            for r in o["relationships"]:
                if isinstance(r, dict):
                    rels.append(r)
                else:
                    rels.append(r.model_dump() if hasattr(r, 'model_dump') else r)
        obs_list.append({
            "name": o["concept_name"],
            "description": o["concept"],
            "relationships": rels,
        })
    return _post_event({"source": source, "observations": obs_list, "domain": domain})


@mcp.tool()
def persona(action: str, name: str = "", query: str = "", cor_template: str = "", domain: str = "general") -> str:
    """SOMA persona selector CLI. Personas define CoR templates for per-turn metadata.

    Actions:
        list        — show all personas
        search      — find personas by name/domain/purpose (use query param)
        activate    — set active persona (use name param)
        active      — show current active persona
        create      — create new persona (use name, cor_template, domain params)
        favorites   — show favorite personas
        fav_add     — add to favorites (use name param)
        fav_remove  — remove from favorites (use name param)

    CoR template format uses {{blanks}} the agent fills each turn:
        "The hypothesis is {{hypothesis}} and evidence is {{evidence}}."

    Example:
        persona(action="create", name="researcher",
                cor_template="Investigating {{hypothesis}}. Evidence: {{evidence}}. Confidence: {{confidence}}. Next: {{next_step}}.",
                domain="research")
        persona(action="activate", name="researcher")
    """
    from soma_prolog.persona_manager import (
        list_personas, search_personas, activate_persona,
        get_active, create_persona, get_favorites,
        add_favorite, remove_favorite, assign_domain, assign_process,
    )
    if action == "list":
        personas = list_personas()
        if not personas:
            return "No personas defined. Create one with action='create'."
        lines = [f"  {p['name']} [{p['domain']}] — {p['cor_template']}" for p in personas]
        return "Personas:\n" + "\n".join(lines)
    elif action == "search":
        results = search_personas(query or name)
        if not results:
            return f"No personas matching '{query or name}'."
        return "\n".join(f"  {r['name']} — {r['cor_template']}" for r in results)
    elif action == "activate":
        return activate_persona(name)
    elif action == "active":
        return get_active()
    elif action == "create":
        if not name or not cor_template:
            return "Need name and cor_template. Example: persona(action='create', name='researcher', cor_template='Investigating {{hypothesis}}...', domain='research')"
        return create_persona(name, cor_template, domain)
    elif action == "favorites":
        favs = get_favorites()
        return f"Favorites: {favs}" if favs else "No favorites set."
    elif action == "fav_add":
        return add_favorite(name)
    elif action == "fav_remove":
        return remove_favorite(name)
    elif action == "assign_domain":
        if not name or not domain:
            return "Need name and domain. Example: persona(action='assign_domain', name='researcher', domain='knowledge_management')"
        return assign_domain(name, domain)
    elif action == "assign_process":
        if not name or not query:
            return "Need name and process (use query param). Example: persona(action='assign_process', name='developer', query='compile_code')"
        return assign_process(name, query)
    else:
        return f"Unknown action '{action}'. Use: list, search, activate, active, create, favorites, fav_add, fav_remove, assign_domain, assign_process"


@mcp.tool()
def restart_daemon(port: int = 8091) -> str:
    """Kill and restart the SOMA Prolog daemon.

    Use when the daemon crashes or needs to reload code after pip install.
    Kills existing process on the port, starts fresh, waits for ready.

    Args:
        port: Port to run daemon on (default 8091)
    """
    import subprocess
    import time
    subprocess.run(["pkill", "-9", "-f", "soma_prolog.api"], capture_output=True)
    time.sleep(2)
    proc = subprocess.Popen(
        ["python3", "-m", "soma_prolog.api", "--port", str(port)],
        stdout=open("/tmp/soma_daemon.log", "w"),
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    time.sleep(4)
    if proc.poll() is not None:
        return f"Daemon failed to start (exit code {proc.returncode}). Check /tmp/soma_daemon.log"
    try:
        body = json.dumps({"source": "healthcheck", "observations": [{"key": "ping", "value": "1", "type": "string_value"}]}).encode()
        req = urllib.request.Request(f"http://localhost:{port}/event", data=body, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=5) as resp:
            result = json.loads(resp.read().decode())
            triples = "triples=" in result.get("result", "")
            return f"Daemon restarted on port {port}. PID={proc.pid}. Healthy={'yes' if triples else 'no'}."
    except Exception as e:
        return f"Daemon started (PID={proc.pid}) but health check failed: {e}"


@mcp.tool()
def add_rule(rule_body: str) -> str:
    """Add a Prolog rule to the live SOMA runtime. Immediately executable.

    The rule is asserted as both a native Prolog clause (for call/1 in
    deduction chains) and as a rule/2 fact (for the meta-interpreter solve/3).

    Args:
        rule_body: Prolog clause string.
            Example: "my_check(X) :- triple(X, is_a, agent), triple(X, has_name, _)"

    Returns:
        Confirmation or error message.
    """
    try:
        body = json.dumps({"rule_body": rule_body}).encode("utf-8")
        req = urllib.request.Request(
            f"{SOMA_URL}/rule",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result.get("result", json.dumps(result))
    except urllib.error.URLError as e:
        return f"SOMA daemon not running at {SOMA_URL}. Error: {e}"
    except Exception as e:
        return f"Error: {e}"
