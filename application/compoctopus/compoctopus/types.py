"""Compoctopus type algebra.

All intermediate representations in the compilation pipeline are defined here.
The pipeline transforms:

    TaskSpec → ChainPlan → AgentProfile → ToolManifest
        → SkillBundle → SystemPrompt → InputPrompt → CompiledAgent

Each type is a well-defined intermediate representation (IR) that one arm
produces and the next arm consumes. The algebra is closed: composing any
sequence of arms produces a valid CompiledAgent or a diagnostic.

This module contains ONLY dataclass/enum definitions — no logic.
Logic lives in the modules that operate on these types.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Sequence


# =============================================================================
# Enumerations
# =============================================================================

class CompilationPhase(Enum):
    """State machine phases — every compiler arm has these.

    Pattern extracted from EvolutionFlow:
        development → (success) → complete
        development → (block)   → debug
        debug       → (success) → complete
        debug       → (block)   → debug (loop)
    """
    ANALYZING = "analyzing"
    COMPILING = "compiling"
    VALIDATING = "validating"
    COMPLETE = "complete"
    BLOCKED = "blocked"
    DEBUG = "debug"


class GeometricInvariant(Enum):
    """The 5 invariants that every compilation output must satisfy.

    Extracted from evolution_system.py analysis:
    1. System prompt ↔ input prompt describe same program from orthogonal angles
    2. Every tool referenced in prompts exists in tool surface; vice versa
    3. Agent scope matches container/permission scope
    4. State machine phase determines prompt template
    5. Feature type determines compilation path
    """
    DUAL_DESCRIPTION = auto()
    CAPABILITY_SURFACE = auto()
    TRUST_BOUNDARY = auto()
    PHASE_TEMPLATE = auto()
    POLYMORPHIC_DISPATCH = auto()


class FeatureType(Enum):
    """Polymorphic dispatch types — determines which compilation path.

    From evolution_system.py: feature_type == "tool" vs "agent" selects
    entirely different mermaid diagrams and task lists.
    """
    TOOL = "tool"
    AGENT = "agent"
    CHAIN = "chain"
    DOMAIN = "domain"
    SKILL = "skill"


class TrustLevel(Enum):
    """Container/permission trust boundaries.

    From evolution_system.py:
        mind_of_god  = ORCHESTRATOR (full access)
        image_of_god = BUILDER      (coding + debug tools)
        creation_of_god = EXECUTOR  (single maker tool only)
    """
    ORCHESTRATOR = "orchestrator"   # Full access, routing decisions
    BUILDER = "builder"             # Hands-on coding, debugging
    EXECUTOR = "executor"           # Single-tool executor, no decisions
    OBSERVER = "observer"           # Read-only, reporting


class ArmKind(Enum):
    """Which compiler arm this CA is.

    Base arms produce one facet of a CompoctopusAgent each.
    Higher-order arms compose base arms into full agents or compilers.
    Bandit prefers to select from the highest order it has achieved.

    None (not in enum) = worker, not an arm (OctoCoder, MermaidMaker, etc.)
    """
    # Base arms (produce one facet each)
    SYSTEM_PROMPT = "system_prompt"     # compiles the system prompt
    INPUT_PROMPT = "input_prompt"       # compiles the mermaid / input prompt
    AGENT = "agent"                     # assembles Heaven agent + SDNA wrapper
    MCP = "mcp"                         # compiles the MCP tool surface
    SKILL = "skill"                     # compiles skills
    CHAIN = "chain"                     # compiles the chain/pipeline structure
    REVIEWER = "reviewer"               # reviews arm outputs — callable as an arm
    # Higher-order (pipelines of arms)
    COMPOCTOPUS_AGENT = "compoctopus_agent"  # chains all base arms → makes a CA
    COMPOCTOPUS = "compoctopus"              # D:D→D — needs self-DI to exist


class PermissionMode(Enum):
    """SDNA/Heaven agent permission modes.

    Controls what filesystem and tool operations the agent can perform.
    Used by AgentProfile and trust boundary validation.
    """
    BYPASS = "bypassPermissions"       # ORCHESTRATOR/BUILDER: full access
    RESTRICTED = "restrictedPermissions"  # EXECUTOR: limited tool access
    READ_ONLY = "readOnly"             # OBSERVER: read-only operations

# =============================================================================
# Atomic building blocks
# =============================================================================

@dataclass(frozen=True)
class ToolSpec:
    """A single tool's specification.

    Represents one callable tool from an MCP or local tool surface.
    The name is what appears in prompts and mermaid diagrams.
    """
    name: str
    description: str = ""
    source_mcp: Optional[str] = None  # Which MCP provides this tool
    parameters: Dict[str, Any] = field(default_factory=dict)

    def __hash__(self) -> int:
        return hash(self.name)


@dataclass(frozen=True)
class MCPConfig:
    """Configuration for one MCP server.

    Maps to the mcp_servers dict entries in HermesConfig.
    """
    name: str
    command: str = ""
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    tools: List[ToolSpec] = field(default_factory=list)

    def __hash__(self) -> int:
        return hash(self.name)


@dataclass(frozen=True)
class SkillSpec:
    """A skill that can be injected into an agent.

    Skills are behavioral context bundles (SKILL.md + supporting files).
    """
    name: str
    description: str = ""
    path: str = ""  # Filesystem path to SKILL.md
    injected_sections: List[str] = field(default_factory=list)


@dataclass
class PromptSection:
    """One XML-tagged section of a system prompt.

    Each section is a projection of the agent's program onto one dimension:
        IDENTITY   → who the agent is
        WORKFLOW   → how it operates (prose dual of mermaid)
        CAPABILITY → what tools it has
        CONSTRAINTS → what it cannot do
    """
    tag: str           # e.g. "IDENTITY", "WORKFLOW", "CAPABILITY"
    content: str       # The prose content
    required: bool = True  # Must this section be present?

    def render(self) -> str:
        return f"<{self.tag}>\n{self.content}\n</{self.tag}>"


@dataclass
class MermaidMessage:
    """A single message/arrow in a sequence diagram."""
    sender: str
    receiver: str
    label: str
    arrow: str = "->>"  # "->>" solid async, "->" solid sync, "-->" dashed


@dataclass
class MermaidBranch:
    """An alt/else block in a sequence diagram."""
    condition: str                                # "Aligned" / "Not Aligned"
    messages: List[MermaidMessage] = field(default_factory=list)


@dataclass
class MermaidAlt:
    """A complete alt/else/end grouping."""
    branches: List[MermaidBranch] = field(default_factory=list)


@dataclass
class MermaidSpec:
    """Operational specification — the executable sequence diagram.

    GRAPH-FIRST: build from structured data, render text as a property.
    The structure IS the source of truth. The text is a view.

    The mermaid diagram IS the program. The LLM follows it as a state machine.
    It specifies exact tool calls in exact order with exact branching.

    This is the dual of the WORKFLOW section in the system prompt:
    - WORKFLOW says WHY and HOW (prose, behavioral intent)
    - MermaidSpec says WHAT and WHEN (diagram, operational spec)

    Usage:
        spec = MermaidSpec()
        spec.add_participant("User")
        spec.add_participant("Compiler")
        spec.add_message("User", "Compiler", "TaskSpec")
        spec.add_alt([
            ("Aligned", [("Compiler", "User", "Result")]),
            ("Not Aligned", [("Compiler", "Compiler", "Fix violations")]),
        ])
        print(spec.diagram)  # Renders full mermaid text
    """
    _participants: List[str] = field(default_factory=list)
    _messages: List[MermaidMessage | MermaidAlt] = field(default_factory=list)

    # ── Builder API ──────────────────────────────────────────────

    def add_participant(self, name: str, alias: Optional[str] = None) -> "MermaidSpec":
        """Add a participant to the diagram."""
        entry = f"{name} as {alias}" if alias else name
        if entry not in self._participants:
            self._participants.append(entry)
        return self

    def add_message(
        self, sender: str, receiver: str, label: str, arrow: str = "->>"
    ) -> "MermaidSpec":
        """Add a message arrow between participants."""
        self._messages.append(MermaidMessage(sender, receiver, label, arrow))
        return self

    def add_alt(
        self, branches: List[tuple[str, List[tuple[str, str, str]]]]
    ) -> "MermaidSpec":
        """Add an alt/else block.

        Args:
            branches: list of (condition, [(sender, receiver, label), ...])
        """
        alt = MermaidAlt(branches=[
            MermaidBranch(
                condition=cond,
                messages=[MermaidMessage(s, r, l) for s, r, l in msgs],
            )
            for cond, msgs in branches
        ])
        self._messages.append(alt)
        return self

    def add_loop(
        self, label: str, messages: List[tuple[str, str, str]]
    ) -> "MermaidSpec":
        """Add a loop block (rendered as loop/end in mermaid)."""
        # Reuse MermaidAlt with a single branch labeled as loop
        alt = MermaidAlt(branches=[
            MermaidBranch(
                condition=f"__loop__{label}",
                messages=[MermaidMessage(s, r, l) for s, r, l in messages],
            )
        ])
        self._messages.append(alt)
        return self

    # ── Computed properties ──────────────────────────────────────

    @property
    def participants(self) -> List[str]:
        """Participant names (without aliases)."""
        return [p.split(" as ")[0] for p in self._participants]

    @property
    def task_list(self) -> List[str]:
        """Extract ordered task names from message labels."""
        tasks = []
        for item in self._messages:
            if isinstance(item, MermaidMessage):
                tasks.append(item.label)
            elif isinstance(item, MermaidAlt):
                for branch in item.branches:
                    for msg in branch.messages:
                        tasks.append(msg.label)
        return tasks

    @property
    def tool_references(self) -> List[str]:
        """Extract tool names referenced in messages.

        Heuristic: any participant that isn't "User" and appears as
        a message receiver is likely a tool/service reference.
        """
        refs = set()
        for item in self._messages:
            msgs = [item] if isinstance(item, MermaidMessage) else [
                m for b in item.branches for m in b.messages
            ]
            for msg in msgs:
                # Self-messages are internal steps, not tool refs
                if msg.sender != msg.receiver:
                    refs.add(msg.receiver)
        # Remove "User" and common non-tool participants
        refs.discard("User")
        return sorted(refs)

    @property
    def branch_points(self) -> List[str]:
        """Extract branch condition labels."""
        points = []
        for item in self._messages:
            if isinstance(item, MermaidAlt):
                labels = [b.condition for b in item.branches
                         if not b.condition.startswith("__loop__")]
                if labels:
                    points.append(" vs ".join(labels))
        return points

    @property
    def diagram(self) -> str:
        """Render the full mermaid sequence diagram text."""
        lines = ["sequenceDiagram"]

        # Participants
        for p in self._participants:
            lines.append(f"    participant {p}")
        lines.append("")

        # Messages and blocks
        for item in self._messages:
            if isinstance(item, MermaidMessage):
                lines.append(
                    f"    {item.sender}{item.arrow}{item.receiver}: {item.label}"
                )
            elif isinstance(item, MermaidAlt):
                if (len(item.branches) == 1
                        and item.branches[0].condition.startswith("__loop__")):
                    # Render as loop block
                    label = item.branches[0].condition.replace("__loop__", "")
                    lines.append(f"    loop {label}")
                    for msg in item.branches[0].messages:
                        lines.append(
                            f"        {msg.sender}{msg.arrow}{msg.receiver}: {msg.label}"
                        )
                    lines.append("    end")
                else:
                    # Render as alt/else
                    for i, branch in enumerate(item.branches):
                        keyword = "alt" if i == 0 else "else"
                        lines.append(f"    {keyword} {branch.condition}")
                        for msg in branch.messages:
                            lines.append(
                                f"        {msg.sender}{msg.arrow}{msg.receiver}: {msg.label}"
                            )
                    lines.append("    end")

        return "\n".join(lines)


# =============================================================================
# Pipeline intermediate representations (IRs)
# =============================================================================

@dataclass
class TaskSpec:
    """The input to the entire compilation pipeline.

    This is what the user or Compoctopus router provides to kick off compilation.
    """
    description: str                           # What needs to happen
    feature_type: FeatureType = FeatureType.AGENT  # Polymorphic dispatch key
    domain_hints: List[str] = field(default_factory=list)  # e.g. ["summarization", "knowledge-graph"]
    constraints: Dict[str, Any] = field(default_factory=dict)  # Hard requirements
    trust_level: TrustLevel = TrustLevel.BUILDER  # Required trust scope
    parent_task: Optional[str] = None          # For onionmorph: which parent invoked this

    def __repr__(self) -> str:
        return (
            f"TaskSpec(desc='{self.description[:50]}', "
            f"type={self.feature_type.value}, trust={self.trust_level.value})"
        )


@dataclass
class ChainPlan:
    """Output of the Chain Compiler.

    Maps a complex multi-stage goal to a sequence of SDNAC units.
    """
    nodes: List[ChainNode] = field(default_factory=list)
    flow_type: str = "sequential"  # "sequential", "parallel", "duo"
    dependencies: Dict[str, List[str]] = field(default_factory=dict)
    # Which node outputs feed into which node inputs


@dataclass
class ChainNode:
    """A single node in a ChainPlan — one SDNAC unit."""
    name: str
    description: str = ""
    requires_mcps: List[str] = field(default_factory=list)  # Hints for MCP compiler
    requires_skills: List[str] = field(default_factory=list)  # Hints for skill compiler


@dataclass
class AgentProfile:
    """Output of the Agent Compiler.

    The specific "who" for an SDNAC unit: model, provider, personality.
    Maps to HeavenAgentConfig / HermesConfig fields.
    """
    name: str = ""
    model: str = "minimax"
    provider: str = "openrouter"
    temperature: float = 0.7
    max_turns: int = 15
    permission_mode: PermissionMode = PermissionMode.BYPASS
    personality: str = ""  # Archetype hint
    backend: str = "heaven"

    def __repr__(self) -> str:
        return (
            f"AgentProfile(name='{self.name}', model={self.model}, "
            f"turns={self.max_turns}, perm={self.permission_mode})"
        )


@dataclass
class ToolManifest:
    """Output of the MCP Compiler.

    The resolved set of MCPs and their tools that the agent will have.
    Every tool here MUST appear in the system prompt.
    Every tool in the system prompt MUST appear here.
    """
    mcps: Dict[str, MCPConfig] = field(default_factory=dict)
    local_tools: List[ToolSpec] = field(default_factory=list)

    @property
    def all_tool_names(self) -> List[str]:
        """Flatten all tools into a single name list."""
        names = []
        for mcp in self.mcps.values():
            for tool in mcp.tools:
                names.append(tool.name)
        for tool in self.local_tools:
            names.append(tool.name)
        return names

    def __repr__(self) -> str:
        return f"ToolManifest(mcps={len(self.mcps)}, tools={len(self.all_tool_names)})"


@dataclass
class SkillBundle:
    """Output of the Skill Compiler.

    Skills selected and configured for injection into the agent.
    """
    skills: List[SkillSpec] = field(default_factory=list)
    injected_context: str = ""  # Combined skill context to append to system prompt


@dataclass
class SystemPrompt:
    """Output of the System Prompt Compiler.

    The complete, validated system prompt with XML-tagged sections.
    """
    sections: List[PromptSection] = field(default_factory=list)
    raw: str = ""  # The composed raw text

    def render(self) -> str:
        if self.raw:
            return self.raw
        return "\n\n".join(s.render() for s in self.sections)

    @property
    def section_tags(self) -> List[str]:
        return [s.tag for s in self.sections]


@dataclass
class InputPrompt:
    """Output of the Input Prompt Compiler.

    The final goal/spec that gets passed to agent.run().
    Contains embedded mermaid diagram aligned with tool surface.
    """
    goal: str = ""                             # The task description
    mermaid: Optional[MermaidSpec] = None       # Embedded sequence diagram
    template_vars: Dict[str, str] = field(default_factory=dict)  # e.g. {feature_request: "..."}


@dataclass
class AlignmentResult:
    """Detailed result of geometric alignment validation.

    Each of the 5 invariants gets a pass/fail with specific violations.
    """
    invariant: GeometricInvariant
    passed: bool = False
    violations: List[str] = field(default_factory=list)
    details: str = ""


@dataclass
class GeometricAlignmentReport:
    """Full report across all 5 invariants.

    This is the output of the GeometricAlignmentValidator.
    """
    results: List[AlignmentResult] = field(default_factory=list)

    @property
    def aligned(self) -> bool:
        return all(r.passed for r in self.results)

    @property
    def violations(self) -> List[str]:
        return [v for r in self.results for v in r.violations]

    def __str__(self) -> str:
        lines = []
        for r in self.results:
            icon = "✅" if r.passed else "❌"
            lines.append(f"{icon} {r.invariant.name}")
            for v in r.violations:
                lines.append(f"    - {v}")
        return "\n".join(lines)


# =============================================================================
# The final output
# =============================================================================

@dataclass
class CompiledAgent:
    """The fully compiled agent configuration.

    This is the output of a complete pipeline run.
    Every field has been co-compiled and cross-validated.

    NOTE: Not using frozen=True because several fields contain mutable
    containers (List, Dict). Making this truly immutable would require
    converting all containers to tuples/frozensets, which would break
    the builder pattern used during compilation. Instead, immutability
    is enforced by convention: after context.freeze(), the CompiledAgent
    is treated as a value object. Any mutation after freeze is a bug.
    """
    task_spec: TaskSpec
    chain_plan: Optional[ChainPlan] = None
    agent_profile: Optional[AgentProfile] = None
    tool_manifest: Optional[ToolManifest] = None
    skill_bundle: Optional[SkillBundle] = None
    system_prompt: Optional[SystemPrompt] = None
    input_prompt: Optional[InputPrompt] = None
    alignment: Optional[GeometricAlignmentReport] = None

    # Compile-time metadata (set by context.freeze())
    compiled_at: float = 0.0
    compile_duration_ms: float = 0.0
    compile_id: str = ""
    pipeline_arms: List[str] = field(default_factory=list)

    @property
    def is_complete(self) -> bool:
        """True if all compilation stages have run."""
        return all([
            self.agent_profile is not None,
            self.tool_manifest is not None,
            self.system_prompt is not None,
            self.input_prompt is not None,
        ])

    @property
    def is_aligned(self) -> bool:
        """True if complete AND geometrically aligned."""
        return self.is_complete and (
            self.alignment is not None and self.alignment.aligned
        )

    def to_link_config(self) -> "LinkConfig":
        """Convert to a LinkConfig (serializable chain ontology config).

        Maps all compiled fields into the universal config format:
        - goal ← input_prompt (what to do)
        - system_prompt ← rendered system prompt
        - model/provider/temperature ← agent profile
        - allowed_tools ← tool manifest
        - skills ← skill bundle injected context
        """
        from compoctopus.chain_ontology import LinkConfig

        profile = self.agent_profile
        return LinkConfig(
            name=profile.name if profile else "agent",
            goal=self.input_prompt.goal if self.input_prompt else self.task_spec.description,
            system_prompt=self.system_prompt.render() if self.system_prompt else "",
            model=profile.model if profile else "",
            provider=profile.provider if profile else "",
            temperature=profile.temperature if profile else 0.7,
            max_turns=profile.max_turns if profile else 10,
            permission_mode=profile.permission_mode.value if profile else "default",
            allowed_tools=self.tool_manifest.all_tool_names if self.tool_manifest else [],
            mcp_servers={},  # populated by SDNABridge
            skills=self.skill_bundle.injected_context if self.skill_bundle else "",
        )

    def to_link(self) -> "ConfigLink":
        """Convert to a ConfigLink (executable chain ontology unit).

        CompiledAgent → Link: the homoiconic bridge.
        This Link can be placed inside any Chain.
        """
        from compoctopus.chain_ontology import ConfigLink
        return ConfigLink(config=self.to_link_config())

    def to_chain(self, chain_name: Optional[str] = None) -> "Chain":
        """Wrap this agent as a single-link Chain.

        Useful when you need Chain type but have a single agent.
        Chain IS a Link, so this is still composable.
        """
        from compoctopus.chain_ontology import Chain
        name = chain_name or (self.agent_profile.name if self.agent_profile else "agent")
        return Chain(chain_name=name, links=[self.to_link()])

    def __repr__(self) -> str:
        profile = self.agent_profile
        return (
            f"CompiledAgent("
            f"task='{self.task_spec.description[:40]}', "
            f"model={profile.model if profile else 'N/A'}, "
            f"tools={len(self.tool_manifest.all_tool_names) if self.tool_manifest else 0}, "
            f"aligned={self.is_aligned}, "
            f"compile_id={self.compile_id or 'N/A'})"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain dict for persistence / wire transfer."""
        return {
            "task_spec": {
                "description": self.task_spec.description,
                "feature_type": self.task_spec.feature_type.value,
                "trust_level": self.task_spec.trust_level.value,
                "domain_hints": self.task_spec.domain_hints,
            },
            "agent_profile": {
                "name": self.agent_profile.name,
                "model": self.agent_profile.model,
                "provider": self.agent_profile.provider,
                "temperature": self.agent_profile.temperature,
                "max_turns": self.agent_profile.max_turns,
                "permission_mode": self.agent_profile.permission_mode.value,
            } if self.agent_profile else None,
            "tool_manifest": {
                "tool_names": self.tool_manifest.all_tool_names,
                "mcp_count": len(self.tool_manifest.mcps),
            } if self.tool_manifest else None,
            "alignment": {
                "aligned": self.alignment.aligned,
                "violations": self.alignment.violations,
            } if self.alignment else None,
            "compile_metadata": {
                "compiled_at": self.compiled_at,
                "compile_duration_ms": self.compile_duration_ms,
                "compile_id": self.compile_id,
                "pipeline_arms": self.pipeline_arms,
            },
        }



# =============================================================================
# Bandit / Sensor types
# =============================================================================

@dataclass
class SensorReading:
    """A reward signal from an agent execution.

    Used by the bandit to decide Construct vs Select.
    """
    config_hash: str = ""      # Hash of the CompiledAgent that was run
    success: bool = False
    turns_taken: int = 0
    goal_accomplished: bool = False
    human_feedback: Optional[float] = None  # 0.0-1.0 satisfaction
    error_type: Optional[str] = None


@dataclass
class GoldenChainEntry:
    """A high-reward configuration that has been "graduated" to Selection.

    When the bandit has enough evidence that a config works well,
    it gets stored here for fast reuse.
    """
    config_hash: str = ""
    compiled_agent: Optional[CompiledAgent] = None
    reward_mean: float = 0.0
    reward_count: int = 0
    domain: str = ""
    feature_type: FeatureType = FeatureType.AGENT


# =============================================================================
# Onionmorph types
# =============================================================================

@dataclass
class RoutingNode:
    """A node in the onionmorph routing tree.

    Represents one level: domain → subdomain → worker.
    """
    name: str
    level: str = ""          # "domain", "subdomain", "worker"
    children: List[RoutingNode] = field(default_factory=list)
    compiled_agent: Optional[CompiledAgent] = None  # The agent at this level


@dataclass
class RoutingTree:
    """The complete onionmorph routing decision.

    Input: a complex multi-domain task
    Output: which domain → which subdomain → which worker
    """
    root: Optional[RoutingNode] = None
    depth: int = 0
    total_agents: int = 0
