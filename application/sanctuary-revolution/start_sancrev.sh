#!/bin/bash
# SANCREV Entry Point (extends CAVE)
# Start sancrev daemon and attach to tmux session
#
# IDEMPOTENT: kills everything before restarting. Safe to run multiple times.

set -e

# Configuration
SESSION="${CAVE_SESSION:-cave}"
WORKDIR="${CAVE_WORKDIR:-$(pwd)}"
AGENT_CMD="${CAVE_AGENT_CMD:-claude --debug}"
PORT="${CAVE_PORT:-8080}"
HEAVEN_DATA="${HEAVEN_DATA_DIR:-/tmp/heaven_data}"

# ============================================================================
# CLEAN KILL — stop everything before starting fresh
# ============================================================================
echo "   Cleaning up previous processes..."

# Kill CAVE/sancrev http_server
if [ -f /tmp/cave.pid ]; then
    kill "$(cat /tmp/cave.pid)" 2>/dev/null || true
    rm -f /tmp/cave.pid
fi
pkill -f "sanctuary_revolution.harness.server.http_server" 2>/dev/null || true
pkill -f "start_sancrev.py" 2>/dev/null || true

# Kill organ daemon
ORGAN_PID_FILE="${HEAVEN_DATA}/organ_daemon.pid"
if [ -f "$ORGAN_PID_FILE" ]; then
    kill "$(cat "$ORGAN_PID_FILE")" 2>/dev/null || true
    rm -f "$ORGAN_PID_FILE"
fi
pkill -f "cave.core.organ_daemon" 2>/dev/null || true

# Kill OMNISANC daemon
OMNISANC_DAEMON_PID_FILE="/tmp/omnisanc_daemon.pid"
if [ -f "$OMNISANC_DAEMON_PID_FILE" ]; then
    kill "$(cat "$OMNISANC_DAEMON_PID_FILE")" 2>/dev/null || true
    rm -f "$OMNISANC_DAEMON_PID_FILE"
fi
pkill -f "omnisanc_core_daemon/daemon.py" 2>/dev/null || true
pkill -f "omnisanc_core_daemon/omnisanc_logic.py" 2>/dev/null || true
rm -f /tmp/omnisanc.sock

# Kill skill watcher daemon
SKILL_WATCHER_PID_FILE="${HEAVEN_DATA}/skill_watcher.pid"
if [ -f "$SKILL_WATCHER_PID_FILE" ]; then
    kill "$(cat "$SKILL_WATCHER_PID_FILE")" 2>/dev/null || true
    rm -f "$SKILL_WATCHER_PID_FILE"
fi
pkill -f "skill_watcher_daemon.py" 2>/dev/null || true

# Let everything die
sleep 1
echo "   Previous processes cleaned."

# Clear all python caches (NON-NEGOTIABLE after pip install)
SP="/home/GOD/.pyenv/versions/3.11.6/lib/python3.11/site-packages"
for pkg in sanctuary_revolution cave observatory carton_mcp heaven_base conductor; do
    find "$SP/$pkg" -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
done
find /tmp/sanctuary-revolution -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
find /tmp/cave -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
echo "   Python caches cleared."

# ============================================================================
# START FRESH
# ============================================================================

# Start sancrev daemon in background (CAVEHTTPServer + SancrevExtension)
CAVE_PORT="$PORT" python /tmp/sanctuary-revolution/start_sancrev.py > /tmp/cave_daemon.log 2>&1 &
CAVE_PID=$!
echo $CAVE_PID > /tmp/cave.pid
echo "   Daemon started (PID: $CAVE_PID, port: $PORT)"

# Wait for server to be ready
echo "   Waiting for server..."
for i in {1..30}; do
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
python -m cave.core.organ_daemon > /tmp/organ_daemon.log 2>&1 &
ORGAN_PID=$!
echo $ORGAN_PID > "$ORGAN_PID_FILE"
echo "   Organ daemon started (PID: $ORGAN_PID, log: /tmp/organ_daemon.log)"

# Start OMNISANC daemon (enforcement layer: hook routing, state machine)
python3 /home/GOD/omnisanc_core_daemon/daemon.py start > /tmp/omnisanc_daemon.log 2>&1 &
sleep 1
if [ -f "$OMNISANC_DAEMON_PID_FILE" ]; then
    echo "   OMNISANC daemon started (PID: $(cat "$OMNISANC_DAEMON_PID_FILE"), log: /tmp/omnisanc_daemon.log)"
else
    echo "   WARNING: OMNISANC daemon may not have started (no PID file)"
fi

# Start skill watcher daemon (skill RAG ingestion: monitors /skills for changes)
python3 /home/GOD/skill_manager_mcp/skill_watcher_daemon.py > /tmp/skill_watcher.log 2>&1 &
SKILL_WATCHER_PID=$!
echo $SKILL_WATCHER_PID > "$SKILL_WATCHER_PID_FILE"
echo "   Skill watcher daemon started (PID: $SKILL_WATCHER_PID, log: /tmp/skill_watcher.log)"

# CartON MCP: SKIPPED (use Claude's stdio MCP instead)
echo "   CartON MCP: SKIPPED (use Claude's stdio MCP instead)"

# Score compiler: SKIPPED
echo "   Score compiler: SKIPPED"

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
