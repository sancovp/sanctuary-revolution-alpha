"""Integration test runner — OctoCoder codes the Bandit.

This is Step 2 of the Compoctopus bootstrap sequence.
OctoCoder (hand-written) receives the Bandit spec and test file,
writes bandit.octo, anneals it, runs tests, rewrites until green.

The agent works in /tmp/compoctopus/ (the container is the sandbox).

Usage:
    cd /tmp/compoctopus
    PYTHONPATH=/tmp/compoctopus python3 -m compoctopus.integration.run_octocoder

Each file iteration is saved to /tmp/compoctopus/iterations/ for inspection.
"""

import asyncio
import logging
import shutil
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger("integration")

# Paths — everything inside /tmp/compoctopus
PROJECT_ROOT = Path("/tmp/compoctopus")
SPEC_FILE = PROJECT_ROOT / "specs" / "bandit_spec.md"
TEST_FILE = PROJECT_ROOT / "tests" / "test_bandit.py"
OCTO_OUTPUT = PROJECT_ROOT / "compoctopus" / "bandit.octo"
PY_OUTPUT = PROJECT_ROOT / "compoctopus" / "bandit.py"
ITERATIONS_DIR = PROJECT_ROOT / "iterations"


SANDBOX_RULES = f"""\
═══ WORKING DIRECTORY ═══

You work in: {PROJECT_ROOT}

Key paths:
  - Write your .octo file to:  {OCTO_OUTPUT}
  - Annealer will produce:     {PY_OUTPUT}
  - Tests are at:              {TEST_FILE}

ANNEAL COMMAND:
  cd {PROJECT_ROOT} && PYTHONPATH={PROJECT_ROOT} python3 -c "from compoctopus.annealer import anneal; r = anneal('{OCTO_OUTPUT}', '{PY_OUTPUT}'); print(r)"

TEST COMMAND:
  cd {PROJECT_ROOT} && PYTHONPATH={PROJECT_ROOT} python3 -m pytest {TEST_FILE} -v --tb=short

Stay inside {PROJECT_ROOT}. Do not modify any existing files.
Only create/edit bandit.octo.
"""


async def run():
    """Run OctoCoder to code the Bandit."""
    from compoctopus.octopus_coder import make_octopus_coder

    ITERATIONS_DIR.mkdir(exist_ok=True)
    iteration = [0]

    logger.info("=" * 60)
    logger.info("INTEGRATION TEST: OctoCoder → Bandit")
    logger.info("=" * 60)
    logger.info("Spec:   %s", SPEC_FILE)
    logger.info("Tests:  %s", TEST_FILE)
    logger.info("Output: %s", OCTO_OUTPUT)
    logger.info("=" * 60)

    spec_content = SPEC_FILE.read_text()
    test_content = TEST_FILE.read_text()

    coder = make_octopus_coder()
    logger.info("OctoCoder created: %s", coder)

    # Inject task-specific Ariadne elements
    try:
        from sdna.ariadne import InjectConfig

        task_elements = [
            InjectConfig(source="literal", inject_as="spec", value=spec_content),
            InjectConfig(source="literal", inject_as="test_file_content", value=test_content),
            InjectConfig(source="literal", inject_as="octo_file", value=str(OCTO_OUTPUT)),
            InjectConfig(source="literal", inject_as="test_file", value=str(TEST_FILE)),
            InjectConfig(source="literal", inject_as="py_output", value=str(PY_OUTPUT)),
            InjectConfig(source="literal", inject_as="sandbox_rules", value=SANDBOX_RULES),
        ]

        for state in coder.ariadne_elements:
            coder.ariadne_elements[state].extend(task_elements)

    except ImportError:
        logger.warning("SDNA not available — cannot inject Ariadne elements")

    # Update goal template
    if coder.hermes_config:
        coder.hermes_config.goal = (
            "═══ CURRENT STATE: {state} ═══\n\n"
            "{instructions}\n\n"
            "{sandbox_rules}\n\n"
            "═══ SPEC ═══\n{spec}\n\n"
            "═══ TEST FILE ({test_file}) ═══\n{test_file_content}\n\n"
            "═══ OUTPUT FILE: {octo_file} ═══\n"
            "═══ ANNEALED OUTPUT: {py_output} ═══\n\n"
            "═══ VALID TRANSITIONS: {valid_transitions} ═══\n\n"
            "When you complete this phase, output the next state name "
            "as a keyword to signal transition."
        )

    # Hook: version each .octo iteration
    original_build = coder._build_ariadne_chain

    def versioning_build(state):
        if OCTO_OUTPUT.exists():
            iteration[0] += 1
            ver = ITERATIONS_DIR / f"bandit_v{iteration[0]}.octo"
            shutil.copy2(OCTO_OUTPUT, ver)
            logger.info("📝 Saved iteration %d → %s", iteration[0], ver)
            if PY_OUTPUT.exists():
                shutil.copy2(PY_OUTPUT, ITERATIONS_DIR / f"bandit_v{iteration[0]}.py")
        return original_build(state)

    coder._build_ariadne_chain = versioning_build

    # Run
    logger.info("Starting OctoCoder execution...")
    try:
        result = await coder.execute(context={})
        logger.info("=" * 60)
        logger.info("RESULT: %s", result.status)
        logger.info("Final state: %s", result.context.get("_final_state"))
        logger.info("Cycles: %s", result.context.get("_cycles"))
        logger.info("Iterations: %d", iteration[0])
        logger.info("=" * 60)

        if OCTO_OUTPUT.exists():
            shutil.copy2(OCTO_OUTPUT, ITERATIONS_DIR / "bandit_final.octo")
        if PY_OUTPUT.exists():
            shutil.copy2(PY_OUTPUT, ITERATIONS_DIR / "bandit_final.py")
            logger.info("✅ Done: %s", PY_OUTPUT)

    except Exception as e:
        logger.error("❌ Failed: %s", e, exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(run())
