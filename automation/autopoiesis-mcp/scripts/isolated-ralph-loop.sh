#!/bin/bash
# Isolated Ralph Loop - Wrapper for ralph-orchestrator
# Uses the SDK-based orchestrator for proper isolation

cd /tmp/ralph-orchestrator

# Pass all arguments to ralph
ralph -a claude "$@"
