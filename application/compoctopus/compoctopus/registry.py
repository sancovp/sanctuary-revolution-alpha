"""Carton-backed registry for MCPs, skills, domains, and arms.

The registry is the knowledge source that the Bandit and compiler arms
query when they need to know:
- "what MCPs exist?"
- "what skills are available?"
- "what domains are registered?"
- "what arms exist for this ArmKind?" (Bandit SELECT/CONSTRUCT decision)

Backed by the Carton knowledge graph:
- MCPs are registered as concepts with tool surface relationships
- Skills are registered as concepts with behavioral descriptions
- Domains are registered as concepts with subdomain hierarchies
- Arms are registered as ArmKind → CA composition recipes

When a CA is created, it auto-registers as an arm in the registry.
The Bandit queries the registry to decide SELECT vs CONSTRUCT.

This module abstracts Carton access behind a clean interface
so compiler arms don't need to know Cypher or the KG schema.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from compoctopus.types import ArmKind, MCPConfig, SkillSpec, ToolSpec

logger = logging.getLogger(__name__)


# =============================================================================
# Registry entries
# =============================================================================

@dataclass
class RegisteredMCP:
    """An MCP server registered in the knowledge graph."""
    name: str
    description: str = ""
    command: str = ""
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    tools: List[ToolSpec] = field(default_factory=list)
    domains: List[str] = field(default_factory=list)  # Which domains this MCP serves

    def to_config(self) -> MCPConfig:
        """Convert to the pipeline MCPConfig type."""
        return MCPConfig(
            name=self.name,
            command=self.command,
            args=self.args,
            env=self.env,
            tools=self.tools,
        )


@dataclass
class RegisteredSkill:
    """A skill registered in the knowledge graph."""
    name: str
    description: str = ""
    path: str = ""
    domains: List[str] = field(default_factory=list)
    behavioral_tags: List[str] = field(default_factory=list)

    def to_spec(self) -> SkillSpec:
        return SkillSpec(name=self.name, description=self.description, path=self.path)


@dataclass
class RegisteredDomain:
    """A domain registered in the knowledge graph."""
    name: str
    description: str = ""
    subdomains: List[str] = field(default_factory=list)
    required_mcps: List[str] = field(default_factory=list)
    required_skills: List[str] = field(default_factory=list)


@dataclass
class RegisteredArm:
    """A compiler arm registered in the registry.

    Maps an ArmKind to a composition recipe of CA packages.
    The Bandit queries these to decide SELECT (reuse) vs CONSTRUCT (build).

    Example:
        RegisteredArm(
            kind=ArmKind.SYSTEM_PROMPT,
            name="default_system_prompt",
            ca_packages=["mermaid_maker", "prompt_engineer"],
            description="Generates system prompt via mermaid + prompt engineering",
        )
    """
    kind: ArmKind
    name: str
    ca_packages: List[str] = field(default_factory=list)  # CA package names composing this arm
    description: str = ""
    compiler_class: Optional[str] = None  # dotted import path to the arm's compiler class
    version: str = "1.0"

    @property
    def is_complete(self) -> bool:
        """An arm is complete if it has at least one CA package."""
        return len(self.ca_packages) > 0


# =============================================================================
# Registry interface
# =============================================================================

class Registry:
    """Carton-backed registry for MCPs, skills, and domains.

    Supports two backends:
    - "static": in-memory dict (testing and standalone use)
    - "carton": Carton KG-backed (production use, requires sync)
    """

    def __init__(self, backend: str = "static"):
        """Initialize registry.

        Args:
            backend: "static" for in-memory dict, "carton" for KG-backed.
        """
        self._backend = backend
        self._mcps: Dict[str, RegisteredMCP] = {}
        self._skills: Dict[str, RegisteredSkill] = {}
        self._domains: Dict[str, RegisteredDomain] = {}
        self._arms: Dict[str, RegisteredArm] = {}  # name → arm
        self._arms_by_kind: Dict[ArmKind, List[str]] = {}  # kind → [arm names]

    # ─────────────────────────────────────────────────────────────────
    # MCP operations
    # ─────────────────────────────────────────────────────────────────

    def register_mcp(self, mcp: RegisteredMCP) -> None:
        """Register an MCP server in the registry."""
        self._mcps[mcp.name] = mcp
        logger.debug("Registry: registered MCP '%s' (tools=%d)", mcp.name, len(mcp.tools))

    def get_mcp(self, name: str) -> Optional[RegisteredMCP]:
        """Get a registered MCP by name."""
        return self._mcps.get(name)

    def list_mcps(self, domain: Optional[str] = None) -> List[RegisteredMCP]:
        """List all registered MCPs, optionally filtered by domain."""
        if domain:
            return [m for m in self._mcps.values() if domain in m.domains]
        return list(self._mcps.values())

    def find_mcps_for_tools(self, tool_names: List[str]) -> List[RegisteredMCP]:
        """Find MCPs that provide the specified tools.

        This is the core query the MCP Compiler uses:
        "Given that the system prompt mentions these tools, which MCPs do I need?"
        """
        needed = set(tool_names)
        result = []
        for mcp in self._mcps.values():
            mcp_tool_names = {t.name for t in mcp.tools}
            if mcp_tool_names & needed:
                result.append(mcp)
        return result

    # ─────────────────────────────────────────────────────────────────
    # Skill operations
    # ─────────────────────────────────────────────────────────────────

    def register_skill(self, skill: RegisteredSkill) -> None:
        """Register a skill in the registry."""
        self._skills[skill.name] = skill
        logger.debug("Registry: registered skill '%s'", skill.name)

    def get_skill(self, name: str) -> Optional[RegisteredSkill]:
        """Get a registered skill by name."""
        return self._skills.get(name)

    def list_skills(self, domain: Optional[str] = None) -> List[RegisteredSkill]:
        """List all registered skills, optionally filtered by domain."""
        if domain:
            return [s for s in self._skills.values() if domain in s.domains]
        return list(self._skills.values())

    def find_skills_for_behavior(self, behavioral_tags: List[str]) -> List[RegisteredSkill]:
        """Find skills matching behavioral requirements.

        This is the core query the Skill Compiler uses:
        "Given that the agent needs to 'follow mermaid diagrams' and
         'observe to knowledge graph', which skills apply?"

        Strategy:
        1. Exact tag overlap (fast, always available)
        2. Carton semantic search (if backend='carton', for fuzzy matching)
        """
        tags_set = set(t.lower() for t in behavioral_tags)

        # Strategy 1: exact tag overlap
        scored = []
        for skill in self._skills.values():
            skill_tags = set(t.lower() for t in skill.behavioral_tags)
            overlap = tags_set & skill_tags
            if overlap:
                scored.append((skill, len(overlap)))

        # Strategy 2: if no exact matches and carton backend, would use semantic search
        # (Carton integration deferred — would call carton.chroma_query here)
        if self._backend == "carton" and not scored:
            logger.debug(
                "Registry: no exact tag matches for %s, "
                "carton semantic search not yet integrated",
                behavioral_tags,
            )

        # Sort by overlap score (most matching tags first)
        scored.sort(key=lambda x: -x[1])
        result = [skill for skill, _ in scored]
        logger.debug(
            "Registry: find_skills_for_behavior(%s) → %d matches",
            behavioral_tags, len(result),
        )
        return result

    # ─────────────────────────────────────────────────────────────────
    # Domain operations
    # ─────────────────────────────────────────────────────────────────

    def register_domain(self, domain: RegisteredDomain) -> None:
        """Register a domain in the registry."""
        self._domains[domain.name] = domain
        logger.debug(
            "Registry: registered domain '%s' (subdomains=%d, mcps=%d)",
            domain.name, len(domain.subdomains), len(domain.required_mcps),
        )

    def get_domain(self, name: str) -> Optional[RegisteredDomain]:
        """Get a registered domain by name."""
        return self._domains.get(name)

    def list_domains(self) -> List[RegisteredDomain]:
        """List all registered domains."""
        return list(self._domains.values())

    def resolve_domain_stack(self, task_description: str) -> List[RegisteredDomain]:
        """Determine which domain(s) a task requires.

        This is the core query the Compoctopus Router uses:
        "Given this task, which domain handles it?"
        May return multiple domains for cross-domain tasks.

        Strategy:
        1. Keyword match against domain descriptions (fast, always available)
        2. Carton semantic search (if backend='carton', for fuzzy matching)
        """
        # Strategy 1: keyword match against domain descriptions
        task_words = set(task_description.lower().split())
        scored = []
        for domain in self._domains.values():
            domain_words = set(domain.description.lower().split()) if domain.description else set()
            # Also match against domain name and subdomain names
            domain_words.add(domain.name.lower())
            domain_words.update(s.lower() for s in domain.subdomains)
            overlap = len(task_words & domain_words)
            if overlap > 0:
                scored.append((domain, overlap))

        # Strategy 2: Carton semantic search (deferred)
        if self._backend == "carton" and not scored:
            logger.debug(
                "Registry: no keyword matches for '%s', "
                "carton semantic search not yet integrated",
                task_description[:40],
            )

        scored.sort(key=lambda x: -x[1])
        result = [d for d, _ in scored]

        if not result:
            result = [RegisteredDomain(name="general")]

        logger.debug(
            "Registry: resolve_domain_stack('%s') → %s",
            task_description[:40], [d.name for d in result],
        )
        return result

    # ─────────────────────────────────────────────────────────────────
    # Arm operations — what the Bandit queries
    # ─────────────────────────────────────────────────────────────────

    def register_arm(self, arm: RegisteredArm) -> None:
        """Register a compiler arm in the registry.

        Called automatically when a CA is created with arm_kind set.
        The Bandit uses list_arms / get_arms_for_kind to decide
        SELECT (reuse existing) vs CONSTRUCT (build new).
        """
        self._arms[arm.name] = arm
        if arm.kind not in self._arms_by_kind:
            self._arms_by_kind[arm.kind] = []
        if arm.name not in self._arms_by_kind[arm.kind]:
            self._arms_by_kind[arm.kind].append(arm.name)
        logger.debug(
            "Registry: registered arm '%s' (kind=%s, cas=%s)",
            arm.name, arm.kind.value, arm.ca_packages,
        )

    def get_arm(self, name: str) -> Optional[RegisteredArm]:
        """Get a registered arm by name."""
        return self._arms.get(name)

    def get_arms_for_kind(self, kind: ArmKind) -> List[RegisteredArm]:
        """Get all registered arms for a specific ArmKind.

        This is the core query the Bandit uses:
        "What SystemPrompt arms exist that I could SELECT?"

        Returns empty list if no arms → Bandit must CONSTRUCT.
        """
        names = self._arms_by_kind.get(kind, [])
        return [self._arms[n] for n in names if n in self._arms]

    def list_arms(self) -> Dict[ArmKind, List[RegisteredArm]]:
        """List all registered arms grouped by kind.

        This is what gets shown to the Bandit for its SELECT/CONSTRUCT decision.
        """
        result: Dict[ArmKind, List[RegisteredArm]] = {}
        for kind, names in self._arms_by_kind.items():
            result[kind] = [self._arms[n] for n in names if n in self._arms]
        return result

    def get_ca_recipe(self, arm_name: str) -> List[str]:
        """Get the CA package names that compose an arm.

        Returns the ordered list of CA packages the arm uses.
        Used by CONSTRUCT to know what to build.
        """
        arm = self._arms.get(arm_name)
        if arm:
            return list(arm.ca_packages)
        return []

    # ─────────────────────────────────────────────────────────────────
    # Carton integration
    # ─────────────────────────────────────────────────────────────────

    def sync_from_carton(self) -> None:
        """Pull all registered MCPs, skills, and domains from Carton KG.

        Queries:
        - MATCH (m:Wiki)-[:IS_A]->(:Wiki {n: "Registered_MCP"}) RETURN m
        - MATCH (s:Wiki)-[:IS_A]->(:Wiki {n: "Registered_Skill"}) RETURN s
        - MATCH (d:Wiki)-[:IS_A]->(:Wiki {n: "Registered_Domain"}) RETURN d
        """
        raise NotImplementedError(
            "sync_from_carton is not yet implemented. "
            "When implemented, will query the Carton KG for all concepts with "
            "IS_A relationships to Registered_MCP, Registered_Skill, and "
            "Registered_Domain, then hydrate the local registry. "
            "Fix: implement Carton integration using carton.query_wiki_graph()."
        )

    def sync_to_carton(self) -> None:
        """Push local registry state to Carton KG.

        Creates/updates concepts for all registered MCPs, skills, domains.
        """
        raise NotImplementedError(
            "sync_to_carton is not yet implemented. "
            "When implemented, will use carton.observe_from_identity_pov to "
            "persist each registered MCP, skill, and domain as concepts with "
            "IS_A relationships (Registered_MCP, Registered_Skill, Registered_Domain). "
            "Fix: implement Carton integration using carton.observe_from_identity_pov()."
        )
