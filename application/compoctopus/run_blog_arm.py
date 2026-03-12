#!/usr/bin/env python3
"""Run the OctoCoder to build a Blog arm.

This is the first live test of the Compoctopus annealing pipeline.
The OctoCoder will:
  1. STUB  → Create .octo file with stub blocks for a blog arm factory
  2. PSEUDO → Fill stubs with #| pseudocode
  3. TESTS → Write pytest tests for the blog arm
  4. ANNEAL → Run annealer to convert .octo → .py
  5. VERIFY → Run pytest
  6. Loop if tests fail

Task: Create a BlogWriter arm that generates blog posts.
"""

import asyncio
import logging
import os
import sys
import tempfile

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)-30s %(levelname)-8s %(message)s",
)

sys.path.insert(0, "/tmp/compoctopus")


BLOG_ARM_SPEC = """
# Blog Arm — CompoctopusAgent Specification

## What to Build
A `BlogWriter` CompoctopusAgent that takes a topic and produces a blog post.
This agent MUST be a REAL agent — with real SDNACs that call an LLM,
not ConfigLinks or stubs.

## CRITICAL: Follow the OctoCoder Pattern
Read `/tmp/compoctopus/compoctopus/agents/octopus_coder/factory.py`.
That is how YOU (the OctoCoder) were built. The BlogWriter MUST follow
the same pattern:
- Real SDNACs (not ConfigLinks) with HermesConfig
- BashTool for file operations
- AriadneChain for context injection
- Heaven backend with ANTHROPIC provider

## Architecture
- Type: CompoctopusAgent with an EvalChain or Chain of 2 SDNACs
- Chain:
    1. `research` SDNAC — takes a topic, uses BashTool to research,
       returns key points about the topic
    2. `write` SDNAC — takes the key points, writes a markdown blog post
       to a file in the workspace

## File Structure (output into workspace)
```
blog_arm/
├── __init__.py          # exports make_blog_writer
├── factory.py           # make_blog_writer(topic, workspace) → CompoctopusAgent
└── tests/
    └── test_blog.py     # tests for the blog arm
```

## factory.py Requirements
1. `make_blog_writer(topic, workspace)` returns a `CompoctopusAgent`
2. The agent has a `Chain` with 2 real SDNACs: "research" and "write"
3. Each SDNAC has a `HermesConfig` with:
   - `backend="heaven"`
   - `model="minimax"`
   - `heaven_inputs` with `HeavenAgentArgs(provider="ANTHROPIC", tools=[BashTool])`
   - `goal` that includes the topic and workspace path
   - `system_prompt` appropriate for the phase
4. The topic and workspace are BAKED INTO each SDNAC's goal
5. The agent has a `SystemPrompt` with tag="IDENTITY"
6. Patch poimandres.agent_step = heaven_agent_step (same as OctoCoder)

## test_blog.py Requirements
STRUCTURAL TESTS:
1. `test_make_blog_writer()` — verifies agent creation, name, chain type
2. `test_chain_has_2_links()` — verifies 2 SDNACs
3. `test_chain_link_names()` — names contain "research" and "write"
4. `test_has_system_prompt()` — system prompt contains "Blog"

BEHAVIORAL TESTS:
5. `test_agent_describe()` — describe() returns string with agent name
6. `test_agent_to_sdna()` — to_sdna() returns dict with correct structure

## Imports Available
```python
from compoctopus.agent import CompoctopusAgent
from compoctopus.chain_ontology import Chain, EvalChain, Link, LinkResult, LinkStatus
from compoctopus.types import SystemPrompt, PromptSection
from sdna.sdna import SDNAC
from sdna.ariadne import AriadneChain, InjectConfig
from sdna.config import HermesConfig, HeavenInputs, HeavenAgentArgs
from heaven_base.tools import BashTool
```
"""


async def main():
    from compoctopus.agents.octopus_coder.factory import make_octopus_coder

    # Use existing workspace if provided, else create new
    if len(sys.argv) > 1:
        workspace = sys.argv[1]
        os.makedirs(workspace, exist_ok=True)
    else:
        workspace = tempfile.mkdtemp(prefix="compoctopus_blog_arm_")
    print(f"\n{'='*60}")
    print(f"🐙 OctoCoder — Building Blog Arm")
    print(f"{'='*60}")
    print(f"Workspace: {workspace}")
    print(f"{'='*60}\n")

    coder = make_octopus_coder(spec=BLOG_ARM_SPEC, workspace=workspace)

    # Context for the coder
    ctx = {
        "spec": BLOG_ARM_SPEC,
        "workspace": workspace,
        "target_module": "blog_arm",
        "output_dir": workspace,
    }

    print(f"Chain: {coder.chain.name}")
    print(f"Links: {[l.name for l in coder.chain.links]}")
    print(f"Evaluator: {coder.chain.evaluator.name}")
    print(f"Max cycles: {coder.chain.max_cycles}")
    print()

    # Run the coder
    try:
        result = await coder.execute(ctx)
        print(f"\n{'='*60}")
        print(f"Result status: {result.status}")
        print(f"Context keys: {list(result.context.keys())}")
        if result.error:
            print(f"Error: {result.error}")
        print(f"{'='*60}")

        # List workspace contents
        for root, dirs, files in os.walk(workspace):
            for f in files:
                path = os.path.join(root, f)
                size = os.path.getsize(path)
                print(f"  {os.path.relpath(path, workspace)} ({size} bytes)")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
