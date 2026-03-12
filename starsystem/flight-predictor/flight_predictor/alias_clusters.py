"""
Alias Clusters for Capability Prediction Bootstrapping (Phase 4.2)

Alias clusters are predefined semantic mappings that bootstrap predictions
before sufficient observation data has accumulated. They encode domain knowledge
about which keywords typically map to which capabilities.

Pattern:
1. Query comes in: "plan the project structure"
2. Keywords extracted: ["plan", "project", "structure"]
3. Alias cluster matching: "plan" matches NAVIGATION cluster
4. Bootstrap prediction: boost navigation-related skills/tools

The alias clusters work WITH the rollup:
- Early on (few observations): alias clusters dominate
- Over time (many observations): rollup patterns dominate
- Configurable weights to blend them

Storage: alias_clusters.json in CAPABILITY_TRACKER_DIR
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .tracking import extract_keywords, get_storage_dir


# ============================================================================
# Default Alias Cluster Definitions
# ============================================================================

# Domain → keywords that suggest this domain
DEFAULT_DOMAIN_ALIASES: dict[str, list[str]] = {
    # Navigation & Planning domain
    "navigation": [
        "plan", "planning", "course", "waypoint", "flight", "starlog",
        "navigate", "navigation", "route", "session", "mission",
        "orient", "orientation", "track", "tracking", "journey",
    ],
    # Building & Implementation domain
    "building": [
        "code", "write", "implement", "create", "make", "build",
        "develop", "construct", "generate", "produce", "scaffold",
        "architect", "design", "structure", "compose", "craft",
    ],
    # Testing & Verification domain
    "testing": [
        "test", "verify", "check", "validate", "assert", "ensure",
        "confirm", "examine", "inspect", "audit", "review",
        "unittest", "pytest", "spec", "coverage", "qa",
    ],
    # Publishing & Deployment domain
    "publishing": [
        "publish", "deploy", "ship", "release", "distribute",
        "push", "upload", "launch", "deliver", "broadcast",
        "package", "bundle", "export", "version",
    ],
    # Documentation domain
    "documentation": [
        "document", "doc", "docs", "readme", "explain", "describe",
        "comment", "annotate", "clarify", "specification", "spec",
        "guide", "tutorial", "reference", "manual",
    ],
    # Debugging & Troubleshooting domain
    "debugging": [
        "debug", "fix", "bug", "error", "issue", "problem",
        "trace", "diagnose", "troubleshoot", "investigate",
        "root", "cause", "analyze", "resolve", "patch",
    ],
    # Configuration & Setup domain
    "configuration": [
        "config", "configure", "setup", "settings", "environment",
        "env", "initialize", "init", "install", "dependency",
        "dependencies", "requirements", "prerequisite",
    ],
    # Data & Analysis domain
    "data": [
        "data", "analyze", "analysis", "query", "database", "db",
        "sql", "neo4j", "graph", "store", "storage", "fetch",
        "retrieve", "extract", "transform", "aggregate",
    ],
    # Communication & Integration domain
    "integration": [
        "api", "mcp", "server", "client", "request", "response",
        "http", "rest", "endpoint", "service", "connect", "integrate",
        "webhook", "callback", "protocol",
    ],
    # Knowledge & Memory domain
    "knowledge": [
        "knowledge", "memory", "remember", "recall", "context",
        "carton", "concept", "wiki", "graph", "semantic",
        "observation", "persist", "store", "retrieve",
    ],
}

# Domain → typical skills in this domain (used for boosting)
DEFAULT_DOMAIN_SKILLS: dict[str, list[str]] = {
    "navigation": [
        "starlog", "waypoint", "flight-config", "starship",
        "make-flight-config", "navigation-skillset",
    ],
    "building": [
        "make-mcp", "make-skill", "make-hook", "make-subagent",
        "make-slash-command", "make-plugin",
    ],
    "testing": [
        "pytest", "unittest", "test-runner", "coverage",
    ],
    "publishing": [
        "git", "github", "release", "deploy",
    ],
    "documentation": [
        "readme", "docstring", "markdown", "sphinx",
    ],
    "debugging": [
        "debug", "trace", "profile", "log",
    ],
    "configuration": [
        "setup", "config", "environment", "install",
    ],
    "data": [
        "query", "database", "neo4j", "carton",
    ],
    "integration": [
        "api", "mcp", "http", "rest", "gnosys-kit",
    ],
    "knowledge": [
        "carton", "wiki", "memory", "observation",
    ],
}

# Domain → typical tools in this domain (used for boosting)
DEFAULT_DOMAIN_TOOLS: dict[str, list[str]] = {
    "navigation": [
        "mcp__starlog__start_starlog",
        "mcp__starlog__end_starlog",
        "mcp__starlog__orient",
        "mcp__starship__fly",
        "mcp__waypoint__start_waypoint_journey",
        "mcp__waypoint__navigate_to_next_waypoint",
    ],
    "building": [
        "Write", "Edit", "MultiEdit", "NotebookEdit",
        "Bash",
    ],
    "testing": [
        "Bash", "Read",
    ],
    "publishing": [
        "Bash",  # git commands
    ],
    "documentation": [
        "Write", "Edit", "Read",
    ],
    "debugging": [
        "Read", "Grep", "Glob", "Bash",
    ],
    "configuration": [
        "Write", "Edit", "Bash",
    ],
    "data": [
        "mcp__carton__query_wiki_graph",
        "mcp__carton__get_concept",
        "mcp__carton__chroma_query",
    ],
    "integration": [
        "mcp__gnosys_kit__run_conversation_shell",
        "WebFetch", "WebSearch",
    ],
    "knowledge": [
        "mcp__carton__add_concept",
        "mcp__carton__add_observation_batch",
        "mcp__carton__query_wiki_graph",
    ],
}


# ============================================================================
# Alias Cluster Data Class
# ============================================================================


@dataclass
class AliasCluster:
    """
    A cluster of semantic aliases for a domain.

    Each cluster defines:
    - keywords: Words that suggest this domain
    - skills: Skills typically associated with this domain
    - tools: Tools typically associated with this domain
    """
    domain: str
    keywords: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "domain": self.domain,
            "keywords": self.keywords,
            "skills": self.skills,
            "tools": self.tools,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AliasCluster":
        """Deserialize from dictionary."""
        return cls(
            domain=data["domain"],
            keywords=data.get("keywords", []),
            skills=data.get("skills", []),
            tools=data.get("tools", []),
        )


@dataclass
class AliasClustersConfig:
    """
    Configuration container for all alias clusters.
    """
    clusters: list[AliasCluster] = field(default_factory=list)
    version: str = "1.0"

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "version": self.version,
            "clusters": [c.to_dict() for c in self.clusters],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AliasClustersConfig":
        """Deserialize from dictionary."""
        return cls(
            version=data.get("version", "1.0"),
            clusters=[AliasCluster.from_dict(c) for c in data.get("clusters", [])],
        )

    def get_cluster(self, domain: str) -> Optional[AliasCluster]:
        """Get cluster by domain name."""
        for cluster in self.clusters:
            if cluster.domain == domain:
                return cluster
        return None

    def add_cluster(self, cluster: AliasCluster) -> None:
        """Add or update a cluster."""
        existing = self.get_cluster(cluster.domain)
        if existing:
            self.clusters.remove(existing)
        self.clusters.append(cluster)


# ============================================================================
# Persistence Functions
# ============================================================================


def get_alias_clusters_file() -> Path:
    """Get the alias clusters JSON file path."""
    return get_storage_dir() / "alias_clusters.json"


def save_alias_clusters(config: AliasClustersConfig) -> Path:
    """Save alias clusters configuration to disk."""
    filepath = get_alias_clusters_file()
    filepath.write_text(json.dumps(config.to_dict(), indent=2))
    return filepath


def load_alias_clusters() -> AliasClustersConfig:
    """
    Load alias clusters from disk, or create default if not exists.

    Always returns a config - creates defaults if file doesn't exist.
    """
    filepath = get_alias_clusters_file()

    if filepath.exists():
        try:
            data = json.loads(filepath.read_text())
            return AliasClustersConfig.from_dict(data)
        except Exception:
            pass

    # Create default config
    config = create_default_alias_clusters()
    save_alias_clusters(config)
    return config


def create_default_alias_clusters() -> AliasClustersConfig:
    """
    Create default alias clusters from hardcoded definitions.
    """
    clusters = []

    for domain, keywords in DEFAULT_DOMAIN_ALIASES.items():
        cluster = AliasCluster(
            domain=domain,
            keywords=keywords,
            skills=DEFAULT_DOMAIN_SKILLS.get(domain, []),
            tools=DEFAULT_DOMAIN_TOOLS.get(domain, []),
        )
        clusters.append(cluster)

    return AliasClustersConfig(clusters=clusters, version="1.0")


def reset_alias_clusters_to_defaults() -> AliasClustersConfig:
    """Reset alias clusters to default configuration."""
    config = create_default_alias_clusters()
    save_alias_clusters(config)
    return config


# ============================================================================
# Alias Matching Functions
# ============================================================================


def match_query_to_domains(query: str, config: Optional[AliasClustersConfig] = None) -> list[tuple[str, float]]:
    """
    Match a query string to domains based on alias clusters.

    Args:
        query: Natural language query
        config: Alias clusters config (loads default if None)

    Returns:
        List of (domain, score) tuples sorted by score descending.
        Score is based on number of keyword matches.
    """
    if config is None:
        config = load_alias_clusters()

    keywords = set(extract_keywords(query))
    if not keywords:
        return []

    domain_scores: dict[str, float] = {}

    for cluster in config.clusters:
        # Count keyword matches
        cluster_keywords = set(cluster.keywords)
        matches = keywords & cluster_keywords

        if matches:
            # Score = proportion of query keywords that matched
            score = len(matches) / len(keywords)
            domain_scores[cluster.domain] = score

    return sorted(domain_scores.items(), key=lambda x: x[1], reverse=True)


def get_bootstrap_predictions(
    query: str,
    config: Optional[AliasClustersConfig] = None,
    top_k: int = 5,
) -> dict[str, list[tuple[str, float]]]:
    """
    Get bootstrap predictions from alias clusters for a query.

    This is the main function for using alias clusters to boost predictions.
    It returns skills and tools that should be boosted based on which
    domains the query matches.

    Args:
        query: Natural language query/description
        config: Alias clusters config (loads default if None)
        top_k: Maximum number of predictions per category

    Returns:
        Dict with 'skills' and 'tools' keys, each containing
        list of (name, score) tuples sorted by score descending.
    """
    if config is None:
        config = load_alias_clusters()

    # Get domain matches
    domain_matches = match_query_to_domains(query, config)

    if not domain_matches:
        return {"skills": [], "tools": []}

    # Aggregate skills and tools from matched domains
    skill_scores: dict[str, float] = {}
    tool_scores: dict[str, float] = {}

    for domain, domain_score in domain_matches:
        cluster = config.get_cluster(domain)
        if cluster is None:
            continue

        # Add skills with score based on domain match
        for skill in cluster.skills:
            # Combine domain score with position (earlier = higher)
            current = skill_scores.get(skill, 0.0)
            skill_scores[skill] = max(current, domain_score)

        # Add tools with score based on domain match
        for tool in cluster.tools:
            current = tool_scores.get(tool, 0.0)
            tool_scores[tool] = max(current, domain_score)

    # Sort and take top k
    top_skills = sorted(skill_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
    top_tools = sorted(tool_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

    return {
        "skills": top_skills,
        "tools": top_tools,
    }


def format_bootstrap_predictions(predictions: dict[str, list[tuple[str, float]]]) -> str:
    """
    Format bootstrap predictions as human-readable output.
    """
    lines = ["=== Alias Cluster Bootstrap Predictions ===", ""]

    if predictions["skills"]:
        lines.append("Skills:")
        for skill, score in predictions["skills"]:
            lines.append(f"  - {skill}: {score:.2f}")
    else:
        lines.append("Skills: (none)")

    lines.append("")

    if predictions["tools"]:
        lines.append("Tools:")
        for tool, score in predictions["tools"]:
            lines.append(f"  - {tool}: {score:.2f}")
    else:
        lines.append("Tools: (none)")

    return "\n".join(lines)


# ============================================================================
# Integration with Feedback Loop
# ============================================================================


def augment_with_alias_clusters(
    query: str,
    rag_skills: Optional[list[str]] = None,
    rag_tools: Optional[list[str]] = None,
    rollup_skills: Optional[list[tuple[str, float]]] = None,
    rollup_tools: Optional[list[tuple[str, float]]] = None,
    rag_weight: float = 0.5,
    rollup_weight: float = 0.3,
    alias_weight: float = 0.2,
    top_k: int = 5,
) -> dict[str, list[tuple[str, float]]]:
    """
    Augment predictions by combining RAG, rollup, and alias cluster sources.

    This is the enhanced feedback loop that incorporates alias clusters:
    - RAG: Based on embedding similarity
    - Rollup: Based on observed usage patterns
    - Alias: Based on predefined semantic mappings

    Early in system usage (few observations), alias clusters help bootstrap.
    Over time, rollup patterns dominate as they're learned from actual usage.

    Args:
        query: Natural language query/description
        rag_skills: Skills from RAG-based prediction
        rag_tools: Tools from RAG-based prediction
        rollup_skills: Skills from rollup (keyword, prob) tuples
        rollup_tools: Tools from rollup (keyword, prob) tuples
        rag_weight: Weight for RAG predictions (default 0.5)
        rollup_weight: Weight for rollup predictions (default 0.3)
        alias_weight: Weight for alias cluster predictions (default 0.2)
        top_k: Number of top predictions to return

    Returns:
        Dict with 'skills' and 'tools' containing combined predictions.
    """
    # Get alias cluster predictions
    alias_preds = get_bootstrap_predictions(query, top_k=top_k * 2)

    # Initialize score accumulators
    skill_scores: dict[str, float] = {}
    tool_scores: dict[str, float] = {}

    # Add RAG predictions
    if rag_skills:
        for i, skill in enumerate(rag_skills):
            base_score = 1.0 - (i * 0.1)  # Rank-based score
            skill_scores[skill] = skill_scores.get(skill, 0.0) + (base_score * rag_weight)

    if rag_tools:
        for i, tool in enumerate(rag_tools):
            base_score = 1.0 - (i * 0.1)
            tool_scores[tool] = tool_scores.get(tool, 0.0) + (base_score * rag_weight)

    # Add rollup predictions
    if rollup_skills:
        for skill, prob in rollup_skills:
            skill_scores[skill] = skill_scores.get(skill, 0.0) + (prob * rollup_weight)

    if rollup_tools:
        for tool, prob in rollup_tools:
            tool_scores[tool] = tool_scores.get(tool, 0.0) + (prob * rollup_weight)

    # Add alias cluster predictions
    for skill, score in alias_preds.get("skills", []):
        skill_scores[skill] = skill_scores.get(skill, 0.0) + (score * alias_weight)

    for tool, score in alias_preds.get("tools", []):
        tool_scores[tool] = tool_scores.get(tool, 0.0) + (score * alias_weight)

    # Sort and return top k
    top_skills = sorted(skill_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
    top_tools = sorted(tool_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

    return {
        "skills": top_skills,
        "tools": top_tools,
    }


# ============================================================================
# Cluster Management Functions
# ============================================================================


def add_keyword_to_cluster(domain: str, keyword: str) -> bool:
    """
    Add a keyword to a cluster.

    Returns True if added, False if already exists.
    """
    config = load_alias_clusters()
    cluster = config.get_cluster(domain)

    if cluster is None:
        # Create new cluster
        cluster = AliasCluster(domain=domain, keywords=[keyword])
        config.add_cluster(cluster)
    elif keyword not in cluster.keywords:
        cluster.keywords.append(keyword)
    else:
        return False

    save_alias_clusters(config)
    return True


def add_skill_to_cluster(domain: str, skill: str) -> bool:
    """
    Add a skill to a cluster.

    Returns True if added, False if already exists.
    """
    config = load_alias_clusters()
    cluster = config.get_cluster(domain)

    if cluster is None:
        cluster = AliasCluster(domain=domain, skills=[skill])
        config.add_cluster(cluster)
    elif skill not in cluster.skills:
        cluster.skills.append(skill)
    else:
        return False

    save_alias_clusters(config)
    return True


def add_tool_to_cluster(domain: str, tool: str) -> bool:
    """
    Add a tool to a cluster.

    Returns True if added, False if already exists.
    """
    config = load_alias_clusters()
    cluster = config.get_cluster(domain)

    if cluster is None:
        cluster = AliasCluster(domain=domain, tools=[tool])
        config.add_cluster(cluster)
    elif tool not in cluster.tools:
        cluster.tools.append(tool)
    else:
        return False

    save_alias_clusters(config)
    return True


def list_all_clusters() -> list[dict]:
    """
    List all clusters with their contents.
    """
    config = load_alias_clusters()
    return [c.to_dict() for c in config.clusters]


def format_clusters_report() -> str:
    """
    Format a human-readable report of all alias clusters.
    """
    config = load_alias_clusters()

    lines = [
        "=" * 60,
        "ALIAS CLUSTERS CONFIGURATION",
        "=" * 60,
        f"Version: {config.version}",
        f"Total Clusters: {len(config.clusters)}",
        "",
    ]

    for cluster in sorted(config.clusters, key=lambda c: c.domain):
        lines.append(f"--- {cluster.domain.upper()} ---")
        lines.append(f"Keywords ({len(cluster.keywords)}): {', '.join(cluster.keywords[:10])}")
        if len(cluster.keywords) > 10:
            lines.append(f"  ... +{len(cluster.keywords) - 10} more")
        lines.append(f"Skills ({len(cluster.skills)}): {', '.join(cluster.skills[:5])}")
        if len(cluster.skills) > 5:
            lines.append(f"  ... +{len(cluster.skills) - 5} more")
        lines.append(f"Tools ({len(cluster.tools)}): {', '.join(cluster.tools[:5])}")
        if len(cluster.tools) > 5:
            lines.append(f"  ... +{len(cluster.tools) - 5} more")
        lines.append("")

    return "\n".join(lines)
