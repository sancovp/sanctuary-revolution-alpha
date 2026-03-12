"""Planner factory — task decomposition via GIINT hierarchy.

The Planner takes a PRD and decomposes it into the GIINT hierarchy:
    Project → Features → Components → Deliverables → Tasks

It uses the llm-intelligence MCP to persist the hierarchy, not just
LLM reasoning. The decomposition is stored in the GIINT system and
queryable by downstream arms (Bandit, OctoCoder).

Tools:
    - BashTool: file I/O, exploration
    - NetworkEditTool: multi-file edits
    - llm-intelligence MCP: planning__create_project, planning__add_feature_to_project, etc.
"""

from __future__ import annotations
from typing import List, Optional
from compoctopus.agent import CompoctopusAgent
from compoctopus.chain_ontology import Chain, Link, LinkResult, LinkStatus
from compoctopus.types import SystemPrompt, PromptSection


# The llm-intelligence MCP server config for SDNAC
LLM_INTELLIGENCE_MCP = {
    "llm-intelligence": {
        "type": "stdio",
        "command": "python",
        "args": ["-m", "llm_intelligence.mcp_server"],
    }
}

PLANNER_SYSTEM_PROMPT = (
    "You are the Planner — the task decomposition arm of Compoctopus.\n\n"
    "Your job: take a PRD (Product Requirements Document) and decompose it\n"
    "into the GIINT hierarchy using the llm-intelligence MCP tools:\n\n"
    "  1. planning__create_project — create the project\n"
    "  2. planning__add_feature_to_project — add features\n"
    "  3. planning__add_component_to_feature — add components\n"
    "  4. planning__add_deliverable_to_component — add deliverables\n"
    "  5. planning__add_task_to_deliverable — add tasks\n\n"
    "You MUST call these tools to persist the hierarchy.\n"
    "You MUST NOT just describe the hierarchy in text.\n"
    "The hierarchy must be stored in the GIINT system so downstream arms can query it.\n\n"
    "Read the PRD carefully. Each layer decomposes the previous:\n"
    "  Project: the overall scope\n"
    "  Features: distinct capabilities\n"
    "  Components: pieces of each feature\n"
    "  Deliverables: concrete outputs per component\n"
    "  Tasks: executable steps per deliverable\n"
)

PHASE_INSTRUCTIONS = {
    "project": (
        "Read the PRD and create the GIINT project.\n"
        "Call planning__create_project with the project name and description.\n"
        "Save the project_id for downstream phases."
    ),
    "features": (
        "Read the PRD and identify distinct features.\n"
        "For each feature, call planning__add_feature_to_project.\n"
        "Features are the major capabilities described in the PRD."
    ),
    "components": (
        "For each feature, identify components.\n"
        "Call planning__add_component_to_feature for each.\n"
        "Components are the pieces that make up a feature."
    ),
    "deliverables": (
        "For each component, identify deliverables.\n"
        "Call planning__add_deliverable_to_component for each.\n"
        "Deliverables are concrete outputs (files, modules, tests)."
    ),
    "tasks": (
        "For each deliverable, identify executable tasks.\n"
        "Call planning__add_task_to_deliverable for each.\n"
        "Tasks are the smallest executable units of work."
    ),
}


def _make_planner_sdnac(phase: str, workspace: str, tools_list=None):
    """Build an SDNAC for one planner phase.

    Each phase gets BashTool + NetworkEditTool + llm-intelligence MCP.
    """
    phase_instructions = PHASE_INSTRUCTIONS.get(phase, "")
    # Escape curly braces — SDNA does .format(**ctx) on goal
    safe_instructions = phase_instructions.replace("{", "{{").replace("}", "}}")
    goal = (
        f"## Workspace\n"
        f"All files MUST be written to: {workspace}\n\n"
        f"## Phase: {phase.upper()}\n"
        f"{safe_instructions}\n\n"
        "## IMPORTANT\n"
        "You MUST use the llm-intelligence MCP tools (planning__*) to persist the hierarchy.\n"
        "Do NOT just output text descriptions — call the actual tools.\n"
    )

    try:
        from sdna.sdna import SDNAC
        from sdna.ariadne import AriadneChain, InjectConfig
        from sdna.config import HermesConfig, HeavenInputs, HeavenAgentArgs
    except ImportError:
        from compoctopus.chain_ontology import ConfigLink, LinkConfig
        return ConfigLink(LinkConfig(
            name=phase.lower(),
            goal=goal,
            system_prompt=PLANNER_SYSTEM_PROMPT,
            model="minimax",
            allowed_tools=["BashTool", "NetworkEditTool"],
        ))

    if tools_list is None:
        from heaven_base.tools import BashTool, NetworkEditTool
        tools_list = [BashTool, NetworkEditTool]

    # Patch poimandres to use Heaven runner
    try:
        from sdna import poimandres
        from sdna.heaven_runner import heaven_agent_step
        poimandres.agent_step = heaven_agent_step
    except ImportError:
        pass

    ariadne = AriadneChain(
        name=f"planner_{phase.lower()}_ariadne",
        elements=[InjectConfig(source="literal", inject_as="instructions", value=goal)],
    )

    hermes = HermesConfig(
        name=f"planner_{phase.lower()}",
        goal=goal,
        backend="heaven",
        model="minimax",
        max_turns=30,
        permission_mode="bypassPermissions",
        mcp_servers=LLM_INTELLIGENCE_MCP,
        heaven_inputs=HeavenInputs(
            agent=HeavenAgentArgs(
                provider="ANTHROPIC",
                max_tokens=8000,
                tools=tools_list,
            ),
        ),
        system_prompt=PLANNER_SYSTEM_PROMPT,
    )

    return SDNAC(name=phase.lower(), ariadne=ariadne, config=hermes)


def make_planner(workspace: str = "/tmp/output") -> CompoctopusAgent:
    """Create the Planner — task decomposition via GIINT hierarchy.

    The Planner reads a PRD from context and decomposes it into:
        Project → Features → Components → Deliverables → Tasks

    Each level is an SDNAC that uses llm-intelligence MCP tools to
    persist the hierarchy into the GIINT system.
    """
    try:
        from heaven_base.tools import BashTool, NetworkEditTool
        tools = [BashTool, NetworkEditTool]
    except ImportError:
        tools = None

    project_sdnac = _make_planner_sdnac("project", workspace, tools)
    features_sdnac = _make_planner_sdnac("features", workspace, tools)
    components_sdnac = _make_planner_sdnac("components", workspace, tools)
    deliverables_sdnac = _make_planner_sdnac("deliverables", workspace, tools)
    tasks_sdnac = _make_planner_sdnac("tasks", workspace, tools)

    chain = Chain(
        chain_name="planner_hierarchy",
        links=[project_sdnac, features_sdnac, components_sdnac, deliverables_sdnac, tasks_sdnac],
    )

    return CompoctopusAgent(
        agent_name="planner",
        chain=chain,
        system_prompt=SystemPrompt(sections=[
            PromptSection(
                tag="IDENTITY",
                content=PLANNER_SYSTEM_PROMPT,
            ),
        ]),
        model="minimax",
    )
