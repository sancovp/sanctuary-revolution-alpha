#!/usr/bin/env bash
# Call GNOSYS (Claude Code) from Conductor.
# Routes through CAVE /self/inject endpoint → tmux
# Usage: call_gnosys.sh "Your task prompt"
#        call_gnosys.sh --file /path/to/prompt

set -euo pipefail

CAVE_URL="${CAVE_URL:-http://localhost:8080}"
PROMPT=""

# Parse args
while [[ $# -gt 0 ]]; do
    case "$1" in
        --file)
            if [[ -z "$2" ]]; then
                echo "ERROR: --file requires a path" >&2
                exit 1
            fi
            PROMPT=$(cat "$2")
            shift 2
            ;;
        --*)
            echo "Unknown option: $1" >&2
            exit 1
            ;;
        *)
            PROMPT="$1"
            shift
            ;;
    esac
done

if [[ -z "$PROMPT" ]]; then
    echo "Usage: call_gnosys.sh [OPTIONS] <prompt>" >&2
    echo "  --file <path>" >&2
    exit 1
fi

# Prepend Conductor: to message
CONDUCTOR_MSG="Conductor: $PROMPT"

# Inject with Conductor: prefix
PAYLOAD=$(python3 -c "import json, sys; print(json.dumps({'message': sys.argv[1], 'press_enter': True}))" "$CONDUCTOR_MSG")

RESPONSE=$(curl -s -X POST "${CAVE_URL}/self/inject" \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD" \
    --max-time 10)

STATUS=$(echo "$RESPONSE" | python3 -c "import json, sys; print(json.load(sys.stdin).get('status', 'error'))" 2>/dev/null || echo "error")

if [[ "$STATUS" == "delivered" ]]; then
    echo "OK, conductor_action: $PROMPT"
fi
