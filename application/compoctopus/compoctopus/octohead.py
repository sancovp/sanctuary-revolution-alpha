"""OctoHead — configurable chat entrypoint for Compoctopus.

Takes any agent's system prompt + any toolkit, always adds OctoHead tools
(CreatePRD, BuildPRD, GoAuto), produces a HeavenAgentConfig you load into
whatever channel you want (Heaven CLI, Conductor, Discord, etc.).

Usage:
    config = make_octohead()  # generic OctoHead
    config = make_octohead(system_prompt="You are a PE specialist.")
"""

from __future__ import annotations

from typing import List, Optional, Type
import json, os
from pathlib import Path

# Model config from user JSON — no hardcoded values
_octo_cfg_path = Path(os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data")) / "conductor_agent_config.json"
_OCTO_CFG = {}
if _octo_cfg_path.exists():
    try:
        _OCTO_CFG = json.loads(_octo_cfg_path.read_text())
    except (json.JSONDecodeError, OSError):
        pass


# Default OctoHead system prompt
OCTOHEAD_SYSTEM_PROMPT = """\
You are OctoHead — the chat interface to Compoctopus, the self-compiling agent compiler.

You guide the user through building agents, prompts, and systems. You operate in phases:

## Phases

### 1. Talk about system/design
Discuss the user's idea. Ask clarifying questions. Understand what they want to build,
how it should work, what architecture fits (Chain, EvalChain, etc.), what types are involved.

### 2. Conceptualize PRD
Draft the PRD in conversation. Lay out the name, description, architecture, links,
types, and — critically — behavioral assertions. Behavioral assertions define what
"correct" means. They are non-negotiable.

### 3. Refine PRD
Review the draft with the user. Challenge assumptions. Add edge cases to assertions.
Make sure every field is right before committing.

### 4. Queue PRD
When the PRD is finalized, call **CreatePRD** with every field filled. This saves
the PRD as a .🪸 (coral) file. Then call **BuildPRD** to send it to the daemon.
The Compoctopus daemon will pick it up and run Planner → Bandit → OctoCoder.

### 5. Talk about system/design | Review results
Return to design discussion, plan next steps, or review .🏄 results when available.

### 6. Go Auto (optional)
When the user says "go auto", call **GoAuto** to trigger one autonomous self-improvement
cycle. Compoctopus will introspect its own codebase, generate improvements, and open a PR.
Only one auto cycle at a time — wait for PR acceptance before triggering another.

## Tools

- **CreatePRD** — Writes a typed PRD as a .🪸 (coral) file. Every field must be filled.
- **BuildPRD** — Sends a .🪸 file to the daemon queue for building.
- **GoAuto** — Triggers one autonomous self-improvement cycle. Singleton.

## File Lifecycle

- `.🪸` (coral) — PRD file
- `.🐙` (octopus) — file being compiled
- `.🏄` (surf) — results report
- `.🤖` (robot) — auto-dev trigger flag

You are the face of Compoctopus. Be helpful, precise, and thorough.
"""


# OctoHead's built-in tools — always included
OCTOHEAD_TOOLS: List[Type] = []

try:
    from compoctopus.tools.create_prd_tool import CreatePRDTool
    if CreatePRDTool is not None:
        OCTOHEAD_TOOLS.append(CreatePRDTool)
except ImportError:
    pass

try:
    from compoctopus.tools.build_prd_tool import BuildPRDTool
    if BuildPRDTool is not None:
        OCTOHEAD_TOOLS.append(BuildPRDTool)
except ImportError:
    pass

try:
    from compoctopus.tools.go_auto_tool import GoAutoTool
    if GoAutoTool is not None:
        OCTOHEAD_TOOLS.append(GoAutoTool)
except ImportError:
    pass


def make_octohead(
    system_prompt: str = "",
    tools: Optional[List[Type]] = None,
    name: str = "compoctopus",
    model: str = "minimax",
) -> "HeavenAgentConfig":
    """Create an OctoHead config — a chat agent with OctoHead tools.

    Args:
        system_prompt: Any agent's identity. Default: generic OctoHead prompt.
        tools: Additional tools beyond OctoHead builtins. Optional.
        name: Agent name. Default: "compoctopus".
        model: Model. Default: "minimax".

    Returns:
        HeavenAgentConfig ready to load into any channel.
    """
    from heaven_base.baseheavenagent import HeavenAgentConfig

    prompt = system_prompt or OCTOHEAD_SYSTEM_PROMPT
    all_tools = list(tools or []) + OCTOHEAD_TOOLS

    return HeavenAgentConfig(
        name=name,
        system_prompt=prompt,
        tools=all_tools,
        model=_OCTO_CFG.get("model", ""),
        use_uni_api=False,
        max_tokens=8000,
        temperature=0.7,
        skillset="octohead",
        extra_model_kwargs=_OCTO_CFG.get("extra_model_kwargs", {}),
        mcp_servers={
            "llm-intelligence": {
                "transport": "stdio",
                "command": "python",
                "args": ["-m", "llm_intelligence.mcp_server"],
            },
        },
    )
