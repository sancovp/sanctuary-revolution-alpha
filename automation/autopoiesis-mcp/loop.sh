#!/bin/bash
# Ralph Wiggum Loop - Autonomous coding system
# Usage: ./loop.sh [plan|build] [max_iterations]
# Examples:
#   ./loop.sh           # Build mode, infinite
#   ./loop.sh plan      # Planning mode, infinite
#   ./loop.sh build 20  # Build mode, max 20 iterations
#   ./loop.sh plan 5    # Planning mode, max 5 iterations

set -e

MODE="${1:-build}"
MAX_ITERATIONS="${2:-0}"
ITERATION=0

# Select prompt file based on mode
case "$MODE" in
    plan)
        PROMPT_FILE="PROMPT_plan.md"
        echo "Starting PLANNING mode..."
        ;;
    build|*)
        PROMPT_FILE="PROMPT_build.md"
        echo "Starting BUILDING mode..."
        ;;
esac

# Verify prompt file exists
if [ ! -f "$PROMPT_FILE" ]; then
    echo "ERROR: $PROMPT_FILE not found"
    exit 1
fi

echo "Prompt: $PROMPT_FILE"
echo "Max iterations: ${MAX_ITERATIONS:-infinite}"
echo "---"

# The loop
while :; do
    ITERATION=$((ITERATION + 1))
    echo "=== Iteration $ITERATION ==="

    # Run claude with the prompt
    cat "$PROMPT_FILE" | claude -p \
        --dangerously-skip-permissions \
        --model opus

    # Push after each iteration (building mode usually commits)
    git push origin "$(git branch --show-current)" 2>/dev/null || true

    # Check max iterations
    if [ "$MAX_ITERATIONS" -gt 0 ] && [ "$ITERATION" -ge "$MAX_ITERATIONS" ]; then
        echo "Reached max iterations ($MAX_ITERATIONS)"
        break
    fi

    echo "--- Iteration $ITERATION complete, restarting with fresh context ---"
    sleep 2
done

echo "Ralph loop finished after $ITERATION iterations"
