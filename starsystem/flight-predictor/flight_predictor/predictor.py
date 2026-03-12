"""
Capability Predictor - Joins skill and tool RAG for unified capability prediction.

This module implements the main predict_capabilities() function that:
1. Takes a CapabilityObservation (list of plan steps)
2. Queries both skill and tool RAG systems for each step
3. Converts results to hierarchical Pydantic models
4. Returns a CapabilityPrediction with recommendations

Pattern follows be_myself awareness model:
structured input → processing → guidance output
"""

import logging
from typing import Optional

from .models import (
    CapabilityObservation,
    CapabilityPrediction,
    CartONFallbackResult,
    PredictedSkill,
    PredictedSkillDomain,
    PredictedSkillset,
    PredictedServer,
    PredictedTool,
    PredictedToolDomain,
    StepPrediction,
)
from .skill_rag import SkillRAGResult, skill_rag_carton_style
from .tool_rag import ToolRAGResult, tool_rag_deductive

logger = logging.getLogger(__name__)


def _convert_skill_result(result: SkillRAGResult) -> list[PredictedSkillDomain]:
    """
    Convert SkillRAGResult dataclass to list of PredictedSkillDomain Pydantic models.

    skill_rag.py returns: DomainAggregation with .categories (list of CategoryAggregation)
    Each CategoryAggregation has .skills (list of SkillgraphHit)
    """
    domains = []

    for domain_agg in result.domains:
        # Convert categories to skillsets (category maps to skillset concept)
        skillsets = []
        for cat in domain_agg.categories:
            skills = [
                PredictedSkill(
                    name=s.skill_name,
                    confidence=s.score,
                    skillset=cat.category,
                    domain=s.domain,
                    category=s.category if s.category else None,
                )
                for s in cat.skills
            ]
            skillsets.append(
                PredictedSkillset(
                    name=cat.category,
                    domain=domain_agg.name,
                    confidence=cat.confidence,
                    skills=skills,
                )
            )

        domains.append(
            PredictedSkillDomain(
                name=domain_agg.name,
                confidence=domain_agg.confidence,
                skillsets=skillsets,
                orphan_skills=[],  # No orphan skills in current skill_rag structure
            )
        )

    return domains


def _convert_tool_result_flat(result: ToolRAGResult) -> list[PredictedToolDomain]:
    """
    Convert flat ToolRAGResult (from deductive chain) to hierarchical PredictedToolDomain.

    The new tool_rag_deductive returns a flat list of predictions, not hierarchical.
    We group by server to create the hierarchy.
    """
    # Group predictions by server
    server_map: dict[str, list[dict]] = {}
    for pred in result.predictions:
        server = pred.get("server", "unknown")
        if server not in server_map:
            server_map[server] = []
        server_map[server].append(pred)

    # Build single domain with servers
    servers = []
    all_confidences = []

    for server_name, tools in server_map.items():
        tool_models = [
            PredictedTool(
                name=t["name"],
                confidence=t["confidence"],
                server=server_name,
                domain="general",  # Not tracked in flat result
                description=None,
            )
            for t in tools
        ]
        all_confidences.extend([t["confidence"] for t in tools])

        servers.append(
            PredictedServer(
                name=server_name,
                domain="general",
                confidence=sum(t["confidence"] for t in tools) / len(tools),
                tools=tool_models,
            )
        )

    if not servers:
        return []

    # Single domain containing all servers
    avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0.0
    return [
        PredictedToolDomain(
            name="general",
            confidence=avg_confidence,
            servers=servers,
            orphan_tools=[],
        )
    ]


def _extract_top_skills(skill_domains: list[PredictedSkillDomain], limit: int = 5) -> list[str]:
    """
    Extract top skill names from hierarchical structure, sorted by confidence.
    """
    all_skills = []

    for domain in skill_domains:
        for ss in domain.skillsets:
            for skill in ss.skills:
                all_skills.append((skill.name, skill.confidence))
        for skill in domain.orphan_skills:
            all_skills.append((skill.name, skill.confidence))

    # Sort by confidence descending, take top N
    all_skills.sort(key=lambda x: x[1], reverse=True)
    return [name for name, _ in all_skills[:limit]]


def _extract_top_tools(tool_domains: list[PredictedToolDomain], limit: int = 5) -> list[str]:
    """
    Extract top tool names from hierarchical structure, sorted by confidence.
    """
    all_tools = []

    for domain in tool_domains:
        for srv in domain.servers:
            for tool in srv.tools:
                all_tools.append((tool.name, tool.confidence))
        for tool in domain.orphan_tools:
            all_tools.append((tool.name, tool.confidence))

    # Sort by confidence descending, take top N
    all_tools.sort(key=lambda x: x[1], reverse=True)
    return [name for name, _ in all_tools[:limit]]


def _aggregate_overall_domains(steps: list[StepPrediction]) -> list[str]:
    """
    Aggregate domain names across all steps, ranked by frequency and confidence.
    """
    domain_scores: dict[str, float] = {}

    for step in steps:
        for sd in step.skill_domains:
            domain_scores[sd.name] = domain_scores.get(sd.name, 0) + sd.confidence
        for td in step.tool_domains:
            domain_scores[td.name] = domain_scores.get(td.name, 0) + td.confidence

    # Sort by accumulated confidence
    sorted_domains = sorted(domain_scores.items(), key=lambda x: x[1], reverse=True)
    return [name for name, _ in sorted_domains[:5]]


def _generate_recommendations(
    steps: list[StepPrediction],
    overall_domains: list[str],
    context_domain: Optional[str],
) -> str:
    """
    Generate natural language recommendations based on predictions.
    """
    if not steps:
        return "No predictions available."

    lines = []

    # Overall domain recommendation
    if overall_domains:
        lines.append(f"Based on your plan, the primary domains are: {', '.join(overall_domains[:3])}.")

    # Context alignment check
    if context_domain:
        if context_domain.lower() in [d.lower() for d in overall_domains]:
            lines.append(f"Your context domain ({context_domain}) aligns well with predicted capabilities.")
        else:
            lines.append(
                f"Note: Your context domain ({context_domain}) differs from predicted domains. "
                "Consider if this is intentional."
            )

    # Per-step high-level recommendations
    for step in steps:
        if step.top_skills or step.top_tools:
            step_summary = f"Step {step.step_number}: "
            if step.top_skills:
                step_summary += f"Consider skills [{', '.join(step.top_skills[:2])}]"
            if step.top_skills and step.top_tools:
                step_summary += " and "
            if step.top_tools:
                step_summary += f"tools [{', '.join(step.top_tools[:2])}]"
            lines.append(step_summary)

    return " ".join(lines) if lines else "Predictions generated but no specific recommendations."


def _parse_carton_gps(gps_result: str) -> list[str]:
    """
    Extract concept names from CartON GPS result string.

    GPS format contains lines like:
    - "📍 Concept_Name (score: 0.85)"
    - Or hierarchical listings with concept names
    """
    import re

    concepts = []
    if not gps_result or "No relevant knowledge found" in gps_result:
        return concepts

    # Pattern 1: "📍 Concept_Name" or numbered "1. Concept_Name"
    pattern1 = re.findall(r'(?:📍|^\d+\.)\s*([A-Z][A-Za-z0-9_]+)', gps_result, re.MULTILINE)
    concepts.extend(pattern1)

    # Pattern 2: Lines with concept names followed by scores
    pattern2 = re.findall(r'([A-Z][A-Za-z0-9_]+)\s*\([^)]*\d+\.\d+', gps_result)
    concepts.extend(pattern2)

    # Dedupe while preserving order
    seen = set()
    unique = []
    for c in concepts:
        if c not in seen:
            seen.add(c)
            unique.append(c)

    return unique[:10]  # Limit to top 10


def _ensure_openai_key() -> None:
    """Ensure OPENAI_API_KEY is set from strata config if not in env."""
    import json
    import os
    from pathlib import Path

    if os.environ.get('OPENAI_API_KEY'):
        return

    # Try strata servers config
    strata_config = Path.home() / '.config' / 'strata' / 'servers.json'
    if strata_config.exists():
        try:
            config = json.loads(strata_config.read_text())
            for srv in config.get('mcpServers', {}).values():
                if 'env' in srv and 'OPENAI_API_KEY' in srv['env']:
                    os.environ['OPENAI_API_KEY'] = srv['env']['OPENAI_API_KEY']
                    return
        except Exception:
            pass


def _run_carton_fallback(query: str) -> Optional[CartONFallbackResult]:
    """
    Run CartON scan as Stage 2 fallback when RAG returns no matches.

    Returns None if CartON also finds nothing or if import fails.
    """
    _ensure_openai_key()

    try:
        from carton_mcp.carton_utils import CartOnUtils
        utils = CartOnUtils()
        gps_result = utils.scan_carton(query, max_results=5)

        concepts = _parse_carton_gps(gps_result)
        if concepts:
            return CartONFallbackResult(
                concepts=concepts,
                query=query,
                reasoning="RAG Stage 1 returned no matches; CartON scan invoked"
            )
    except ImportError:
        logger.warning("CartON fallback unavailable: carton_mcp not installed")
    except Exception as e:
        logger.warning(f"CartON fallback failed: {e}")

    return None


def predict_capabilities(
    observation: CapabilityObservation,
    n_results: int = 10,
) -> CapabilityPrediction:
    """
    Predict capabilities needed for a plan based on skill and tool RAG.

    Takes a list of plan steps and returns hierarchical predictions for each step,
    showing which skills and tools are likely needed.

    Args:
        observation: CapabilityObservation with plan steps and optional context domain
        n_results: Maximum number of RAG results to process per query

    Returns:
        CapabilityPrediction with:
        - Per-step predictions (skill_domains, tool_domains, top_skills, top_tools)
        - Overall domain summary
        - Natural language recommendations

    Example:
        >>> from capability_predictor.models import CapabilityObservation, PlanStep
        >>> obs = CapabilityObservation(
        ...     steps=[
        ...         PlanStep(step_number=1, description="Plan the project structure"),
        ...         PlanStep(step_number=2, description="Implement the core logic"),
        ...     ],
        ...     context_domain="PAIAB"
        ... )
        >>> prediction = predict_capabilities(obs)
        >>> prediction.steps[0].top_skills
        ['starlog', 'waypoint', 'flight-config']
        >>> prediction.overall_domains
        ['navigation', 'building']
    """
    logger.info(f"Predicting capabilities for {len(observation.steps)} steps")

    step_predictions = []

    for step in observation.steps:
        logger.info(f"Processing step {step.step_number}: {step.description[:50]}...")

        # Query skill RAG (Layer 0: exact term match + Layer 1: semantic fallback)
        skill_result = skill_rag_carton_style(step.description, n_results)

        # Query tool RAG with typed fields from PlanStep
        tool_result = tool_rag_deductive(
            description=step.description,
            deliverable=step.deliverable,
            action_type=step.action_type,
            domain=step.domain,
            context_tags=step.context_tags,
            n_results=n_results,
        )

        # Convert to Pydantic models
        skill_domains = _convert_skill_result(skill_result)
        tool_domains = _convert_tool_result_flat(tool_result)

        # Extract top items
        top_skills = _extract_top_skills(skill_domains)
        top_tools = _extract_top_tools(tool_domains)

        # Stage 2: CartON fallback based on match SCORES
        # Get best scores from skill and tool results
        best_skill_score = 0.0
        for domain in skill_domains:
            for ss in domain.skillsets:
                for skill in ss.skills:
                    best_skill_score = max(best_skill_score, skill.confidence)

        best_tool_score = 0.0
        for domain in tool_domains:
            for srv in domain.servers:
                for tool in srv.tools:
                    best_tool_score = max(best_tool_score, tool.confidence)

        best_overall_score = max(best_skill_score, best_tool_score)

        # Fallback thresholds based on layered exactness
        # 1.0 = exact match, 0.7+ = good semantic match, <0.5 = weak match
        EXACT_THRESHOLD = 0.95
        GOOD_THRESHOLD = 0.7
        WEAK_THRESHOLD = 0.5

        carton_fallback = None
        if best_overall_score < WEAK_THRESHOLD:
            # Weak matches - definitely need CartON fallback
            logger.info(f"Weak match (score={best_overall_score:.2f}) - triggering CartON fallback")
            carton_fallback = _run_carton_fallback(step.description)
        elif best_overall_score < GOOD_THRESHOLD:
            # Medium matches - CartON might help supplement
            logger.info(f"Medium match (score={best_overall_score:.2f}) - triggering CartON fallback for supplementation")
            carton_fallback = _run_carton_fallback(step.description)

        step_predictions.append(
            StepPrediction(
                step_number=step.step_number,
                description=step.description,
                skill_domains=skill_domains,
                tool_domains=tool_domains,
                top_skills=top_skills,
                top_tools=top_tools,
                carton_fallback=carton_fallback,
            )
        )

    # Aggregate overall domains
    overall_domains = _aggregate_overall_domains(step_predictions)

    # Generate recommendations
    recommendations = _generate_recommendations(
        step_predictions,
        overall_domains,
        observation.context_domain,
    )

    result = CapabilityPrediction(
        steps=step_predictions,
        overall_domains=overall_domains,
        recommendations=recommendations,
    )

    logger.info(f"Prediction complete: {len(overall_domains)} overall domains identified")
    return result


def format_capability_prediction(prediction: CapabilityPrediction) -> str:
    """
    Format CapabilityPrediction as compact [Domain: capability] output.

    Returns:
        Formatted string with domain-grouped capabilities
    """
    lines = ["🎯 Capability Prediction"]

    # Recommendations (compact)
    if prediction.recommendations:
        lines.append(f"💡 {prediction.recommendations}")

    # Per-step details in [domain: capability] format
    for step in prediction.steps:
        lines.append(f"\n**Step {step.step_number}**: {step.description[:50]}")

        # Skills grouped by domain
        if step.skill_domains:
            skill_parts = []
            for d in step.skill_domains[:3]:
                top_skills = [s.name for s in d.skillsets[0].skills[:2]] if d.skillsets else []
                if top_skills:
                    skill_parts.append(f"[{d.name}: {', '.join(top_skills)}]")
            if skill_parts:
                lines.append(f"  🎯 {' '.join(skill_parts)}")

        # Tools grouped by domain
        if step.tool_domains:
            tool_parts = []
            for d in step.tool_domains[:3]:
                top_tools = [t.name for t in d.servers[0].tools[:2]] if d.servers else []
                if top_tools:
                    tool_parts.append(f"[{d.name}: {', '.join(top_tools)}]")
            if tool_parts:
                lines.append(f"  🔧 {' '.join(tool_parts)}")

        # CartON fallback (Stage 2)
        if step.carton_fallback and step.carton_fallback.concepts:
            lines.append(f"  🔮 CartON: {', '.join(step.carton_fallback.concepts[:5])}")

    return "\n".join(lines)
