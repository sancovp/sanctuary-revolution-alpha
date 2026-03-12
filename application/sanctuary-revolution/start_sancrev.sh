#!/bin/bash
# SANCREV Entry Point (extends CAVE)
# Start sancrev daemon and attach to tmux session

set -e

# Configuration
SESSION="${CAVE_SESSION:-cave}"
WORKDIR="${CAVE_WORKDIR:-$(pwd)}"
AGENT_CMD="${CAVE_AGENT_CMD:-claude --debug}"
PORT="${CAVE_PORT:-8080}"

# Start sancrev daemon in background (includes all CAVE routes + game domain)
python -m sanctuary_revolution.harness.server.http_server --port "$PORT" > /tmp/cave_daemon.log 2>&1 &
CAVE_PID=$!
echo $CAVE_PID > /tmp/cave.pid
echo "   Daemon started (PID: $CAVE_PID, port: $PORT)"

# Wait for server to be ready
echo "   Waiting for server..."
for i in {1..10}; do
    if curl -s "http://localhost:$PORT/health" > /dev/null 2>&1; then
        echo "   Server ready!"
        break
    fi
    sleep 1
done

# Check if server started successfully
if ! curl -s "http://localhost:$PORT/health" > /dev/null 2>&1; then
    echo "Failed to start sancrev server"
    kill $CAVE_PID 2>/dev/null
    exit 1
fi

# Start organ daemon (perception layer: Discord polling, sanctum rituals, RNG events)
ORGAN_PID_FILE="${HEAVEN_DATA_DIR:-/tmp/heaven_data}/organ_daemon.pid"
if [ -f "$ORGAN_PID_FILE" ] && kill -0 "$(cat "$ORGAN_PID_FILE")" 2>/dev/null; then
    echo "   Organ daemon already running (PID: $(cat "$ORGAN_PID_FILE"))"
else
    rm -f "$ORGAN_PID_FILE"
    python -m cave.core.organ_daemon > /tmp/organ_daemon.log 2>&1 &
    echo "   Organ daemon started (PID: $!, log: /tmp/organ_daemon.log)"
fi

# Start OMNISANC daemon (enforcement layer: hook routing, state machine)
# daemon.py manages its own PID file at /tmp/omnisanc_daemon.pid and socket at /tmp/omnisanc.sock
OMNISANC_DAEMON_PID_FILE="/tmp/omnisanc_daemon.pid"
if [ -f "$OMNISANC_DAEMON_PID_FILE" ] && kill -0 "$(cat "$OMNISANC_DAEMON_PID_FILE")" 2>/dev/null; then
    echo "   OMNISANC daemon already running (PID: $(cat "$OMNISANC_DAEMON_PID_FILE"))"
else
    # Kill any stale omnisanc processes before starting fresh
    pkill -f "omnisanc_core_daemon/daemon.py" 2>/dev/null || true
    pkill -f "omnisanc_core_daemon/omnisanc_logic.py" 2>/dev/null || true
    rm -f "$OMNISANC_DAEMON_PID_FILE" /tmp/omnisanc.sock
    sleep 1
    python3 /home/GOD/omnisanc_core_daemon/daemon.py start > /tmp/omnisanc_daemon.log 2>&1 &
    sleep 1
    if [ -f "$OMNISANC_DAEMON_PID_FILE" ]; then
        echo "   OMNISANC daemon started (PID: $(cat "$OMNISANC_DAEMON_PID_FILE"), log: /tmp/omnisanc_daemon.log)"
    else
        echo "   WARNING: OMNISANC daemon may not have started (no PID file)"
    fi
fi

# Start skill watcher daemon (skill RAG ingestion: monitors /skills for changes)
SKILL_WATCHER_PID_FILE="${HEAVEN_DATA_DIR:-/tmp/heaven_data}/skill_watcher.pid"
if [ -f "$SKILL_WATCHER_PID_FILE" ] && kill -0 "$(cat "$SKILL_WATCHER_PID_FILE")" 2>/dev/null; then
    echo "   Skill watcher daemon already running (PID: $(cat "$SKILL_WATCHER_PID_FILE"))"
else
    rm -f "$SKILL_WATCHER_PID_FILE"
    python3 /home/GOD/skill_manager_mcp/skill_watcher_daemon.py > /tmp/skill_watcher.log 2>&1 &
    SKILL_WATCHER_PID=$!
    echo $SKILL_WATCHER_PID > "$SKILL_WATCHER_PID_FILE"
    echo "   Skill watcher daemon started (PID: $SKILL_WATCHER_PID, log: /tmp/skill_watcher.log)"
fi

# Start CartON MCP server (SSE transport on port 8000)
CARTON_PID_FILE="${HEAVEN_DATA_DIR:-/tmp/heaven_data}/carton_mcp.pid"
if [ -f "$CARTON_PID_FILE" ] && kill -0 "$(cat "$CARTON_PID_FILE")" 2>/dev/null; then
    echo "   CartON MCP already running (PID: $(cat "$CARTON_PID_FILE"))"
else
    rm -f "$CARTON_PID_FILE"
    carton-mcp > /tmp/carton_mcp.log 2>&1 &
    CARTON_PID=$!
    echo $CARTON_PID > "$CARTON_PID_FILE"
    echo "   CartON MCP started (PID: $CARTON_PID, port: 8000, log: /tmp/carton_mcp.log)"
    # Wait for SSE server to be ready
    for i in {1..10}; do
        if curl -s "http://localhost:8000/sse" --max-time 1 > /dev/null 2>&1; then
            echo "   CartON MCP ready!"
            break
        fi
        sleep 1
    done
fi

# Attach to tmux session or create new one
if tmux -u has-session -t "$SESSION" 2>/dev/null; then
    echo "   Attaching to existing session: $SESSION"
    tmux -u attach -t "$SESSION"
else
    echo "   Creating new session: $SESSION"
    tmux -u new-session -d -s "$SESSION" -c "$WORKDIR"
    tmux send-keys -t "$SESSION" "$AGENT_CMD" Enter
    tmux -u attach -t "$SESSION"
fi

echo "CAVE session ended (daemon still running)"
echo "   To stop daemon: ./stop_cave.sh"
