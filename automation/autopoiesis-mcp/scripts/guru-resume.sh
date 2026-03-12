#!/bin/bash
# Resume guru loop - sets status to active in /tmp/guru_loop.md

GURU_FILE="/tmp/guru_loop.md"

if [ ! -f "$GURU_FILE" ]; then
    echo "ERROR: No guru loop to resume. File not found: $GURU_FILE"
    exit 1
fi

# Read current content
CONTENT=$(cat "$GURU_FILE")

# Check if already active
if echo "$CONTENT" | grep -q "^status: active"; then
    echo "Guru loop is already active."
    exit 0
fi

# Replace status: paused with status: active
NEW_CONTENT=$(echo "$CONTENT" | sed 's/^status: paused/status: active/')

echo "$NEW_CONTENT" > "$GURU_FILE"

echo "Guru loop RESUMED."
echo "The bodhisattva vow is now enforced again."
echo "You must emanate before exit."
