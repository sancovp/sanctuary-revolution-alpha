#!/bin/bash
# Setup guru loop - creates /tmp/guru_loop.md with emanation enforcement
# Usage: setup-guru.sh TARGET_LEVEL [CONTEXT_FILES...]
#
# TARGET_LEVEL: L1, L2, L3, L4, L5, L6 (complexity ladder)
# CONTEXT_FILES: Optional paths to implementation plan, spec, etc.
#
# Task comes from STARSHIP course (course_linked: true)

TARGET_LEVEL="$1"
shift
CONTEXT_FILES=("$@")

if [ -z "$TARGET_LEVEL" ]; then
    echo "ERROR: No target level provided"
    echo "Usage: setup-guru.sh TARGET_LEVEL [CONTEXT_FILES...]"
    echo ""
    echo "TARGET_LEVEL options:"
    echo "  L1 - Skill only"
    echo "  L2 - Skill + Flight"
    echo "  L3 - Skill + Flight + MCP"
    echo "  L4 - Persona (frame + skillset + MCP set)"
    echo "  L5 - Scoring + Goldenization"
    echo "  L6 - Deployed product"
    exit 1
fi

# Build context_files YAML list
CONTEXT_YAML=""
if [ ${#CONTEXT_FILES[@]} -gt 0 ]; then
    CONTEXT_YAML="context_files:"
    for f in "${CONTEXT_FILES[@]}"; do
        CONTEXT_YAML="$CONTEXT_YAML
  - $f"
    done
fi

# Create guru loop file
cat > /tmp/guru_loop.md << EOF
---
created: $(date -Iseconds)
status: active
course_linked: true
target_level: $TARGET_LEVEL
$CONTEXT_YAML
---

# Emanation Enforcement Active

Task inherited from STARSHIP course.
Target complexity level: $TARGET_LEVEL

Use STARLOG to track progress and decisions.
Keep an implementation plan document in the project directory.
EOF

echo "Guru loop activated at /tmp/guru_loop.md"
echo "Target level: $TARGET_LEVEL"
if [ ${#CONTEXT_FILES[@]} -gt 0 ]; then
    echo "Context files:"
    for f in "${CONTEXT_FILES[@]}"; do
        echo "  - $f"
    done
fi
echo ""
echo "The stop hook will now enforce the bodhisattva vow."
echo "You must complete the course task AND build an emanation at level $TARGET_LEVEL."
echo "Exit with <vow>ABSOLVED</vow> when ready for samaya gate."
