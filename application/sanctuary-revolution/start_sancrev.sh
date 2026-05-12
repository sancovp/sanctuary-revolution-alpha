#!/bin/bash
# SANCREV Entry Point (extends CAVE)
# Start sancrev daemon and attach to tmux session
#
# IDEMPOTENT: kills everything before restarting. Safe to run multiple times.

set -e

# Resolve script directory (no hardcoded paths)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Source env (API keys + Neo4j creds). Spawnee bootstrap inside each
# Python daemon is the primary defense (see spawnee-side-env-bootstrap.md),
# but exporting here means subprocesses get a sane baseline even before
# they call _get_strata_carton_env. :- defaults preserve any caller overrides.
source /home/GOD/system_config.sh 2>/dev/null || true
export NEO4J_URI="${NEO4J_URI:-bolt://host.docker.internal:7687}"
export NEO4J_USER="${NEO4J_USER:-neo4j}"
export NEO4J_PASSWORD="${NEO4J_PASSWORD:-password}"
export HEAVEN_DATA_DIR="${HEAVEN_DATA_DIR:-/tmp/heaven_data}"
export CHROMA_PERSIST_DIR="${CHROMA_PERSIST_DIR:-/tmp/carton_chroma_db}"

# Configuration
SESSION="${CAVE_SESSION:-cave}"
WORKDIR="${CAVE_WORKDIR:-$(pwd)}"
AGENT_CMD="${CAVE_AGENT_CMD:-claude --debug}"
PORT="${CAVE_PORT:-8080}"
HEAVEN_DATA="${HEAVEN_DATA_DIR:-/tmp/heaven_data}"

echo ""
echo "  ============================================================"
echo "    WAKING DREAMER — Compound Intelligence Boot Sequence"
echo "  ============================================================"
echo ""

# ============================================================================
# CLEAN KILL — stop everything before starting fresh
# ============================================================================
echo "  [1/7] Clearing previous incarnation..."

# Container-default services that squat sancrev ports.
# This container is the Anthropic computer-use-demo image; on container boot
# it auto-launches:
#   - /home/GOD/core/image/http_server.py on :8080 (the CAVE port) — old HEAVEN API
#   - streamlit on :8501 (computer_use_demo UI)
#   - websockify on :6080 (noVNC bridge to :5900)
# Without these kills, CAVE bring-up below silently fails on EADDRINUSE
# while the broken curl-s health check returns 0 from the demo's 404 page.
pkill -f "bin/python http_server\.py" 2>/dev/null || true
pkill -f "computer_use_demo/streamlit\.py" 2>/dev/null || true
pkill -f "websockify.*noVNC" 2>/dev/null || true

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

# Kill observation worker daemon (carton relaunches it on MCP connect)
pkill -f "observation_worker_daemon" 2>/dev/null || true

# Kill score compiler daemon
SCORE_COMPILER_PID_FILE="${HEAVEN_DATA}/score_compiler.pid"
if [ -f "$SCORE_COMPILER_PID_FILE" ]; then
    kill "$(cat "$SCORE_COMPILER_PID_FILE")" 2>/dev/null || true
    rm -f "$SCORE_COMPILER_PID_FILE"
fi
pkill -f "starlog_mcp.score_compiler" 2>/dev/null || true

# Let everything die
sleep 1

# Clear all python caches (NON-NEGOTIABLE after pip install)
SP="/home/GOD/.pyenv/versions/3.11.6/lib/python3.11/site-packages"
for pkg in sanctuary_revolution cave observatory carton_mcp heaven_base conductor; do
    find "$SP/$pkg" -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
done
find "$SCRIPT_DIR" -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
find /tmp/cave -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
echo "        Previous world dissolved. Caches purged."

# Kill YOUKNOW daemon
pkill -f "youknow_kernel.daemon" 2>/dev/null || true
sleep 1

# ============================================================================
# START FRESH
# ============================================================================

echo ""
echo "  [2/8] Starting YOUKNOW daemon..."
python3 -m youknow_kernel.daemon > /tmp/youknow_daemon.log 2>&1 &
YOUKNOW_PID=$!
echo $YOUKNOW_PID > "${HEAVEN_DATA}/youknow_daemon.pid"

# Wait for YOUKNOW to be ready (required — nothing works without validation)
for i in {1..15}; do
    if curl -s "http://localhost:8102/health" > /dev/null 2>&1; then
        echo "        YOUKNOW daemon online — port 8102, PID $YOUKNOW_PID"
        break
    fi
    sleep 1
done

if ! curl -s "http://localhost:8102/health" > /dev/null 2>&1; then
    echo "        FATAL: YOUKNOW daemon failed to start. Cannot proceed without validation."
    echo "        Check /tmp/youknow_daemon.log"
    kill $YOUKNOW_PID 2>/dev/null
    exit 1
fi

echo ""
echo "  [3/8] Initializing CAVE body..."
CAVE_PORT="$PORT" python "$SCRIPT_DIR/start_sancrev.py" > /tmp/cave_daemon.log 2>&1 &
CAVE_PID=$!
echo $CAVE_PID > /tmp/cave.pid

# Wait for server to be ready
for i in {1..30}; do
    if curl -s "http://localhost:$PORT/health" > /dev/null 2>&1; then
        break
    fi
    sleep 1
done

# Check if server started successfully
if ! curl -s "http://localhost:$PORT/health" > /dev/null 2>&1; then
    echo "        FATAL: CAVE body failed to materialize"
    kill $CAVE_PID 2>/dev/null
    exit 1
fi
echo "        CAVE body online — port $PORT, PID $CAVE_PID"

echo ""
echo "  [4/8] Wiring organs..."
python -m cave.core.organ_daemon > /tmp/organ_daemon.log 2>&1 &
ORGAN_PID=$!
echo $ORGAN_PID > "$ORGAN_PID_FILE"
echo "        Perception layer active — Discord, rituals, RNG"

echo ""
echo "  [5/8] Engaging OMNISANC enforcement..."
python3 /home/GOD/omnisanc_core_daemon/daemon.py start > /tmp/omnisanc_daemon.log 2>&1 &
sleep 1
if [ -f "$OMNISANC_DAEMON_PID_FILE" ]; then
    echo "        OMNISANC online — state machine enforcing"
else
    echo "        WARNING: OMNISANC failed to engage"
fi

echo ""
echo "  [6/8] Loading skill matrix..."
python3 /home/GOD/skill_manager_mcp/skill_watcher_daemon.py > /tmp/skill_watcher.log 2>&1 &
SKILL_WATCHER_PID=$!
echo $SKILL_WATCHER_PID > "$SKILL_WATCHER_PID_FILE"
echo "        Skill watcher scanning — RAG ingestion active"

echo ""
echo "  [7/8] Compiling starsystem scores..."
echo "        Querying Neo4j for all starsystems..."
python3 -m starlog_mcp.score_compiler 2>&1 | while IFS= read -r line; do echo "        $line"; done || echo "        WARNING: Initial score compilation failed"
echo "        Starting score compiler daemon (10min cycle)..."
python3 -m starlog_mcp.score_compiler --daemon > /tmp/score_compiler.log 2>&1 &
SCORE_COMPILER_PID=$!
echo $SCORE_COMPILER_PID > "$SCORE_COMPILER_PID_FILE"
echo "        Kardashev map compiled — daemon running"

echo ""
echo "  [8/8] Populating agents..."
AGENT_COUNT=$(curl -s "http://localhost:$PORT/cave_agents" 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d))" 2>/dev/null || echo "?")
echo "        $AGENT_COUNT agents registered"

echo ""
echo "  ============================================================"
echo "    All systems nominal. Going to Sanctuary..."
echo "  ============================================================"
echo ""

# Attach to tmux session or create new one
if tmux -u has-session -t "$SESSION" 2>/dev/null; then
    tmux -u attach -t "$SESSION"
else
    tmux -u new-session -d -s "$SESSION" -c "$WORKDIR"
    tmux send-keys -t "$SESSION" "$AGENT_CMD" Enter
    tmux -u attach -t "$SESSION"
fi
