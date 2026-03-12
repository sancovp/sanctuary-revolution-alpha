"""
CartON-style Skill RAG: ChromaDB Skillgraphs → Hierarchical Results

Pattern:
1. RAG query → Get Skillgraph hits from ChromaDB (ontological sentences)
2. Extract metadata → Domain, category, pattern from Skillgraph
3. Hierarchical output → Group by domain/category
"""

import logging
import os
from dataclasses import dataclass, field

import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)

HEAVEN_DATA_DIR = os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data")

# Neo4j connection for graph layers
NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://host.docker.internal:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "password")


@dataclass
class ReasoningStep:
    """One layer's contribution to the reasoning chain."""
    layer: int
    layer_name: str
    action: str  # "boost", "expand", "filter"
    detail: str
    affected: list[str] = field(default_factory=list)


@dataclass
class SkillgraphHit:
    """Individual Skillgraph match from RAG."""
    name: str  # Skillgraph_X
    skill_name: str  # The root skill
    domain: str
    category: str  # understand, preflight, single_turn_process
    pattern: str
    score: float  # 0-1, higher is better
    sentence: str  # The ontological sentence


@dataclass
class CategoryAggregation:
    """Skills grouped by category within a domain."""
    category: str
    skills: list[SkillgraphHit] = field(default_factory=list)
    confidence: float = 0.0


@dataclass
class DomainAggregation:
    """Skills grouped by domain."""
    name: str
    categories: list[CategoryAggregation] = field(default_factory=list)
    confidence: float = 0.0


@dataclass
class SkillRAGResult:
    """Hierarchical result from Skillgraph RAG."""
    query: str
    domains: list[DomainAggregation] = field(default_factory=list)
    raw_hits: list[SkillgraphHit] = field(default_factory=list)
    reasoning_chain: list[ReasoningStep] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "query": self.query,
            "domains": [
                {
                    "name": d.name,
                    "confidence": d.confidence,
                    "categories": [
                        {
                            "category": cat.category,
                            "confidence": cat.confidence,
                            "skills": [
                                {
                                    "skillgraph": s.name,
                                    "skill": s.skill_name,
                                    "domain": s.domain,
                                    "category": s.category,
                                    "pattern": s.pattern,
                                    "score": s.score
                                }
                                for s in cat.skills
                            ]
                        }
                        for cat in d.categories
                    ]
                }
                for d in self.domains
            ],
            "raw_hits_count": len(self.raw_hits)
        }


def get_chroma_client() -> chromadb.ClientAPI:
    """Get ChromaDB client for skill embeddings."""
    chroma_path = os.path.join(HEAVEN_DATA_DIR, "chroma_db")
    return chromadb.PersistentClient(
        path=chroma_path,
        settings=Settings(anonymized_telemetry=False)
    )


def _exact_term_match_skills(query: str, n_results: int = 10) -> list[SkillgraphHit]:
    """
    Layer 0: EXACT TERM MATCH on Skillgraph concept names.

    Split query into words, find concepts where those exact words appear in the name.
    Rank by maximum overlap (most matching terms = highest rank).
    """
    # Split query into terms
    query_terms = set(query.lower().replace("-", " ").replace("_", " ").split())
    query_terms = {t for t in query_terms if len(t) > 1}  # Filter single chars

    if not query_terms:
        return []

    try:
        client = get_chroma_client()
        collection = client.get_or_create_collection(
            name="skillgraphs",
            metadata={"hnsw:space": "cosine"}
        )

        # Get ALL concept names from ChromaDB
        all_items = collection.get(include=["metadatas", "documents"])

        matches = []
        for i, doc_id in enumerate(all_items["ids"]):
            metadata = all_items["metadatas"][i] if all_items["metadatas"] else {}
            document = all_items["documents"][i] if all_items["documents"] else ""

            skillgraph_name = metadata.get("name", doc_id.split(":", 1)[-1])

            # Convert concept name to terms: Skillgraph_Make_Skill → {"make", "skill"}
            concept_terms = set(skillgraph_name.lower().replace("skillgraph_", "").replace("_", " ").split())

            # Count how many query terms match
            overlap = query_terms & concept_terms
            if overlap:
                # Score = proportion of query terms matched
                score = len(overlap) / len(query_terms)

                skill_name = skillgraph_name.replace("Skillgraph_", "Skill_")
                raw_domain = metadata.get("domain", "unknown")
                matches.append(SkillgraphHit(
                    name=skillgraph_name,
                    skill_name=metadata.get("skill", skill_name),
                    domain=raw_domain.title().replace(" ", "_"),
                    category=metadata.get("category", "").replace("Category_", ""),
                    pattern=metadata.get("pattern", "Generic_Skill_Pattern"),
                    score=score,
                    sentence=document
                ))

        # Sort by score (highest first)
        matches.sort(key=lambda x: x.score, reverse=True)

        return matches[:n_results]

    except Exception:
        logger.exception("Skillgraph exact term match failed")
        return []


def _semantic_search_skills(query: str, n_results: int = 10, domain_filter: str | None = None) -> list[SkillgraphHit]:
    """
    Layer 1: SEMANTIC SEARCH on Skillgraph embeddings.

    Falls back to ChromaDB vector similarity when exact term match misses.
    Optionally filters by domain metadata.
    """
    try:
        client = get_chroma_client()
        collection = client.get_or_create_collection(
            name="skillgraphs",
            metadata={"hnsw:space": "cosine"}
        )

        if collection.count() == 0:
            return []

        where_filter = None
        if domain_filter:
            where_filter = {"domain": domain_filter}

        results = collection.query(
            query_texts=[query],
            n_results=min(n_results, collection.count()),
            include=["metadatas", "documents", "distances"],
            where=where_filter
        )

        if not results["ids"] or not results["ids"][0]:
            return []

        hits = []
        for i, doc_id in enumerate(results["ids"][0]):
            metadata = results["metadatas"][0][i] if results["metadatas"] else {}
            document = results["documents"][0][i] if results["documents"] else ""
            distance = results["distances"][0][i] if results["distances"] else 1.0

            # ChromaDB cosine distance: 0 = identical, 2 = opposite
            # Convert to similarity score: 1 - (distance / 2)
            score = 1.0 - (distance / 2.0)

            # Threshold: reject low-confidence matches
            if score < 0.35:
                continue

            skillgraph_name = metadata.get("name", doc_id.split(":", 1)[-1])
            skill_name = skillgraph_name.replace("Skillgraph_", "Skill_")
            raw_domain = metadata.get("domain", "unknown")

            hits.append(SkillgraphHit(
                name=skillgraph_name,
                skill_name=metadata.get("skill", skill_name),
                domain=raw_domain.title().replace(" ", "_"),
                category=metadata.get("category", "").replace("Category_", ""),
                pattern=metadata.get("pattern", "Generic_Skill_Pattern"),
                score=score,
                sentence=document
            ))

        return hits

    except Exception:
        logger.exception("Skillgraph semantic search failed")
        return []


def _deduplicate_hits(hits: list[SkillgraphHit]) -> list[SkillgraphHit]:
    """Remove duplicate hits, keeping the one with the highest score."""
    seen: dict[str, SkillgraphHit] = {}
    for hit in hits:
        if hit.name not in seen or hit.score > seen[hit.name].score:
            seen[hit.name] = hit
    return sorted(seen.values(), key=lambda x: x.score, reverse=True)


def _get_neo4j_driver():
    """Get Neo4j driver for graph queries. Returns None on failure."""
    try:
        from neo4j import GraphDatabase
        return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    except Exception:
        logger.warning("Neo4j connection failed — graph layers disabled")
        return None


def _layer_produces_boost(
    hits: list[SkillgraphHit], query: str
) -> tuple[list[SkillgraphHit], ReasoningStep]:
    """
    Layer 2: HAS_PRODUCES graph boost.

    For each candidate, check what it produces via Neo4j HAS_PRODUCES edges.
    If produced artifact name has term overlap with query, boost that hit's score.
    Single batched Cypher query for all candidates.
    """
    if not hits:
        return hits, ReasoningStep(
            layer=2, layer_name="PRODUCES", action="boost",
            detail="No candidates to check"
        )

    query_terms = set(query.lower().replace("-", " ").replace("_", " ").split())
    query_terms = {t for t in query_terms if len(t) > 2}

    if not query_terms:
        return hits, ReasoningStep(
            layer=2, layer_name="PRODUCES", action="boost",
            detail="No usable query terms"
        )

    concept_names = [h.name.replace("Skillgraph_", "Skill_") for h in hits]

    driver = _get_neo4j_driver()
    if not driver:
        return hits, ReasoningStep(
            layer=2, layer_name="PRODUCES", action="boost",
            detail="Neo4j unavailable"
        )

    try:
        with driver.session() as session:
            result = session.run(
                "MATCH (s:Wiki)-[:HAS_PRODUCES]->(t:Wiki) "
                "WHERE s.n IN $names "
                "RETURN s.n AS skill, t.n AS produces",
                {"names": concept_names}
            )
            produces_map = {}
            for record in result:
                produces_map[record["skill"]] = record["produces"]
    except Exception:
        logger.warning("Neo4j produces query failed")
        return hits, ReasoningStep(
            layer=2, layer_name="PRODUCES", action="boost",
            detail="Query failed"
        )
    finally:
        driver.close()

    if not produces_map:
        return hits, ReasoningStep(
            layer=2, layer_name="PRODUCES", action="boost",
            detail=f"No produces edges found for {len(concept_names)} candidates"
        )

    boosted = []
    for hit in hits:
        concept = hit.name.replace("Skillgraph_", "Skill_")
        produces = produces_map.get(concept)
        if produces:
            artifact_terms = set(produces.lower().replace("_", " ").split())
            overlap = query_terms & artifact_terms
            if overlap:
                boost = len(overlap) / max(len(query_terms), 1) * 0.15
                hit.score = min(1.0, hit.score + boost)
                boosted.append(f"{hit.name}+{boost:.2f}(→{produces})")

    hits.sort(key=lambda x: x.score, reverse=True)

    detail = (
        f"Checked {len(produces_map)} produces edges. Boosted: {', '.join(boosted)}"
        if boosted
        else f"No term overlap between query [{query_terms}] and produced artifacts"
    )
    return hits, ReasoningStep(
        layer=2, layer_name="PRODUCES", action="boost",
        detail=detail, affected=boosted
    )


def _layer_requires_expand(
    hits: list[SkillgraphHit], max_expand: int = 5
) -> tuple[list[SkillgraphHit], ReasoningStep]:
    """
    Layer 3: REQUIRES reverse expansion.

    For understand skills in the hit set, find preflight/action skills that
    REQUIRE them. Surface those action skills alongside the understand context.
    This answers: "you found context X — here are skills that USE context X."
    """
    if not hits:
        return hits, ReasoningStep(
            layer=3, layer_name="REQUIRES", action="expand",
            detail="No candidates to expand"
        )

    concept_names = [h.name.replace("Skillgraph_", "Skill_") for h in hits]
    existing = {h.name for h in hits}

    # Only expand from understand skills (they're the dependency targets)
    understand_concepts = [
        h.name.replace("Skillgraph_", "Skill_") for h in hits
        if "understand" in h.name.lower() or "understand" in h.category.lower()
    ]

    if not understand_concepts:
        return hits, ReasoningStep(
            layer=3, layer_name="REQUIRES", action="expand",
            detail="No understand skills to trace REQUIRES from"
        )

    driver = _get_neo4j_driver()
    if not driver:
        return hits, ReasoningStep(
            layer=3, layer_name="REQUIRES", action="expand",
            detail="Neo4j unavailable"
        )

    try:
        with driver.session() as session:
            # Reverse trace: who REQUIRES these understand skills?
            result = session.run(
                "MATCH (action:Wiki)-[:REQUIRES]->(dep:Wiki) "
                "WHERE dep.n IN $deps AND action.n STARTS WITH 'Skill_' "
                "AND NOT action.n IN $existing "
                "RETURN action.n AS action_skill, dep.n AS depends_on "
                "LIMIT $limit",
                {"deps": understand_concepts, "existing": concept_names, "limit": max_expand}
            )
            expansions = [(r["action_skill"], r["depends_on"]) for r in result]
    except Exception:
        logger.warning("Neo4j REQUIRES query failed")
        return hits, ReasoningStep(
            layer=3, layer_name="REQUIRES", action="expand",
            detail="Query failed"
        )
    finally:
        driver.close()

    expanded_names = []
    for action_skill, depends_on in expansions:
        sg_name = action_skill.replace("Skill_", "Skillgraph_")
        if sg_name not in existing:
            # Score slightly below the understand skill it depends on
            dep_hit = next((h for h in hits if h.name.replace("Skillgraph_", "Skill_") == depends_on), None)
            base_score = dep_hit.score * 0.85 if dep_hit else 0.5

            hits.append(SkillgraphHit(
                name=sg_name,
                skill_name=action_skill,
                domain="Expanded",
                category="preflight",
                pattern="Requires_Expansion",
                score=base_score,
                sentence=""
            ))
            expanded_names.append(f"{sg_name}(needs {depends_on})")
            existing.add(sg_name)

    hits.sort(key=lambda x: x.score, reverse=True)

    detail = (
        f"Traced REQUIRES from {understand_concepts}. Expanded: {', '.join(expanded_names)}"
        if expanded_names
        else f"No action skills require {understand_concepts}"
    )
    return hits, ReasoningStep(
        layer=3, layer_name="REQUIRES", action="expand",
        detail=detail, affected=expanded_names
    )


def _aggregate_by_domain_category(hits: list[SkillgraphHit]) -> list[DomainAggregation]:
    """Aggregate skills by domain and category."""
    # domain -> category -> [skills]
    domain_map: dict[str, dict[str, list[SkillgraphHit]]] = {}

    for hit in hits:
        domain = hit.domain
        category = hit.category or "uncategorized"

        if domain not in domain_map:
            domain_map[domain] = {}
        if category not in domain_map[domain]:
            domain_map[domain][category] = []

        domain_map[domain][category].append(hit)

    # Convert to aggregations
    domains = []
    for domain_name, categories in domain_map.items():
        cat_aggs = []
        all_scores = []

        for cat_name, skills in categories.items():
            cat_scores = [s.score for s in skills]
            cat_confidence = sum(cat_scores) / len(cat_scores) if cat_scores else 0.0
            all_scores.extend(cat_scores)

            cat_aggs.append(CategoryAggregation(
                category=cat_name,
                skills=sorted(skills, key=lambda x: x.score, reverse=True),
                confidence=cat_confidence
            ))

        domain_confidence = sum(all_scores) / len(all_scores) if all_scores else 0.0

        domains.append(DomainAggregation(
            name=domain_name,
            categories=sorted(cat_aggs, key=lambda x: x.confidence, reverse=True),
            confidence=domain_confidence
        ))

    return sorted(domains, key=lambda x: x.confidence, reverse=True)


def skill_rag_carton_style(query: str, n_results: int = 10) -> SkillRAGResult:
    """
    CartON-style skill RAG using Skillgraph ontological sentences.

    Args:
        query: Natural language query describing what skill you need
        n_results: Maximum number of RAG results

    Returns:
        SkillRAGResult with hierarchical domain/category/skill structure
    """
    logger.info(f"Skill RAG query: {query}")
    reasoning_chain: list[ReasoningStep] = []

    # Layer 0: EXACT TERM MATCH on concept names
    exact_hits = _exact_term_match_skills(query, n_results)
    reasoning_chain.append(ReasoningStep(
        layer=0, layer_name="EXACT", action="search",
        detail=f"{len(exact_hits)} hits from term match",
        affected=[h.name for h in exact_hits[:5]]
    ))

    # Layer 1: SEMANTIC SEARCH (always runs, dedup handles overlap)
    semantic_hits = _semantic_search_skills(query, n_results)
    reasoning_chain.append(ReasoningStep(
        layer=1, layer_name="SEMANTIC", action="search",
        detail=f"{len(semantic_hits)} hits from vector similarity",
        affected=[h.name for h in semantic_hits[:5]]
    ))

    # Merge: exact hits first (higher trust), then semantic, deduplicate
    hits = _deduplicate_hits(exact_hits + semantic_hits)

    if not hits:
        logger.info("No skillgraph hits from either layer")
        return SkillRAGResult(query=query, reasoning_chain=reasoning_chain)

    # Layer 2: HAS_PRODUCES graph boost (Cypher deepens)
    hits, produces_step = _layer_produces_boost(hits, query)
    reasoning_chain.append(produces_step)
    logger.info(f"Layer 2 (produces): {produces_step.detail}")

    # Layer 3: REQUIRES reverse expansion (Cypher expands)
    hits, requires_step = _layer_requires_expand(hits)
    reasoning_chain.append(requires_step)
    logger.info(f"Layer 3 (requires): {requires_step.detail}")

    logger.info(f"Final: {len(hits)} hits after {len(reasoning_chain)} layers")

    domains = _aggregate_by_domain_category(hits)

    return SkillRAGResult(
        query=query,
        domains=domains,
        raw_hits=hits,
        reasoning_chain=reasoning_chain
    )


def format_skill_rag_result(result: SkillRAGResult) -> str:
    """Format SkillRAGResult as human-readable output."""
    lines = [f"🎯 Skill RAG Results for: '{result.query}'"]
    lines.append("=" * 60)

    if not result.domains:
        lines.append("\n⚠️ No skill predictions found")
        return "\n".join(lines)

    for domain in result.domains:
        lines.append(f"\n📁 Domain: {domain.name} (confidence: {domain.confidence:.2f})")

        for cat in domain.categories:
            lines.append(f"  📦 {cat.category} ({cat.confidence:.2f}):")
            for skill in cat.skills[:3]:
                # Extract readable skill name
                skill_display = skill.skill_name.replace("Skill_", "").replace("_", "-").lower()
                lines.append(f"    - {skill_display} ({skill.score:.2f})")
            if len(cat.skills) > 3:
                lines.append(f"    ... +{len(cat.skills) - 3} more")

    lines.append(f"\n💡 Total: {len(result.raw_hits)} skills across {len(result.domains)} domains")
    return "\n".join(lines)


# Quick test function
def test_skill_rag():
    """Test skill RAG with sample queries."""
    queries = [
        "build MCP server",
        "understand Claude Code architecture",
        "create a new skill",
    ]

    for q in queries:
        result = skill_rag_carton_style(q, n_results=5)
        print(format_skill_rag_result(result))
        print("\n")


if __name__ == "__main__":
    test_skill_rag()
