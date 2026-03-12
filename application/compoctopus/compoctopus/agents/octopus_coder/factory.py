"""OctoCoder factory — make_octopus_coder() + helpers.

Invariant: every CA package has factory.py with the make_<name>() function.

Architecture:
    make_octopus_coder(spec, workspace) builds an EvalChain:
        flow = Chain([stub_sdnac, tests_sdnac, pseudo_sdnac, anneal_sdnac])
        evaluator = verify_sdnac
        EvalChain wraps flow + evaluator, loops on verify failure.

    ALL phases are SDNACs (fresh LLM conversation per phase).
    ALL phases use BashTool for file I/O.
    The spec and workspace are BAKED INTO every SDNAC's goal.
    On cycle failure, STUB sees existing work and stubs ON TOP of it.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from compoctopus.agent import CompoctopusAgent
from compoctopus.chain_ontology import (
    Chain,
    EvalChain,
    Link,
    LinkResult,
    LinkStatus,
)
from compoctopus.types import PromptSection, SystemPrompt

from compoctopus.agents.octopus_coder.prompts import (
    CODER_STATE_INSTRUCTIONS,
    OCTO_SYNTAX_REFERENCE,
)


# =============================================================================
# Shared system prompt — injected into every SDNAC
# =============================================================================

from compoctopus.agents.octopus_coder.reference_tests import REFERENCE_TESTS_PROMPT

_CODER_SYSTEM_PROMPT = (
    "You are the 🐙 Coder — the Compoctopus bootstrap kernel.\n\n"
    "You compile understanding into code. You explore, learn, stub,\n"
    "fill, test, and iterate until the code works.\n\n"
    "## Container Context\n"
    "Your container name is `antigravity_python_dev`.\n"
    "Use absolute paths like /tmp/... for file operations.\n"
    "Use BashTool for ALL file operations (reading, writing, running).\n"
    "Write files with: cat > /path/to/file << 'EOF'\n"
    "Read files with: cat /path/to/file\n"
    "Find files with: find /path -name '*.octo' or ls -la /path/\n\n"
    "## MANDATORY TESTING RULES\n"
    "You MUST write TWO kinds of tests. BOTH are required.\n\n"
    "STRUCTURAL TESTS: Verify the code was assembled correctly.\n"
    "  - Correct types, names, field counts\n"
    "  - Correct imports and interfaces\n"
    "  - Correct configuration (links, prompts, tools)\n\n"
    "BEHAVIORAL TESTS: Call the ENTIRE piece of code EXACTLY AS IT WILL BE\n"
    "  USED IN THE WILD. The test IS a real usage of the code.\n"
    "  - Create the agent with the real factory function\n"
    "  - Call `await agent.execute(ctx)` with a real task\n"
    "  - This WILL make real API calls to MiniMax. That is correct and expected.\n"
    "  - Assert that the agent actually DID what it's designed to do:\n"
    "    files it wrote exist and contain correct content,\n"
    "    outputs it produced are real and valid,\n"
    "    the result status is SUCCESS.\n"
    "  - Use pytest-asyncio for async tests.\n"
    "  - A test that passes in under 5 seconds for an agent with LLM calls\n"
    "    is a FAKE TEST. Real LLM calls take 30+ seconds.\n\n"
    "The code MUST provably do what it is designed to do BEFORE you release it.\n"
    "If you only write structural tests, you have FAILED.\n\n"
    + REFERENCE_TESTS_PROMPT + "\n\n"
    + OCTO_SYNTAX_REFERENCE
)


# =============================================================================
# SDNAC builder — one per phase, with spec+workspace baked in
# =============================================================================

def _make_coder_sdnac(phase: str, spec: str, workspace: str,
                      tools_list=None) -> Link:
    """Build an SDNAC for one coder phase.

    Each SDNAC gets:
    - Phase-specific goal with SPEC and WORKSPACE baked in
    - BashTool for all file operations
    - Shared _CODER_SYSTEM_PROMPT
    - AriadneChain that injects the instructions into context

    The spec and workspace are part of the goal string so the LLM
    always knows WHAT to build and WHERE to write files.
    """
    # Build the goal: phase instructions + spec + workspace
    phase_instructions = CODER_STATE_INSTRUCTIONS[phase]
    # Escape curly braces in spec — SDNA does .format(**ctx) on the goal
    # which would interpret {task}, {tags} etc from behavioral assertions
    safe_spec = spec.replace("{", "{{").replace("}", "}}")
    goal = (
        f"## Workspace\n"
        f"All files MUST be written to: {workspace}\n\n"
        f"## Phase: {phase}\n"
        f"{phase_instructions}\n\n"
        "## Specification\n"
    ) + safe_spec + "\n"



    try:
        from sdna.sdna import SDNAC
        from sdna.ariadne import AriadneChain, InjectConfig
        from sdna.config import HermesConfig, HeavenInputs, HeavenAgentArgs
    except ImportError:
        # Test environment — return a ConfigLink with the config data
        from compoctopus.chain_ontology import ConfigLink, LinkConfig
        return ConfigLink(LinkConfig(
            name=phase.lower(),
            goal=goal,
            system_prompt=_CODER_SYSTEM_PROMPT,
            model="minimax",
            allowed_tools=[t.__name__ if hasattr(t, '__name__') else str(t)
                           for t in (tools_list or [])],
        ))

    if tools_list is None:
        from heaven_base.tools import BashTool
        from heaven_base.tools import NetworkEditTool
        tools_list = [BashTool, NetworkEditTool]

    # Patch poimandres to use Heaven runner
    try:
        from sdna import poimandres
        from sdna.heaven_runner import heaven_agent_step
        poimandres.agent_step = heaven_agent_step
    except ImportError:
        pass

    ariadne = AriadneChain(
        name=f"coder_{phase.lower()}_ariadne",
        elements=[
            InjectConfig(
                source="literal",
                inject_as="instructions",
                value=goal,
            ),
        ],
    )

    hermes = HermesConfig(
        name=f"octopus_coder_{phase.lower()}",
        goal=goal,
        backend="heaven",
        model="minimax",
        max_turns=30,
        permission_mode="bypassPermissions",
        heaven_inputs=HeavenInputs(
            agent=HeavenAgentArgs(
                provider="ANTHROPIC",
                max_tokens=8000,
                tools=tools_list,
            ),
        ),
        system_prompt=_CODER_SYSTEM_PROMPT,
    )

    return SDNAC(name=phase.lower(), ariadne=ariadne, config=hermes)


# =============================================================================
# make_octopus_coder() — builds an EvalChain
# =============================================================================

def make_octopus_coder(spec: str = "", workspace: str = "/tmp/output") -> CompoctopusAgent:
    """Create the 🐙 Coder — the bootstrap kernel agent.

    Args:
        spec: The specification of what to build. This gets baked into
              every SDNAC's goal so the agent always knows the task.
        workspace: Absolute path where the agent writes ALL output files.
                   Baked into every goal so the agent knows WHERE to write.

    Architecture:
        EvalChain(
            flow = Chain([stub, tests, pseudo, anneal]),
            evaluator = verify,
            max_cycles = 5,
        )

    Phase order: STUB → TESTS → PSEUDO → ANNEAL → VERIFY
    All phases are SDNACs with BashTool.
    On failure, the cycle restarts with existing work intact.
    """

    # --- All SDNACs use BashTool ---
    try:
        from heaven_base.tools import BashTool
        from heaven_base.tools import NetworkEditTool
        tools = [BashTool, NetworkEditTool]
    except ImportError:
        tools = None

    stub_sdnac = _make_coder_sdnac("STUB", spec, workspace, tools)
    tests_sdnac = _make_coder_sdnac("TESTS", spec, workspace, tools)
    pseudo_sdnac = _make_coder_sdnac("PSEUDO", spec, workspace, tools)
    anneal_sdnac = _make_coder_sdnac("ANNEAL", spec, workspace, tools)
    verify_sdnac = _make_coder_sdnac("VERIFY", spec, workspace, tools)

    # --- Compose EvalChain ---
    chain = EvalChain(
        chain_name="octopus_coder",
        links=[stub_sdnac, tests_sdnac, pseudo_sdnac, anneal_sdnac],
        evaluator=verify_sdnac,
        max_cycles=5,
        approval_key="approved",
    )

    return CompoctopusAgent(
        agent_name="octopus_coder",
        chain=chain,
        system_prompt=SystemPrompt(sections=[
            PromptSection(
                tag="IDENTITY",
                content=(
                    "You are the 🐙 Coder — the Compoctopus bootstrap kernel.\n\n"
                    "You compile understanding into code through the Annealing Cycle:\n"
                    "  STUB → TESTS → PSEUDO → ANNEAL → VERIFY → (cycle)\n\n"
                    "STUB: Explore, trace deps, gather context, produce .octo stubs\n"
                    "TESTS: Write witnessing assertions from spec + stubs\n"
                    "PSEUDO: Fill #| lines with real executable code\n"
                    "ANNEAL: Run annealer (mechanical marker strip)\n"
                    "VERIFY: Run pytest\n\n"
                    "On failure, you cycle back to STUB — but on top of existing work.\n"
                    "You never start over. You refine."
                ),
            ),
            PromptSection(
                tag="OCTO_SYNTAX",
                content=OCTO_SYNTAX_REFERENCE,
            ),
            PromptSection(
                tag="TOOLS",
                content=(
                    "You have one tool: BashTool.\n\n"
                    "Use it for ALL operations:\n"
                    "- Read files: cat /path/to/file\n"
                    "- Write files: cat > /path/to/file << 'EOF'\n"
                    "- Find files: find /path -name '*.octo'\n"
                    "- Run annealer: python3 -c \"from compoctopus.annealer ...\"\n"
                    "- Run tests: python3 -m pytest /path/to/tests.py -v\n"
                ),
            ),
            PromptSection(
                tag="SANDBOX",
                content=(
                    "CRITICAL SAFETY RULE:\n\n"
                    f"You work ONLY in: {workspace}\n"
                    "All files MUST be created inside this directory.\n\n"
                    "You MUST NOT:\n"
                    "  - Read or write ANY files outside the workspace\n"
                    "  - Modify any existing project files\n"
                    "  - Install packages or modify the environment\n\n"
                    "All file paths in your output must be within the workspace."
                ),
            ),
        ]),
        model="minimax",
    )


# =============================================================================
# CodeCompiler — Link whose execute() runs the OctoCoder agent
# =============================================================================

class CodeCompiler(Link):
    """Link that compiles a spec + tests into working code.

    execute() creates and runs the OctoCoder agent, which explores
    the spec, writes .octo code, fills it, anneals to Python, runs
    tests, and iterates until green.
    """

    def __init__(self, coder_factory=None):
        self.coder_factory = coder_factory
        self.name = "code_compiler"

    async def execute(self, context=None, **kwargs):
        ctx = dict(context) if context else {}
        if not ctx.get("spec"):
            return LinkResult(
                status=LinkStatus.ERROR,
                context=ctx,
                error="No spec in context",
            )

        if self.coder_factory:
            coder = self.coder_factory()
        else:
            coder = make_octopus_coder(
                spec=ctx["spec"],
                workspace=ctx.get("workspace", "/tmp/output"),
            )

        result = await coder.execute(ctx)
        return result

    def describe(self, depth=0):
        indent = "  " * depth
        return f'{indent}CodeCompiler "{self.name}" → OctoCoder agent'
