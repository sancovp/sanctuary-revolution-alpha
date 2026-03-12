"""
Whole-Graph Cypher Logic Matching for Flight Predictor.

Pattern from starsystem reward_system.py _get_complexity_score():
ONE Cypher query, multiple OPTIONAL MATCH chains with typed IS_A checks,
returns everything in one shot. No N+1. No iterative loops.

This module replaces the iterative _query_relationship() pattern in tool_rag.py
and the per-concept Neo4j queries in skill_rag.py.
"""

import logging
import os
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://host.docker.internal:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "password")


def _get_driver():
    """Get Neo4j driver. Returns None on failure."""
    try:
        from neo4j import GraphDatabase
        return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    except Exception:
        logger.warning("Neo4j connection failed — graph logic disabled")
        return None


def _run_query(cypher: str, params: dict) -> list[dict]:
    """Run a Cypher query and return list of record dicts."""
    driver = _get_driver()
    if not driver:
        return []
    try:
        with driver.session() as session:
            result = session.run(cypher, params)
            return [dict(record) for record in result]
    except Exception as e:
        logger.warning(f"Cypher query failed: {e}")
        return []
    finally:
        driver.close()


# ============================================================================
# Skill Graph Logic — ONE query to find all matching skills
# ============================================================================

@dataclass
class GraphSkillMatch:
    """A skill matched by graph logic."""
    name: str
    domain: str
    category: str
    has_what: str
    has_when: str
    has_produces: str
    score: float  # term overlap + graph boost
    graph_depth: int  # how many relationships confirmed
    reasoning: str


def skill_graph_logic_match(
    query: str,
    domain_filter: Optional[str] = None,
    max_results: int = 20
) -> list[GraphSkillMatch]:
    """
    Find skills using ONE whole-graph Cypher query.

    Logic: Match skills that have domain, category, what, when, produces
    relationships. Score by how many of these exist AND term overlap with query.

    This replaces the 4-layer iterative approach in skill_rag.py.
    """
    query_terms = set(query.lower().replace("-", " ").replace("_", " ").split())
    query_terms = {t for t in query_terms if len(t) > 2}

    if not query_terms:
        return []

    # Build WHERE clause for domain filter
    domain_clause = ""
    params: dict = {"limit": max_results}
    if domain_filter:
        domain_clause = "AND domain.n CONTAINS $domain_filter"
        params["domain_filter"] = domain_filter

    # ONE query matching EXACT Skill/SkillSpec model fields.
    # See: .claude/rules/graph-assembly-logic.md for canonical mapping.
    # Domains are BARE names (e.g. "Paiab"), NOT "Domain_Paiab".
    cypher = f"""
    MATCH (s:Wiki)
    WHERE s.n STARTS WITH 'Skill_'
    AND NOT s.n CONTAINS '_v'

    OPTIONAL MATCH (s)-[:HAS_DOMAIN]->(domain:Wiki)
        {domain_clause}
    OPTIONAL MATCH (s)-[:HAS_CATEGORY]->(cat:Wiki)
    OPTIONAL MATCH (s)-[:HAS_WHAT]->(what:Wiki)
    OPTIONAL MATCH (s)-[:HAS_WHEN]->(whenn:Wiki)
    OPTIONAL MATCH (s)-[:HAS_PRODUCES]->(produces:Wiki)
    OPTIONAL MATCH (s)-[:REQUIRES]->(dep:Wiki)
    OPTIONAL MATCH (s)-[:DESCRIBES]->(component:Wiki)
    OPTIONAL MATCH (s)-[:PART_OF]->(starsystem:Wiki)
    OPTIONAL MATCH (s)-[:INSTANTIATES]->(pattern:Wiki)
    OPTIONAL MATCH (s)-[:IS_A]->(type:Wiki)

    WITH s,
         collect(DISTINCT domain.n) as domains,
         collect(DISTINCT cat.n) as categories,
         collect(DISTINCT what.n) as whats,
         collect(DISTINCT whenn.n) as whens,
         collect(DISTINCT produces.n) as produces_list,
         collect(DISTINCT dep.n) as requires_list,
         collect(DISTINCT component.n) as components,
         collect(DISTINCT starsystem.n) as starsystems,
         collect(DISTINCT pattern.n) as patterns,
         collect(DISTINCT type.n) as types,
         (CASE WHEN size(collect(DISTINCT domain.n)) > 0 THEN 1 ELSE 0 END +
          CASE WHEN size(collect(DISTINCT cat.n)) > 0 THEN 1 ELSE 0 END +
          CASE WHEN size(collect(DISTINCT what.n)) > 0 THEN 1 ELSE 0 END +
          CASE WHEN size(collect(DISTINCT whenn.n)) > 0 THEN 1 ELSE 0 END +
          CASE WHEN size(collect(DISTINCT produces.n)) > 0 THEN 1 ELSE 0 END) as completeness

    RETURN s.n as name, s.d as description, domains, categories, whats, whens,
           produces_list, requires_list, components, starsystems, patterns, types, completeness
    ORDER BY completeness DESC
    LIMIT $limit
    """

    records = _run_query(cypher, params)
    if not records:
        return []

    # Score by term overlap + completeness (5 SkillSpec fields)
    matches = []
    for rec in records:
        name = rec["name"]
        desc = rec.get("description") or ""
        domains = rec.get("domains") or []
        categories = rec.get("categories") or []
        whats = rec.get("whats") or []
        whens = rec.get("whens") or []
        produces = rec.get("produces_list") or []
        completeness = rec.get("completeness", 0)

        # Build searchable text from all graph fields
        all_text = " ".join([
            name.lower().replace("_", " "),
            desc.lower(),
            " ".join((d or "").lower().replace("_", " ") for d in domains),
            " ".join((w or "").lower().replace("_", " ") for w in whats),
            " ".join((w or "").lower().replace("_", " ") for w in whens),
            " ".join((p or "").lower().replace("_", " ") for p in produces),
        ])

        text_terms = set(all_text.split())
        overlap = query_terms & text_terms
        if not overlap:
            continue

        term_score = len(overlap) / len(query_terms)
        # Completeness bonus: 0.1 per SkillSpec field present (max 0.5)
        completeness_bonus = completeness * 0.1
        total_score = min(1.0, term_score + completeness_bonus)

        matches.append(GraphSkillMatch(
            name=name,
            domain=domains[0] if domains else "Unknown",
            category=categories[0] if categories else "unknown",
            has_what=whats[0] if whats else "",
            has_when=whens[0] if whens else "",
            has_produces=produces[0] if produces else "",
            score=round(total_score, 3),
            graph_depth=completeness,
            reasoning=f"Matched terms: {overlap}, completeness: {completeness}/5"
        ))

    matches.sort(key=lambda m: m.score, reverse=True)
    return matches[:max_results]


# ============================================================================
# Tool Graph Logic — ONE query to find all matching tools
# ============================================================================

@dataclass
class GraphToolMatch:
    """A tool matched by graph logic."""
    name: str
    server: str
    domain: str
    is_a: list[str]
    score: float
    graph_depth: int
    reasoning: str


def tool_graph_logic_match(
    query: str,
    deliverable: Optional[str] = None,
    action_type: Optional[str] = None,
    domain: Optional[str] = None,
    max_results: int = 20
) -> list[GraphToolMatch]:
    """
    Find tools using ONE whole-graph Cypher query.

    Logic: Match tools with their server, domain, IS_A, INSTANTIATES,
    and PART_OF relationships. Score by term overlap + typed field matches.

    This replaces the 6-layer iterative approach in tool_rag.py.
    """
    query_terms = set(query.lower().replace("-", " ").replace("_", " ").split())
    query_terms = {t for t in query_terms if len(t) > 1}

    if not query_terms:
        return []

    # Build optional WHERE clauses for typed filters
    where_clauses = []
    params: dict = {"limit": max_results}

    if deliverable:
        where_clauses.append("(inst.n CONTAINS $deliverable OR inst.n IS NULL)")
        params["deliverable"] = deliverable
    if action_type:
        where_clauses.append(f"(isa.n CONTAINS $action_type OR isa.n IS NULL)")
        params["action_type"] = action_type.capitalize()
    if domain:
        where_clauses.append("(domain.n CONTAINS $domain OR domain.n IS NULL)")
        params["domain"] = domain

    extra_where = ""
    if where_clauses:
        extra_where = "WHERE " + " AND ".join(where_clauses)

    # ONE query: match tools with typed relationships.
    # Tool concepts use HAS_NODE for MCP server, HAS_DOMAIN for bare domain names.
    cypher = f"""
    MATCH (t:Wiki)
    WHERE t.n STARTS WITH 'Toolgraph_'

    OPTIONAL MATCH (t)-[:HAS_NODE]->(server:Wiki)
    OPTIONAL MATCH (t)-[:IS_A]->(isa:Wiki)
    OPTIONAL MATCH (t)-[:INSTANTIATES]->(inst:Wiki)
    OPTIONAL MATCH (t)-[:HAS_DOMAIN]->(domain:Wiki)
    OPTIONAL MATCH (t)-[:PART_OF]->(parent:Wiki)
    OPTIONAL MATCH (t)-[:HAS_PATTERN]->(pattern:Wiki)

    WITH t,
         collect(DISTINCT server.n) as servers,
         collect(DISTINCT isa.n) as is_a_list,
         collect(DISTINCT inst.n) as instantiates_list,
         collect(DISTINCT domain.n) as domains,
         collect(DISTINCT parent.n) as parents,
         collect(DISTINCT pattern.n) as patterns,
         (CASE WHEN size(collect(DISTINCT server.n)) > 0 THEN 1 ELSE 0 END +
          CASE WHEN size(collect(DISTINCT isa.n)) > 0 THEN 1 ELSE 0 END +
          CASE WHEN size(collect(DISTINCT inst.n)) > 0 THEN 1 ELSE 0 END +
          CASE WHEN size(collect(DISTINCT domain.n)) > 0 THEN 1 ELSE 0 END) as completeness

    RETURN
        t.n as name,
        t.d as description,
        servers,
        is_a_list,
        instantiates_list,
        domains,
        parents,
        patterns,
        completeness
    ORDER BY completeness DESC
    LIMIT $limit
    """

    records = _run_query(cypher, params)
    if not records:
        return []

    matches = []
    for rec in records:
        name = rec["name"]
        desc = rec.get("description") or ""
        servers = rec.get("servers") or []
        is_a_list = rec.get("is_a_list") or []
        instantiates = rec.get("instantiates_list") or []
        domains = rec.get("domains") or []
        completeness = rec.get("completeness", 0)

        # Build searchable text from all graph fields
        all_text = " ".join([
            name.lower().replace("toolgraph_", "").replace("_", " "),
            desc.lower(),
            " ".join((s or "").lower().replace("_", " ") for s in servers),
            " ".join((i or "").lower().replace("_", " ") for i in is_a_list),
            " ".join((d or "").lower().replace("_", " ") for d in domains),
        ])

        text_terms = set(all_text.split())
        overlap = query_terms & text_terms
        if not overlap:
            continue

        term_score = len(overlap) / len(query_terms)
        completeness_bonus = completeness * 0.08
        # Bonus for typed filter matches
        typed_bonus = 0.0
        if deliverable and any(deliverable.lower() in (i or "").lower() for i in instantiates):
            typed_bonus += 0.15
        if action_type and any(action_type.lower() in (i or "").lower() for i in is_a_list):
            typed_bonus += 0.10
        if domain and any(domain.lower() in (d or "").lower() for d in domains):
            typed_bonus += 0.10

        total_score = min(1.0, term_score + completeness_bonus + typed_bonus)

        matches.append(GraphToolMatch(
            name=name.replace("Toolgraph_", ""),
            server=servers[0] if servers else "unknown",
            domain=domains[0] if domains else "general",
            is_a=[i for i in is_a_list if i],
            score=round(total_score, 3),
            graph_depth=completeness,
            reasoning=f"Matched terms: {overlap}, completeness: {completeness}/4, typed: {typed_bonus:.2f}"
        ))

    matches.sort(key=lambda m: m.score, reverse=True)
    return matches[:max_results]


# ============================================================================
# Flight Graph Logic — ONE query to find matching flights
# ============================================================================

@dataclass
class GraphFlightMatch:
    """A flight config matched by graph logic."""
    name: str
    domain: str
    description: str
    step_count: int
    score: float
    reasoning: str


def flight_graph_logic_match(
    query: str,
    domain_filter: Optional[str] = None,
    max_results: int = 10
) -> list[GraphFlightMatch]:
    """
    Find flight configs using ONE whole-graph Cypher query.

    Matches Flight_Config concepts with their domain, steps, and skill references.
    """
    query_terms = set(query.lower().replace("-", " ").replace("_", " ").split())
    query_terms = {t for t in query_terms if len(t) > 2}

    if not query_terms:
        return []

    domain_clause = ""
    params: dict = {"limit": max_results}
    if domain_filter:
        domain_clause = "AND domain.n CONTAINS $domain_filter"
        params["domain_filter"] = domain_filter

    cypher = f"""
    MATCH (f:Wiki)
    WHERE (f)-[:IS_A]->(:Wiki {{n: 'Flight_Config'}})
       OR f.n STARTS WITH 'Flight_'

    OPTIONAL MATCH (f)-[:HAS_DOMAIN]->(domain:Wiki)
        {domain_clause}
    OPTIONAL MATCH (f)-[:HAS_STEP]->(step:Wiki)
    OPTIONAL MATCH (f)-[:REQUIRES]->(skill:Wiki)
        WHERE skill.n STARTS WITH 'Skill_'
    OPTIONAL MATCH (f)-[:PART_OF]->(starsystem:Wiki)

    WITH f,
         collect(DISTINCT domain.n) as domains,
         count(DISTINCT step) as step_count,
         collect(DISTINCT skill.n) as skills,
         collect(DISTINCT starsystem.n) as starsystems

    RETURN
        f.n as name,
        f.d as description,
        domains,
        step_count,
        skills,
        starsystems
    ORDER BY step_count DESC
    LIMIT $limit
    """

    records = _run_query(cypher, params)
    if not records:
        return []

    matches = []
    for rec in records:
        name = rec["name"]
        desc = rec.get("description") or ""
        domains = rec.get("domains") or []
        step_count = rec.get("step_count", 0)

        all_text = " ".join([
            name.lower().replace("_", " "),
            desc.lower(),
        ])

        text_terms = set(all_text.split())
        overlap = query_terms & text_terms
        if not overlap:
            continue

        term_score = len(overlap) / len(query_terms)
        matches.append(GraphFlightMatch(
            name=name,
            domain=domains[0] if domains else "unknown",
            description=desc[:200],
            step_count=step_count,
            score=round(term_score, 3),
            reasoning=f"Matched terms: {overlap}"
        ))

    matches.sort(key=lambda m: m.score, reverse=True)
    return matches[:max_results]


# ============================================================================
# Unified Graph Logic — ONE MEGA query for everything
# ============================================================================

@dataclass
class UnifiedGraphResult:
    """Results from unified graph logic matching."""
    skills: list[GraphSkillMatch] = field(default_factory=list)
    tools: list[GraphToolMatch] = field(default_factory=list)
    flights: list[GraphFlightMatch] = field(default_factory=list)
    query: str = ""

    def format(self) -> str:
        """Human-readable output."""
        lines = [f"Graph Logic Results for: '{self.query}'", "=" * 60]

        if self.skills:
            lines.append(f"\nSkills ({len(self.skills)}):")
            for s in self.skills[:5]:
                lines.append(f"  {s.name} [{s.domain}/{s.category}] score={s.score} depth={s.graph_depth}/5")

        if self.tools:
            lines.append(f"\nTools ({len(self.tools)}):")
            for t in self.tools[:5]:
                lines.append(f"  {t.name} [{t.server}] score={t.score} depth={t.graph_depth}/4")

        if self.flights:
            lines.append(f"\nFlights ({len(self.flights)}):")
            for f in self.flights[:5]:
                lines.append(f"  {f.name} [{f.domain}] steps={f.step_count} score={f.score}")

        if not (self.skills or self.tools or self.flights):
            lines.append("\nNo graph matches found.")

        return "\n".join(lines)


def unified_graph_logic_match(
    query: str,
    domain: Optional[str] = None,
    deliverable: Optional[str] = None,
    action_type: Optional[str] = None,
    max_results: int = 10
) -> UnifiedGraphResult:
    """
    Run all graph logic matches in parallel-style (3 separate queries,
    each still ONE query per type — no N+1).
    """
    skills = skill_graph_logic_match(query, domain_filter=domain, max_results=max_results)
    tools = tool_graph_logic_match(query, deliverable=deliverable, action_type=action_type,
                                    domain=domain, max_results=max_results)
    flights = flight_graph_logic_match(query, domain_filter=domain, max_results=max_results)

    return UnifiedGraphResult(
        skills=skills,
        tools=tools,
        flights=flights,
        query=query,
    )
