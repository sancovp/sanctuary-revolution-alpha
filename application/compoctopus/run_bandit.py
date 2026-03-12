#!/usr/bin/env python3
"""Run OctoCoder to build the Bandit — using typed PRD."""

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

from compoctopus.prd import PRD, LinkSpec, TypeSpec, BehavioralAssertion

BANDIT_PRD = PRD(
    name="bandit",
    description="Select/construct decision layer for Compoctopus",
    architecture="Chain",
    system_prompt_identity=(
        "You are the Bandit — the select/construct decision layer.\n"
        "Given a task, you tag it, search history for similar successful requests,\n"
        "select the best worker, dispatch the task, and record the outcome."
    ),
    links=[
        LinkSpec(
            name="tag",
            kind="SDNAC",
            description="LLM generates tags from the task description",
            inputs=["ctx['task']"],
            outputs=["ctx['tags']", "ctx['request_path']"],
        ),
        LinkSpec(
            name="select",
            kind="FunctionLink",
            description="Search history for similar successful requests. Default to octopus_coder.",
            inputs=["ctx['tags']", "ctx['request_path']"],
            outputs=["ctx['selected_worker']"],
        ),
        LinkSpec(
            name="dispatch",
            kind="FunctionLink",
            description="Run the selected worker on the task. Default to octopus_coder.",
            inputs=["ctx['task']", "ctx['selected_worker']"],
            outputs=["ctx['dispatch_result']"],
        ),
        LinkSpec(
            name="record",
            kind="FunctionLink",
            description="Update the request JSON with outcome and duration",
            inputs=["ctx['request_path']", "ctx['dispatch_result']"],
            outputs=["ctx['outcome']"],
        ),
    ],
    types=[
        TypeSpec(
            name="RequestRecord",
            kind="TypedDict",
            fields={
                "request_id": "str",
                "timestamp": "str",
                "task": "str",
                "tags": "List[str]",
                "selected_worker": "Optional[str]",
                "outcome": "Optional[str]",
                "duration_seconds": "Optional[float]",
            },
            description="JSON file written to history_dir for each request",
        ),
    ],
    file_structure={
        "bandit/__init__.py": "exports make_bandit",
        "bandit/factory.py": "make_bandit(history_dir) -> CompoctopusAgent",
        "bandit/request_io.py": "write_request, read_request, update_outcome, find_similar_requests",
        "bandit/tests/test_bandit.py": "structural + behavioral tests",
    },
    imports_available=[
        "from compoctopus.agent import CompoctopusAgent",
        "from compoctopus.chain_ontology import Chain, FunctionLink, LinkResult, LinkStatus",
        "from compoctopus.types import SystemPrompt, PromptSection",
        "from sdna.sdna.sdna.sdnac import SDNAC",
        "from sdna.config import HermesConfigInput, DovetailModel",
    ],
    behavioral_assertions=[
        BehavioralAssertion(
            description="agent.execute() creates a request JSON file in history_dir",
            setup=(
                "import tempfile, glob, json\n"
                "        from bandit.factory import make_bandit\n"
                "        tmpdir = tempfile.mkdtemp()"
            ),
            call=(
                "agent = make_bandit(history_dir=tmpdir)\n"
                "        result = await agent.execute({'task': 'Build a REST API with Flask'})"
            ),
            assertions=[
                "request_files = glob.glob(os.path.join(tmpdir, '*.json'))",
                "assert len(request_files) >= 1, 'Bandit should write a request JSON file'",
                "with open(request_files[0]) as f: data = json.load(f)",
                "assert data['task'] == 'Build a REST API with Flask'",
                "assert isinstance(data['tags'], list), 'Tags should be a list'",
                "assert len(data['tags']) >= 1, 'Should have at least one tag'",
            ],
        ),
        BehavioralAssertion(
            description="agent.execute() selects a worker and records outcome",
            setup=(
                "import tempfile, glob, json\n"
                "        from bandit.factory import make_bandit\n"
                "        tmpdir = tempfile.mkdtemp()"
            ),
            call=(
                "agent = make_bandit(history_dir=tmpdir)\n"
                "        result = await agent.execute({'task': 'Write unit tests for a calculator'})"
            ),
            assertions=[
                "request_files = glob.glob(os.path.join(tmpdir, '*.json'))",
                "assert len(request_files) >= 1, 'Should have request file'",
                "with open(request_files[0]) as f: data = json.load(f)",
                "assert data.get('selected_worker') is not None, 'Worker should be selected'",
                "assert data.get('outcome') in ('success', 'failure'), "
                "'Outcome should be recorded'",
            ],
        ),
    ],
)


async def main():
    from compoctopus.agents.octopus_coder.factory import make_octopus_coder

    if len(sys.argv) > 1:
        workspace = sys.argv[1]
        os.makedirs(workspace, exist_ok=True)
    else:
        workspace = tempfile.mkdtemp(prefix="compoctopus_bandit_")

    spec = BANDIT_PRD.to_spec_string()

    print(f"\n{'='*60}")
    print(f"OctoCoder -- Building Bandit (Typed PRD)")
    print(f"{'='*60}")
    print(f"Workspace: {workspace}")
    print(f"Behavioral assertions: {len(BANDIT_PRD.behavioral_assertions)}")
    print(f"{'='*60}\n")

    coder = make_octopus_coder(spec=spec, workspace=workspace)

    ctx = {
        "spec": spec,
        "workspace": workspace,
        "target_module": "bandit",
        "output_dir": workspace,
    }

    result = await coder.execute(ctx)

    print(f"\n{'='*60}")
    print(f"Result: {result.status}")
    if result.error:
        print(f"Error: {result.error}")
    print(f"Context keys: {list(result.context.keys())}")
    print(f"{'='*60}")

    for root, dirs, files in os.walk(workspace):
        for f in files:
            if not f.endswith('.pyc') and '__pycache__' not in root:
                path = os.path.join(root, f)
                print(f"  {os.path.relpath(path, workspace)} ({os.path.getsize(path)} bytes)")


if __name__ == "__main__":
    asyncio.run(main())
