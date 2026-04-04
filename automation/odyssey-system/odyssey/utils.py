"""Odyssey utils — ALL logic lives here. Onion arch inner layer.

dispatch() determines event type from CartON, calls the right do_x().
Each do_x() instances ONE SDNAC with a HermesConfig and runs it.
Pattern: hierarchical_summarize/flow.py (deterministic query → goal → execute → verify).
"""

import logging
import os
from typing import Dict, Any, Optional
from datetime import datetime

from sdna import sdna_flow, sdnac, ariadne
from sdna.config import HermesConfig

from .config import (
    get_odyssey_mcp_servers,
    HEAVEN_INPUTS,
    DEFAULT_MODEL,
    MEASURE_BUILD_SYSTEM_PROMPT,
    MEASURE_NARRATIVE_SYSTEM_PROMPT,
    LEARN_BUILD_SYSTEM_PROMPT,
    LEARN_NARRATIVE_SYSTEM_PROMPT,
)
from .models import OdysseyEvent, OdysseyResult

logger = logging.getLogger(__name__)


# =============================================================================
# Type detection — deterministic CartON query, no LLM
# =============================================================================

def _get_concept_type(concept_ref: str) -> str:
    """Query CartON for concept's is_a type to determine dispatch target.

    Returns: measure_build, measure_narrative, learn_build, learn_narrative, or unknown.
    """
    try:
        from neo4j import GraphDatabase
        uri = os.getenv("NEO4J_URI", "bolt://host.docker.internal:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        pw = os.getenv("NEO4J_PASSWORD", "password")
        driver = GraphDatabase.driver(uri, auth=(user, pw))

        with driver.session() as s:
            result = s.run(
                "MATCH (c:Wiki {n: $name})-[:IS_A]->(t:Wiki) RETURN t.n as type_name",
                name=concept_ref,
            )
            types = [r["type_name"].lower() for r in result]

        driver.close()

        # Dispatch rules:
        # Bml_Learning → measure_build (GNOSYS said "done", verify it)
        # Odyssey_Inclusion_Map → learn_build (measurement done, make decision)
        # Odyssey_Narrative_Analysis → learn_narrative (cross-build analysis done)
        # Accumulation trigger → measure_narrative (periodic cross-build review)
        if "bml_learning" in types or "done_signal" in types:
            return "measure_build"
        elif "odyssey_inclusion_map" in types or "odyssey_measurement_analysis" in types:
            return "learn_build"
        elif "odyssey_narrative_analysis" in types:
            return "learn_narrative"
        else:
            # Check if this is a narrative accumulation trigger
            if concept_ref.startswith("Odyssey_Learning_Decision_"):
                return "measure_narrative"
            return "unknown"

    except Exception as e:
        logger.error(f"Type detection failed for {concept_ref}: {e}")
        return "unknown"


# =============================================================================
# Dispatch — the router
# =============================================================================

def dispatch(concept_ref: str, model: str = DEFAULT_MODEL) -> OdysseyResult:
    """Route an event to the correct do_x method. Called by OdysseyOrgan.process()."""
    import asyncio

    concept_type = _get_concept_type(concept_ref)
    logger.info(f"Odyssey dispatch: {concept_ref} -> {concept_type}")

    if concept_type == "unknown":
        return OdysseyResult(
            success=False,
            event_type="unknown",
            concept_ref=concept_ref,
            error=f"Unknown concept type for {concept_ref}",
        )

    runners = {
        "measure_build": _do_measure_build,
        "measure_narrative": _do_measure_narrative,
        "learn_build": _do_learn_build,
        "learn_narrative": _do_learn_narrative,
    }

    runner = runners[concept_type]

    # Run async SDNAC in sync context (same pattern as CompoctopusAgent.compile)
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                result = pool.submit(asyncio.run, runner(concept_ref, model)).result()
        else:
            result = asyncio.run(runner(concept_ref, model))
        return result
    except Exception as e:
        logger.error(f"Odyssey dispatch failed: {e}")
        return OdysseyResult(
            success=False,
            event_type=concept_type,
            concept_ref=concept_ref,
            error=str(e),
        )


# =============================================================================
# The 4 do_x methods — each instances ONE SDNAC
# =============================================================================

async def _do_measure_build(concept_ref: str, model: str = DEFAULT_MODEL) -> OdysseyResult:
    """Verify a BUILD agent's claimed completion. Creates Odyssey_Inclusion_Map + Odyssey_Measurement_Analysis."""
    timestamp = datetime.now().strftime("%Y%m%d")

    goal = (
        f"Verify the build output claimed by concept: {concept_ref}\n\n"
        f"STEPS:\n"
        f"1. Use get_concept('{concept_ref}') to read the claimed completion\n"
        f"2. Use get_concept_network('{concept_ref}', depth=2) to trace the full concept web\n"
        f"3. For each Inclusion_Map in the web: verify the done signal has structural proof\n"
        f"   - Does it show what code changed? What test passed? What artifact was produced?\n"
        f"   - Or is it vague like 'did the thing'?\n"
        f"4. Check for hallucination: did the agent claim things exist that don't?\n"
        f"   - Use query_wiki_graph to verify referenced concepts actually exist\n"
        f"   - If fabricated, call flag_hallucination with evidence\n"
        f"5. Create your assessment:\n"
        f"   add_concept(concept_name='Odyssey_Inclusion_Map_{concept_ref}_{timestamp}',\n"
        f"     is_a=['Odyssey_Inclusion_Map'], part_of=['{concept_ref}'],\n"
        f"     instantiates=['Odyssey_Inclusion_Map'],\n"
        f"     concept='PASS or FAIL with reasoning for each item checked')\n"
        f"6. Create measurement summary:\n"
        f"   add_concept(concept_name='Odyssey_Measurement_Analysis_{concept_ref}_{timestamp}',\n"
        f"     is_a=['Odyssey_Measurement_Analysis'], part_of=['{concept_ref}'],\n"
        f"     instantiates=['Odyssey_Measurement_Analysis'],\n"
        f"     concept='Total checked, PASS count, FAIL count, hallucinations found, recommendation: CONTINUE or REDO')\n\n"
        f"GOAL ACCOMPLISHED when both concepts are created."
    )

    flow = sdna_flow('odyssey_measure_build', sdnac('odyssey_measure_build', ariadne('odyssey_prep'),
        config=HermesConfig(
            name="odyssey_measure_build",
            system_prompt=MEASURE_BUILD_SYSTEM_PROMPT,
            goal=goal,
            model=model,
            max_turns=20,
            permission_mode="bypassPermissions",
            backend="heaven",
            heaven_inputs=HEAVEN_INPUTS,
            mcp_servers=get_odyssey_mcp_servers(),
        )))

    result = await flow.execute()
    status = str(getattr(result, 'status', '?'))

    return OdysseyResult(
        success="success" in status.lower(),
        event_type="measure_build",
        concept_ref=concept_ref,
        concepts_created=[
            f"Odyssey_Inclusion_Map_{concept_ref}_{timestamp}",
            f"Odyssey_Measurement_Analysis_{concept_ref}_{timestamp}",
        ],
    )


async def _do_measure_narrative(concept_ref: str, model: str = DEFAULT_MODEL) -> OdysseyResult:
    """Cross-build pattern analysis. Creates Odyssey_Narrative_Analysis."""
    timestamp = datetime.now().strftime("%Y%m%d")

    goal = (
        f"Analyze patterns across recent build cycles triggered by: {concept_ref}\n\n"
        f"STEPS:\n"
        f"1. Query CartON for recent Odyssey_Learning_Decision concepts:\n"
        f"   query_wiki_graph(\"MATCH (n:Wiki) WHERE n.n STARTS WITH 'Odyssey_Learning_Decision_' "
        f"RETURN n.n, n.d ORDER BY n.t DESC LIMIT 20\")\n"
        f"2. Analyze decision distribution: how many CONTINUE vs REDO?\n"
        f"3. Check for Groundhog Day: same task/deliverable getting REDO repeatedly?\n"
        f"4. Check for drift: are later builds solving different problems than intended?\n"
        f"5. Create analysis:\n"
        f"   add_concept(concept_name='Odyssey_Narrative_Analysis_{timestamp}',\n"
        f"     is_a=['Odyssey_Narrative_Analysis'], part_of=['Giint_Project_Odyssey_System'],\n"
        f"     instantiates=['Odyssey_Narrative_Analysis'],\n"
        f"     concept='Total builds analyzed, CONTINUE/REDO ratio, stuck patterns found, health score')\n\n"
        f"GOAL ACCOMPLISHED when analysis concept is created."
    )

    flow = sdna_flow('odyssey_measure_narrative', sdnac('odyssey_measure_narr', ariadne('odyssey_prep'),
        config=HermesConfig(
            name="odyssey_measure_narrative",
            system_prompt=MEASURE_NARRATIVE_SYSTEM_PROMPT,
            goal=goal,
            model=model,
            max_turns=15,
            permission_mode="bypassPermissions",
            backend="heaven",
            heaven_inputs=HEAVEN_INPUTS,
            mcp_servers=get_odyssey_mcp_servers(),
        )))

    result = await flow.execute()
    status = str(getattr(result, 'status', '?'))

    return OdysseyResult(
        success="success" in status.lower(),
        event_type="measure_narrative",
        concept_ref=concept_ref,
        concepts_created=[f"Odyssey_Narrative_Analysis_{timestamp}"],
    )


async def _do_learn_build(concept_ref: str, model: str = DEFAULT_MODEL) -> OdysseyResult:
    """Make CONTINUE/REDO decision. Creates Odyssey_Learning_Decision (THE TK trigger)."""
    timestamp = datetime.now().strftime("%Y%m%d")

    goal = (
        f"Make a learn decision based on measurement: {concept_ref}\n\n"
        f"STEPS:\n"
        f"1. Read the measurement: get_concept('{concept_ref}')\n"
        f"2. Trace its web: get_concept_network('{concept_ref}', depth=2)\n"
        f"3. Find the Odyssey_Measurement_Analysis in the web — read its recommendation\n"
        f"4. Make YOUR decision (you are adversarial — don't just agree):\n"
        f"   - CONTINUE: All inclusion maps passed, no hallucinations, evidence is structural\n"
        f"   - REDO: Any failure, any hallucination, any vague evidence\n"
        f"5. Create decision:\n"
        f"   add_concept(concept_name='Odyssey_Learning_Decision_{concept_ref}_{timestamp}',\n"
        f"     is_a=['Odyssey_Learning_Decision'], part_of=['{concept_ref}'],\n"
        f"     instantiates=['Odyssey_Learning_Decision'],\n"
        f"     concept='Decision: CONTINUE or REDO. Reasoning: ...')\n"
        f"6. If REDO: create a new task attempt:\n"
        f"   - Find the original GIINT_Task from the concept web\n"
        f"   - add_concept(concept_name='GIINT_Task_<original>_Attempt_N',\n"
        f"     is_a=['GIINT_Task'], part_of=[<original_deliverable>],\n"
        f"     instantiates=['GIINT_Task'],\n"
        f"     concept='REDO: <what was wrong and what needs to be fixed>')\n\n"
        f"GOAL ACCOMPLISHED when decision concept is created."
    )

    flow = sdna_flow('odyssey_learn_build', sdnac('odyssey_learn_build', ariadne('odyssey_prep'),
        config=HermesConfig(
            name="odyssey_learn_build",
            system_prompt=LEARN_BUILD_SYSTEM_PROMPT,
            goal=goal,
            model=model,
            max_turns=15,
            permission_mode="bypassPermissions",
            backend="heaven",
            heaven_inputs=HEAVEN_INPUTS,
            mcp_servers=get_odyssey_mcp_servers(),
        )))

    result = await flow.execute()
    status = str(getattr(result, 'status', '?'))

    return OdysseyResult(
        success="success" in status.lower(),
        event_type="learn_build",
        concept_ref=concept_ref,
        concepts_created=[f"Odyssey_Learning_Decision_{concept_ref}_{timestamp}"],
    )


async def _do_learn_narrative(concept_ref: str, model: str = DEFAULT_MODEL) -> OdysseyResult:
    """Narrative-level learn: detect stuck patterns, escalate or create rules."""
    timestamp = datetime.now().strftime("%Y%m%d")

    goal = (
        f"Analyze narrative-level patterns from: {concept_ref}\n\n"
        f"STEPS:\n"
        f"1. Read the narrative analysis: get_concept('{concept_ref}')\n"
        f"2. Check rerun ratio: if > 50%% with 3+ reruns → ESCALATE\n"
        f"3. Check for repeated adaptations that failed → systemic issue\n"
        f"4. Decision:\n"
        f"   - HEALTHY: Ratio is fine, no stuck patterns\n"
        f"   - ESCALATE: Stuck pattern detected, human needs to intervene\n"
        f"   - ADAPT: Create new skill or rule to fix systemic root cause\n"
        f"5. Create decision:\n"
        f"   add_concept(concept_name='Odyssey_Narrative_Decision_{timestamp}',\n"
        f"     is_a=['Odyssey_Narrative_Decision'], part_of=['Giint_Project_Odyssey_System'],\n"
        f"     instantiates=['Odyssey_Narrative_Decision'],\n"
        f"     concept='Decision: HEALTHY/ESCALATE/ADAPT. Details: ...')\n\n"
        f"GOAL ACCOMPLISHED when decision concept is created."
    )

    flow = sdna_flow('odyssey_learn_narrative', sdnac('odyssey_learn_narr', ariadne('odyssey_prep'),
        config=HermesConfig(
            name="odyssey_learn_narrative",
            system_prompt=LEARN_NARRATIVE_SYSTEM_PROMPT,
            goal=goal,
            model=model,
            max_turns=10,
            permission_mode="bypassPermissions",
            backend="heaven",
            heaven_inputs=HEAVEN_INPUTS,
            mcp_servers=get_odyssey_mcp_servers(),
        )))

    result = await flow.execute()
    status = str(getattr(result, 'status', '?'))

    return OdysseyResult(
        success="success" in status.lower(),
        event_type="learn_narrative",
        concept_ref=concept_ref,
        concepts_created=[f"Odyssey_Narrative_Decision_{timestamp}"],
    )
