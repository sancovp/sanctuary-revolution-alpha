"""Unified *graph RAG - Query all graph types and return combined capability recommendations.

Queries: Toolgraph + Skillgraph + Flightgraph + Missiongraph + Flowgraph
Returns: Unified recommendations with hierarchical context.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

from .tool_rag import tool_rag_carton_style, format_tool_rag_result, ToolRAGResult
from .skill_rag import skill_rag_carton_style, format_skill_rag_result, SkillRAGResult
from .flight_rag import flight_rag_query, format_flight_rag_result, FlightRAGResult
from .mission_rag import mission_rag_query, format_mission_rag_result, MissionRAGResult

logger = logging.getLogger(__name__)


@dataclass
class UnifiedRAGResult:
    """Combined results from all *graph RAG queries."""
    query: str
    tools: Optional[ToolRAGResult] = None
    skills: Optional[SkillRAGResult] = None
    flights: Optional[FlightRAGResult] = None
    missions: Optional[MissionRAGResult] = None

    def has_results(self) -> bool:
        """Check if any RAG returned results."""
        return any([
            self.tools and self.tools.domains,
            self.skills and self.skills.domains,
            self.flights and self.flights.hits,
            self.missions and self.missions.hits,
        ])

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "query": self.query,
            "tools": self.tools.to_dict() if self.tools else None,
            "skills": self.skills.to_dict() if self.skills else None,
            "flights": self.flights.to_dict() if self.flights else None,
            "missions": self.missions.to_dict() if self.missions else None,
        }


def unified_rag_query(
    query: str,
    n_results: int = 5,
    include_tools: bool = True,
    include_skills: bool = True,
    include_flights: bool = True,
    include_missions: bool = True,
) -> UnifiedRAGResult:
    """
    Query all *graph RAG systems and return unified recommendations.

    Args:
        query: Natural language query
        n_results: Max results per RAG type
        include_*: Which RAG types to query

    Returns:
        UnifiedRAGResult with all matching capabilities
    """
    logger.info(f"Unified RAG query: {query}")

    result = UnifiedRAGResult(query=query)

    if include_tools:
        try:
            result.tools = tool_rag_carton_style(query, n_results)
        except Exception:
            logger.exception("Tool RAG failed")

    if include_skills:
        try:
            result.skills = skill_rag_carton_style(query, n_results)
        except Exception:
            logger.exception("Skill RAG failed")

    if include_flights:
        try:
            result.flights = flight_rag_query(query, n_results)
        except Exception:
            logger.exception("Flight RAG failed")

    if include_missions:
        try:
            result.missions = mission_rag_query(query, n_results)
        except Exception:
            logger.exception("Mission RAG failed")

    return result


def _format_missions(result: UnifiedRAGResult, compact: bool) -> list[str]:
    """Format mission results."""
    lines = []
    if result.missions and result.missions.hits:
        lines.append("\n📋 MISSIONS (multi-session workflows):")
        for m in result.missions.hits[:2 if compact else 5]:
            lines.append(f"  • {m.mission_name} ({m.score:.2f}) [{m.domain}] flights:{m.flight_count}")
    return lines


def _format_flights(result: UnifiedRAGResult, compact: bool) -> list[str]:
    """Format flight results."""
    lines = []
    if result.flights and result.flights.hits:
        lines.append("\n🛫 FLIGHTS (step-by-step procedures):")
        for f in result.flights.hits[:2 if compact else 5]:
            lines.append(f"  • {f.flight_name} ({f.score:.2f}) [{f.domain}] slots:{f.slot_count}")
    return lines


def _format_skills(result: UnifiedRAGResult, compact: bool) -> list[str]:
    """Format skill results."""
    lines = []
    if result.skills and result.skills.domains:
        lines.append("\n📚 SKILLS (knowledge packages):")
        for domain in result.skills.domains[:2 if compact else 3]:
            for cat in domain.categories[:2]:
                for s in cat.skills[:2 if compact else 3]:
                    lines.append(f"  • {s.name} ({s.score:.2f}) [{cat.category}]")
    return lines


def _format_tools(result: UnifiedRAGResult, compact: bool) -> list[str]:
    """Format tool results."""
    lines = []
    if result.tools and result.tools.domains:
        lines.append("\n🔧 TOOLS (primitives):")
        for domain in result.tools.domains[:2 if compact else 3]:
            if domain.servers:
                srv = domain.servers[0]
                tool_names = ", ".join(t.name for t in srv.tools[:3])
                lines.append(f"  • {srv.name}: [{tool_names}]")
            elif domain.orphan_tools:
                tool_names = ", ".join(t.name for t in domain.orphan_tools[:3])
                lines.append(f"  • {domain.name}: [{tool_names}]")
    return lines


def format_unified_rag_result(result: UnifiedRAGResult, compact: bool = True) -> str:
    """Format UnifiedRAGResult for injection into Claude context."""
    lines = [f"🎯 Capability Recommendations for: '{result.query}'", "=" * 60]

    if not result.has_results():
        lines.append("\n⚠️ No capability matches found")
        return "\n".join(lines)

    lines.extend(_format_missions(result, compact))
    lines.extend(_format_flights(result, compact))
    lines.extend(_format_skills(result, compact))
    lines.extend(_format_tools(result, compact))

    return "\n".join(lines)


def get_capability_context(query: str, compact: bool = True) -> str:
    """
    One-shot function for CAVE integration: query → formatted context string.

    This is the main entry point for capability resolution.
    """
    result = unified_rag_query(query)
    return format_unified_rag_result(result, compact=compact)
