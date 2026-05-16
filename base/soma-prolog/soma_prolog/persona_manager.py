"""SOMA Persona Manager — CLI for persona selection and CoR templates.

Personas are stored in SOMA as observed concepts. This module reads
from SQLite (read-only) and writes by posting events to the daemon.
The MCP tool is a thin wrapper around this.

State file: /tmp/soma_data/active_persona.json
  {name, cor_template, domain, favorites: []}
"""
import json
import os
import sqlite3
import urllib.request

SOMA_URL = "http://localhost:8091"
SOMA_DB = "/tmp/soma_data/soma.db"
STATE_FILE = "/tmp/soma_data/active_persona.json"


def _load_state():
    if os.path.exists(STATE_FILE):
        try:
            return json.loads(open(STATE_FILE).read())
        except Exception:
            pass
    return {"name": None, "cor_template": None, "domain": None, "favorites": []}


def _save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def _query_db(sql, params=()):
    if not os.path.exists(SOMA_DB):
        return []
    conn = sqlite3.connect(SOMA_DB)
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return rows


def _post_event(source, observations):
    data = json.dumps({"source": source, "observations": observations}).encode()
    req = urllib.request.Request(
        f"{SOMA_URL}/event", data=data,
        headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode())


def list_personas():
    rows = _query_db(
        "SELECT DISTINCT s.subject, s.object FROM soma_triples s "
        "WHERE s.predicate = 'has_cor_template'"
    )
    personas = []
    for name, template in rows:
        domain_rows = _query_db(
            "SELECT object FROM soma_triples WHERE subject=? AND predicate='has_persona_domain'",
            (name,)
        )
        domain = domain_rows[0][0] if domain_rows else "general"
        personas.append({"name": name, "domain": domain, "cor_template": template[:80]})
    return personas


def search_personas(query):
    q = f"%{query}%"
    rows = _query_db(
        "SELECT DISTINCT s.subject FROM soma_triples s "
        "WHERE (s.subject LIKE ? OR s.object LIKE ?) "
        "AND s.predicate IN ('has_cor_template', 'has_persona_domain', 'is_a')",
        (q, q)
    )
    results = []
    for (name,) in rows:
        tmpl = _query_db(
            "SELECT object FROM soma_triples WHERE subject=? AND predicate='has_cor_template'",
            (name,)
        )
        if tmpl:
            results.append({"name": name, "cor_template": tmpl[0][0][:80]})
    return results


def activate_persona(name):
    state = _load_state()
    tmpl_rows = _query_db(
        "SELECT object FROM soma_triples WHERE subject=? AND predicate='has_cor_template'",
        (name,)
    )
    if not tmpl_rows:
        return f"Persona '{name}' not found or has no CoR template."
    domain_rows = _query_db(
        "SELECT object FROM soma_triples WHERE subject=? AND predicate='has_persona_domain'",
        (name,)
    )
    state["name"] = name
    state["cor_template"] = tmpl_rows[0][0]
    state["domain"] = domain_rows[0][0] if domain_rows else "general"
    _save_state(state)
    _post_event("persona_manager", [
        {"key": "has_active_persona", "value": name, "type": "string_value"},
    ])
    return f"Activated persona: {name}\nCoR: {state['cor_template']}\nDomain: {state['domain']}"


def get_active():
    state = _load_state()
    if not state["name"]:
        return "No active persona. Use select_persona to activate one."
    return f"Active: {state['name']}\nCoR: {state['cor_template']}\nDomain: {state['domain']}"


def add_favorite(name):
    state = _load_state()
    if name not in state["favorites"]:
        state["favorites"].append(name)
        _save_state(state)
    return f"Added {name} to favorites: {state['favorites']}"


def remove_favorite(name):
    state = _load_state()
    state["favorites"] = [f for f in state["favorites"] if f != name]
    _save_state(state)
    return f"Removed {name}. Favorites: {state['favorites']}"


def get_favorites():
    state = _load_state()
    return state["favorites"]


def assign_domain(name, domain):
    obs = [{
        "name": name, "source": "persona_manager",
        "description": f"Domain assignment for {name}",
        "relationships": [{"relationship": "has_persona_domain", "related": [domain]}]
    }]
    _post_event("persona_manager", obs)
    return f"Assigned domain '{domain}' to persona '{name}'."


def assign_process(name, process):
    obs = [{
        "name": name, "source": "persona_manager",
        "description": f"Process assignment for {name}",
        "relationships": [{"relationship": "has_persona_process", "related": [process]}]
    }]
    _post_event("persona_manager", obs)
    return f"Assigned process '{process}' to persona '{name}'."


def create_persona(name, cor_template, domain="general"):
    obs = [{
        "name": name,
        "source": "persona_manager",
        "description": f"SOMA persona for {domain}",
        "relationships": [
            {"relationship": "is_a", "related": ["agent"]},
            {"relationship": "part_of", "related": ["soma"]},
            {"relationship": "instantiates", "related": ["agent"]},
            {"relationship": "produces", "related": ["cor_metadata"]},
            {"relationship": "dolce_category", "related": ["agentive_social_object"]},
            {"relationship": "has_cor_template", "related": [cor_template]},
            {"relationship": "has_persona_domain", "related": [domain]},
        ]
    }]
    _post_event("persona_manager", obs)
    return f"Created persona: {name}\nCoR: {cor_template}\nDomain: {domain}"
