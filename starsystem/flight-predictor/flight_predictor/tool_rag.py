"""
CartON-style Tool RAG: Deductive Reasoning Chain

Pattern:
1. EMBED: description → seed Toolgraph_* concepts
2. DEDUCE: For each typed field, construct semantic query
3. TRAVERSE: CartON relationships (IS_A, PART_OF, HAS, INSTANTIATES)
4. EXPAND: Find siblings via same server/pattern
5. FILTER: Prune by tag relationships at each layer
6. RECURSE: Each layer's output feeds next layer's deduction

The chain preserves emergent identity through exact matches at every step.
Concepts JIT created on miss. Duplicates tagged together over time.
"""

import logging
import os
from dataclasses import dataclass, field
from typing import Optional

import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)

# Import CartON utils - graceful fallback if not available
try:
    from carton_mcp.carton_utils import CartOnUtils
    CARTON_AVAILABLE = True
except ImportError:
    CARTON_AVAILABLE = False
    CartOnUtils = None


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class ReasoningStep:
    """One step in the deductive chain."""
    layer: int
    query_type: str  # EMBEDDING, IS_A, PART_OF, HAS, INSTANTIATES
    reasoning: str   # Why this query
    query: str       # The query made
    results: list[str] = field(default_factory=list)
    filtered_out: list[str] = field(default_factory=list)


@dataclass
class ToolRAGResult:
    """Result with full reasoning chain."""
    query: str
    seed_concepts: list[str] = field(default_factory=list)
    expanded_concepts: list[str] = field(default_factory=list)
    final_concepts: list[str] = field(default_factory=list)
    reasoning_chain: list[ReasoningStep] = field(default_factory=list)
    predictions: list[dict] = field(default_factory=list)  # Final tool predictions
    reweight_hint: str = ""

    def format(self) -> str:
        """Human-readable output."""
        lines = [f"🔧 Tool RAG: '{self.query}'", "=" * 50]

        lines.append(f"\nSeeds (embedding): {self.seed_concepts[:5]}")
        lines.append(f"Expanded (deduction): {self.expanded_concepts[:5]}")
        lines.append(f"Final: {self.final_concepts[:10]}")

        lines.append("\n📊 Reasoning Chain:")
        for step in self.reasoning_chain:
            lines.append(f"  L{step.layer} [{step.query_type}]: {step.reasoning}")
            if step.results:
                lines.append(f"       → found: {step.results[:3]}{'...' if len(step.results) > 3 else ''}")
            if step.filtered_out:
                lines.append(f"       ✂ filtered: {step.filtered_out[:3]}")

        if self.predictions:
            lines.append("\n🎯 Predictions:")
            for p in self.predictions[:5]:
                lines.append(f"  - {p['name']} ({p['confidence']:.2f}) [{p.get('server', '?')}]")

        if self.reweight_hint:
            lines.append(f"\n{self.reweight_hint}")

        return "\n".join(lines)


# ============================================================================
# Naming Conventions
# ============================================================================

def to_toolgraph_name(tool_name: str) -> str:
    """tool_name → Toolgraph_Tool_Name"""
    words = tool_name.replace("-", "_").split("_")
    title_cased = "_".join(w.capitalize() for w in words)
    return f"Toolgraph_{title_cased}"


def from_toolgraph_name(concept: str) -> str:
    """Toolgraph_Tool_Name → tool_name"""
    if concept.startswith("Toolgraph_"):
        name = concept[10:]  # Remove prefix
        return name.lower().replace("_", "-")
    return concept


# ============================================================================
# ChromaDB Layer
# ============================================================================

def _get_chroma_client():
    """Get ChromaDB client for tool embeddings."""
    heaven_data = os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data")
    return chromadb.PersistentClient(
        path=os.path.join(heaven_data, "chroma_db"),
        settings=Settings(anonymized_telemetry=False)
    )


@dataclass
class TermMatchResult:
    """Result from exact term match with metadata."""
    concept: str
    score: float  # Term overlap proportion (0-1)
    overlap_count: int
    server: str  # From ChromaDB metadata


def _exact_term_match(query: str, n_results: int = 10) -> tuple[list[TermMatchResult], ReasoningStep]:
    """
    Layer 0: EXACT TERM MATCH on concept names.

    Split query into words, find concepts where those exact words appear in the name.
    Rank by maximum overlap (most matching terms = highest rank).

    Returns TermMatchResult with actual scores and server from metadata.
    """
    # Split query into terms
    query_terms = set(query.lower().replace("-", " ").replace("_", " ").split())
    query_terms = {t for t in query_terms if len(t) > 1}  # Filter single chars

    if not query_terms:
        return [], ReasoningStep(
            layer=0, query_type="EXACT_TERM_MATCH",
            reasoning="No valid query terms",
            query=query, results=[]
        )

    try:
        client = _get_chroma_client()
        collection = client.get_or_create_collection("toolgraphs")

        # Get ALL concept names from ChromaDB
        all_items = collection.get(include=["metadatas"])

        matches = []
        for doc_id, metadata in zip(all_items["ids"], all_items["metadatas"] or [{}] * len(all_items["ids"])):
            concept = metadata.get("name") or (doc_id.split(":", 1)[-1] if ":" in doc_id else doc_id)
            server = metadata.get("part_of", "unknown")  # Server from metadata!

            # Convert concept name to terms: Toolgraph_Add_Concept → {"add", "concept"}
            concept_terms = set(concept.lower().replace("toolgraph_", "").replace("_", " ").split())

            # Count how many query terms match
            overlap = query_terms & concept_terms
            if overlap:
                # Score = proportion of query terms matched
                score = len(overlap) / len(query_terms)
                matches.append(TermMatchResult(
                    concept=concept,
                    score=score,
                    overlap_count=len(overlap),
                    server=server
                ))

        # Sort by score (highest first), then by overlap count
        matches.sort(key=lambda x: (x.score, x.overlap_count), reverse=True)

        results = matches[:n_results]

        step = ReasoningStep(
            layer=0,
            query_type="EXACT_TERM_MATCH",
            reasoning=f"Match terms {query_terms} against concept names",
            query=query,
            results=[r.concept for r in results]
        )

        return results, step

    except Exception as e:
        logger.warning(f"Exact term match failed: {e}")
        return [], ReasoningStep(
            layer=0, query_type="EXACT_TERM_MATCH",
            reasoning=f"Find concepts for '{query}'",
            query=query, results=[]
        )


# ============================================================================
# CartON Traversal Layers
# ============================================================================

def _get_carton():
    """Get CartON utils instance."""
    if not CARTON_AVAILABLE:
        return None
    return CartOnUtils()


def _query_relationship(
    carton,
    concept: str,
    rel_type: str,
    depth: int = 1
) -> list[str]:
    """Query CartON for concepts connected by relationship type."""
    if not carton:
        return []

    try:
        result = carton.get_concept_network(
            concept_name=concept,
            depth=depth,
            rel_types=[rel_type]
        )

        connected = []
        if result.get("success") and result.get("network"):
            for item in result["network"]:
                for path in item.get("relationship_paths", []):
                    if path and path[0] == rel_type:
                        c = item.get("connected_concept")
                        if c and c not in connected:
                            connected.append(c)
        return connected

    except Exception as e:
        logger.warning(f"CartON query failed for {concept} {rel_type}: {e}")
        return []


def _layer_instantiates(
    concepts: list[str],
    deliverable: str,
    carton
) -> tuple[list[str], list[str], ReasoningStep]:
    """Filter/expand by INSTANTIATES deliverable."""
    if not deliverable:
        return concepts, [], ReasoningStep(
            layer=1, query_type="INSTANTIATES",
            reasoning="No deliverable specified, skipping",
            query="", results=concepts
        )

    # Query: what INSTANTIATES this deliverable?
    matches = []
    for concept in concepts:
        instantiates = _query_relationship(carton, concept, "INSTANTIATES")
        if deliverable in instantiates or any(deliverable.lower() in i.lower() for i in instantiates):
            matches.append(concept)

    # Also search for things that instantiate the deliverable directly
    # This expands beyond seeds
    expanded = _query_relationship(carton, deliverable, "INSTANTIATES")
    new_concepts = [c for c in expanded if c.startswith("Toolgraph_") and c not in concepts]

    filtered_out = [c for c in concepts if c not in matches]

    step = ReasoningStep(
        layer=1,
        query_type="INSTANTIATES",
        reasoning=f"What INSTANTIATES {deliverable}?",
        query=f"? INSTANTIATES {deliverable}",
        results=matches + new_concepts,
        filtered_out=filtered_out
    )

    return matches, new_concepts, step


def _layer_isa_pattern(
    concepts: list[str],
    action_type: str,
    carton
) -> tuple[list[str], list[str], ReasoningStep]:
    """Filter/expand by IS_A action pattern."""
    if not action_type:
        return concepts, [], ReasoningStep(
            layer=2, query_type="IS_A",
            reasoning="No action_type specified, skipping",
            query="", results=concepts
        )

    pattern = f"{action_type.capitalize()}_Pattern"

    matches = []
    for concept in concepts:
        is_a = _query_relationship(carton, concept, "IS_A")
        if pattern in is_a or any(action_type.lower() in i.lower() for i in is_a):
            matches.append(concept)

    # Expand: find other tools that IS_A the same pattern
    expanded = _query_relationship(carton, pattern, "IS_A")
    new_concepts = [c for c in expanded if c.startswith("Toolgraph_") and c not in concepts]

    filtered_out = [c for c in concepts if c not in matches]

    step = ReasoningStep(
        layer=2,
        query_type="IS_A",
        reasoning=f"What IS_A {pattern}?",
        query=f"? IS_A {pattern}",
        results=matches + new_concepts,
        filtered_out=filtered_out
    )

    return matches, new_concepts, step


def _layer_partof_domain(
    concepts: list[str],
    domain: str,
    carton
) -> tuple[list[str], list[str], ReasoningStep]:
    """Filter/expand by PART_OF domain chain."""
    if not domain:
        return concepts, [], ReasoningStep(
            layer=3, query_type="PART_OF",
            reasoning="No domain specified, skipping",
            query="", results=concepts
        )

    domain_concept = f"Domain_{domain}"

    matches = []
    for concept in concepts:
        # Check PART_OF chain (tool -> server -> domain)
        part_of = _query_relationship(carton, concept, "PART_OF", depth=2)
        if domain_concept in part_of or any(domain.lower() in p.lower() for p in part_of):
            matches.append(concept)

    # Expand: find other tools in this domain
    # Query domain for what's PART_OF it (reverse)
    in_domain = _query_relationship(carton, domain_concept, "PART_OF")
    new_concepts = [c for c in in_domain if c.startswith("Toolgraph_") and c not in concepts]

    filtered_out = [c for c in concepts if c not in matches]

    step = ReasoningStep(
        layer=3,
        query_type="PART_OF",
        reasoning=f"What is PART_OF {domain_concept}?",
        query=f"? PART_OF* {domain_concept}",
        results=matches + new_concepts,
        filtered_out=filtered_out
    )

    return matches, new_concepts, step


def _layer_has_sense_expansion(
    concepts: list[str],
    carton
) -> tuple[list[str], ReasoningStep]:
    """
    Expand via HAS_SENSE semantic equivalence.

    If concept A has_sense X, find ALL concepts that also has_sense X.
    These are semantically equivalent and should be returned together.
    """
    if not concepts or not carton:
        return [], ReasoningStep(
            layer=4, query_type="HAS_SENSE",
            reasoning="No concepts or CartON unavailable",
            query="", results=[]
        )

    # Find what each concept HAS_SENSE
    sense_targets = set()
    for concept in concepts:
        senses = _query_relationship(carton, concept, "HAS_SENSE", depth=1)
        sense_targets.update(senses)

    if not sense_targets:
        return [], ReasoningStep(
            layer=4, query_type="HAS_SENSE",
            reasoning="No HAS_SENSE relationships found on matched concepts",
            query=f"? HAS_SENSE ?",
            results=[]
        )

    # Find ALL concepts that share these HAS_SENSE targets (equivalence class)
    equivalents = []
    for sense in sense_targets:
        # Query: what concepts HAS_SENSE this target? (reverse query)
        try:
            result = carton.query_wiki_graph(
                f"""
                MATCH (c:Wiki)-[:HAS_SENSE]->(s:Wiki {{n: $sense}})
                WHERE c.n STARTS WITH 'Toolgraph_'
                RETURN c.n as concept
                """,
                parameters={"sense": sense}
            )
            if result.get("success") and result.get("data"):
                for row in result["data"]:
                    c = row.get("concept")
                    if c and c not in concepts and c not in equivalents:
                        equivalents.append(c)
        except Exception as e:
            logger.warning(f"HAS_SENSE reverse query failed: {e}")

    step = ReasoningStep(
        layer=4,
        query_type="HAS_SENSE",
        reasoning=f"Find equivalents via HAS_SENSE: {list(sense_targets)[:3]}",
        query=f"? HAS_SENSE {list(sense_targets)[:2]}",
        results=equivalents
    )

    return equivalents, step


def _layer_expand_siblings(
    concepts: list[str],
    carton
) -> tuple[list[str], ReasoningStep]:
    """Expand by finding siblings in same server."""
    if not concepts:
        return [], ReasoningStep(
            layer=4, query_type="PART_OF",
            reasoning="No concepts to expand",
            query="", results=[]
        )

    # Find servers for each concept
    servers = set()
    for concept in concepts:
        part_of = _query_relationship(carton, concept, "PART_OF", depth=1)
        for p in part_of:
            if p.startswith("Server_") or "server" in p.lower():
                servers.add(p)

    # Find all tools in those servers
    siblings = []
    for server in servers:
        in_server = _query_relationship(carton, server, "PART_OF")
        for tool in in_server:
            if tool.startswith("Toolgraph_") and tool not in concepts and tool not in siblings:
                siblings.append(tool)

    step = ReasoningStep(
        layer=4,
        query_type="PART_OF (siblings)",
        reasoning=f"Find siblings in servers: {list(servers)[:3]}",
        query=f"? PART_OF {list(servers)[:2]}",
        results=siblings
    )

    return siblings, step


def _layer_filter_tags(
    concepts: list[str],
    tags: list[str],
    carton
) -> tuple[list[str], ReasoningStep]:
    """Filter by IS_A tag relationships."""
    if not tags:
        return concepts, ReasoningStep(
            layer=5, query_type="IS_A (tags)",
            reasoning="No tags specified, keeping all",
            query="", results=concepts
        )

    matches = []
    filtered_out = []

    for concept in concepts:
        is_a = _query_relationship(carton, concept, "IS_A")
        # Keep if any tag matches
        if any(tag in is_a or any(tag.lower() in i.lower() for i in is_a) for tag in tags):
            matches.append(concept)
        else:
            filtered_out.append(concept)

    step = ReasoningStep(
        layer=5,
        query_type="IS_A (tags)",
        reasoning=f"Filter by tags: {tags}",
        query=f"? IS_A {tags}",
        results=matches,
        filtered_out=filtered_out
    )

    return matches, step


# ============================================================================
# Main RAG Function
# ============================================================================

def tool_rag_deductive(
    description: str,
    deliverable: Optional[str] = None,
    action_type: Optional[str] = None,
    domain: Optional[str] = None,
    context_tags: Optional[list[str]] = None,
    n_results: int = 10
) -> ToolRAGResult:
    """
    Deductive reasoning chain for tool RAG.

    Args:
        description: Natural language step description
        deliverable: What this step produces (INSTANTIATES query)
        action_type: create/read/update/delete/etc (IS_A pattern query)
        domain: PAIAB/CAVE/SANCTUM/etc (PART_OF domain query)
        context_tags: Additional IS_A filters
        n_results: Max results

    Returns:
        ToolRAGResult with predictions and reasoning chain
    """
    carton = _get_carton()
    reasoning_chain = []
    all_expanded = []

    # Layer 0: EXACT TERM MATCH on concept names
    seed_results, step0 = _exact_term_match(description, n_results * 2)
    reasoning_chain.append(step0)

    if not seed_results:
        return ToolRAGResult(
            query=description,
            reasoning_chain=reasoning_chain,
            reweight_hint=_get_reweight_hint()
        )

    # Build lookup for scores and servers from Layer 0
    match_info: dict[str, TermMatchResult] = {r.concept: r for r in seed_results}
    seeds = [r.concept for r in seed_results]
    current = seeds.copy()

    # Layer 1: Filter/expand by INSTANTIATES deliverable
    if deliverable:
        filtered, expanded, step1 = _layer_instantiates(current, deliverable, carton)
        reasoning_chain.append(step1)
        current = filtered if filtered else current  # Keep original if no matches
        all_expanded.extend(expanded)

    # Layer 2: Filter/expand by IS_A action pattern
    if action_type:
        filtered, expanded, step2 = _layer_isa_pattern(current, action_type, carton)
        reasoning_chain.append(step2)
        current = filtered if filtered else current
        all_expanded.extend(expanded)

    # Layer 3: Filter/expand by PART_OF domain
    if domain:
        filtered, expanded, step3 = _layer_partof_domain(current, domain, carton)
        reasoning_chain.append(step3)
        current = filtered if filtered else current
        all_expanded.extend(expanded)

    # Layer 4: Expand via HAS_SENSE semantic equivalence
    equivalents, step4 = _layer_has_sense_expansion(current, carton)
    reasoning_chain.append(step4)
    all_expanded.extend(equivalents)

    # Layer 5: Expand by siblings in same server
    siblings, step5 = _layer_expand_siblings(current, carton)
    reasoning_chain.append(step5)
    all_expanded.extend(siblings)

    # Layer 6: Filter by context tags
    if context_tags:
        all_concepts = list(set(current + all_expanded))
        filtered, step5 = _layer_filter_tags(all_concepts, context_tags, carton)
        reasoning_chain.append(step5)
        final = filtered
    else:
        final = list(set(current + all_expanded))

    # Build predictions using actual scores and servers from Layer 0
    predictions = []
    for concept in final[:n_results]:
        # Use match_info if available (from Layer 0), else defaults
        info = match_info.get(concept)
        if info:
            score = info.score
            server = info.server
        else:
            # Expanded concepts - use lower confidence, try to get server from metadata
            score = 0.5  # Expanded concepts get base score
            server = "unknown"

        predictions.append({
            "name": from_toolgraph_name(concept),
            "concept": concept,
            "server": server,
            "confidence": score,  # Actual term overlap score!
            "from_expansion": concept in all_expanded
        })

    return ToolRAGResult(
        query=description,
        seed_concepts=seeds,
        expanded_concepts=list(set(all_expanded)),
        final_concepts=final[:n_results],
        reasoning_chain=reasoning_chain,
        predictions=predictions,
        reweight_hint=_get_reweight_hint()
    )


def _get_reweight_hint() -> str:
    """Return the re-weight hint text."""
    return """💡 Re-weight: Add relationships to *graph concepts (Toolgraph_*, etc.)
   Example: Toolgraph_X IS_A High_Priority → re-index → better predictions"""


# ============================================================================
# Convenience wrapper matching old interface
# ============================================================================

def tool_rag_carton_style(query: str, n_results: int = 10) -> ToolRAGResult:
    """Backward-compatible wrapper using just description."""
    return tool_rag_deductive(description=query, n_results=n_results)


def format_tool_rag_result(result: ToolRAGResult) -> str:
    """Format result for display - backward compatible."""
    return result.format()


# ============================================================================
# Test
# ============================================================================

if __name__ == "__main__":
    # Test with structured input
    result = tool_rag_deductive(
        description="Create the skill package directory structure",
        deliverable="Skill_Package",
        action_type="create",
        domain="PAIAB",
        context_tags=None,
        n_results=5
    )
    print(result.format())
