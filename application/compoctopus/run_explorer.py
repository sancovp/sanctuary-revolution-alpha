#!/usr/bin/env python3
"""Run OctoCoder to build the Repo Explorer — callgraph tracer + context bundler.

The Explorer runs BEFORE the coder. It traces imports, callgraphs,
and dependency chains to produce a "context bundle" — the exact set
of files, functions, and classes the LLM needs to edit something.

This is deterministic Python (ast module), NOT an LLM call.
It's a FunctionLink that feeds into coder SDNACs via Dovetail.
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
# Repo Explorer Specification
# =============================================================================

EXPLORER_SPEC = """
# Repo Explorer — Callgraph Tracer + Context Bundler

## CRITICAL: Follow the OctoCoder Pattern
Read `/tmp/compoctopus/compoctopus/agents/octopus_coder/factory.py`.
That shows how a CompoctopusAgent is built. The Explorer follows
the same pattern but uses FunctionLinks (deterministic Python),
not SDNACs, because code analysis doesn't need an LLM.

## What the Explorer Does
Given a repo path and a target (file, function, class), the Explorer:
1. Parses Python files with `ast` module
2. Traces the callgraph from the target outward
3. Follows imports recursively
4. Identifies "logic regions" — the minimal set of code context
   an LLM needs to understand/edit that target
5. Outputs a context bundle: ordered list of code snippets with
   file paths, line ranges, and dependency relationships

## Architecture
- Type: CompoctopusAgent with a Chain of 3 FunctionLinks
- Chain:
    1. `parse` FunctionLink — parse all .py files in repo, build AST index
    2. `trace` FunctionLink — from target, trace callgraph + imports recursively
    3. `bundle` FunctionLink — package traced code into a context bundle

All deterministic. No LLM calls. Pure Python using `ast` and `importlib`.

## File Structure (output into workspace)
```
explorer/
    __init__.py           # exports make_explorer, explore_repo
    factory.py            # make_explorer(repo_path) -> CompoctopusAgent
    parser.py             # parse_repo(repo_path) -> RepoIndex
    tracer.py             # trace_target(index, target) -> CallGraph
    bundler.py            # bundle_context(graph) -> ContextBundle
    types.py              # RepoIndex, CallGraph, ContextBundle, CodeRegion
    tests/
        test_explorer.py  # tests
```

## types.py Requirements
```python
@dataclass
class CodeRegion:
    file_path: str         # absolute path
    start_line: int
    end_line: int
    name: str              # function/class name
    kind: str              # "function", "class", "module"
    source: str            # the actual code text
    imports: List[str]     # what this region imports
    calls: List[str]       # what this region calls

@dataclass
class RepoIndex:
    files: Dict[str, ast.Module]     # path -> parsed AST
    symbols: Dict[str, CodeRegion]   # qualified_name -> region
    import_map: Dict[str, str]       # imported_name -> source_file

@dataclass
class CallGraph:
    target: str                       # the starting symbol
    nodes: Dict[str, CodeRegion]      # all reachable regions
    edges: List[Tuple[str, str]]      # caller -> callee pairs
    depth: Dict[str, int]             # symbol -> depth from target

@dataclass
class ContextBundle:
    target: str
    regions: List[CodeRegion]   # ordered by dependency (deps first)
    total_lines: int
    total_tokens_estimate: int  # rough estimate for context planning
    summary: str                # one-line summary of what's in the bundle
```

## parser.py Requirements
1. `parse_repo(repo_path)` -> RepoIndex
   - Walk all .py files (skip __pycache__, .git, venv)
   - Parse each with ast.parse()
   - Extract all function defs, class defs with line ranges
   - Build import_map: track what each file imports and from where
   - Build symbols dict: qualified names like "module.Class.method"

## tracer.py Requirements
1. `trace_target(index, target_name, max_depth=5)` -> CallGraph
   - Start from target_name in the symbols dict
   - Use ast.NodeVisitor to find all Name/Attribute nodes (calls)
   - Resolve each call to a symbol in the index
   - Recurse up to max_depth
   - Track edges (caller -> callee) and depth

## bundler.py Requirements
1. `bundle_context(graph, max_tokens=50000)` -> ContextBundle
   - Topological sort the callgraph (dependencies first)
   - For each CodeRegion, include the source code
   - Estimate tokens (chars / 4 roughly)
   - If over max_tokens, prune deepest nodes first
   - Generate a one-line summary

## factory.py Requirements
1. `make_explorer(repo_path)` -> CompoctopusAgent
   - Chain of 3 FunctionLinks: parse, trace, bundle
   - parse: calls parse_repo(), stores RepoIndex in ctx["repo_index"]
   - trace: reads ctx["target"], calls trace_target(), stores CallGraph in ctx["callgraph"]
   - bundle: calls bundle_context(), stores ContextBundle in ctx["context_bundle"]
2. Also export a convenience function:
   `explore_repo(repo_path, target, max_depth=5)` -> ContextBundle
   - Does all 3 steps in one call, no agent needed

## test_explorer.py Requirements
STRUCTURAL TESTS:
1. test_parse_repo — parse a small test repo, verify symbols found
2. test_import_map — verify import tracking works
3. test_trace_simple — trace from a function, verify callgraph
4. test_trace_recursive — trace follows imports across files
5. test_bundle — bundle produces ordered regions
6. test_bundle_token_limit — bundle prunes when over limit

BEHAVIORAL TESTS:
7. test_explore_compoctopus — run explore_repo on
   /tmp/compoctopus/compoctopus/agents/octopus_coder/factory.py
   targeting make_octopus_coder. Assert:
   - context_bundle has regions
   - regions include chain_ontology.py (Chain, EvalChain)
   - regions include prompts.py (CODER_STATE_INSTRUCTIONS)
   - regions include types.py (SystemPrompt)
   - total_lines > 0
   - total_tokens_estimate > 0
8. test_explore_agent_execute — run on CompoctopusAgent,
   targeting execute(). Assert it traces into chain_ontology.

## Imports Available
```python
import ast
import os
import sys
import importlib.util
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Set
from compoctopus.agent import CompoctopusAgent
from compoctopus.chain_ontology import Chain, FunctionLink, LinkResult, LinkStatus
from compoctopus.types import SystemPrompt, PromptSection
```
"""


async def main():
    from compoctopus.agents.octopus_coder.factory import make_octopus_coder

    if len(sys.argv) > 1:
        workspace = sys.argv[1]
        os.makedirs(workspace, exist_ok=True)
    else:
        workspace = tempfile.mkdtemp(prefix="compoctopus_explorer_")

    print(f"\n{'='*60}")
    print(f"🐙 OctoCoder — Building Repo Explorer")
    print(f"{'='*60}")
    print(f"Workspace: {workspace}")
    print(f"{'='*60}\n")

    coder = make_octopus_coder(spec=EXPLORER_SPEC, workspace=workspace)

    ctx = {
        "spec": EXPLORER_SPEC,
        "workspace": workspace,
        "target_module": "explorer",
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

    for root, dirs, files in os.walk(workspace):
        for f in files:
            if not f.endswith('.pyc') and '__pycache__' not in root and '.pytest_cache' not in root:
                path = os.path.join(root, f)
                print(f"  {os.path.relpath(path, workspace)} ({os.path.getsize(path)} bytes)")


if __name__ == "__main__":
    asyncio.run(main())
