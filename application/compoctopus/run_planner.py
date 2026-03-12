#!/usr/bin/env python3
"""Run OctoCoder to build the Planner — task decomposition via GIINT hierarchy.

The Planner takes "build X" and produces a structured project hierarchy:
  PROJECT → FEATURE → COMPONENT → DELIVERABLE → TASK

Each level is a fresh SDNAC conversation (no context decay).
Output feeds downstream to the Bandit, which dispatches tasks to workers.
"""

import asyncio
import logging
import os
import sys
import tempfile

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(name)-30s %(levelname)-8s %(message)s',
)

sys.path.insert(0, '/tmp/compoctopus')

# =============================================================================
# Planner Specification
# =============================================================================

PLANNER_SPEC = """
# Planner — Task Decomposition via GIINT Hierarchy

## CRITICAL: Follow the OctoCoder Pattern
Read `/tmp/compoctopus/compoctopus/agents/octopus_coder/factory.py`.
That shows how a CompoctopusAgent is built with real SDNACs, HermesConfig,
BashTool, AriadneChain. The Planner MUST follow this same SDNAC pattern.

## What the Planner Does
Takes a high-level task description and decomposes it into a structured
hierarchy of work items that can be executed by workers (via the Bandit).

The hierarchy follows the GIINT model:
  PROJECT → FEATURES → COMPONENTS → DELIVERABLES → TASKS

Each level is a fresh SDNAC conversation (no context decay).
Dovetails validate the hand-off between levels.

## Architecture
- Type: CompoctopusAgent with a Chain of 5 SDNACs
- Chain (sequential, no loops):
    1. `project` SDNAC — Creates or identifies the project scope
    2. `features` SDNAC — Breaks project into features
    3. `components` SDNAC — Breaks features into components
    4. `deliverables` SDNAC — Breaks components into deliverables
    5. `tasks` SDNAC — Breaks deliverables into concrete tasks

Each SDNAC uses BashTool to write its output as JSON to the workspace.

## File Structure (output into workspace)
```
planner/
├── __init__.py           # exports make_planner
├── factory.py            # make_planner(task, workspace) → CompoctopusAgent
├── hierarchy.py          # PlanHierarchy dataclass — the structured output
└── tests/
    └── test_planner.py   # tests for the planner
```

## factory.py Requirements
1. `make_planner(task, workspace)` returns a `CompoctopusAgent`
   - `task` is the high-level task description
   - `workspace` is where outputs go
2. The agent has a `Chain` with 5 real SDNACs
3. Each SDNAC has a `HermesConfig` with:
   - `backend="heaven"`, `model="minimax"`
   - `heaven_inputs` with `HeavenAgentArgs(provider="ANTHROPIC", tools=[BashTool])`
   - `goal` that includes the task and workspace
   - `system_prompt` appropriate for the decomposition level
4. Each SDNAC's goal tells it:
   - What level of the hierarchy to produce
   - To read the previous level's output from the workspace
   - To write its output as JSON to the workspace
5. The agent has a `SystemPrompt` with tag="IDENTITY"

## hierarchy.py Requirements
1. `PlanHierarchy` dataclass with nested structure:
   ```python
   @dataclass
   class Task:
       name: str
       description: str  # specific enough for a coder to execute
       
   @dataclass
   class Deliverable:
       name: str
       tasks: List[Task]
       
   @dataclass
   class Component:
       name: str
       deliverables: List[Deliverable]
       
   @dataclass
   class Feature:
       name: str
       components: List[Component]
       
   @dataclass
   class PlanHierarchy:
       project_name: str
       features: List[Feature]
   ```
2. `to_json()` and `from_json()` methods for serialization

## test_planner.py Requirements
STRUCTURAL TESTS:
1. `test_make_planner()` — verifies agent creation, name, chain type
2. `test_chain_has_5_links()` — verifies 5 SDNACs
3. `test_chain_link_names()` — names are project, features, components, deliverables, tasks
4. `test_has_system_prompt()` — system prompt contains "Planner"

BEHAVIORAL TESTS:
5. `test_plan_hierarchy_dataclass()` — PlanHierarchy creates, nests correctly
6. `test_hierarchy_to_json()` — serializes to JSON
7. `test_hierarchy_from_json()` — deserializes from JSON roundtrip

## Imports Available
```python
from compoctopus.agent import CompoctopusAgent
from compoctopus.chain_ontology import Chain, Link, LinkResult, LinkStatus
from compoctopus.types import SystemPrompt, PromptSection
from sdna.sdna import SDNAC
from sdna.ariadne import AriadneChain, InjectConfig
from sdna.config import HermesConfig, HeavenInputs, HeavenAgentArgs
from heaven_base.tools import BashTool
from dataclasses import dataclass, field, asdict
from typing import List
import json
```
"""


async def main():
    from compoctopus.agents.octopus_coder.factory import make_octopus_coder

    # Use existing workspace if provided, else create new
    if len(sys.argv) > 1:
        workspace = sys.argv[1]
        os.makedirs(workspace, exist_ok=True)
    else:
        workspace = tempfile.mkdtemp(prefix="compoctopus_planner_")

    print(f"\n{'='*60}")
    print(f"🐙 OctoCoder — Building Planner")
    print(f"{'='*60}")
    print(f"Workspace: {workspace}")
    print(f"{'='*60}\n")

    coder = make_octopus_coder(spec=PLANNER_SPEC, workspace=workspace)

    ctx = {
        "spec": PLANNER_SPEC,
        "workspace": workspace,
        "target_module": "planner",
        "output_dir": workspace,
    }

    print(f"Chain: {coder.chain.name}")
    print(f"Links: {[l.name for l in coder.chain.links]}")
    print(f"Evaluator: {coder.chain.evaluator.name}")
    print()

    result = await coder.execute(ctx)

    print(f"\n{'='*60}")
    print(f"Result: {result.status}")
    if result.error:
        print(f"Error: {result.error}")
    print(f"Context keys: {list(result.context.keys())}")
    print(f"{'='*60}")

    # Show output files
    for root, dirs, files in os.walk(workspace):
        for f in files:
            if not f.endswith('.pyc') and '__pycache__' not in root and '.pytest_cache' not in root:
                path = os.path.join(root, f)
                print(f"  {os.path.relpath(path, workspace)} ({os.path.getsize(path)} bytes)")


if __name__ == "__main__":
    asyncio.run(main())
