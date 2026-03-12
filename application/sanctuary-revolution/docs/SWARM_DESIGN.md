# HEAVEN Swarm: Multi-Agent Team Orchestration

## Status: DESIGN (not implemented)

## Overview

A **swarm** is a team of N agents orchestrated through the sancrev HTTP server.
Each agent runs in its own tmux session. The server acts as the message bus —
routing messages between agents via file-based inboxes.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│              Sancrev HTTP Server (:8080)             │
│                                                      │
│  In-memory state:                                    │
│    swarms: {                                         │
│      "research_team": {                              │
│        agents: {                                     │
│          "leader":  {session, status, inbox_path}    │
│          "coder":   {session, status, inbox_path}    │
│          "analyst": {session, status, inbox_path}    │
│        }                                             │
│      }                                               │
│    }                                                 │
│                                                      │
│  Endpoints:                                          │
│    POST /swarm/start     → create swarm from config  │
│    POST /swarm/send      → route msg to agent inbox  │
│    POST /swarm/broadcast → msg to all teammates      │
│    GET  /swarm/status    → agent statuses            │
│    POST /swarm/stop      → kill all tmux sessions    │
│    GET  /swarm/inbox/:name → read agent's inbox      │
│                                                      │
│  Background loops:                                   │
│    _swarm_delivery_loop() → poll inboxes, deliver    │
│                                                      │
└──────────┬──────────────────────────┬────────────────┘
           │                          │
     ┌─────▼─────┐             ┌─────▼─────┐
     │ Agent A   │             │ Agent B   │
     │ (tmux)    │             │ (tmux)    │
     │           │             │           │
     │ CodeAgent │             │ CodeAgent │
     │ actor     │             │ actor     │
     │           │             │           │
     │ SENDS via:│             │ SENDS via:│
     │  skill    │             │  skill    │
     │  (curl)   │             │  (curl)   │
     │           │             │           │
     │ RECEIVES: │             │ RECEIVES: │
     │ • stop    │             │ • stop    │
     │   hook    │             │   hook    │
     │ • tmux    │             │ • tmux    │
     │   inject  │             │   inject  │
     │   (idle)  │             │   (idle)  │
     └───────────┘             └───────────┘
```

## Components

### 1. HTTP Endpoints (added to http_server.py)

#### `POST /swarm/start`
```json
{
  "config": {
    "swarm_name": "research_team",
    "leader": {"name": "leader", "agent_config": "lead_researcher"},
    "teammates": [
      {"name": "coder", "agent_config": "heaven_coder_agent"},
      {"name": "analyst", "agent_config": "analysis_agent"}
    ]
  }
}
```
- Creates a `CodeAgent` for each member
- Each gets a tmux session: `swarm_<swarm_name>_<agent_name>`
- Spawns the agent command in each session
- Registers the swarm in server state

#### `POST /swarm/send`
```json
{
  "swarm_name": "research_team",
  "to": "coder",
  "message": "Analyze the auth module",
  "from": "leader",
  "priority": 0
}
```
- Writes message to the target agent's inbox file
- Server's delivery loop picks it up

#### `POST /swarm/broadcast`
```json
{
  "swarm_name": "research_team",
  "message": "Status update: phase 1 complete",
  "from": "leader",
  "exclude": ["leader"],
  "priority": 0
}
```

#### `GET /swarm/status`
```json
{
  "swarm_name": "research_team"
}
```
Returns agent statuses: idle/busy, inbox count, tmux session alive.

#### `POST /swarm/stop`
Kills all tmux sessions for the swarm.

### 2. Message Delivery Loop (`_swarm_delivery_loop`)

Background async task (same pattern as `_conductor_inbox_loop`):

```python
async def _swarm_delivery_loop():
    """Poll all swarm agent inboxes and deliver messages."""
    while True:
        for swarm_name, swarm in swarm_state.items():
            for agent_name, agent_info in swarm["agents"].items():
                msg = _dequeue_swarm_inbox(swarm_name, agent_name)
                if msg:
                    if agent_info["status"] == "idle":
                        # Agent is waiting — inject via tmux
                        _tmux_send_keys(agent_info["session"], msg["content"])
                    else:
                        # Agent is busy — queue for stop hook injection
                        agent_info["pending_messages"].append(msg)
        await asyncio.sleep(2.0)  # Same cadence as conductor
```

### 3. Agent Message Sending (Skill)

Agents send messages via a skill that curls the server:

**Skill: `swarm-send-message`**
```bash
# Send a message to a teammate
curl -s -X POST http://localhost:8080/swarm/send \
  -H "Content-Type: application/json" \
  -d "{\"swarm_name\": \"$SWARM_NAME\", \"to\": \"$1\", \"message\": \"$2\", \"from\": \"$AGENT_NAME\"}"
```

Or agents use BashTool to call this directly.

### 4. Agent Message Receiving

Two paths:

**Path A: Stop Hook (agent is mid-turn)**
- When an agent finishes a turn, the server's stop hook checks for pending messages
- If messages exist, they get injected into the agent's context before the next turn
- Prevents the agent from going idle when work is waiting

**Path B: tmux Injection (agent is idle)**
- When an agent is idle (waiting for input), and a message arrives
- The delivery loop uses `tmux send-keys` to inject the message directly
- Agent processes it as if the user typed it

### 5. Idle Detection

An agent is "idle" when:
- Its tmux pane shows a prompt/input marker
- It hasn't produced output for N seconds
- It explicitly calls itself idle (via a tool or stop hook)

The server can detect this by periodically capturing the pane and checking for the prompt marker.

## File Layout

```
HEAVEN_DATA_DIR/swarm/
├── research_team/
│   ├── swarm_state.json          # Swarm config + agent sessions
│   ├── leader_inbox.jsonl        # Leader's message inbox (append-only)
│   ├── coder_inbox.jsonl         # Coder's inbox
│   └── analyst_inbox.jsonl       # Analyst's inbox
```

Inbox format (JSONL — one message per line):
```json
{"id": "msg_001", "from": "leader", "content": "Analyze auth module", "priority": 0, "ts": "2026-03-06T08:00:00Z", "delivered": false}
```

## Integration Points

### SwarmTool (heaven_base/tools/swarm_tool.py)
- BaseHeavenTool that curls the sancrev server endpoints
- Agents use this to start/manage swarms
- Already created via `make_heaven_tool_from_docstring`

### Conductor
- Conductor gets SwarmTool in its tools list
- Can start swarms, send messages, check status
- Receives swarm status updates through its own inbox

### CodeAgent (sanctuary_revolution/harness/core/agent.py)
- Already has: inbox (deque), tmux control, message types
- Just needs: file-based inbox persistence, stop hook integration

### Existing Patterns to Follow
- `_conductor_inbox_loop()` — same polling pattern for swarm delivery
- `_dequeue_file_inbox()` — same file dequeue for swarm inboxes
- `/conductor/message` endpoint — same pattern for `/swarm/send`

## Config Format

```json
{
  "swarm_name": "research_team",
  "leader": {
    "name": "leader",
    "agent_config": "lead_researcher",
    "system_prompt_suffix": "You are the team leader. Use the swarm-send-message skill to coordinate."
  },
  "teammates": [
    {
      "name": "coder",
      "agent_config": "heaven_coder_agent",
      "system_prompt_suffix": "You are the coding specialist. Use swarm-send-message to report findings."
    },
    {
      "name": "analyst",
      "agent_config": "analysis_agent",
      "system_prompt_suffix": "You are the data analyst. Use swarm-send-message to share insights."
    }
  ]
}
```

## What Exists Already

| Component | Status | Location |
|-----------|--------|----------|
| CodeAgent (Actor model) | ✅ Done | `sanctuary_revolution/harness/core/agent.py` |
| Inbox + message types | ✅ Done | Same file |
| tmux session management | ✅ Done | Same file |
| Heartbeat loop | ✅ Done | `harness/server/heartbeat_loop.py` |
| Conductor inbox pattern | ✅ Done | `harness/server/http_server.py` |
| SwarmTool (BaseHeavenTool) | ✅ Done | `heaven_base/tools/swarm_tool.py` (needs rewire to HTTP) |
| ChainTool (BaseHeavenTool) | ✅ Done | `heaven_base/tools/chain_tool.py` |
| ConstrainedBashTool | ✅ Done | `heaven_base/tools/constrained_bash_tool.py` |
| tmux.swarm.conf | ✅ Done | `heaven_base/swarm/tmux.swarm.conf` |
| Example config | ✅ Done | `examples/swarm_config.json` |
| HTTP endpoints | ❌ TODO | Add to `http_server.py` |
| Delivery loop | ❌ TODO | Add to `http_server.py` |
| Send-message skill | ❌ TODO | Create in skills catalog |
| Stop hook integration | ❌ TODO | Wire into agent turn lifecycle |
| Idle detection | ❌ TODO | Pane capture + prompt detection |
| SwarmTool HTTP rewire | ❌ TODO | Change from direct to curl-based |
