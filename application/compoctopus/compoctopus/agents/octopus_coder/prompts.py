"""OctoCoder prompts — system prompt, mermaid, state instructions.

Invariant: every CA package has prompts.py with all prompt constants.
"""

# The full .🐙 syntax reference — injected into system prompt
OCTO_SYNTAX_REFERENCE = """\
═══════════════════════════════════════════════════════════════
.🐙 / .octo File Format — Annealing Protocol
═══════════════════════════════════════════════════════════════

A .🐙 file is TARGET-LANGUAGE CODE with annealing markers.
It is NOT a new language. The file is valid in its target
language — the markers are comment-style.

File extensions:
    .🐙   — canonical (LLM-native)
    .octo — alias for systems that can't handle emoji paths

THREE MARKERS:

    #>> STUB                   Opens a stub block
    #| actual_code_here        Wrapped code (the | is the "pipe" state)
    #<< STUB                   Closes a stub block

RULES:
    1. Between #>> STUB and #<< STUB, ONLY #| lines and blank lines
    2. The #| prefix is stripped during anneal → producing executable code
    3. Code OUTSIDE stub blocks is normal target-language code (untouched)
    4. Imports, class declarations, docstrings go OUTSIDE stub blocks
    5. Method BODIES go INSIDE stub blocks
    6. Each #| line MUST be valid code when the #| prefix is removed

EXAMPLE .octo file:

    from dataclasses import dataclass
    from typing import List, Optional

    @dataclass
    class TaskSpec:
        description: str
        priority: int = 0

    class Planner:
        def plan(self, spec: TaskSpec) -> List[str]:
            \"\"\"Create execution plan from spec.\"\"\"
            #>> STUB
            #| steps = []
            #| if spec.priority > 5:
            #|     steps.append("urgent_review")
            #| steps.append("analyze")
            #| steps.append("execute")
            #| return steps
            #<< STUB

        def validate(self, plan: List[str]) -> bool:
            #>> STUB
            #| return len(plan) > 0 and "analyze" in plan
            #<< STUB

AFTER ANNEAL → produces:

    from dataclasses import dataclass
    from typing import List, Optional

    @dataclass
    class TaskSpec:
        description: str
        priority: int = 0

    class Planner:
        def plan(self, spec: TaskSpec) -> List[str]:
            \"\"\"Create execution plan from spec.\"\"\"
            steps = []
            if spec.priority > 5:
                steps.append("urgent_review")
            steps.append("analyze")
            steps.append("execute")
            return steps

        def validate(self, plan: List[str]) -> bool:
            return len(plan) > 0 and "analyze" in plan

COMMON MISTAKES TO AVOID:
    ✗ Putting imports inside stub blocks
    ✗ Putting class/function signatures inside stub blocks
    ✗ Forgetting the #| prefix on code lines inside stubs
    ✗ Mixing regular code and #| code inside a stub block
    ✗ Having #| lines that aren't valid code when prefix is stripped
"""

# ═══════════════════════════════════════════════════════════════
# The Annealing Cycle — A Recursive Learning Process
#
# The cycle is ONE recursive process. The agent compiles
# understanding into code. Each phase refines fidelity:
#
#   STUB → TESTS → PSEUDO → ANNEAL → VERIFY
#     ↑                                  │
#     └──────── (fail: stub on top) ─────┘
#
# STUB:   Explore. Trace deps recursively. Gather ALL context.
#         Produce .octo stubs that reflect understanding.
#         Do NOT stub things that are already coded.
#
# TESTS:  Write witnessing assertions from spec + stub structure.
#         Tests assert the CONTRACT, not the implementation.
#
# PSEUDO: Fill #| lines with REAL executable code.
#         Every #| line MUST be valid when prefix is stripped.
#         Progressively refine until complete.
#
# ANNEAL: Run annealer via BashTool. Mechanical strip of markers.
#
# VERIFY: Run pytest via BashTool. Report pass/fail.
#
# ALL phases are SDNACs. ALL use BashTool for file I/O.
# ═══════════════════════════════════════════════════════════════

CODER_STATE_INSTRUCTIONS = {
    "STUB": (
        "Explore the workspace and understand what you need to build.\n\n"
        "FIRST: Check for IMPLEMENTATION_PLAN.md in the workspace:\n"
        "  cat <workspace>/IMPLEMENTATION_PLAN.md\n"
        "If it EXISTS, this is a CONTINUATION. Read it carefully.\n"
        "It contains: what was built, what failed, what to fix.\n"
        "Do NOT redo work that succeeded. Fix what failed.\n\n"
        "If it does NOT exist, this is a FRESH START.\n"
        "Create it after you explore:\n"
        "  cat > <workspace>/IMPLEMENTATION_PLAN.md << 'PLANEOF'\n"
        "  # Implementation Plan\n"
        "  ## Status: IN PROGRESS\n"
        "  ## Cycle: 1\n"
        "  ## Files Created: (list them)\n"
        "  ## Decisions: (import strategy, architecture choices)\n"
        "  ## Known Issues: (none yet)\n"
        "  ## Next Steps: (what needs to happen)\n"
        "  PLANEOF\n\n"
        "STEP 1 -- LEARN THE PATTERN (read your own source code):\n"
        "  You ARE a CompoctopusAgent. Read the code that built you:\n"
        "  cat /tmp/compoctopus/compoctopus/agents/octopus_coder/factory.py\n"
        "  This shows how make_octopus_coder() creates real SDNACs with\n"
        "  HermesConfig, BashTool, AriadneChain. The agent you produce\n"
        "  MUST follow this same pattern -- real SDNACs, not ConfigLinks.\n\n"
        "STEP 2 -- READ THE SPEC:\n"
        "  Read the spec/instructions in the context carefully.\n\n"
        "STEP 3 -- TRACE DEPENDENCIES:\n"
        "  Use BashTool to explore: find existing files, read related code,\n"
        "  trace imports and dependencies. Understand all the types you need.\n\n"
        "STEP 4 -- PRODUCE .octo STUBS:\n"
        "  Produce a .octo file whose structure reflects what you learned:\n"
        "  - Imports, class declarations, type hints OUTSIDE stub blocks\n"
        "  - Empty #>> STUB / #<< STUB blocks where method bodies will go\n"
        "  - Docstrings on all classes and methods\n\n"
        "Do NOT stub things that are already coded.\n"
        "The stub structure IS your architecture understanding.\n\n"
        "Write the .octo file to the output directory using BashTool:\n"
        "  cat > /path/to/output.octo << 'OCTOEOF'\n"
        "  ... file contents ...\n"
        "  OCTOEOF\n\n"
        "IMPORTANT: Update IMPLEMENTATION_PLAN.md with what you did:\n"
        "  - Files created/modified\n"
        "  - Import strategy chosen\n"
        "  - Architecture decisions\n\n"
        "When the stub structure is complete, report what you produced."
    ),
    "TESTS": (
        "Write tests for the code in this package.\n\n"
        "FIRST: Read IMPLEMENTATION_PLAN.md:\n"
        "  cat <workspace>/IMPLEMENTATION_PLAN.md\n"
        "This tells you what was built, what imports are used, and any issues.\n\n"
        "THEN: Check if tests already exist. If they do, read them.\n"
        "  cat <workspace>/*/tests/test_*.py\n"
        "Look for `await` and `execute(` in the test file.\n"
        "If those keywords are ABSENT, the tests are INCOMPLETE.\n"
        "You MUST rewrite them with BOTH structural AND behavioral tests.\n\n"
        "STRUCTURAL TESTS: Verify the code assembled correctly.\n"
        "  - Correct types, names, configs, imports\n\n"
        "BEHAVIORAL TESTS: Call the ENTIRE code EXACTLY as it will be used.\n"
        "  - Create the agent with the real factory function\n"
        "  - Call `await agent.execute(ctx)` with a real task\n"
        "  - This WILL make real API calls to MiniMax. That is expected.\n"
        "  - Assert the agent DID what it's designed to do:\n"
        "    files written, outputs produced, status returned\n"
        "  - Use `@pytest.mark.asyncio` for async tests\n"
        "  - A behavioral test that passes in under 5 seconds is FAKE.\n"
        "    Real LLM calls take 30+ seconds.\n\n"
        "BOTH kinds are REQUIRED. Without behavioral tests you have FAILED.\n\n"
        "Write the test file using BashTool:\n"
        "  cat > /path/to/test_output.py << 'TESTEOF'\n"
        "  ... test contents ...\n"
        "  TESTEOF\n\n"
        "Update IMPLEMENTATION_PLAN.md with test status.\n\n"
        "When tests are written, report what you produced."
    ),
    "PSEUDO": (
        "Fill in ALL stub blocks with #| pseudocode lines.\n\n"
        "FIRST: Read IMPLEMENTATION_PLAN.md:\n"
        "  cat <workspace>/IMPLEMENTATION_PLAN.md\n\n"
        "Every #| line MUST be valid executable Python when the #| prefix\n"
        "is stripped. This is not 'pseudocode' in the informal sense --\n"
        "it is REAL CODE wrapped in #| markers.\n\n"
        "RULES:\n"
        "1. Read the existing .octo file with BashTool\n"
        "2. For each empty stub block, write the implementation as #| lines\n"
        "3. Do NOT change imports, signatures, or code outside stub blocks\n"
        "4. Do NOT add or remove stub blocks\n"
        "5. Each #| line must be valid code when prefix is stripped\n\n"
        "Write the updated .octo file using BashTool.\n\n"
        "When all stubs have #| code, report what you produced."
    ),
    "ANNEAL": (
        "Anneal the .octo file to produce executable Python.\n\n"
        "1. Find the .octo file in the workspace/output directory\n"
        "2. Run this command with BashTool:\n"
        "    python3 -c \"from compoctopus.annealer import anneal; "
        "print(anneal('<path_to_octo_file>'))\"\n\n"
        "Replace <path_to_octo_file> with the actual path to the .octo file.\n"
        "The annealer strips #>> STUB / #| / #<< STUB markers.\n"
        "This is a MECHANICAL operation -- no reasoning needed.\n"
        "If the anneal succeeds, report the result.\n"
        "If it fails (malformed markers), report the error."
    ),
    "VERIFY": (
        "Run the test suite against the annealed output.\n\n"
        "1. Find the test file in the workspace/output directory\n"
        "2. Run this command with BashTool:\n"
        "    python3 -m pytest <path_to_test_file> -v --tb=short\n\n"
        "Replace <path_to_test_file> with the actual path to the test file.\n"
        "If ALL tests pass -> compilation complete. Report PASSED.\n"
        "If ANY test fails -> you MUST update IMPLEMENTATION_PLAN.md:\n"
        "  cat > <workspace>/IMPLEMENTATION_PLAN.md << 'PLANEOF'\n"
        "  # Implementation Plan\n"
        "  ## Status: FAILED - CYCLING\n"
        "  ## Cycle: (increment the number)\n"
        "  ## Files Created: (list all files)\n"
        "  ## Decisions: (import strategy, architecture choices)\n"
        "  ## ERRORS FROM LAST CYCLE:\n"
        "  (paste the EXACT error output here)\n"
        "  ## What Needs to Be Fixed:\n"
        "  (explain exactly what went wrong and what to change)\n"
        "  ## Next Steps: (concrete fixes for next cycle)\n"
        "  PLANEOF\n\n"
        "This is CRITICAL. If you do not write the errors to\n"
        "IMPLEMENTATION_PLAN.md, the next cycle will repeat the same mistake."
    ),
}

