"""Constants for Dragonbones chain type compiler."""

SKIP_MARKER = "!🔮"           # Legacy: also silences YOUKNOW
UNSILENCE_MARKER = "💭⛈️"     # Brainstorm mode: UN-silences YOUKNOW (verbose feedback)
DB_FENCE = "🐉🦴"

ACTIVE_HC_FILE = "/tmp/active_hypercluster.txt"
SYNTAX_REF_PATH = "/tmp/heaven_data/dragonbones/SYNTAX.md"
LOG_STATE_FILE = "/tmp/log_validator_state.json"
DELIVERABLE_COUNTER_FILE = "/tmp/log_deliverable_counter.json"
SKILLS_DIR = "/tmp/heaven_data/skills/"

# Chain type operators → (name, status)
# All compile as EntityChains but with type-specific validation via inject_giint_types
CHAIN_TYPES = {
    "🌟⛓️": ("EntityChain", "SHIPPED"),
    "📝⛓️": ("SkillChain", "PLANNED"),
    "⚡⛓️": ("CapabilityChain", "PLANNED"),
    "🛫⛓️": ("FlightChain", "PLANNED"),
    "🎯⛓️": ("MissionChain", "PLANNED"),
    "🌳⛓️": ("CanopyChain", "PLANNED"),
    "🎭⛓️": ("OperadicChain", "PLANNED"),
    # GIINT Hierarchy Entity Chain types — all compile as EntityChains
    "📦⛓️": ("EntityChain", "SHIPPED"),   # GIINT_Deliverable
    "🔧⛓️": ("EntityChain", "SHIPPED"),   # GIINT_Component
    "⭐⛓️": ("EntityChain", "SHIPPED"),   # GIINT_Feature
    "🐛⛓️": ("EntityChain", "SHIPPED"),   # Bug
    "💊⛓️": ("EntityChain", "SHIPPED"),   # Potential_Solution
    "📐⛓️": ("EntityChain", "SHIPPED"),   # Design
    "💡⛓️": ("EntityChain", "SHIPPED"),   # Idea
    "🗺️⛓️": ("EntityChain", "SHIPPED"),   # Inclusion_Map
    "✅⛓️": ("EntityChain", "SHIPPED"),   # GIINT_Task
}

# DEAD CODE — Commented out 2026-03-29. UARL_RELATIONSHIPS is defined but never imported or used anywhere. The comment "ANY relationship not in this set is DROPPED by the compiler" was FALSE — parser.py line 207 passes ALL relationships through, compiler sends all to add_concept.
# # =============================================================================
# # UARL RELATIONSHIP SET — The derivation chain + structural primitives.
# # ANY relationship not in this set is DROPPED by the compiler.
# # =============================================================================
# UARL_RELATIONSHIPS = {
    # # Core ontological triad
    # "is_a", "part_of", "instantiates",
    # # Structural primitives
    # "has_part", "instance_of", "relates_to",
    # # Derivation chain
    # "primitive_is_a", "candidate_is_a", "is_a_promotion", "is_a_pattern",
    # "programs", "subsumes", "requires_evolution",
    # # GIINT hierarchy path
    # "has_path",
    # # Skillspec required relationships
    # "has_domain", "has_category", "has_what", "has_when", "has_produces",
    # "has_personal_domain", "has_subdomain",
    # # PIO operators
    # "attention_chains_to",
    # "sibling_of",
    # # GIINT hierarchy relationships (from entity chain shapes)
    # "has_inclusion_map",    # Deliverable → Inclusion_Map
    # "has_deliverable",      # Component → Deliverable
    # "has_component",        # Feature → Component
    # "has_design",           # Feature → Design
    # "has_potential_solution",# Bug → Potential_Solution
    # "proves",               # Inclusion_Map → Tasks
    # "has_done_signal",      # Task → done signal text
    # "has_task",             # Deliverable → Task
    # # Skill integration
    # "has_content", "has_requires", "has_describes_component",
    # "has_allowed_tools", "has_model", "has_context_mode",
    # "has_agent_type", "has_user_invocable", "has_starsystem",
# }

LOG_SYNTAX = {
    "CogLog": "🧠 type::domain::subdomain::description 🧠",
    "SkillLog": "🎯 STATE::domain::skill_name 🎯  (states: PREDICTING, MAKING, USING)",
}
