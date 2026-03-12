#!/bin/bash

# Autopoiesis Stop Script
# Cancels the active autopoiesis loop by archiving the promise

set -euo pipefail

if [[ -f /tmp/active_promise.md ]]; then
  ITERATION=$(grep '^iteration:' /tmp/active_promise.md | sed 's/iteration: *//' || echo "unknown")
  mkdir -p /tmp/promise_history
  mv /tmp/active_promise.md "/tmp/promise_history/cancelled_$(date +%Y%m%d_%H%M%S).md"
  echo "✓ Cancelled autopoiesis loop (was at iteration $ITERATION)"
  echo ""
  echo "Promise archived to /tmp/promise_history/"
else
  echo "No active autopoiesis loop found."
fi
