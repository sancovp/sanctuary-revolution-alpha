#!/bin/bash
# BrainHook toggle - use with !brainhook in Claude Code
# Part of the Autopoiesis plugin

state_file="/tmp/brainhook_state.txt"

if [[ "$(cat "$state_file" 2>/dev/null)" == "on" ]]; then
  echo "off" > "$state_file"
  echo "🧠 BrainHook OFF"
else
  echo "on" > "$state_file"
  echo "🧠 BrainHook ON"
fi
