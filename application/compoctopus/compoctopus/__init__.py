"""Compoctopus: Self-Compiling Agent Compiler Pipeline.

═══════════════════════════════════════════════════════════════════════════
TYPE HIERARCHY — everything reduces to Link
═══════════════════════════════════════════════════════════════════════════

    Link                         "I execute"
    │
    ├── Chain(Link)              "I execute Links in sequence"
    │   │                         (a Chain IS a Link — homoiconic)
    │   │
    │   ├── EvalChain(Chain)     "I loop: run chain → evaluate → repeat"
    │   │                         (SDNAFlowchain / OVP pattern)
    │   │
    │   └── Compiler(Chain)      "I execute Links that PRODUCE new Links"
    │       │                     (D:D→D — structure in, structure out)
    │       │
    │       ├── ChainSelect      "I look up a golden chain" (exploit)
    │       ├── ChainConstruct   "I assemble a pipeline"   (explore)
    │       └── Bandit           "I pick Select or Construct"
    │
    ├── CompilerArm(Link)        "I am one step of compilation"
    │   ├── ChainCompiler
    │   ├── AgentConfigCompiler
    │   ├── MCPCompiler
    │   ├── SkillCompiler
    │   ├── SystemPromptCompiler
    │   └── InputPromptCompiler
    │
    └── ConfigLink(Link)         "I wrap a config dict"
        (leaf node — becomes SDNAC at runtime)


═══════════════════════════════════════════════════════════════════════════
BANDIT STRUCTURE — the head of the octopus
═══════════════════════════════════════════════════════════════════════════

    Bandit(Compiler)
    ├── ChainSelect(Compiler)    → golden chain store
    └── ChainConstruct(Compiler) → CompilerPipeline(Chain)
        └── [Arm, Arm, Arm, Arm, Arm, Arm]
                    ↓
              outputs: Link


═══════════════════════════════════════════════════════════════════════════
GROWTH — Compoctopus is a self-extending compiler
═══════════════════════════════════════════════════════════════════════════

    The output type is Link, not CompiledAgent. This is critical.

    compile("agent")         → Link (an SDNAC)
    compile("pipeline")      → Link (a CompilerPipeline — a Chain)
    compile("arm")           → Link (a CompilerArm)
    compile("compoctopus")   → Link (a Bandit — i.e. itself)

    Because the output is Link, it can be fed BACK as a new arm:

        Bandit → compile → Link
                              ↓
                         register as new arm
                              ↓
                         Bandit (now with more arms)
                              ↓
                         compile again → Link → ...

    Each compilation potentially extends the compiler.
    The pipeline doesn't have a fixed number of arms — it grows.


═══════════════════════════════════════════════════════════════════════════
QUINE — D:D→D fixed point
═══════════════════════════════════════════════════════════════════════════

    The fully operational Compoctopus has all its parts encoded
    in itself. It can compile any of its abstractions, including
    itself:

        compile(compoctopus) ≈ compoctopus

    This is not a special MetaCompiler mode. It falls out naturally
    from three facts:

        1. Compoctopus IS a Link (Bandit → Compiler → Chain → Link)
        2. Compoctopus OUTPUTS Links
        3. Therefore Compoctopus can output itself

    The fixed point is: the compiler that compiles itself produces
    something equivalent to itself. That's D:D→D.


═══════════════════════════════════════════════════════════════════════════
SDNA MAPPING — what the output becomes at runtime
═══════════════════════════════════════════════════════════════════════════

    chain_ontology       SDNA runtime
    ──────────────       ────────────
    Link              →  SDNAC         (atomic agent unit)
    Chain             →  SDNAFlow      (sequence of agents)
    EvalChain         →  SDNAFlowchain (sequence + OVP loop)
    Compiler          →  (Compoctopus-specific, no SDNA equiv)

Usage:
    from compoctopus import Bandit, TaskSpec
    bandit = Bandit(arm_registry={...})
    compiled = bandit.compile_with_pipeline(TaskSpec(description="..."))
"""

__version__ = "0.1.0"

# Package-level logger: NullHandler by default (library best practice).
# Users enable logging via: logging.getLogger('compoctopus').setLevel(logging.DEBUG)
import logging
logging.getLogger(__name__).addHandler(logging.NullHandler())

# Core types
from compoctopus.types import (
    ArmKind,
    TaskSpec,
    FeatureType,
    TrustLevel,
    PermissionMode,
    CompilationPhase,
    GeometricInvariant,
    # IR types
    MermaidMessage,
    MermaidBranch,
    MermaidAlt,
    MermaidSpec,
    PromptSection,
    ToolSpec,
    MCPConfig,
    ToolManifest,
    SkillSpec,
    SkillBundle,
    SystemPrompt,
    InputPrompt,
    ChainPlan,
    ChainNode,
    AgentProfile,
    CompiledAgent,
    # Alignment
    AlignmentResult,
    GeometricAlignmentReport,
    # Bandit
    SensorReading,
    GoldenChainEntry,
    # Onionmorph
    RoutingNode,
    RoutingTree,
)

# Core classes
from compoctopus.base import (
    CompilerArm, CompilerPipeline,
    SelfCompilationResult, PartialCompilationReport, ArmStatus,
)
from compoctopus.context import CompilationContext
from compoctopus.alignment import GeometricAlignmentValidator
from compoctopus.state_machine import StateMachine, PhaseTransition, make_compiler_sm
from compoctopus.mermaid import MermaidParser, MermaidGenerator, MermaidValidator
from compoctopus.chain_ontology import (
    Link, Chain, EvalChain, Compiler, ConfigLink, LinkConfig,
    LinkResult, LinkStatus,
)
from compoctopus.registry import Registry
from compoctopus.router import Bandit, ChainSelect, ChainConstruct
from compoctopus.sensors import SensorStore
from compoctopus.golden_chains import GoldenChainStore
from compoctopus.onionmorph import OnionmorphRouter
from compoctopus.meta import MetaCompiler
from compoctopus.mock import (
    MockToolSpec, MockHeavenTool, make_mock_tool,
    auto_mock_from_mermaid, auto_mock_manifest, auto_mock_from_empire,
)
from compoctopus.giint_bridge import (
    TaskStatus, AssigneeType, ProjectType,
    Task as GIINTTask, Deliverable as GIINTDeliverable,
    Component as GIINTComponent, Feature as GIINTFeature,
    Project as GIINTProject,
    ProjectRegistry, get_registry,
    create_project, get_project, list_projects,
    add_feature_to_project, add_component_to_feature,
    add_deliverable_to_component, add_task_to_deliverable,
    ProjectCompiler,
)
from compoctopus.octopus_coder import (
    CompoctopusAgent, make_octopus_coder, make_planner,
    CodeCompiler,
    compile as compoctopus_compile,
)

# Public API
from compoctopus.run import run_from_prd, run_from_prd_sync, run_autonomously

# Arms
from compoctopus.arms import (
    make_chain_compiler,
    make_agent_config_compiler,
    make_mcp_compiler,
    make_skill_compiler,
    make_system_prompt_compiler,
    make_input_prompt_compiler,
    ReviewerCompiler,
)

__all__ = [
    # Version
    "__version__",
    # Types
    "ArmKind", "TaskSpec", "FeatureType", "TrustLevel", "PermissionMode",
    "CompilationPhase", "GeometricInvariant",
    "MermaidSpec", "PromptSection", "ToolSpec", "MCPConfig",
    "ToolManifest", "SkillSpec", "SkillBundle",
    "SystemPrompt", "InputPrompt",
    "ChainPlan", "ChainNode", "AgentProfile", "CompiledAgent",
    "AlignmentResult", "GeometricAlignmentReport",
    "SensorReading", "GoldenChainEntry",
    "RoutingNode", "RoutingTree",
    # Core
    "CompilerArm", "CompilerPipeline",
    "CompilationContext",
    "GeometricAlignmentValidator",
    "StateMachine", "PhaseTransition", "make_compiler_sm",
    "MermaidParser", "MermaidGenerator", "MermaidValidator",
    "Registry",
    "Bandit", "ChainSelect", "ChainConstruct",
    "SensorStore", "GoldenChainStore",
    "OnionmorphRouter", "MetaCompiler",
    # Arms
    "make_chain_compiler", "make_agent_config_compiler", "make_mcp_compiler",
    "make_skill_compiler", "make_system_prompt_compiler", "make_input_prompt_compiler",
    "ReviewerCompiler",
    # Chain Ontology
    "Link", "Chain", "EvalChain", "Compiler", "ConfigLink", "LinkConfig",
    "LinkResult", "LinkStatus",
    # GIINT (re-exported from llm_intelligence.projects)
    "GIINTProject", "GIINTFeature", "GIINTComponent", "GIINTDeliverable", "GIINTTask",
    "TaskStatus", "AssigneeType", "ProjectType",
    "ProjectRegistry", "get_registry",
    "create_project", "get_project", "list_projects",
    "add_feature_to_project", "add_component_to_feature",
    "add_deliverable_to_component", "add_task_to_deliverable",
    "ProjectCompiler",
    # Agents & Compilers
    "CompoctopusAgent", "make_octopus_coder", "make_planner",
    "CodeCompiler", "compoctopus_compile",
]
