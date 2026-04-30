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
    CLASSIFY_CONVERSATION_SYSTEM_PROMPT,
    HARVEST_EPISODE_SYSTEM_PROMPT,
    HARVEST_JOURNEY_SYSTEM_PROMPT,
    HARVEST_EPIC_SYSTEM_PROMPT,
    CREATE_ODYSSEY_SYSTEM_PROMPT,
)
from .models import OdysseyEvent, OdysseyResult

logger = logging.getLogger(__name__)


# =============================================================================
# Type detection — deterministic CartON query, no LLM
# =============================================================================

def _get_concept_type(concept_ref: str) -> str:
    """Query CartON for concept's is_a type to determine dispatch target."""
    try:
        from carton_mcp.carton_utils import CartOnUtils
        result = CartOnUtils().query_wiki_graph(
            "MATCH (c:Wiki {n: $name})-[:IS_A]->(t:Wiki) RETURN t.n as type_name",
            {"name": concept_ref},
        )
        types = [r["type_name"].lower() for r in result.get("data", [])] if result.get("success") else []

        # Dispatch rules:
        # BUILD VERIFICATION CHAIN:
        # Bml_Learning / Done_Signal → measure_build (GNOSYS said "done", verify it)
        # Odyssey_Inclusion_Map / Odyssey_Measurement_Analysis → learn_build (make decision)
        # Odyssey_Learning_Decision → measure_narrative (cross-Epic analysis)
        # Odyssey_Narrative_Analysis → learn_narrative (TWI extraction)
        #
        # NARRATIVE HARVEST CHAIN:
        # Executive_Summary / Phase_Aggregation → harvest_episode
        # Episode_ accumulation → harvest_journey
        # Journey_ accumulation → harvest_epic
        # Epic_ accumulation → create_odyssey
        if "bml_learning" in types or "done_signal" in types:
            return "measure_build"
        elif "odyssey_inclusion_map" in types or "odyssey_measurement_analysis" in types:
            return "learn_build"
        elif "odyssey_narrative_analysis" in types:
            return "learn_narrative"
        elif "executive_summary" in types or "phase_aggregation" in types or "odyssey_narrative_decision" in types:
            return "classify_conversation"
        elif "narrative_classification" in types:
            return "harvest_episode"
        elif "episode" in types or "episode_arc" in types:
            return "harvest_journey"
        elif "journey" in types or "journey_arc" in types:
            return "harvest_epic"
        elif "epic" in types or "epic_arc" in types:
            return "create_odyssey"
        else:
            if concept_ref.startswith("Odyssey_Learning_Decision_"):
                return "measure_narrative"
            return "unknown"

    except Exception as e:
        logger.error(f"Type detection failed for {concept_ref}: {e}")
        return "unknown"


# =============================================================================
# Dispatch — the router
# =============================================================================
# Decision Taxonomy (GIINT hierarchy = hypothesis):
#
# CONTINUE (hypothesis holds, execution varies):
#   REDO   — retry same task, same approach
#   EVOLVE — system grows first (skill/rule/agent/hierarchy update), then retry
#            Making tools for yourself IS continuation, not a pivot.
#
# PIVOT (hypothesis falsified — something expected to fall out is NOT):
#   ESCALATE     — base system needs development. Architecture gap.
#   REQUIREMENTS — project intent must change. New component/feature needed.
#   DIALOGUE     — strategic direction may be wrong. Conductor message to Isaac.
#
# Key test: did this failure SURPRISE the hypothesis, or was it expected
# execution variation? Expected variation = CONTINUE. Surprise = PIVOT.
#
# NOTE: Odyssey_Narrative_Decision IS_A Transformational_Wisdom_Intent (TWI).
# TYPING BLOCKED ON: SOMA↔YOUKNOW integration not yet designed.
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
        "classify_conversation": _do_classify_conversation,
        "harvest_episode": _do_harvest_episode,
        "harvest_journey": _do_harvest_journey,
        "harvest_epic": _do_harvest_epic,
        "create_odyssey": _do_create_odyssey,
    }

    runner = runners[concept_type]

    # Run async SDNAC in sync context (same pattern as CompoctopusAgent.compile)
    try:
        try:
            asyncio.get_running_loop()
            # Already in async context (e.g. FastAPI), use thread pool
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                result = pool.submit(asyncio.run, runner(concept_ref, model)).result()
        except RuntimeError:
            # No running loop (daemon thread case), just asyncio.run
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


def dispatch_chain(concept_ref: str, model: str = DEFAULT_MODEL, max_depth: int = 4) -> list:
    """Dispatch and auto-chain through the full ML pipeline.

    The chain follows chain_to pointers from each result:
      done_signal → measure_build → learn_build → measure_narrative → learn_narrative
    Each step creates concepts that feed the next. Stops when chain_to is None
    or max_depth reached.

    Called by: OdysseyOrgan.process() and observation_worker_daemon.py
    """
    results = []
    current = concept_ref
    for i in range(max_depth):
        logger.info(f"Odyssey chain step {i+1}/{max_depth}: {current}")
        result = dispatch(current, model)
        results.append(result)
        if not result.success or not result.chain_to:
            break
        current = result.chain_to
    return results


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

    analysis_name = f"Odyssey_Measurement_Analysis_{concept_ref}_{timestamp}"
    return OdysseyResult(
        success="success" in status.lower(),
        event_type="measure_build",
        concept_ref=concept_ref,
        concepts_created=[
            f"Odyssey_Inclusion_Map_{concept_ref}_{timestamp}",
            analysis_name,
        ],
        chain_to=analysis_name,  # → learn_build
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

    narrative_name = f"Odyssey_Narrative_Analysis_{timestamp}"
    return OdysseyResult(
        success="success" in status.lower(),
        event_type="measure_narrative",
        concept_ref=concept_ref,
        concepts_created=[narrative_name],
        chain_to=narrative_name,  # → learn_narrative
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
        f"   - CONTINUE/REDO: Execution failed but direction is right. Retry same task.\n"
        f"   - CONTINUE/EVOLVE: System needs to grow first — create skill, rule, agent,\n"
        f"     or update GIINT hierarchy description. Then retry. Capability gap, not direction problem.\n"
        f"   - PIVOT/ESCALATE: Base system needs development. Architecture gap.\n"
        f"   - PIVOT/REQUIREMENTS: GIINT hierarchy hypothesis is wrong. New component or\n"
        f"     feature needed that wasn't in the structure.\n"
        f"   Key test: did this failure SURPRISE the hypothesis, or expected execution variation?\n"
        f"5. Create decision:\n"
        f"   add_concept(concept_name='Odyssey_Learning_Decision_{concept_ref}_{timestamp}',\n"
        f"     is_a=['Odyssey_Learning_Decision'], part_of=['{concept_ref}'],\n"
        f"     instantiates=['Odyssey_Learning_Decision'],\n"
        f"     concept='Decision: CONTINUE/REDO or CONTINUE/EVOLVE or PIVOT/ESCALATE or PIVOT/REQUIREMENTS. Reasoning: ...')\n"
        f"6. Based on decision:\n"
        f"   - REDO: create GIINT_Task_<original>_Attempt_N with gap list\n"
        f"   - EVOLVE: create GIINT_Tasks for the specific evolution needed:\n"
        f"     skill spec, rule spec, hierarchy update spec, agent spec\n"
        f"   - PIVOT: create Conductor message describing what needs to change\n\n"
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

    decision_name = f"Odyssey_Learning_Decision_{concept_ref}_{timestamp}"
    return OdysseyResult(
        success="success" in status.lower(),
        event_type="learn_build",
        concept_ref=concept_ref,
        concepts_created=[decision_name],
        chain_to=decision_name,  # → measure_narrative
    )


async def _do_learn_narrative(concept_ref: str, model: str = DEFAULT_MODEL) -> OdysseyResult:
    """Narrative-level learn: detect stuck patterns, escalate or create rules."""
    timestamp = datetime.now().strftime("%Y%m%d")

    goal = (
        f"You are researching the human+AI compound intelligence system.\n\n"
        f"CURRENT INPUT: {concept_ref}\n\n"
        f"STEP 1 — Read existing TWIs (what already steers the system):\n"
        f"Call: get_concept('Claude_Code_Rule_Twi_Global_Intents')\n\n"
        f"STEP 2 — Check previous TWI hypotheses (did predictions hold?):\n"
        f"Call: query_wiki_graph(cypher_query=\"MATCH (t:Wiki)-[:IS_A]->(:Wiki {{n: 'Twi_Hypothesis'}}) "
        f"RETURN t.n AS name, t.d AS desc ORDER BY t.t DESC LIMIT 5\")\n"
        f"For each previous hypothesis, check: did the predicted outcome happen?\n"
        f"Note which held and which didn't.\n\n"
        f"STEP 3 — Read recent episodes for patterns:\n"
        f"Call: query_wiki_graph(cypher_query=\"MATCH (e:Wiki)-[:IS_A]->(:Wiki {{n: 'Episode'}}) "
        f"RETURN e.n AS name, e.d AS desc ORDER BY e.t DESC LIMIT 10\")\n"
        f"Also read the current narrative analysis: get_concept('{concept_ref}')\n\n"
        f"STEP 4 — Look for patterns: what keeps working? what keeps failing? what's NOT covered by existing TWIs?\n\n"
        f"STEP 5 — Decision:\n"
        f"  CONTINUE/HEALTHY: Previous hypotheses confirmed. No new TWI needed.\n"
        f"  CONTINUE/EVOLVE: Pattern found that needs a new TWI.\n"
        f"  PIVOT/ESCALATE: Architecture broken beyond TWI. Isaac intervenes.\n"
        f"  PIVOT/DIALOGUE: Strategic direction wrong. Conductor message.\n\n"
        f"STEP 6 — Create decision concept:\n"
        f"add_concept(concept_name='Odyssey_Narrative_Decision_{timestamp}',\n"
        f"  is_a=['Odyssey_Narrative_Decision'], part_of=['Giint_Project_Odyssey_System'],\n"
        f"  instantiates=['Odyssey_Narrative_Decision'],\n"
        f"  concept='Decision: [type]. Previous hypotheses: [confirmed/falsified]. Details: ...')\n\n"
        f"STEP 7 — If EVOLVE, create TWI as hypothesis:\n"
        f"a) Create the hypothesis concept:\n"
        f"   add_concept(concept_name='Twi_Hypothesis_{timestamp}',\n"
        f"     is_a=['Twi_Hypothesis'], part_of=['Giint_Project_Odyssey_System'],\n"
        f"     instantiates=['Twi_Hypothesis'],\n"
        f"     concept='theme: [in order to X you must Y] | hypothesis: [I predict that adding this TWI will cause Z] | evidence: [episodes that support this] | aesop_type: [warning/celebration/irony/growth/discovery]')\n"
        f"b) Append the TWI rule to the global intents:\n"
        f"   add_concept(concept_name='Claude_Code_Rule_Twi_Global_Intents',\n"
        f"     is_a=['Claude_Code_Rule'],\n"
        f"     part_of=['Giint_Project_Odyssey_System'],\n"
        f"     instantiates=['Claude_Code_Rule'],\n"
        f"     concept='- <TWI here, MAX 150 chars, applies to BOTH human AND AI>',\n"
        f"     desc_update_mode='append',\n"
        f"     relationships=[{{'relationship': 'has_scope', 'related': ['global']}}])\n"
        f"   RULES: Tweet-sized. 150 chars max. Starts with '- '. NOT a summary — THE LESSON.\n"
        f"   Must apply to BOTH human AND AI. A shared cognitive architecture, not an AI instruction.\n\n"
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


# =============================================================================
# Narrative classification — determines WHAT a conversation IS before harvest
# =============================================================================

async def _do_classify_conversation(concept_ref: str, model: str = DEFAULT_MODEL) -> OdysseyResult:
    """Classify a conversation before narrative harvest. Compares L5 against TWIs to determine story role."""
    timestamp = datetime.now().strftime("%Y%m%d")

    goal = (
        f"Classify this conversation for narrative placement: {concept_ref}\n\n"
        f"STEPS:\n"
        f"1. Read active TWIs:\n"
        f"   get_concept('Claude_Code_Rule_Twi_Global_Intents')\n"
        f"2. Read the L5 summary:\n"
        f"   get_concept('{concept_ref}')\n"
        f"3. Read its L4 phases:\n"
        f"   get_concept_network('{concept_ref}', depth=2)\n"
        f"4. Determine which OMNISANC zone this happened in:\n"
        f"   - Look for starsystem references → STARSYSTEM zone\n"
        f"   - Look for HOME/orient/standup references → HOME zone\n"
        f"   - Look for plot_course/equip/skill browsing → STARPORT zone\n"
        f"5. For each phase, compare against TWIs:\n"
        f"   - Does this phase ALIGN with a TWI? → advancement\n"
        f"   - Does this phase VIOLATE a TWI? → conflict\n"
        f"   - List each TWI alignment and violation found\n"
        f"6. Detect skill/mastery state:\n"
        f"   - Skill INTRODUCED (shown existing) → Act 1a\n"
        f"   - Skill being LEARNED → Act 2a\n"
        f"   - Learning CLASHES with larger obstacle → Midpoint\n"
        f"   - Existing mastery tried FUTILELY → Act 2b\n"
        f"   - Mastery DEMONSTRATED → Act 3\n"
        f"7. Check for existing episodes on the same topic:\n"
        f"   query_wiki_graph(\"MATCH (e:Wiki)-[:IS_A]->(:Wiki {{n:'Episode'}}) "
        f"RETURN e.n, substring(e.d, 0, 200) ORDER BY e.t DESC LIMIT 10\")\n"
        f"8. Classify:\n"
        f"   - COMPLETE_JOURNEY: full 3-act arc in one conversation\n"
        f"   - NEW_EPISODE: starts a new episode about a specific topic\n"
        f"   - CONTINUE_EPISODE: continues existing episode (specify which)\n"
        f"   - FUN_AND_GAMES: routine mastery, Act 2a training\n"
        f"   - ORDINARY_WORLD: Act 1a status quo maintenance\n"
        f"   - MIDPOINT_CLASH: training clashed with larger obstacle\n"
        f"9. Create classification concept:\n"
        f"   add_concept(concept_name='Narrative_Classification_{concept_ref}_{timestamp}',\n"
        f"     is_a=['Narrative_Classification'], part_of=['{concept_ref}'],\n"
        f"     instantiates=['Narrative_Classification'],\n"
        f"     concept='classification: <type> | zone: <HOME|STARPORT|STARSYSTEM> | "
        f"twi_alignments: [list] | twi_violations: [list] | mastery_state: <state> | "
        f"suggested_episode: <existing episode ref or NEW> | beat_position: <position>',\n"
        f"     relationships=[{{'relationship': 'classifies', 'related': ['{concept_ref}']}}])\n\n"
        f"GOAL ACCOMPLISHED when classification concept is created."
    )

    flow = sdna_flow('odyssey_classify', sdnac('odyssey_classify', ariadne('odyssey_prep'),
        config=HermesConfig(
            name="odyssey_classify_conversation",
            system_prompt=CLASSIFY_CONVERSATION_SYSTEM_PROMPT,
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

    classification_name = f"Narrative_Classification_{concept_ref}_{timestamp}"
    return OdysseyResult(
        success="success" in status.lower(),
        event_type="classify_conversation",
        concept_ref=concept_ref,
        concepts_created=[classification_name],
        chain_to=classification_name,  # → harvest_episode
    )


# =============================================================================
# Narrative harvest chain — Episode → Journey → Epic → Odyssey
# =============================================================================

async def _do_harvest_episode(concept_ref: str, model: str = DEFAULT_MODEL) -> OdysseyResult:
    """Create EpisodeArc from classified conversation. TWI comparison drives scene extraction."""
    timestamp = datetime.now().strftime("%Y%m%d")

    goal = (
        f"Create Episode scene graph from classified conversation: {concept_ref}\n\n"
        f"STEPS:\n"
        f"1. Read the classification: get_concept('{concept_ref}')\n"
        f"   This tells you: classification type, zone, TWI alignments/violations,\n"
        f"   mastery state, suggested episode ref, beat position.\n"
        f"2. Read the original L5 summary (follow classifies relationship):\n"
        f"   get_concept_network('{concept_ref}', depth=1, rel_types=['CLASSIFIES'])\n"
        f"3. Read active TWIs:\n"
        f"   get_concept('Claude_Code_Rule_Twi_Global_Intents')\n"
        f"4. For each phase/iteration in the summary, compare against TWIs:\n"
        f"   - ALIGNED with TWI → ADVANCEMENT beat (the work advances a premise)\n"
        f"   - VIOLATES TWI → CONFLICT beat (the work tests/breaks a premise)\n"
        f"   - The gap between intent and reality IS the central conflict\n"
        f"   This comparison IS how you identify scenes. Drama EMERGES from it.\n"
        f"5. SCENE CLAIM CHECK — before claiming an iteration for a scene:\n"
        f"   query_wiki_graph(\"MATCH (i:Wiki {{n: '<iteration_name>'}})-[:HAS_SCENE]->(s:Wiki) "
        f"RETURN s.n LIMIT 1\")\n"
        f"   If already claimed → skip. Iteration parts compose into ONE scene only.\n"
        f"6. For EACH identified scene, create scene group + 8 SceneMachine nodes:\n"
        f"   a. Scene group:\n"
        f"      add_concept(concept_name='Scene_<N>_{concept_ref}_{timestamp}',\n"
        f"        is_a=['Scene'], part_of=['Episode_{concept_ref}_{timestamp}'],\n"
        f"        instantiates=['Scene_Model'],\n"
        f"        concept='scene_number: <N> | scene_title: <what> | beat_position: <position> | "
        f"twi_ref: <which TWI this tests> | advancement_or_conflict: <which>')\n"
        f"   b. 8 node concepts (BridgingIn through BridgingOut):\n"
        f"      add_concept(concept_name='Scene_<N>_<NodeName>_{concept_ref}_{timestamp}',\n"
        f"        is_a=['Scene_Node'], part_of=['Scene_<N>_{concept_ref}_{timestamp}'],\n"
        f"        instantiates=['Scene_Machine_Node'],\n"
        f"        concept='<dramatic content from TWI comparison>')\n"
        f"   c. Link nodes: and_then relationships. Link scenes: next_scene.\n"
        f"   d. Mark claimed iterations: add has_scene relationship from iteration to scene.\n"
        f"7. Extract 2-3 Dialog concepts per scene with EXACT quotes.\n"
        f"   add_concept(concept_name='Dialog_<Speaker>_<N>_{concept_ref}_{timestamp}',\n"
        f"     is_a=['Dialog'], part_of=['Scene_<N>_{concept_ref}_{timestamp}'],\n"
        f"     instantiates=['Dialog_Moment'],\n"
        f"     concept='speaker: <human|agent|system> | content: <EXACT QUOTE> | "
        f"context: <why this matters> | source_iteration: <CartON ref>')\n"
        f"8. Create Episode concept with act grouping:\n"
        f"   add_concept(concept_name='Episode_{concept_ref}_{timestamp}',\n"
        f"     is_a=['Episode'], part_of=[<giint_deliverable>],\n"
        f"     instantiates=['Episode_Arc'],\n"
        f"     concept='summary: ... | starsystem: ... | giint_path: ... | "
        f"central_conflict: <TWI violation pattern> | entry_state: ... | exit_state: ...',\n"
        f"     relationships=[{{'relationship': 'has_scene', 'related': [<scene names>]}},\n"
        f"                    {{'relationship': 'has_dialog', 'related': [<dialog names>]}},\n"
        f"                    {{'relationship': 'act_1', 'related': [<setup scene names>]}},\n"
        f"                    {{'relationship': 'act_2', 'related': [<confrontation scene names>]}},\n"
        f"                    {{'relationship': 'act_3', 'related': [<resolution scene names>]}}])\n\n"
        f"GOAL ACCOMPLISHED when episode + scenes + nodes + dialogs are created with act grouping."
    )

    flow = sdna_flow('odyssey_harvest_episode', sdnac('odyssey_harvest_ep', ariadne('odyssey_prep'),
        config=HermesConfig(
            name="odyssey_harvest_episode",
            system_prompt=HARVEST_EPISODE_SYSTEM_PROMPT,
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

    episode_name = f"Episode_{concept_ref}_{timestamp}"

    # Post-step: GAS validation — serialize episode to Prolog + evaluate
    gas_result = None
    if "success" in status.lower():
        try:
            gas_result = _validate_episode_via_gas(episode_name, timestamp)
            logger.info(f"GAS validation for {episode_name}: {gas_result.get('status', '?')}")
        except Exception as e:
            logger.error(f"GAS validation failed for {episode_name}: {e}")

    return OdysseyResult(
        success="success" in status.lower(),
        event_type="harvest_episode",
        concept_ref=concept_ref,
        concepts_created=[episode_name],
        chain_to=episode_name,  # → harvest_journey (if enough episodes accumulate)
    )


def _validate_episode_via_gas(episode_name: str, timestamp: str) -> dict:
    """Read episode + scenes from CartON, serialize to Prolog, run GAS evaluation.

    Called after harvest_episode SDNAC creates CartON concepts.
    Reads the concepts back, serializes to Prolog via gas_bridge,
    runs evaluate_submission(), stores result.
    """
    from pathlib import Path
    from .gas_bridge import serialize_episode, GAS_WORKSPACE_DIR

    try:
        from carton_mcp.carton_utils import CartOnUtils
        carton = CartOnUtils()
    except Exception as e:
        logger.error(f"GAS validation: CartON unavailable: {e}")
        return {"status": "error", "error": str(e)}

    # 1. Read the episode concept via Cypher
    ep_result = carton.query_wiki_graph(
        "MATCH (c:Wiki {n: $name}) RETURN c.n AS name, c.d AS desc",
        {"name": episode_name},
    )
    ep_desc = ""
    if ep_result and ep_result.get("success") and ep_result.get("data"):
        ep_desc = ep_result["data"][0].get("desc", "")
    else:
        return {"status": "error", "error": f"Episode {episode_name} not found in CartON"}

    # 2. Read scenes (HAS_SCENE relationships)
    scene_result = carton.query_wiki_graph(
        "MATCH (ep:Wiki {n: $name})-[:HAS_SCENE]->(s:Wiki) RETURN s.n AS name, s.d AS desc ORDER BY s.n",
        {"name": episode_name},
    )
    scene_concepts = scene_result.get("data", []) if scene_result and scene_result.get("success") else []

    # 3. Read active TWI
    twi_result = carton.query_wiki_graph(
        "MATCH (c:Wiki {n: 'Claude_Code_Rule_Twi_Global_Intents'}) RETURN c.d AS desc",
    )
    twi_text = ""
    if twi_result and twi_result.get("success") and twi_result.get("data"):
        twi_text = twi_result["data"][0].get("desc", "")

    # Parse TWI — take first line that starts with "- "
    in_order_to = ""
    learn_to_truly = ""
    for line in twi_text.split("\n"):
        line = line.strip()
        if line.startswith("- ") and not in_order_to:
            in_order_to = line[2:].strip()[:100]
            learn_to_truly = "embody this wisdom"  # default if TWI doesn't have learn_to_truly form
            break

    # 4. Build scene dicts from CartON concepts
    scenes = []
    for i, sc in enumerate(scene_concepts, 1):
        desc = sc.get("desc", "")
        scenes.append(dict(
            scene_number=i,
            scene_title=sc.get("name", f"scene_{i}"),
            bridging_in=desc[:200] if desc else "scene content",
            intention="intention from scene",
            conflict="conflict from scene",
            exposition="exposition from scene",
            characterization="characterization from scene",
            revelation="revelation from scene",
            outside_forces="outside forces from scene",
            bridging_out="bridging out from scene",
        ))

    # If no scenes found, create a minimal one from episode description
    if not scenes:
        scenes.append(dict(
            scene_number=1,
            scene_title=episode_name,
            bridging_in=ep_desc[:200] if ep_desc else "episode content",
            intention="intention", conflict="conflict",
            exposition="exposition", characterization="characterization",
            revelation="revelation", outside_forces="outside forces",
            bridging_out="bridging out",
        ))

    # 5. Serialize to Prolog
    prolog_text = serialize_episode(
        episode_id=episode_name,
        target_depth=4,
        twi_id="active_twi",
        in_order_to=in_order_to or "improve the system",
        learn_to_truly=learn_to_truly or "embody this wisdom",
        scenes=scenes,
    )

    # 6. Write workspace file
    workspace_dir = Path(GAS_WORKSPACE_DIR)
    workspace_dir.mkdir(parents=True, exist_ok=True)
    workspace_path = workspace_dir / f"{episode_name}.pl"
    workspace_path.write_text(prolog_text)

    # 7. Run GAS evaluation
    from ghost_story_bootstrap.harness import evaluate_submission
    foundation_path = str(Path(__file__).resolve().parent / "foundation.pl")
    if not Path(foundation_path).exists():
        # Fallback to extracted location
        foundation_path = "/tmp/gas_v1_extracted/gas_bootstrap_depth_system/foundation.pl"
    gas_result = evaluate_submission(str(workspace_path), foundation_path=foundation_path)

    # 8. Log result
    logger.info(f"GAS validation: {episode_name} → {gas_result.get('status', '?')}")

    return gas_result


async def _do_harvest_journey(concept_ref: str, model: str = DEFAULT_MODEL) -> OdysseyResult:
    """Aggregate Episodes about the same GIINT_Component into a JourneyArc."""
    timestamp = datetime.now().strftime("%Y%m%d")

    goal = (
        f"Aggregate episodes into a Journey (Hero's Journey 3-act arc) for: {concept_ref}\n\n"
        f"STEPS:\n"
        f"1. Read this episode: get_concept('{concept_ref}')\n"
        f"2. Find which GIINT_Component it belongs to from part_of relationships\n"
        f"3. Query all Episode_ concepts for the same component:\n"
        f"   query_wiki_graph(\"MATCH (e:Wiki)-[:IS_A]->(t:Wiki {{n:'Episode'}}) "
        f"WHERE e.n STARTS WITH 'Episode_' RETURN e.n, e.d ORDER BY e.t\")\n"
        f"4. If fewer than 3 episodes for same component, say GOAL ACCOMPLISHED without creating journey.\n"
        f"5. Read active TWIs to check compliance:\n"
        f"   get_concept('Claude_Code_Rule_Twi_Global_Intents')\n"
        f"6. For each episode, read its Dialog_ concepts (has_dialog relationships):\n"
        f"   get_concept_network('<episode_name>', depth=1, rel_types=['HAS_DIALOG'])\n"
        f"7. Synthesize the Journey:\n"
        f"   a. Map episodes to Act positions:\n"
        f"      - Act 1 (Setup): early episodes, entering the work, establishing intent\n"
        f"      - Act 2 (Confrontation): obstacle episodes, complications, central conflict\n"
        f"      - Act 3 (Resolution): breakthrough or failure, the return with boon\n"
        f"   b. Identify the CENTRAL CONFLICT — the thing that caused the journey to be LONGER\n"
        f"      than it should've been. Compare active TWIs vs actual behavior in episodes.\n"
        f"   c. Select 3-5 CRITICAL Dialog_ concepts from across all episodes — the turning\n"
        f"      points that tell the journey's story. Reference existing Dialog_ concept names.\n"
        f"   d. Extract the BOON — the ONE transferable insight/framework.\n"
        f"      The boon IS a framework that becomes an infoproduct.\n"
        f"8. Create journey:\n"
        f"   add_concept(concept_name='Journey_<component>_{timestamp}',\n"
        f"     is_a=['Journey'], part_of=[<giint_component>],\n"
        f"     instantiates=['Journey_Arc'],\n"
        f"     concept='summary: ... | act_1_episodes: [...] | act_2_episodes: [...] | "
        f"act_3_episodes: [...] | central_conflict: ... | twi_compliance: ... | boon_framework: ...',\n"
        f"     relationships=[{{'relationship': 'has_episode', 'related': [<episode concept names>]}},\n"
        f"                    {{'relationship': 'has_critical_dialog', 'related': [<existing Dialog_ concept names>]}}])\n\n"
        f"GOAL ACCOMPLISHED when journey concept is created with proper relationships."
    )

    flow = sdna_flow('odyssey_harvest_journey', sdnac('odyssey_harvest_jr', ariadne('odyssey_prep'),
        config=HermesConfig(
            name="odyssey_harvest_journey",
            system_prompt=HARVEST_JOURNEY_SYSTEM_PROMPT,
            goal=goal,
            model=model,
            max_turns=12,
            permission_mode="bypassPermissions",
            backend="heaven",
            heaven_inputs=HEAVEN_INPUTS,
            mcp_servers=get_odyssey_mcp_servers(),
        )))

    result = await flow.execute()
    status = str(getattr(result, 'status', '?'))

    return OdysseyResult(
        success="success" in status.lower(),
        event_type="harvest_journey",
        concept_ref=concept_ref,
        concepts_created=[],  # dynamic — agent creates if enough episodes
    )


async def _do_harvest_epic(concept_ref: str, model: str = DEFAULT_MODEL) -> OdysseyResult:
    """Aggregate Journeys about the same GIINT_Feature into an EpicArc."""
    timestamp = datetime.now().strftime("%Y%m%d")

    goal = (
        f"Aggregate journeys into an Epic for: {concept_ref}\n\n"
        f"STEPS:\n"
        f"1. Read this journey: get_concept('{concept_ref}')\n"
        f"2. Find which GIINT_Feature it belongs to\n"
        f"3. Query all Journey_ concepts for the same feature\n"
        f"4. If 2+ journeys exist for same feature, synthesize an Epic:\n"
        f"   - Feature-level summary\n"
        f"   - Key learnings across journeys\n"
        f"   - Feature-level boon\n"
        f"5. Create epic:\n"
        f"   add_concept(concept_name='Epic_<feature>_{timestamp}',\n"
        f"     is_a=['Epic'], part_of=[<giint_feature>],\n"
        f"     instantiates=['Epic_Arc'],\n"
        f"     concept='summary: ... | key_learnings: [...] | boon: ...')\n\n"
        f"GOAL ACCOMPLISHED when done."
    )

    flow = sdna_flow('odyssey_harvest_epic', sdnac('odyssey_harvest_ep', ariadne('odyssey_prep'),
        config=HermesConfig(
            name="odyssey_harvest_epic",
            system_prompt=HARVEST_EPIC_SYSTEM_PROMPT,
            goal=goal,
            model=model,
            max_turns=12,
            permission_mode="bypassPermissions",
            backend="heaven",
            heaven_inputs=HEAVEN_INPUTS,
            mcp_servers=get_odyssey_mcp_servers(),
        )))

    result = await flow.execute()
    status = str(getattr(result, 'status', '?'))

    return OdysseyResult(
        success="success" in status.lower(),
        event_type="harvest_epic",
        concept_ref=concept_ref,
        concepts_created=[],
    )


async def _do_create_odyssey(concept_ref: str, model: str = DEFAULT_MODEL) -> OdysseyResult:
    """Aggregate Epics into an OdysseyArc — the story of a GIINT_Project."""
    timestamp = datetime.now().strftime("%Y%m%d")

    goal = (
        f"Create an Odyssey narrative from accumulated Epics: {concept_ref}\n\n"
        f"STEPS:\n"
        f"1. Read this epic: get_concept('{concept_ref}')\n"
        f"2. Find which GIINT_Project it belongs to\n"
        f"3. Query all Epic_ concepts for the same project\n"
        f"4. Find RETROACTIVE CONTINUITY — how epics that seemed separate were about the same thing\n"
        f"5. Identify the emerging THEME — the grand argument across all epics\n"
        f"6. Create odyssey:\n"
        f"   add_concept(concept_name='Odyssey_<project>_{timestamp}',\n"
        f"     is_a=['Odyssey_Arc'], part_of=[<giint_project>],\n"
        f"     instantiates=['Odyssey_Arc'],\n"
        f"     concept='epics: [...] | theme: ... | retroactive_continuity: ...')\n\n"
        f"GOAL ACCOMPLISHED when odyssey concept is created."
    )

    flow = sdna_flow('odyssey_create_odyssey', sdnac('odyssey_create_od', ariadne('odyssey_prep'),
        config=HermesConfig(
            name="odyssey_create_odyssey",
            system_prompt=CREATE_ODYSSEY_SYSTEM_PROMPT,
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
        event_type="create_odyssey",
        concept_ref=concept_ref,
        concepts_created=[],
    )
