#!/bin/bash
# Pause guru loop - sets status to paused in /tmp/guru_loop.md

GURU_FILE="/tmp/guru_loop.md"

if [ ! -f "$GURU_FILE" ]; then
    echo "ERROR: No guru loop active. File not found: $GURU_FILE"
    exit 1
fi

# Read current content
CONTENT=$(cat "$GURU_FILE")

# Check if already paused
if echo "$CONTENT" | grep -q "^status: paused"; then
    echo "Guru loop is already paused."
    exit 0
fi

# Replace status: active with status: paused
NEW_CONTENT=$(echo "$CONTENT" | sed 's/^status: active/status: paused/')

echo "$NEW_CONTENT" > "$GURU_FILE"

echo "Guru loop PAUSED."
echo "The stop hook will now allow exit without emanation."
echo "Use /guru-resume to continue the vow."
