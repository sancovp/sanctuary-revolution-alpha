#!/usr/bin/env bash
# Call Researcher SDNAC from Conductor.
# Same container — invokes the SDNA runner directly via Python.
#
# Usage:
#   call_researcher.sh "Phase prompt or task"
#
# Researcher runs as an SDNAC (blocking). Output goes to stdout.

set -euo pipefail

if [[ -z "${1:-}" ]]; then
    echo "Usage: call_researcher.sh <prompt>" >&2
    exit 1
fi

PROMPT="$1"

python3 -c "
import asyncio
import sys
sys.path.insert(0, '/tmp/conductor')
from conductor.agents import make_researcher_sdnac

async def main():
    # Load system prompt from config
    from pathlib import Path
    prompt_path = Path('/tmp/heaven_data/researcher_system_prompt.md')
    system_prompt = prompt_path.read_text() if prompt_path.exists() else 'You are Dr. Randy BrainBrane, a research scientist.'
    researcher = make_researcher_sdnac(system_prompt)
    result = await researcher.execute({'phase_prompt': '''$PROMPT'''})
    print(result.context)

asyncio.run(main())
"
