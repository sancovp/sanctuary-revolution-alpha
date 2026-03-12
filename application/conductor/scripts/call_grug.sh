#!/usr/bin/env bash
# Call Grug (Claude Code on separate container) from Conductor.
# Cross-container via docker exec + tmux.
#
# Usage:
#   call_grug.sh "Code task prompt"
#
# Sends prompt to Grug's container tmux session.
# Conductor polls for GRUG_DONE signal separately via ClaudePConnector.

set -euo pipefail

GRUG_CONTAINER="${GRUG_CONTAINER:-repo-lord}"
GRUG_TMUX="${GRUG_TMUX_SESSION:-lord}"

if [[ -z "${1:-}" ]]; then
    echo "Usage: call_grug.sh <prompt>" >&2
    exit 1
fi

PROMPT="$1"

# Check container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${GRUG_CONTAINER}$"; then
    echo "ERROR: Container '$GRUG_CONTAINER' not running" >&2
    exit 2
fi

# Send to Grug's tmux session inside the container
docker exec "$GRUG_CONTAINER" tmux send-keys -t "$GRUG_TMUX" "$PROMPT" Enter

echo "OK: Prompt sent to $GRUG_CONTAINER:$GRUG_TMUX (${#PROMPT} chars)"
