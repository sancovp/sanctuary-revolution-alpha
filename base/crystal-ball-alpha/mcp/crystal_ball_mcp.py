#!/usr/bin/env python3
"""Crystal Ball MCP — Unified ontological engine.

Architecture:
  ┌─────────┐    MCP/stdio    ┌──────────────────┐   WebSocket    ┌──────────┐
  │   LLM   │ ◄────────────► │ Crystal Ball MCP  │ ◄───────────► │ Frontend │
  │(Claude) │                │  (this server)    │               │  (Vite)  │
  └─────────┘                └──────────────────┘               └──────────┘
                                      │
                        ┌─────────────┼──────────────┐
                        │ HTTP        │ Python       │
                        ▼             ▼              │
                 ┌──────────────┐  ┌──────────┐     │
                 │ Crystal Ball │  │ YOUKNOW  │     │
                 │  SaaS        │  │ Compiler │     │
                 │  (:3000)     │  │ (UARL)   │     │
                 └──────────────┘  └──────────┘     │
                                        │           │
                                        ▼           │
                                   ┌──────────┐    │
                                   │domain.owl│    │
                                   └──────────┘    │

Tool 1: crystal_ball(input, help?)
  - Detects UARL predicates → routes to YOUKNOW compiler
  - Otherwise passes input to CB state machine engine
  - Single entry point for all ontological operations

Tool 2: wait_for_user_to_use_frontend()
  - Long-polls for frontend WebSocket suggestion

Tool 3: youknow_status()
  - Diagnostic: shows Cat_of_Cat size, domain.owl path, entity list
"""

from __future__ import annotations

import os
import json
import asyncio
import logging
import threading
from typing import Optional
from datetime import datetime

import httpx
from mcp.server.fastmcp import FastMCP

try:
    import websockets
    from websockets.server import serve as ws_serve
    HAS_WS = True
except ImportError:
    HAS_WS = False

# ─── Setup ─────────────────────────────────────────────────────────

logger = logging.getLogger("crystal-ball-mcp")
logging.basicConfig(level=logging.INFO)

mcp = FastMCP("crystal-ball", "Crystal Ball ontological space scryer — LLM ↔ Frontend bridge")

# TRIGGERS: Crystal Ball frontend via HTTP to localhost:3000
CB_API = os.getenv("CRYSTAL_BALL_API", "http://localhost:3000")
CB_API_KEY = os.getenv("CRYSTAL_BALL_API_KEY", "")

# ─── WebSocket State ───────────────────────────────────────────────

_frontend_websockets: set = set()
_ws_lock = threading.Lock()
_frontend_event = threading.Event()
_frontend_message: str = ""
_ws_loop: asyncio.AbstractEventLoop | None = None


def _is_frontend_connected() -> bool:
    with _ws_lock:
        return len(_frontend_websockets) > 0


# ─── HTTP ──────────────────────────────────────────────────────────

async def _cb_post(input_str: str) -> dict:
    """POST to the CB FLOW endpoint. FLOW is the only way in."""
    url = f"{CB_API}/api/cb/flow"
    headers = {}
    if CB_API_KEY:
        headers["Authorization"] = f"Bearer {CB_API_KEY}"

    async with httpx.AsyncClient(timeout=300.0, headers=headers) as client:
        resp = await client.post(url, json={"input": input_str})
        resp.raise_for_status()
        return resp.json()



# ─── Help Text ─────────────────────────────────────────────────────

HELP_TEXT = """
Crystal Ball is a coordinate state machine with an integrated
ontology compiler (YOUKNOW / UARL).

You navigate spaces by typing text commands. Each space is a tree of
selections. Every valid path through the tree maps to a unique real
number — your mineSpace. MineSpaces inherit all properties of ℝ:
ordering, density, continuity.

The state machine guides you through the flow:
  create → bloom → fill → lock → mine

Repeat at higher orders to expand the kernel exhaustively. When a
mineSpace is complete, resolve coordinates into deliverables.

The coordinate grammar uses digits 0-9:
  0     superposition (all possibilities)
  1-7   select a child by primacy
  8     drill into a subspace
  88    close drill (exit subspace)
  9     wrap (+7, extends selection range: 91=8th, 92=9th, ...)

═══ CB COMMANDS ═══════════════════════════════════════════════════

list
    List all spaces.

create {name}
    Create a new space.

{space}
    Enter a space (shows its tree).

{space} {coordinate}
    Navigate to a coordinate within a space.
    Blooms into the node — the engine tells you what to do next.

{label}
    After blooming, type a label to add a child node.
    The engine tracks your position and prompts you.

lock
    Lock the current position (mark it as decided).

freeze
    Freeze the current position (immutable).

{space} mine
    Mine the space — enumerate all valid coordinate paths,
    project them as real numbers on the mineSpace plane,
    and persist the mineSpace to storage.

{space} mine view
    Observe the persisted mineSpace — shows valid points,
    their real number encodings, and projected kernels.

═══ YOUKNOW / UARL ═══════════════════════════════════════════════

Any input containing a UARL predicate is automatically compiled
through the YOUKNOW ontology engine:

  {Subject} is_a {Object}
  {Subject} embodies {Object}
  {Subject} manifests {Object}
  {Subject} reifies {Object}
  {Subject} programs {Object}

Additional predicates are comma-separated:
  Group is_a AlgebraicStructure, analogical_pattern SetWithOp,
      description My-description, y_layer Y1, part_of Math,
      python_class group, instantiates AlgebraicStructure,
      justifies is_a, has_msc Group_MSC, cat_of_cat_bounded true

Admitted statements persist to domain.owl. Rejected statements
go to SOUP with structured feedback on what's missing.

═══════════════════════════════════════════════════════════════════
"""


# ─── UARL Predicate Detection ─────────────────────────────────────

# Core UARL predicates that indicate a YOUKNOW statement
_UARL_PREDICATES = {
    "is_a", "part_of", "embodies", "manifests", "reifies", "programs",
    "analogical_pattern", "produces", "instantiates",
}


def _is_youknow_statement(text: str) -> bool:
    """Detect whether input is a YOUKNOW/UARL statement vs CB command.

    A UARL statement contains one of the core predicates as a word boundary.
    CB commands are things like: list, create X, X mine, X 1.2, lock, etc.
    """
    words = text.replace(",", " ").split()
    return any(w in _UARL_PREDICATES for w in words)


def _compile_youknow(statement: str) -> dict:
    """Run a statement through the YOUKNOW ontology compiler.

    Returns structured result with admission status and feedback.
    """
    if not _youknow_ready:
        return {
            "error": "YOUKNOW kernel not loaded",
            "detail": f"Kernel dir: {_YOUKNOW_KERNEL_DIR}, exists: {_YOUKNOW_KERNEL_DIR.exists()}"
        }

    try:
        result = _youknow_compile(statement)
        admitted = result == "OK"

        ideas = []
        if not admitted and "Unknown:" in result:
            unknown_part = (
                result.split("Unknown:")[1].split(". Missing:")[0].strip()
                if "Missing:" in result
                else result.split("Unknown:")[1].strip()
            )
            ideas.append({"type": "broken_chain", "detail": unknown_part})
        if not admitted and "Missing:" in result:
            missing_part = result.split("Missing:")[1].strip()
            ideas.append({"type": "missing", "detail": missing_part})

        return {
            "admitted": admitted,
            "response": result,
            "statement": statement,
            "ideas": ideas,
            "cat_of_cat_size": len(_cat.entities),
        }

    except Exception as e:
        return {"error": str(e), "statement": statement}


# ─── Stratum → Y-Layer mapping ─────────────────────────────────────

_STRATUM_TO_Y = {
    "universal": "Y1",
    "subclass": "Y2",
    "instance": "Y3",
    "instance_universal": "Y4",
    "instance_subtype": "Y5",
    "instance_instance": "Y6",
}


def _sanitize(label: str) -> str:
    """Sanitize labels for UARL: spaces→underscores, strip special chars."""
    if not label:
        return ""
    return label.replace(" ", "_").replace(",", "").replace('"', "").strip("_")


def _build_uarl(subject: str, predicates: dict) -> str:
    """Build a complete UARL statement from subject and predicate dict.

    predicates is {predicate_name: value}, e.g.:
      {"is_a": "Movies", "part_of": "MovieSpace", "y_layer": "Y2",
       "description": "Subclass-of-Movies", "produces": "ActionSubspace"}

    Returns: "Subject is_a Movies, part_of MovieSpace, y_layer Y2, ..."
    """
    pred_parts = []
    for pred, val in predicates.items():
        if val:
            pred_parts.append(f"{pred} {val}")
    if not pred_parts:
        return subject
    # First predicate joins directly to subject (no comma)
    # Subsequent predicates are comma-separated
    return f"{subject} {', '.join(pred_parts)}"


def _extract_ontological_claims(cb_result: dict) -> list[str]:
    """Extract COMPLETE UARL statements from a CB operation result.

    Every CB structural operation IS an ontological claim.
    CB runs YOUKNOW — this function reads what CB did and generates
    the FULL UARL statements with every predicate CB has data for:
      is_a, part_of, y_layer, description, produces, cat_of_cat_bounded

    Returns a list of complete UARL statement strings.
    """
    claims = []
    view = cb_result.get("view", "")
    data = cb_result.get("data")
    cursor = cb_result.get("cursor", {})
    space_name = cursor.get("space")

    # ═══ CREATE: new space ═══
    if view.startswith("Created space") and space_name:
        claims.append(_build_uarl(_sanitize(space_name), {
            "is_a": "CB_Space",
            "description": f"Crystal-Ball-space-{_sanitize(space_name)}",
            "y_layer": "Y1",
            "cat_of_cat_bounded": "true",
        }))

    # ═══ ADD: child added under parent ═══
    if "Added" in view and isinstance(data, dict):
        child_label = _sanitize(data.get("label", ""))
        parent_label = _sanitize(data.get("parentLabel", ""))
        # Node data from nodeToData
        stratum = data.get("stratum")
        y_layer = _STRATUM_TO_Y.get(stratum, "")
        has_subspace = data.get("hasSubspace", False)
        produced_space = data.get("producedSpace", "")
        coord = cursor.get("coordinate", "")

        if child_label and parent_label:
            preds = {
                "is_a": parent_label,
                "part_of": _sanitize(space_name) if space_name else "",
                "y_layer": y_layer,
                "description": f"{child_label}-under-{parent_label}-at-{coord}" if coord else "",
            }
            if produced_space:
                preds["produces"] = _sanitize(produced_space)
            preds["cat_of_cat_bounded"] = "true"
            claims.append(_build_uarl(child_label, preds))
        elif child_label and space_name:
            claims.append(_build_uarl(child_label, {
                "part_of": _sanitize(space_name),
                "y_layer": y_layer,
                "cat_of_cat_bounded": "true",
            }))

    # ═══ MULTI-FILL: multiple children added under parent ═══
    if isinstance(data, dict) and data.get("addedLabels") and data.get("label"):
        parent_label = _sanitize(data["label"])
        stratum = data.get("stratum")
        y_layer = _STRATUM_TO_Y.get(stratum, "")

        for child_label_raw in data["addedLabels"]:
            child_label = _sanitize(child_label_raw)
            if child_label and child_label != parent_label:
                claims.append(_build_uarl(child_label, {
                    "is_a": parent_label,
                    "part_of": _sanitize(space_name) if space_name else "",
                    "y_layer": y_layer,
                    "cat_of_cat_bounded": "true",
                }))

    # ═══ LOCK: node locked ═══
    if "Locked:" in view and isinstance(data, dict):
        node_label = _sanitize(data.get("label", ""))
        if node_label and space_name:
            claims.append(_build_uarl(node_label, {
                "part_of": _sanitize(space_name),
                "y_layer": _STRATUM_TO_Y.get(data.get("stratum"), ""),
                "cat_of_cat_bounded": "true",
            }))

        # KERNEL COMPLETE → space produces MineSpace
        if data.get("kernelComplete") and space_name:
            claims.append(_build_uarl(_sanitize(space_name), {
                "produces": "CB_MineSpace",
                "y_layer": "Y3",
                "description": f"Locked-kernel-{_sanitize(space_name)}-produces-its-configuration-space",
                "cat_of_cat_bounded": "true",
            }))

    # ═══ MINE: coordinate paths → real number encodings ═══
    if "Mine:" in view and isinstance(data, dict):
        mine_data = data.get("mineSpace")
        if mine_data and isinstance(mine_data, dict):
            deliverable = _sanitize(mine_data.get("deliverable", ""))
            if deliverable:
                claims.append(_build_uarl(deliverable, {
                    "is_a": "CB_MineSpace",
                    "y_layer": "Y3",
                    "description": f"MineSpace-for-{deliverable}",
                    "cat_of_cat_bounded": "true",
                }))
            # Each valid known point IS an ontological address
            for point in (mine_data.get("known") or []):
                if isinstance(point, dict) and point.get("status") == "valid":
                    label = _sanitize(point.get("label", ""))
                    coord = point.get("coordinate", "")
                    if label and deliverable:
                        claims.append(_build_uarl(label, {
                            "part_of": deliverable,
                            "description": f"Valid-coordinate-{coord}-in-{deliverable}",
                            "cat_of_cat_bounded": "true",
                        }))
        elif space_name:
            claims.append(_build_uarl(_sanitize(space_name), {
                "produces": "CB_MineSpace",
                "y_layer": "Y3",
                "cat_of_cat_bounded": "true",
            }))

    # ═══ FREEZE: node frozen → reifies ═══
    if "Frozen:" in view and isinstance(data, dict):
        node_label = _sanitize(data.get("label", ""))
        if node_label and space_name:
            claims.append(_build_uarl(node_label, {
                "reifies": _sanitize(space_name),
                "y_layer": _STRATUM_TO_Y.get(data.get("stratum"), ""),
                "description": f"Frozen-node-{node_label}-reifies-{_sanitize(space_name)}",
                "cat_of_cat_bounded": "true",
            }))

    # ═══ RENAME: space renamed ═══
    if "Renamed" in view and "→" in view:
        import re
        m = re.search(r'Renamed "([^"]+)" → "([^"]+)"', view)
        if m:
            new_name = _sanitize(m.group(2))
            claims.append(_build_uarl(new_name, {
                "is_a": "CB_Space",
                "description": f"Renamed-space-{new_name}",
                "cat_of_cat_bounded": "true",
            }))

    # ═══ SWARM: agent filled nodes ═══
    if "Swarm" in view and isinstance(data, dict):
        for action in (data.get("actions") or []):
            if isinstance(action, dict):
                label = _sanitize(action.get("label", ""))
                parent_label = _sanitize(action.get("parentLabel", ""))
                if label and parent_label:
                    claims.append(_build_uarl(label, {
                        "is_a": parent_label,
                        "part_of": _sanitize(space_name) if space_name else "",
                        "cat_of_cat_bounded": "true",
                    }))

    return claims


# ─── Tool 1: crystal_ball ─────────────────────────────────────────

@mcp.tool()
async def crystal_ball(input: str, help: bool = False) -> str:
    """Talk to the Crystal Ball state machine.

    Crystal Ball is a coordinate state machine. You navigate spaces by
    typing. It guides you through the flow: create → bloom → fill →
    lock → mine. Every valid path maps to a unique real number.

    Args:
        input: Text command for the CB engine (e.g. "list", "MySpace",
               "MySpace 1.2", "Alpha", "lock", "MySpace mine")
               
               For list operations, send newline-separated commands:
               "Myth\\nSceneFormat\\nGenre\\nDramatica"
        help: If True, return usage guide instead of executing

    Returns:
        JSON result from Crystal Ball engine (includes view, interaction
        prompts, cursor position, and data)
    """
    if help:
        return HELP_TEXT

    if not input or not input.strip():
        return HELP_TEXT

    stripped = input.strip()

    # ─── YOUKNOW: if input contains UARL predicates, compile it ──
    if _youknow_ready and _is_youknow_statement(stripped):
        result = _compile_youknow(stripped)

        # Broadcast YOUKNOW result to frontends too
        _broadcast_from_mcp({
            "type": "youknow_result",
            "input": input,
            "result": result,
            "timestamp": datetime.now().isoformat(),
        })

        return json.dumps(result, indent=2)

    # ─── CB FLOW: normal Crystal Ball state machine ──
    try:
        result = await _cb_post(stripped)

        # ─── YOUKNOW POST-PROCESS: compile ontological claims from CB ──
        # CB's geometry already declares every relationship positionally.
        # Extract the claims and compile them through YOUKNOW.
        youknow_feedback = None
        if _youknow_ready and isinstance(result, dict):
            claims = _extract_ontological_claims(result)
            if claims:
                youknow_feedback = []
                for claim in claims[:3]:
                    try:
                        yk_result = _compile_youknow(claim)
                        youknow_feedback.append(yk_result)
                    except Exception:
                        pass
                if youknow_feedback:
                    result["youknow"] = youknow_feedback

        # Broadcast to connected frontends
        _broadcast_from_mcp({
            "type": "crystal_ball_result",
            "input": input,
            "result": result,
            "timestamp": datetime.now().isoformat(),
        })

        return json.dumps(result, indent=2)

    except httpx.HTTPStatusError as e:
        return json.dumps({
            "error": f"HTTP {e.response.status_code}",
            "detail": e.response.text,
            "input": input,
        })
    except Exception as e:
        return json.dumps({"error": str(e), "input": input})


# ─── Tool 2: wait_for_user_to_use_frontend ────────────────────────

@mcp.tool()
async def wait_for_user_to_use_frontend(timeout_seconds: int = 120) -> str:
    """Wait for the user to interact with the Crystal Ball frontend.

    Opens a pending request that waits for the frontend to send an
    LLM suggestion prompt. When the user interacts with the 3D
    visualization, the frontend sends a suggestion back through
    the WebSocket bridge.

    Args:
        timeout_seconds: How long to wait before timing out (default: 120s)

    Returns:
        The user's suggestion/intent from the frontend, or an error
    """
    global _frontend_message

    if not _is_frontend_connected():
        return json.dumps({
            "error": "Frontend Not Turned On",
            "hint": "Start the Crystal Ball frontend (npm run dev) and ensure "
                    "it connects to the MCP WebSocket bridge on port 7346.",
        })

    _frontend_event.clear()
    _frontend_message = ""

    _broadcast_from_mcp({
        "type": "waiting_for_input",
        "message": "LLM is waiting for your input...",
        "timeout_seconds": timeout_seconds,
        "timestamp": datetime.now().isoformat(),
    })

    got_it = _frontend_event.wait(timeout=timeout_seconds)

    if got_it:
        return json.dumps({
            "user_suggestion": _frontend_message,
            "timestamp": datetime.now().isoformat(),
        })
    else:
        return json.dumps({
            "timeout": True,
            "message": f"No input received from frontend within {timeout_seconds}s",
        })


# ─── WebSocket Bridge ─────────────────────────────────────────────

WS_PORT = int(os.getenv("CRYSTAL_BALL_WS_PORT", "7346"))


async def _broadcast_async(event: dict):
    with _ws_lock:
        clients = set(_frontend_websockets)
    if not clients:
        return
    msg = json.dumps(event)
    dead = set()
    for ws in clients:
        try:
            await ws.send(msg)
        except Exception:
            dead.add(ws)
    if dead:
        with _ws_lock:
            _frontend_websockets -= dead


def _broadcast_from_mcp(event: dict):
    if _ws_loop is None:
        return
    asyncio.run_coroutine_threadsafe(_broadcast_async(event), _ws_loop)


async def _ws_handler(websocket):
    global _frontend_message

    try:
        addr = getattr(websocket, 'remote_address', None) or str(id(websocket))
    except Exception:
        addr = str(id(websocket))

    with _ws_lock:
        _frontend_websockets.add(websocket)
    logger.info(f"Frontend connected: {addr}")

    try:
        while True:
            try:
                raw_msg = await websocket.recv()
            except Exception:
                break

            try:
                msg = json.loads(raw_msg)
            except json.JSONDecodeError:
                continue

            msg_type = msg.get("type", "")

            if msg_type == "suggest":
                _frontend_message = msg.get("prompt", "")
                _frontend_event.set()
                logger.info(f"Suggestion: {_frontend_message[:80]}...")

            elif msg_type == "ping":
                try:
                    await websocket.send(json.dumps({
                        "type": "pong",
                        "ts": datetime.now().isoformat(),
                    }))
                except Exception:
                    break

            elif msg_type == "connect":
                logger.info(f"Frontend identified: {msg.get('client', 'unknown')}")
                try:
                    await websocket.send(json.dumps({
                        "type": "welcome",
                        "message": "Connected to Crystal Ball MCP bridge",
                    }))
                except Exception:
                    break

    except Exception as e:
        logger.info(f"Frontend disconnected: {addr} ({e})")
    finally:
        with _ws_lock:
            _frontend_websockets.discard(websocket)
        logger.info(f"Frontend removed: {addr}")


async def _start_ws_server():
    if not HAS_WS:
        logger.warning("websockets not installed — frontend bridge disabled")
        return

    async with ws_serve(_ws_handler, "127.0.0.1", WS_PORT):
        logger.info(f"Crystal Ball WS bridge on ws://127.0.0.1:{WS_PORT}")
        await asyncio.Future()


# ─── YOUKNOW Integration ─────────────────────────────────────────

import sys
from pathlib import Path

# Add youknow kernel to Python path
_YOUKNOW_KERNEL_DIR = Path(__file__).parent.parent / "youknow_v225" / "youknow_kernel_current"
if _YOUKNOW_KERNEL_DIR.exists():
    sys.path.insert(0, str(_YOUKNOW_KERNEL_DIR))

# Set HEAVEN_DATA_DIR for persistent domain ontology
_HEAVEN_DATA_DIR = os.getenv("HEAVEN_DATA_DIR", os.path.expanduser("~/Desktop/heaven_data"))
os.environ["HEAVEN_DATA_DIR"] = _HEAVEN_DATA_DIR

# Pre-load Cat_of_Cat so it stays persistent across calls
_youknow_ready = False
try:
    from youknow_kernel.owl_types import get_cat
    from youknow_kernel.compiler import youknow as _youknow_compile
    _cat = get_cat()
    _youknow_ready = True
    logger.info(f"YOUKNOW loaded: {len(_cat.entities)} entities in Cat_of_Cat, HEAVEN_DATA_DIR={_HEAVEN_DATA_DIR}")
except Exception as e:
    logger.warning(f"YOUKNOW not available: {e}")


@mcp.tool()
async def youknow(statement: str) -> str:
    """Compile a statement through the YOUKNOW ontology compiler.

    YOUKNOW is the gnostic kernel. It validates claims against the
    Universal Axiomatic Reality Language (UARL) and admits them to the
    ONT (ontology) or sends them to SOUP (unvalidated) with feedback
    on what's missing.

    This is an iterative process: call youknow(), read what's missing,
    provide it, call again. Each admission builds the ontology.

    The compiler persists to domain.owl — admitted concepts survive
    across server restarts.

    Args:
        statement: A UARL statement like:
            "Dog is_a Animal"
            "Group is_a AlgebraicStructure, analogical_pattern SetWithOperations"
            "X embodies Y"
            "X manifests Y"
            "X reifies Y"
            "X programs Y"

    Returns:
        Compiler result — "OK" if admitted to ONT, or SOUP response
        explaining what's missing and how to fix it.
    """
    if not statement or not statement.strip():
        return json.dumps({
            "error": "Empty statement",
            "hint": "Provide a UARL statement like 'Dog is_a Animal'"
        })

    result = _compile_youknow(statement.strip())
    return json.dumps(result, indent=2)


@mcp.tool()
async def youknow_status() -> str:
    """Check the status of the YOUKNOW ontology compiler.

    Returns the number of entities in Cat_of_Cat, the domain.owl path,
    and a list of all known entity names.
    """
    if not _youknow_ready:
        return json.dumps({"ready": False, "error": "YOUKNOW not loaded"})

    return json.dumps({
        "ready": True,
        "cat_of_cat_entities": len(_cat.entities),
        "heaven_data_dir": _HEAVEN_DATA_DIR,
        "domain_owl": str(Path(_HEAVEN_DATA_DIR) / "ontology" / "domain.owl"),
        "domain_owl_exists": (Path(_HEAVEN_DATA_DIR) / "ontology" / "domain.owl").exists(),
        "entity_names": sorted(_cat.entities.keys()),
    }, indent=2)


# ─── Main ─────────────────────────────────────────────────────────

def main():
    def run_ws_bridge():
        global _ws_loop
        loop = asyncio.new_event_loop()
        _ws_loop = loop
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_start_ws_server())

    bridge_thread = threading.Thread(target=run_ws_bridge, daemon=True)
    bridge_thread.start()
    logger.info(f"WS bridge starting on port {WS_PORT}")

    mcp.run()


if __name__ == "__main__":
    main()

