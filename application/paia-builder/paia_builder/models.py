"""PAIA Builder Models - Built on youknow-kernel.

Components extend PIOEntity for ontological grounding.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, computed_field
from enum import Enum
from datetime import datetime

# Import from youknow-kernel
from youknow_kernel import PIOEntity, ValidationLevel, YOUKNOW


# =============================================================================
# ACHIEVEMENT TIERS (per component)
# =============================================================================

class AchievementTier(str, Enum):
    """Achievement tier with point values."""
    NONE = "none"           # 0 pts - Not started
    COMMON = "common"       # 10 pts - Created any X
    UNCOMMON = "uncommon"   # 25 pts - X works correctly
    RARE = "rare"           # 50 pts - X is golden (battle-tested)
    EPIC = "epic"           # 100 pts - X is productizable/used by others
    LEGENDARY = "legendary" # 250 pts - X generates revenue

TIER_POINTS = {
    AchievementTier.NONE: 0,
    AchievementTier.COMMON: 10,
    AchievementTier.UNCOMMON: 25,
    AchievementTier.RARE: 50,
    AchievementTier.EPIC: 100,
    AchievementTier.LEGENDARY: 250,
}

# Tier contracts - what you must truthfully declare to claim each tier
TIER_CONTRACTS = {
    AchievementTier.COMMON: "Exists with name and description. Created.",
    AchievementTier.UNCOMMON: "Works correctly. Tested without errors.",
    AchievementTier.RARE: "Battle-tested. Survived real usage in production.",
    AchievementTier.EPIC: "Used by others successfully. External validation.",
    AchievementTier.LEGENDARY: "Generates revenue. Economic proof.",
}

# Valid tier transitions (state machine)
TIER_TRANSITIONS = {
    AchievementTier.NONE: [AchievementTier.COMMON],
    AchievementTier.COMMON: [AchievementTier.UNCOMMON],
    AchievementTier.UNCOMMON: [AchievementTier.RARE],
    AchievementTier.RARE: [AchievementTier.EPIC],
    AchievementTier.EPIC: [AchievementTier.LEGENDARY],
    AchievementTier.LEGENDARY: [],  # Terminal state
}

# Tier → ValidationLevel mapping (from CONTINUITY.md)
# This maps game progression to ontological validation
TIER_TO_VALIDATION = {
    AchievementTier.NONE: ValidationLevel.EMBODIES,       # Declared
    AchievementTier.COMMON: ValidationLevel.EMBODIES,     # Created
    AchievementTier.UNCOMMON: ValidationLevel.MANIFESTS,  # Works correctly
    AchievementTier.RARE: ValidationLevel.REIFIES,        # Battle-tested
    AchievementTier.EPIC: ValidationLevel.REIFIES,        # Used by others
    AchievementTier.LEGENDARY: ValidationLevel.PRODUCES,  # Generates revenue
}


# =============================================================================
# GOLDENIZATION SPECTRUM (per component)
# =============================================================================

class GoldenStatus(str, Enum):
    """Goldenization spectrum - component maturity."""
    QUARANTINE = "quarantine"  # Untested, new/conflicting, awaiting review
    CRYSTAL = "crystal"        # Validated, tested, not yet production-proven
    GOLDEN = "golden"          # Battle-tested, proven, recommended

# Valid goldenization transitions
GOLDEN_TRANSITIONS = {
    GoldenStatus.QUARANTINE: [GoldenStatus.CRYSTAL],
    GoldenStatus.CRYSTAL: [GoldenStatus.GOLDEN, GoldenStatus.QUARANTINE],  # Can regress
    GoldenStatus.GOLDEN: [GoldenStatus.CRYSTAL],  # Can regress if broken
}


# =============================================================================
# GAME PHASES
# =============================================================================

class GamePhase(str, Enum):
    """Game phase based on level progression within PAIAB."""
    EARLY = "early"       # L1-5: Building gear, learning, first goldenizations
    MID = "mid"           # L6-9: Epic achievements, publishing, external validation
    LATE = "late"         # L10-12: Legendary achievements, revenue emerging
    ENDGAME = "endgame"   # L13+: PAIA construction complete


# =============================================================================
# COMPONENT STATUS (basic lifecycle)
# =============================================================================

class ComponentStatus(str, Enum):
    """Basic lifecycle status of a component."""
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    VALIDATED = "validated"


class HookType(str, Enum):
    """Claude Code hook types."""
    PRE_TOOL_USE = "PreToolUse"
    POST_TOOL_USE = "PostToolUse"
    USER_PROMPT_SUBMIT = "UserPromptSubmit"
    NOTIFICATION = "Notification"
    STOP = "Stop"


class SkillCategory(str, Enum):
    """Skill category types."""
    UNDERSTAND = "understand"
    PREFLIGHT = "preflight"
    SINGLE_TURN_PROCESS = "single_turn_process"


# =============================================================================
# COMPONENT MODELS (with tier + goldenization)
# =============================================================================

class ComponentBase(PIOEntity):
    """[VEHICLE] Subsystem base - extends PIOEntity for ontological grounding.

    Components are Vehicle subsystems. Each subsystem has:
    - tier: [TOWERING] layer completion (none→legendary)
    - golden: [CROWNING] tower completion (quarantine→golden)
    - status: lifecycle phase (planned→validated)

    Inherits from PIOEntity: name, description, is_a, part_of, validation_level, etc.
    """
    # PIOEntity already has: name, description, is_a, part_of, validation_level, created
    status: ComponentStatus = ComponentStatus.PLANNED
    tier: AchievementTier = AchievementTier.NONE
    golden: GoldenStatus = GoldenStatus.QUARANTINE
    notes: List[str] = Field(default_factory=list)
    custom: Dict[str, Any] = Field(default_factory=dict)
    updated: Optional[datetime] = None

    @computed_field
    @property
    def points(self) -> int:
        return TIER_POINTS[self.tier]

    def can_advance_tier(self, to_tier: AchievementTier) -> bool:
        return to_tier in TIER_TRANSITIONS.get(self.tier, [])

    def advance_tier(self, to_tier: AchievementTier) -> bool:
        """Advance to a new tier, updating validation_level accordingly.

        Returns True if successful, False if invalid transition.
        Tier progression automatically updates ValidationLevel per TIER_TO_VALIDATION.
        """
        if not self.can_advance_tier(to_tier):
            return False
        self.tier = to_tier
        self.validation_level = TIER_TO_VALIDATION[to_tier]
        self.updated = datetime.now()
        return True

    def can_transition_golden(self, to_status: GoldenStatus) -> bool:
        return to_status in GOLDEN_TRANSITIONS.get(self.golden, [])


class SkillResourceSpec(BaseModel):
    """Resource file in a skill's resources/ directory."""
    filename: str
    content_type: str = "markdown"  # markdown, json, yaml, txt, etc.
    content: Optional[str] = None  # Actual content or template


class SkillSpec(ComponentBase):
    """Skill component - the actual shape of what gets built.

    A skill is a PACKAGE (directory) containing:
    - SKILL.md: Main injection content (brief, points to reference)
    - reference.md: TOC describing everything in skill
    - resources/: Knowledge files (can be large)
    - scripts/: Executable scripts
    - templates/: Template files
    """
    # Metadata
    domain: str  # PAIAB, SANCTUM, CAVE
    subdomain: Optional[str] = None
    category: SkillCategory  # understand, preflight, single_turn_process

    # Trigger conditions
    what: Optional[str] = None  # What this skill does
    when: Optional[str] = None  # When to use it (trigger condition)

    # Actual structure (what gets built)
    skill_md: Optional[str] = None  # SKILL.md content
    reference_md: Optional[str] = None  # reference.md content
    resources: List[SkillResourceSpec] = Field(default_factory=list)
    scripts: List[str] = Field(default_factory=list)  # Script filenames
    templates: List[str] = Field(default_factory=list)  # Template filenames

    # Runtime hints
    allowed_tools: Optional[str] = None
    model: Optional[str] = None
    # path is DERIVED from name, not specified


class OnionLayerSpec(BaseModel):
    """Specification for a single layer in onion architecture."""
    filename: str  # e.g. "utils.py", "core.py"
    layer_type: str  # "primitives", "types", "facade"
    content: Optional[str] = None  # Code skeleton
    imports_from: List[str] = Field(default_factory=list)  # Layers this imports from
    exports: List[str] = Field(default_factory=list)  # What this layer exports


class OnionArchSpec(BaseModel):
    """Onion Architecture - the reusable inner layers.

    This is the COMMON part of any backend package:
    1. util_deps/    - Atomic dependencies, no internal imports
    2. utils.py      - ALL THE STUFF: primitives, mixins, adapters
    3. models.py     - Pydantic models, types (optional)
    4. core.py       - LIBRARY FACADE: small, wraps utils

    The SERVER layer is NOT here - that's what makes each spec unique:
    - MCPSpec adds mcp_server.py
    - APISpec would add api.py (FastAPI)
    - CLISpec would add cli.py
    - TreeShellSpec wraps in TreeShell

    Rules:
    - Each layer only imports from layers inside it
    - Facades are SMALL - pure delegation, no logic
    - utils.py has ALL THE STUFF
    - Logic in facade = smell, move it inward
    """
    package_name: str
    # Layers (ordered inside→out, stops at core)
    util_deps: List[str] = Field(default_factory=list)  # Atomic dep filenames
    utils: Optional[OnionLayerSpec] = None  # The meat - ALL THE STUFF
    models: Optional[OnionLayerSpec] = None  # Types/schemas (optional)
    core: Optional[OnionLayerSpec] = None  # Library facade - wraps utils


class MCPToolSpec(BaseModel):
    """MCP tool = thin wrapper around core function.

    from .core import tool_name

    @mcp.tool()
    def tool_name(param: type) -> return_type:
        '''AI-facing docstring (optional override)'''
        return core.tool_name(param)
    """
    core_function: str  # Which core function to wrap
    ai_description: Optional[str] = None  # Override docstring for AI (None = use core's)


class MCPSpec(ComponentBase):
    """MCP server component - OnionArch + MCP server layer.

    Build structure:
    my_mcp/
    ├── [OnionArchSpec layers]   # util_deps, utils, models, core
    └── mcp_server.py            # THIS IS THE UNIQUE PART
    """
    # Runtime config (for Claude Code mcp-config.json)
    command: Optional[str] = None  # e.g. "python", "node"
    args: List[str] = Field(default_factory=list)  # e.g. ["-m", "my_mcp.server"]
    env: Dict[str, str] = Field(default_factory=dict)  # Environment variables

    # Inner onion (reusable)
    onion: Optional[OnionArchSpec] = None

    # Server layer (MCP-specific - the unique part)
    server: Optional[OnionLayerSpec] = None  # mcp_server.py
    tools: List[MCPToolSpec] = Field(default_factory=list)

    # TreeShell wrapping (optional enhancement)
    treeshell: bool = False
    treeshell_actions: List[str] = Field(default_factory=list)

    # Package info
    package_path: Optional[str] = None


class HookSpec(ComponentBase):
    """Claude Code hook - event handler that triggers on tool use.

    Build structure:
    hooks/
    └── my_hook.py           # Single Python file
        - hook_type in filename or CLAUDE.md reference
        - Receives event data via stdin (JSON)
        - Returns: continue, block, or modified content
    """
    hook_type: HookType
    # What gets built
    script_content: Optional[str] = None  # Python script content
    # Trigger configuration
    tool_patterns: List[str] = Field(default_factory=list)  # e.g. ["Edit", "Write"]
    event_filter: Optional[str] = None  # Optional filter expression
    # Behavior
    blocks: bool = False  # Whether hook can block operations
    modifies_output: bool = False  # Whether hook modifies tool output


class SlashCommandSpec(ComponentBase):
    """Slash command - user-invocable prompt injection.

    Build structure:
    commands/
    └── my-command.md        # Markdown file with frontmatter
        ---
        description: "..."
        argument_hint: "<arg>"
        ---
        Prompt content here...
    """
    argument_hint: Optional[str] = None
    # What gets built
    prompt_content: Optional[str] = None  # Markdown body content
    # Metadata
    requires_args: bool = False
    allowed_contexts: List[str] = Field(default_factory=list)  # e.g. ["code", "chat"]


class AgentModel(str, Enum):
    """Valid agent models."""
    SONNET = "sonnet"
    OPUS = "opus"
    HAIKU = "haiku"
    INHERIT = "inherit"


class AgentPermissionMode(str, Enum):
    """Agent permission modes."""
    DEFAULT = "default"
    ACCEPT_EDITS = "acceptEdits"
    DONT_ASK = "dontAsk"
    BYPASS = "bypassPermissions"
    PLAN = "plan"


class AgentForkType(str, Enum):
    """Type of agent fork relationship."""
    CHILD = "child"  # Inherits from parent, evolves separately
    SIBLING = "sibling"  # Alternative version, same generation


class AgentSpec(ComponentBase):
    """Custom subagent - matches Claude Code agent config.

    Build structure:
    agents/
    └── my-agent.md          # Markdown with YAML frontmatter
        ---
        model: sonnet
        tools: [Bash, Read, Write]
        disallowedTools: [Edit]
        permissionMode: default
        skills: [skill-1, skill-2]
        ---
        System prompt content here...
    """
    # Runtime config (for agents.toml / frontmatter)
    tools: List[str] = Field(default_factory=list)  # Tool allowlist
    disallowed_tools: List[str] = Field(default_factory=list)  # Tool denylist
    model: AgentModel = AgentModel.SONNET
    permission_mode: AgentPermissionMode = AgentPermissionMode.DEFAULT
    skills: List[str] = Field(default_factory=list)  # Skills to inject at startup

    # What gets built
    system_prompt: Optional[str] = None  # Markdown body content
    system_prompt_ref: Optional[str] = None  # OR reference to SystemPromptSpec

    # Lineage tracking
    forked_from: Optional[str] = None  # Parent agent name if forked
    fork_type: Optional[AgentForkType] = None  # child or sibling


class PersonaSpec(ComponentBase):
    """Persona - bundles frame + MCP set + skillset + identity.

    Build structure:
    personas/
    └── my-persona.json      # Persona definition
        {
          "name": "...",
          "domain": "...",
          "frame": "...",         # or frame_file path
          "mcp_set": "...",
          "skillset": "...",
          "carton_identity": "..."
        }
    """
    domain: str  # PAIAB, SANCTUM, CAVE
    subdomain: Optional[str] = None
    # What gets built
    frame: Optional[str] = None  # Cognitive frame prompt text
    frame_file: Optional[str] = None  # OR path to frame file
    # Bundle references
    mcp_set: Optional[str] = None  # strata set name
    skillset: Optional[str] = None  # skillset name
    carton_identity: Optional[str] = None  # CartON identity for observations


class PluginSpec(ComponentBase):
    """Claude Code plugin - composition of components.

    Build structure:
    my-plugin/
    ├── plugin.json          # Manifest
    ├── skills/              # Skill packages
    ├── mcps/                # MCP packages
    ├── hooks/               # Hook scripts
    ├── commands/            # Slash command files
    └── agents/              # Agent definitions
    """
    git_url: Optional[str] = None
    # Component references (by name)
    skills: List[str] = Field(default_factory=list)
    mcps: List[str] = Field(default_factory=list)
    hooks: List[str] = Field(default_factory=list)
    commands: List[str] = Field(default_factory=list)
    agents: List[str] = Field(default_factory=list)
    # What gets built
    manifest: Optional[Dict[str, Any]] = None  # plugin.json content


class ContainerSpec(ComponentBase):
    """Container = Plugin + runtime environment.

    Build structure:
    Dockerfile that:
    - FROM base image (paia-agent:latest)
    - COPY plugin
    - pip install MCP dependencies
    - Configure Claude Code
    """
    base_image: str = "paia-agent:latest"
    plugin: Optional[str] = None  # PluginSpec name to install
    mcp_dependencies: List[str] = Field(default_factory=list)  # pip packages
    env_vars: Dict[str, str] = Field(default_factory=dict)
    ports: List[int] = Field(default_factory=lambda: [8421])  # Command server


class PAIACompiler(ComponentBase):
    """PAIA Compiler = callable compilation target.

    NOT a giint Deliverable - this is the compilation machinery.
    giint Deliverables are for tracking project hierarchy.
    PAIACompiler is for building actual artifacts.

    For PAIASpec:
    1. Build image from ContainerSpec
    2. Start container
    3. User auths
    4. Agent assembles per instructions
    5. Work until done
    6. Output: upgraded image
    7. Rebuild → Re-auth → Re-test (live integration)
    8. Green? → Trust → Self-evolve via GitHub
    """
    spec_type: str  # Which spec type this compiles
    spec_name: str  # Name of the spec to compile
    container: Optional[str] = None  # ContainerSpec name (if container-based)
    # Compilation outputs
    output_image: Optional[str] = None  # Docker image tag after compilation
    github_repo: Optional[str] = None  # For self-evolution
    # Trust level
    trusted: bool = False  # Green tests = can self-evolve


# Legacy alias for backwards compatibility
DeliverableSpec = PAIACompiler


class FlightStepSpec(BaseModel):
    """Specification for a flight config step."""
    step_number: int
    title: str
    instruction: str
    skills_to_equip: List[str] = Field(default_factory=list)

class FlightSpec(ComponentBase):
    """Flight config - replayable workflow template.

    Build structure:
    flights/
    └── my_flight_config.json
        {
          "payload_discovery": {"domain": "...", "category": "..."},
          "version": "1.0.0",
          "root_files": [
            {"step_1.json": {"title": "...", "instruction": "..."}},
            ...
          ]
        }
    """
    domain: str  # payload_discovery.domain
    category: Optional[str] = None  # e.g. "meta", "debugging", "research"
    version: str = "1.0.0"
    # What gets built
    steps: List[FlightStepSpec] = Field(default_factory=list)  # Step definitions
    prerequisite_skills: List[str] = Field(default_factory=list)  # Skills to equip before


class MetastackFieldSpec(BaseModel):
    """Specification for a metastack model field."""
    name: str
    field_type: str  # e.g. "str", "int", "List[str]"
    description: Optional[str] = None
    default: Optional[str] = None

class MetastackSpec(ComponentBase):
    """Metastack model - Pydantic-based templates for structured outputs.

    Build structure:
    metastack/
    └── my_model.py
        class MyModel(BaseModel):
            field1: str
            field2: int
    """
    domain: str  # e.g. "greeting", "code_review"
    # What gets built
    fields: List[MetastackFieldSpec] = Field(default_factory=list)
    base_class: str = "BaseModel"  # Parent class


class GIINTBlueprintSpec(ComponentBase):
    """GIINT Blueprint - template for respond() outputs."""
    domain: str  # e.g. "respond", "planning"
    template_path: Optional[str] = None  # Path to template file


class OperadicFlowSpec(ComponentBase):
    """Operadic Flow - composable workflow unit."""
    domain: str
    input_type: Optional[str] = None  # Expected input structure
    output_type: Optional[str] = None  # Expected output structure
    vendored_to: List[str] = Field(default_factory=list)  # Deliverables this is vendored to


class FrontendIntegrationSpec(ComponentBase):
    """Frontend integration - UI tools like TreeKanban."""
    integration_type: str  # e.g. "treekanban", "dashboard", "visualizer"
    api_url: Optional[str] = None
    board_name: Optional[str] = None  # For kanban-type integrations


class AutomationSpec(ComponentBase):
    """Automation - n8n, zapier, make.com workflows."""
    platform: str  # e.g. "n8n", "zapier", "make"
    workflow_id: Optional[str] = None
    webhook_url: Optional[str] = None
    triggers: List[str] = Field(default_factory=list)  # What triggers this automation


class AgentGANInitiator(str, Enum):
    """What initiates an Agent GAN cycle."""
    COMMAND = "command"  # Slash command triggers GAN
    MCP_TOOL_PROMPT = "mcp_tool_prompt"  # MCP tool call triggers GAN
    FLIGHT_STEP = "flight_step"  # Flight config step triggers GAN
    OMNISANC_ERROR = "omnisanc_error"  # Omnisanc error state triggers GAN


class SystemPromptType(str, Enum):
    """Type of system prompt - determines structure requirements."""
    MAIN = "main"  # Main CLAUDE.md - the root system prompt
    PERSONA_FRAME = "persona_frame"  # Domain-specific persona frame (additive to main)
    SUBAGENT = "subagent"  # Subagent system prompt


class SystemPromptSectionType(str, Enum):
    """Types of XML-tagged sections in a system prompt."""
    BACKGROUND = "background"  # Context, environment info
    META_PERSONA = "meta_persona"  # Identity, name, description, likes/dislikes
    DEFINITIONS = "definitions"  # Key terms and concepts
    RULES = "rules"  # Hard constraints, invariants
    ARCHITECTURE = "architecture"  # Meta-architecture, patterns, hierarchy
    WORKFLOWS = "workflows"  # Core workflows, decision flows
    REINFORCEMENT = "reinforcement"  # Key points, reminders, emphasis
    PAIA = "paia"  # PAIA-specific content wrapper
    WARNINGS = "warnings"  # Debug problems, edge cases
    CUSTOM = "custom"  # User-defined section type


class SystemPromptSection(BaseModel):
    """A single XML-tagged section in a system prompt."""
    section_type: SystemPromptSectionType
    tag_name: str  # The actual XML tag name (e.g., "architecture", "meta_persona")
    content: str  # The section content
    order: int = 0  # Order within the prompt (lower = earlier)


class SystemPromptConfig(BaseModel):
    """Configuration defining required/optional sections for a prompt type."""
    name: str  # Config name (e.g., "gnosys_main", "domain_persona")
    prompt_type: SystemPromptType
    required_sections: List[SystemPromptSectionType] = Field(default_factory=list)
    optional_sections: List[SystemPromptSectionType] = Field(default_factory=list)
    description: Optional[str] = None


class SystemPromptSpec(ComponentBase):
    """System prompt component - CLAUDE.md, persona frames, subagent prompts.

    Composed of XML-tagged sections. Can reference a config for validation.
    """
    prompt_type: SystemPromptType
    sections: List[SystemPromptSection] = Field(default_factory=list)
    config_name: Optional[str] = None  # Reference to SystemPromptConfig for validation
    domain: Optional[str] = None  # Which domain (PAIAB, SANCTUM, CAVE)
    path: Optional[str] = None  # Path to prompt file if stored externally


class AgentGANSpec(ComponentBase):
    """Agent GAN - two agents in adversarial/collaborative cycle."""
    initiator: AgentGANInitiator  # What triggers this GAN
    agents: List[str] = Field(default_factory=list, min_length=2, max_length=2)  # Exactly 2 agents
    agent_roles: Dict[str, str] = Field(default_factory=dict)  # role_name -> agent_name mapping


class AgentDUOSpec(ComponentBase):
    """Agent DUO - specialized GAN with challenger/generator roles.

    Cycle: challenger expands context or writes rejection judgment,
    then generator produces output based on challenge.
    """
    initiator: AgentGANInitiator  # What triggers this DUO
    challenger: str  # Agent that expands context or writes challenge/rejection
    generator: str  # Agent that generates based on challenger output


# =============================================================================
# GEAR PROGRESSION (full model)
# =============================================================================

class GEARDimension(BaseModel):
    """A single GEAR dimension."""
    score: int = Field(default=0, ge=0, le=100)
    notes: List[str] = Field(default_factory=list)
    last_updated: Optional[datetime] = None

    def set_score(self, score: int, note: Optional[str] = None):
        """Set score (clamped 0-100)."""
        self.score = min(100, max(0, score))
        self.last_updated = datetime.now()
        if note:
            self.notes.append(note)

    def bar(self) -> str:
        filled = self.score // 10
        return f"[{'█' * filled}{'░' * (10-filled)}] {self.score}%"


class GEAR(BaseModel):
    """Full GEAR: Gear, Experience, Achievements wrt Reality.

    GEAR IS FRACTAL - each dimension contains the others contextually:
    G = made of EAR (Gear requires Experience, Achievements, Reality)
    E = made of GAR (Experience involves Gear, Achievements, Reality)
    A = made of GER (Achievements need Gear, Experience, Reality)
    R = made of GEA (Reality grounds Gear, Experience, Achievements)

    KEY INSIGHT: E produces G. Experience IS the work. Cannot have G without E.
    """
    gear: GEARDimension = Field(default_factory=GEARDimension)
    experience: GEARDimension = Field(default_factory=GEARDimension)
    achievements: GEARDimension = Field(default_factory=GEARDimension)
    reality: GEARDimension = Field(default_factory=GEARDimension)

    # E = Experience = the timeline of work
    # This is the SOURCE - G is derived from this
    experience_events: List["ExperienceEvent"] = Field(default_factory=list)

    # Progression tracking
    level: int = 1
    total_points: int = 0

    @computed_field
    @property
    def overall(self) -> int:
        return (self.gear.score + self.experience.score +
                self.achievements.score + self.reality.score) // 4

    @computed_field
    @property
    def phase(self) -> GamePhase:
        """Determine game phase from level."""
        if self.level <= 5:
            return GamePhase.EARLY
        elif self.level <= 9:
            return GamePhase.MID
        elif self.level <= 12:
            return GamePhase.LATE
        else:
            return GamePhase.ENDGAME

    @computed_field
    @property
    def is_constructed(self) -> bool:
        """PAIA constructed when overall >= 80 and at least ENDGAME."""
        return self.overall >= 80 and self.level >= 13

    def display(self) -> str:
        """[VEHICLE] Display hull construction status."""
        status = "[CROWNING] VEHICLE CONSTRUCTED" if self.is_constructed else "[TOWERING] HULL IN PROGRESS"
        lines = [
            f"Flight Level {self.level} | {self.phase.value.upper()}",
            f"Energy: {self.total_points} pts",
            f"",
            f"├── Gear:         {self.gear.bar()}",
            f"├── Experience:   {self.experience.bar()}",
            f"├── Achievements: {self.achievements.bar()}",
            f"└── Reality:      {self.reality.bar()}",
            f"",
            f"Overall: {self.overall}% → {status}"
        ]
        return "\n".join(lines)


# =============================================================================
# LEVEL THRESHOLDS (state machine for progression)
# =============================================================================

LEVEL_THRESHOLDS = {
    1: 0,
    2: 50,
    3: 100,
    4: 175,
    5: 275,
    6: 400,
    7: 550,
    8: 725,
    9: 925,
    10: 1150,
    11: 1400,
    12: 1700,
    13: 2050,  # ENDGAME begins
}


def calculate_level(points: int) -> int:
    """Calculate level from total points."""
    level = 1
    for lvl, threshold in sorted(LEVEL_THRESHOLDS.items()):
        if points >= threshold:
            level = lvl
    return level


# =============================================================================
# EXPERIENCE EVENTS (work timeline)
# =============================================================================

class ExperienceEventType(str, Enum):
    """Type of experience event - what action was taken."""
    COMPONENT_ADDED = "component_added"
    TIER_ADVANCED = "tier_advanced"
    GOLDEN_ADVANCED = "golden_advanced"
    GOLDEN_REGRESSED = "golden_regressed"
    PAIA_CREATED = "paia_created"
    PAIA_FORKED = "paia_forked"
    VERSION_TICKED = "version_ticked"
    CUSTOM = "custom"


class ExperienceEvent(BaseModel):
    """An experience event - a unit of work in the timeline.

    E = Experience = the timeline of doing.
    Every action IS an experience event.
    G (Gear) is the OUTPUT of E. Cannot have G without E having happened.
    """
    event_type: ExperienceEventType
    timestamp: datetime = Field(default_factory=datetime.now)
    component_type: Optional[str] = None  # e.g., "skills", "mcps"
    component_name: Optional[str] = None  # e.g., "my-skill"
    details: str = ""  # Human-readable description

    # GEAR fractal: each event contains all dimensions contextually
    # G = what gear was involved
    # E = this event itself
    # A = what achievement this contributes to
    # R = how this grounds in reality
    gear_context: Optional[str] = None  # What gear was used/created
    achievement_context: Optional[str] = None  # What tier/validation this advances
    reality_context: Optional[str] = None  # How this connects to real world


# =============================================================================
# VERSION TRACKING
# =============================================================================

class VersionEntry(BaseModel):
    """Historical version entry."""
    version: str
    description: str
    timestamp: datetime = Field(default_factory=datetime.now)


# =============================================================================
# MAIN PAIA MODEL
# =============================================================================

class PAIAForkType(str, Enum):
    """Type of PAIA fork relationship."""
    CHILD = "child"  # Inherits from parent, evolves separately
    SIBLING = "sibling"  # Alternative version, same generation


class Player(BaseModel):
    """[PILOT] Player - the one constructing Vehicles.

    In SOSEEH: Pilot = Player = OVP (Victory-Promise).
    The Pilot builds and commands multiple Vehicles (PAIAs).

    GEAR at Player level:
    G = PAIAs (the pilot's fleet)
    E = experiences WITH those PAIAs
    A = achievements inside those experiences
    R = wrt society/civilization (larger reality)
    """
    model_config = {"arbitrary_types_allowed": True}

    name: str
    description: str = ""

    # The player's YOUKNOW - validates their ontology at civilization scale
    youknow: YOUKNOW = Field(default_factory=YOUKNOW)

    # G = Gear = PAIAs
    paias: List["PAIA"] = Field(default_factory=list)

    # E = Experience notes (interactions with PAIAs)
    experience_notes: List[str] = Field(default_factory=list)

    # Player-level GEAR
    gear_state: GEAR = Field(default_factory=GEAR)

    created: datetime = Field(default_factory=datetime.now)
    updated: Optional[datetime] = None

    def sync_gear(self) -> None:
        """Derive Player GEAR from PAIAs.

        G = PAIAs with overall > 0 (active PAIAs)
        E = experience notes + sum of PAIA experience
        A = average of PAIA achievement scores
        R = average of PAIA reality scores (civilization grounding)

        NOTE: Each PAIA should be synced via gear_ops.sync_gear(paia) before
        calling this method. Player.sync_gear aggregates already-synced PAIAs.
        """
        total_paias = len(self.paias)

        if total_paias == 0:
            return

        # NOTE: PAIAs should already be synced via gear_ops.sync_gear(paia)
        # We just aggregate their scores here

        # G = PAIAs that are active (have components)
        active = sum(1 for p in self.paias if p.gear_state.overall > 0)
        gear_score = int((active / total_paias) * 100)
        self.gear_state.gear.set_score(gear_score)

        # E = experience notes + PAIA experience average
        paia_exp_avg = sum(p.gear_state.experience.score for p in self.paias) // total_paias
        notes_score = min(50, len(self.experience_notes) * 5)  # Cap at 50
        experience_score = min(100, paia_exp_avg + notes_score)
        self.gear_state.experience.set_score(experience_score)

        # A = average of PAIA achievements
        achievements_score = sum(p.gear_state.achievements.score for p in self.paias) // total_paias
        self.gear_state.achievements.set_score(achievements_score)

        # R = average of PAIA reality (civilization = aggregate of PAIAs' reality)
        reality_score = sum(p.gear_state.reality.score for p in self.paias) // total_paias
        self.gear_state.reality.set_score(reality_score)

        # Level from total points across all PAIAs
        self.gear_state.total_points = sum(p.gear_state.total_points for p in self.paias)
        self.gear_state.level = calculate_level(self.gear_state.total_points)

    def add_paia(self, paia: "PAIA") -> None:
        """Add a PAIA to the player's collection."""
        self.paias.append(paia)
        self.updated = datetime.now()

    def add_experience(self, note: str) -> None:
        """Record an experience with PAIAs."""
        self.experience_notes.append(note)
        self.updated = datetime.now()


class PAIA(BaseModel):
    """[VEHICLE] Personal AI Agent - the hull you are constructing.

    PAIA = Vehicle in SOSEEH. You (Pilot) build this Vehicle.
    Each PAIA has:
    - YOUKNOW: validates component ontology
    - 16 subsystem types: skills, mcps, hooks, etc.
    - GEAR state: construction progress

    [TOWERING] = advancing subsystem tiers
    [CROWNING] = goldenizing subsystems
    """
    model_config = {"arbitrary_types_allowed": True}

    name: str
    description: str
    version: str = "0.1.0"
    version_history: List[VersionEntry] = Field(default_factory=list)
    git_dir: Optional[str] = None
    source_dir: Optional[str] = None
    forked_from_paia: Optional[str] = None  # Source PAIA name if forked
    fork_type: Optional[PAIAForkType] = None  # child or sibling

    # The YOUKNOW kernel - validates component ontology (excluded from JSON serialization)
    youknow: YOUKNOW = Field(default_factory=YOUKNOW, exclude=True)

    # Components (gear slots)
    skills: List[SkillSpec] = Field(default_factory=list)
    mcps: List[MCPSpec] = Field(default_factory=list)
    hooks: List[HookSpec] = Field(default_factory=list)
    commands: List[SlashCommandSpec] = Field(default_factory=list)
    agents: List[AgentSpec] = Field(default_factory=list)
    personas: List[PersonaSpec] = Field(default_factory=list)
    plugins: List[PluginSpec] = Field(default_factory=list)
    flights: List[FlightSpec] = Field(default_factory=list)
    metastacks: List[MetastackSpec] = Field(default_factory=list)
    giint_blueprints: List[GIINTBlueprintSpec] = Field(default_factory=list)
    operadic_flows: List[OperadicFlowSpec] = Field(default_factory=list)
    frontend_integrations: List[FrontendIntegrationSpec] = Field(default_factory=list)
    automations: List[AutomationSpec] = Field(default_factory=list)
    agent_gans: List[AgentGANSpec] = Field(default_factory=list)
    agent_duos: List[AgentDUOSpec] = Field(default_factory=list)
    system_prompts: List[SystemPromptSpec] = Field(default_factory=list)
    system_prompt_configs: List[SystemPromptConfig] = Field(default_factory=list)

    # Progression
    gear_state: GEAR = Field(default_factory=GEAR)

    # Meta
    created: datetime = Field(default_factory=datetime.now)
    updated: Optional[datetime] = None

    def all_components(self) -> List[ComponentBase]:
        """Get all components as flat list."""
        return (self.skills + self.mcps + self.hooks + self.commands +
                self.agents + self.personas + self.plugins + self.flights +
                self.metastacks + self.giint_blueprints + self.operadic_flows +
                self.frontend_integrations + self.automations +
                self.agent_gans + self.agent_duos + self.system_prompts)

    def recalculate_points(self, legendary_count: int = 0) -> int:
        """Recalculate total points from all component tiers.

        Args:
            legendary_count: Number of legendary components (adds 1M each)
        """
        tier_points = sum(c.points for c in self.all_components())
        legendary_bonus = legendary_count * 1_000_000
        total = tier_points + legendary_bonus
        self.gear_state.total_points = total
        self.gear_state.level = calculate_level(total)
        return total

    def component_summary(self) -> Dict[str, Dict[str, int]]:
        """Summary of components by type and tier."""
        summary = {}
        for comp_type in ["skills", "mcps", "hooks", "commands", "agents", "personas", "plugins", "flights",
                          "metastacks", "giint_blueprints", "operadic_flows", "frontend_integrations", "automations",
                          "agent_gans", "agent_duos", "system_prompts"]:
            comps = getattr(self, comp_type)
            by_tier = {}
            for tier in AchievementTier:
                count = sum(1 for c in comps if c.tier == tier)
                if count > 0:
                    by_tier[tier.value] = count
            if by_tier:
                summary[comp_type] = by_tier
        return summary

    def golden_summary(self) -> Dict[str, int]:
        """Count components by goldenization status."""
        counts = {s.value: 0 for s in GoldenStatus}
        for c in self.all_components():
            counts[c.golden.value] += 1
        return counts

    def register_component(self, component: ComponentBase, component_type: str) -> None:
        """Register a component in YOUKNOW ontology.

        Sets is_a based on component type (e.g., SkillSpec is_a skill).
        """
        # Set is_a relationship based on component type
        if not component.is_a:
            component.is_a = [component_type]
        elif component_type not in component.is_a:
            component.is_a.append(component_type)

        # Register in YOUKNOW
        self.youknow.add_entity(component)

    def sync_to_youknow(self) -> int:
        """Sync all components to YOUKNOW ontology.

        Returns count of entities registered.
        """
        type_map = {
            "skills": "skill",
            "mcps": "mcp",
            "hooks": "hook",
            "commands": "slash_command",
            "agents": "agent",
            "personas": "persona",
            "plugins": "plugin",
            "flights": "flight",
            "metastacks": "metastack",
            "giint_blueprints": "giint_blueprint",
            "operadic_flows": "operadic_flow",
            "frontend_integrations": "frontend_integration",
            "automations": "automation",
            "agent_gans": "agent_gan",
            "agent_duos": "agent_duo",
            "system_prompts": "system_prompt",
        }

        count = 0
        for attr, comp_type in type_map.items():
            for comp in getattr(self, attr):
                self.register_component(comp, comp_type)
                count += 1

        return count

    def validate_component(self, name: str) -> "ValidationResult":
        """Validate a component traces to pattern_of_isa."""
        from youknow_kernel import ValidationResult
        return self.youknow.validate_entity(name)

    # NOTE: sync_gear() removed - use gear_ops.sync_gear(paia) instead
    # This follows onion architecture: models have no logic, utils have all logic

    def set_experience(self, score: int, note: Optional[str] = None) -> None:
        """Self-report Experience score.

        E comes from CartON timelines - user declares their experience level.
        """
        self.gear_state.experience.set_score(score, note)

    def set_reality(self, score: int, note: Optional[str] = None) -> None:
        """Self-report Reality score.

        R = wrt Reality. User declares how reality has changed.
        """
        self.gear_state.reality.set_score(score, note)
