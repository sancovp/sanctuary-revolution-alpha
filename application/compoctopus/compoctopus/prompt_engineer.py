"""Prompt Engineer — the conversational front-end to Compoctopus.

A chat agent that talks to the user, understands what they want to build,
and writes a typed PRD JSON to a queue directory. The Planner → Bandit
system picks up PRDs from the queue and builds them.

This is NOT an SDNAC — it uses Heaven's non-interactive HeavenClient.

Usage:
    # Programmatic (from agent code)
    from compoctopus.prompt_engineer import generate_prd
    prd_path = await generate_prd("Build a REST API for widget management")

    # CLI one-shot
    python -m compoctopus.prompt_engineer "Build a REST API for widget management"

    # CLI from spec file
    python -m compoctopus.prompt_engineer --file spec.md
"""

from __future__ import annotations

import json
import os
import re
import sys
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(name)-30s %(levelname)-8s %(message)s',
)

logger = logging.getLogger(__name__)

# The PRD schema baked into the system prompt
PRD_SCHEMA_PROMPT = """\
You are the Prompt Engineer for Compoctopus — a self-compiling agent compiler.

Your job: take the user's description of what they want to build and produce
a typed PRD (Product Requirements Document) as JSON.

The PRD schema:

```json
{
  "name": "project_name",
  "description": "What this project does",
  "architecture": "Chain or EvalChain",
  "links": [
    {
      "name": "link_name",
      "kind": "SDNAC or FunctionLink",
      "description": "What this link does",
      "inputs": ["ctx['input_name']"],
      "outputs": ["ctx['output_name']"]
    }
  ],
  "types": [
    {
      "name": "TypeName",
      "kind": "dataclass or TypedDict or enum",
      "fields": {"field_name": "field_type"},
      "description": "What this type represents"
    }
  ],
  "behavioral_assertions": [
    {
      "description": "What execute() must do",
      "setup": "Python code to create the agent",
      "call": "Python code to call execute()",
      "assertions": ["assert statements that must pass"]
    }
  ],
  "imports_available": ["from x import Y"],
  "system_prompt_identity": "Who this agent is",
  "file_structure": {"path": "description"}
}
```

RULES:
1. behavioral_assertions are CRITICAL — they define what "correct" means
2. Each assertion must include real setup, call, and assert code
3. The PRD must be specific enough that a coder can implement without thinking
4. When you have enough info, call the CreatePRD tool with every slot filled
5. Do NOT output JSON text — call the CreatePRD tool instead
6. If given a spec file, analyze it and produce the PRD from it
7. Always include at least 2 behavioral assertions
8. Always include file_structure showing what files to create
"""


def get_queue_dir() -> Path:
    """Get or create the PRD queue directory."""
    queue = Path(os.environ.get("COMPOCTOPUS_QUEUE", "/tmp/compoctopus_queue"))
    queue.mkdir(parents=True, exist_ok=True)
    return queue


def save_prd_to_queue(prd_json: dict, queue_dir: Path) -> Path:
    """Save a PRD JSON to the queue directory."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = prd_json.get("name", "unnamed").replace(" ", "_").lower()
    filename = f"prd_{name}_{timestamp}.json"
    path = queue_dir / filename
    with open(path, "w") as f:
        json.dump(prd_json, f, indent=2)
    return path


def extract_prd_from_response(response: str) -> Optional[dict]:
    """Try to extract a JSON PRD from the agent's response."""
    match = re.search(r'```json\s*\n(.*?)\n```', response, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            return None
    return None


def make_prompt_engineer_config():
    """Create a HeavenAgentConfig for the Prompt Engineer chat agent."""
    from heaven_base.baseheavenagent import HeavenAgentConfig
    from compoctopus.tools.create_prd_tool import CreatePRDTool

    return HeavenAgentConfig(
        name="compoctopus_prompt_engineer",
        system_prompt=PRD_SCHEMA_PROMPT,
        provider="anthropic",
        model="minimax",
        max_tokens=8000,
        temperature=0.7,
        tools=[CreatePRDTool],
    )


async def generate_prd(description: str, spec_file: Optional[str] = None) -> Optional[Path]:
    """Generate a PRD from a description or spec file. Non-interactive.

    Args:
        description: What to build (e.g. "Build a REST API for widgets")
        spec_file: Optional path to a spec file to read

    Returns:
        Path to the saved PRD JSON in the queue, or None on failure
    """
    from heaven_base.cli.heaven_client import HeavenClient

    config = make_prompt_engineer_config()
    queue_dir = get_queue_dir()

    # Build the message
    message = f"Build this:\n\n{description}"
    if spec_file and os.path.exists(spec_file):
        with open(spec_file) as f:
            spec_content = f.read()
        message = (
            f"Here is a spec file. Read it and produce a PRD:\n\n"
            f"---\n{spec_content}\n---\n\n"
            f"Additional context: {description}"
        )

    logger.info("Sending to Prompt Engineer: %s", description[:80])

    async with HeavenClient(agent_config=config) as client:
        result = await client.send_message(message)

        if result.success:
            prd_json = extract_prd_from_response(result.agent_response)
            if prd_json:
                path = save_prd_to_queue(prd_json, queue_dir)
                logger.info("PRD saved to: %s", path)
                return path
            else:
                logger.error("Could not extract PRD JSON from response")
                logger.debug("Response: %s", result.agent_response[:500])
        else:
            logger.error("Prompt Engineer failed: %s", result.error)

    return None


def generate_prd_sync(description: str, spec_file: Optional[str] = None) -> Optional[Path]:
    """Sync wrapper for generate_prd."""
    import asyncio
    return asyncio.run(generate_prd(description, spec_file))


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Compoctopus Prompt Engineer")
    parser.add_argument("description", nargs="?", default="", help="What to build")
    parser.add_argument("--file", "-f", help="Path to spec file")
    args = parser.parse_args()

    if not args.description and not args.file:
        parser.error("Provide a description or --file")

    result = generate_prd_sync(
        description=args.description or "See spec file",
        spec_file=args.file,
    )

    if result:
        print(f"\n✅ PRD saved to: {result}")
    else:
        print("\n❌ Failed to generate PRD")
        sys.exit(1)
