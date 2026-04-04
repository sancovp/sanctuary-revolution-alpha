"""TreeShell functions for TreeKanban — wraps HeavenBMLSQLiteClient methods.

These are the callable functions that treekanban_family.json nodes point to.
They import heaven_bml_sqlite directly — no MCP, no strata, no execute_action.
"""

import json
import os
from typing import Optional, Dict, List
from heaven_bml_sqlite.heaven_bml_sqlite_client import HeavenBMLSQLiteClient


def _get_default_board() -> str:
    """Get board name from GIINT_TREEKANBAN_BOARD env var, falling back to strata config."""
    board = os.getenv("GIINT_TREEKANBAN_BOARD")
    if board:
        return board
    # Try reading from strata config
    try:
        strata_path = os.path.expanduser("~/.config/strata/servers.json")
        with open(strata_path) as f:
            strata = json.load(f)
        board = strata.get("mcp", {}).get("servers", {}).get("giint-llm-intelligence", {}).get("env", {}).get("GIINT_TREEKANBAN_BOARD")
        if board:
            return board
    except Exception:
        pass
    return "poimandres_v2"


DEFAULT_BOARD = _get_default_board()


def _client() -> HeavenBMLSQLiteClient:
    return HeavenBMLSQLiteClient()


def view_board(show_details: bool = False) -> str:
    """View all cards across all lanes on the TreeKanban board."""
    client = _client()
    all_cards = client.get_all_cards(DEFAULT_BOARD)
    if not all_cards:
        return "No cards found on board."
    # Group by lane
    lanes = {}
    for card in all_cards:
        lane = card.get('status', 'backlog')
        lanes.setdefault(lane, []).append(card)
    total = len(all_cards)
    lines = [f"Board '{DEFAULT_BOARD}': {total} cards across {len(lanes)} lanes."]
    for lane_name in ['plan', 'build', 'measure', 'learn', 'done', 'backlog']:
        cards = lanes.pop(lane_name, [])
        if cards:
            lines.append(f"\n  {lane_name.upper()} ({len(cards)}):")
            for card in cards[:10]:  # Show first 10 per lane
                title = card.get('title', 'Untitled')[:50]
                tags = json.loads(card.get('tags', '[]'))
                tag_str = f" [{','.join(tags[:3])}]" if tags else ""
                lines.append(f"    #{card['id']} {title}{tag_str}")
            if len(cards) > 10:
                lines.append(f"    ... and {len(cards)-10} more")
    # Any remaining lanes
    for lane_name, cards in lanes.items():
        lines.append(f"\n  {lane_name.upper()} ({len(cards)}):")
        for card in cards[:5]:
            title = card.get('title', 'Untitled')[:50]
            lines.append(f"    #{card['id']} {title}")
        if len(cards) > 5:
            lines.append(f"    ... and {len(cards)-5} more")
    return "\n".join(lines)


def view_lane(lane: str = "build") -> str:
    """View cards in a specific lane (plan, build, done, backlog).

    Shows ALL cards in the lane, not just prioritized ones.
    """
    client = _client()
    all_cards = client.get_all_cards(DEFAULT_BOARD)
    cards = [c for c in all_cards if c.get('status') == lane]
    if not cards:
        return f"No cards in lane '{lane}'."
    # Sort: prioritized first, then NA
    def sort_key(card):
        p = card.get('priority', 'NA')
        if p in ('NA', 'none', '', None):
            return (1, card.get('id', 0))
        try:
            parts = [int(x) for x in p.split('.')]
            return (0, tuple(parts + [0]*10))
        except Exception:
            return (1, card.get('id', 0))
    cards.sort(key=sort_key)
    lines = [f"Lane '{lane}' ({len(cards)} cards):"]
    for card in cards:
        priority = card.get('priority', 'NA')
        title = card.get('title', 'Untitled')[:60]
        tags = json.loads(card.get('tags', '[]'))
        tag_str = f" [{','.join(tags)}]" if tags else ""
        depth = priority.count('.') if priority not in ['NA', 'none', '', None] else 0
        indent = "  " * depth
        lines.append(f"  {indent}[{priority:>6}] #{card['id']} {title}{tag_str}")
    return "\n".join(lines)


def view_card(card_id: int = 0) -> str:
    """View a single card's full details by ID."""
    client = _client()
    all_cards = client.get_all_cards(DEFAULT_BOARD)
    for card in all_cards:
        if str(card['id']) == str(card_id):
            tags = json.loads(card.get('tags', '[]'))
            lines = [
                f"Card #{card['id']}",
                f"  Title:       {card.get('title', 'Untitled')}",
                f"  Lane:        {card.get('status', 'unknown')}",
                f"  Priority:    {card.get('priority', 'NA')}",
                f"  Tags:        {', '.join(tags) if tags else 'none'}",
                f"  Description: {card.get('description', '(none)')}",
            ]
            return "\n".join(lines)
    return f"Card {card_id} not found on board '{DEFAULT_BOARD}'."


def create_card(title: str = "", description: str = "",
                 lane: str = "backlog", starsystem: str = "",
                 assignee: str = "", tags: str = "[]") -> str:
    """Create a card on the board.

    starsystem: REQUIRED — starsystem name tag (e.g. 'gnosys-plugin-v2')
    assignee: REQUIRED — 'ai-human', 'ai-only', or 'human-only' (canopy routing)
    tags: additional tags as JSON array string (e.g. operadic flow IDs, giint refs)

    Cards flow through PBML lanes:
      plan → build → measure → learn → (done | back to build)
    ai-only cards get auto-routed to agent via canopy.
    """
    if not starsystem:
        return "ERROR: starsystem is required. Every card must be tagged with its starsystem."
    if not assignee:
        return "ERROR: assignee is required. Must be 'ai-human', 'ai-only', or 'human-only'."
    if assignee not in ("ai-human", "ai-only", "human-only"):
        return f"ERROR: assignee must be 'ai-human', 'ai-only', or 'human-only', got '{assignee}'."
    if not title:
        return "ERROR: title is required."

    client = _client()
    extra = json.loads(tags) if isinstance(tags, str) else tags
    all_tags = [starsystem, assignee] + extra

    result = client.create_card(DEFAULT_BOARD, title, description, lane, all_tags)
    if result:
        return f"Created card #{result['id']}: {title} [lane={lane}] tags={all_tags}"
    return "Failed to create card."


def move_above(card_id: int = 0, target_id: int = 0) -> str:
    """Move a card above a target card (preserves family structure)."""
    client = _client()
    success = client.move_card_above(DEFAULT_BOARD, card_id, target_id)
    return f"Moved #{card_id} above #{target_id}" if success else "Move failed."


def move_below(card_id: int = 0, target_id: int = 0) -> str:
    """Move a card below a target card (preserves family structure)."""
    client = _client()
    success = client.move_card_below(DEFAULT_BOARD, card_id, target_id)
    return f"Moved #{card_id} below #{target_id}" if success else "Move failed."


def get_family(card_id: int = 0) -> str:
    """Get family tree for a card (parent, children, siblings)."""
    client = _client()
    family = client.get_family(DEFAULT_BOARD, card_id)
    if not family.get('card'):
        return f"Card {card_id} not found."
    lines = [f"Family for #{card_id}:"]
    if family.get('parent'):
        p = family['parent']
        lines.append(f"  Parent:   #{p['id']} ({p.get('priority','NA')}) {p.get('title','')}")
    c = family['card']
    lines.append(f"  Card:     #{c['id']} ({c.get('priority','NA')}) {c.get('title','')}")
    for child in family.get('children', []):
        lines.append(f"  Child:    #{child['id']} ({child.get('priority','NA')}) {child.get('title','')}")
    for sib in family.get('siblings', []):
        lines.append(f"  Sibling:  #{sib['id']} ({sib.get('priority','NA')}) {sib.get('title','')}")
    return "\n".join(lines)


def get_next_task() -> str:
    """Get the highest-priority card from the build lane."""
    client = _client()
    cards = client.get_prioritized_cards(DEFAULT_BOARD, "build")
    if not cards:
        return "No tasks in build lane."
    card = cards[0]
    tags = json.loads(card.get('tags', '[]'))
    return f"Next task: #{card['id']} [{card.get('priority','NA')}] {card.get('title','')} (tags: {','.join(tags) if tags else 'none'})"


def add_tag(card_id: int = 0, tag: str = "") -> str:
    """Add a tag to a card."""
    client = _client()
    success = client.add_tag(DEFAULT_BOARD, card_id, tag)
    return f"Added tag '{tag}' to #{card_id}" if success else "Failed."


def remove_tag(card_id: int = 0, tag: str = "") -> str:
    """Remove a tag from a card."""
    client = _client()
    success = client.remove_tag(DEFAULT_BOARD, card_id, tag)
    return f"Removed tag '{tag}' from #{card_id}" if success else "Failed."


def move_to_lane(card_id: int = 0, lane: str = "") -> str:
    """Move a card to a different PBML lane.

    Valid lanes: backlog, plan, build, measure, learn, done, blocked, archive.
    Respects PBML ratchet: backlog→plan→build→measure→learn→done.
    """
    VALID_LANES = {"backlog", "plan", "build", "measure", "learn", "done", "blocked", "archive"}
    if not lane:
        return "ERROR: lane is required."
    if lane not in VALID_LANES:
        return f"ERROR: invalid lane '{lane}'. Valid: {', '.join(sorted(VALID_LANES))}"
    if not card_id:
        return "ERROR: card_id is required."
    client = _client()
    result = client._make_request("PUT", f"/api/sqlite/cards/{card_id}", {"board": DEFAULT_BOARD, "status": lane})
    if result:
        return f"Moved #{card_id} to '{lane}'"
    return f"Failed to move #{card_id} to '{lane}'"
