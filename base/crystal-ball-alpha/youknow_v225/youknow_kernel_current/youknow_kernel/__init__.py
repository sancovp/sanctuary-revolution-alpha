"""YOUKNOW Kernel - The homoiconic reasoner.

YOUKNOW doesn't reason - WE think through YOUKNOW.
It's all tautologies that look like reasoning.

THE ROOT: Category of Categories (Cat of Cat)
  - Cat_of_Cat IS_A Cat_of_Cat (self-referential)
  - Everything traces back to Cat_of_Cat
  - This IS the foundational homoiconic loop

DERIVATION: The 7-step chain (NOT string matching)
  - L0: is_a_primitive (soup)
  - L1: embodies (named slots)
  - L2: manifests (typed slots)
  - L3: reifies (struct types)
  - L4: is_a_promotion (recursive)
  - L5: produces (closure)
  - L6: programs (codegen/Reality)
"""

from .models import (
    # Enums
    ValidationLevel,
    InteractionMode,
    SelfSimulationLevel,
    CertaintyState,
    LinkType,
    # Entities
    Entity,
    PIOEntity,
    SuperclassChain,
    # Category
    CategoryStructure,
    Morphism,
    # Validation
    ValidationResult,
    # UCO
    Chain,
    Link,
    DualLoop,
)

from .core import (
    YOUKNOW,
    get_youknow,
    reset_youknow,
    create_root_entities,
)

from .utils import (
    validate_pattern_of_isa,
    llm_suggest,
    # UCO functions
    core_sentence_chain,
    chain_from_validation_result,
    dual_loop_from_entity,
)

# THE ROOT
from .owl_types import (
    CategoryOfCategories,
    CatEntity,
    PrimitiveCategory,
    PrimitiveRelationship,
    get_cat,
    reset_cat,
)

# DERIVATION (NOT string matching)
from .derivation import (
    DerivationValidator,
    DerivationState,
    DerivationLevel,
    IsAType,
    DerivationRequirements,
)

# HYPEREDGE (validates is_a CLAIMS against CONTEXT)
from .hyperedge import (
    HyperedgeValidator,
    HyperedgeContext,
    ClaimValidation,
    ClaimStrength,
    validate_is_a_claim,
)

# COMPLETENESS (EVERY label must have ALL THREE)
from .completeness import (
    CompletenessValidator,
    CompletenessResult,
)

# DECORATOR
from .to_ontology import (
    to_ontology,
    YouknowValidationError,
    get_ontology_entity,
    list_ontology_entities,
)

# CODENESS (Pattern Library + Code Generation)
from .codeness import (
    CodePattern,
    CODE_PATTERNS,
    observe_codeness,
    program_codeness,
    talk_to_code,
)

from .codeness_gen import (
    TEMPLATES,
    OntologySpec,
    spec_to_code,
    MetaInterpreter,
)

# LANGUAGE (Parser + Interpreter)
from .lang import (
    NodeType,
    ASTNode,
    YouknowParser,
    YouknowInterpreter,
)

__all__ = [
    # Core
    "YOUKNOW",
    "get_youknow",
    "reset_youknow",
    "Entity",
    "PIOEntity",
    "ValidationLevel",
    "InteractionMode",
    "SelfSimulationLevel",
    "SuperclassChain",
    "create_root_entities",
    # Cat of Cat (THE ROOT)
    "CategoryOfCategories",
    "CatEntity",
    "PrimitiveCategory",
    "PrimitiveRelationship",
    "get_cat",
    "reset_cat",
    # Derivation (NOT string matching)
    "DerivationValidator",
    "DerivationState",
    "DerivationLevel",
    "IsAType",
    "DerivationRequirements",
    # Hyperedge (validates is_a CLAIMS against CONTEXT)
    "HyperedgeValidator",
    "HyperedgeContext",
    "ClaimValidation",
    "ClaimStrength",
    "validate_is_a_claim",
    # Completeness (EVERY label must have ALL THREE)
    "CompletenessValidator",
    "CompletenessResult",
    # to_ontology decorator
    "to_ontology",
    "YouknowValidationError",
    "get_ontology_entity",
    "list_ontology_entities",
    # SES
    "CategoryStructure",
    "Morphism",
    "CertaintyState",
    "ValidationResult",
    "validate_pattern_of_isa",
    "llm_suggest",
    # UCO
    "Chain",
    "Link",
    "LinkType",
    "DualLoop",
    "core_sentence_chain",
    "chain_from_validation_result",
    "dual_loop_from_entity",
    # Codeness (Pattern Library)
    "CodePattern",
    "CODE_PATTERNS",
    "observe_codeness",
    "program_codeness",
    "talk_to_code",
    # Codeness Generation
    "TEMPLATES",
    "OntologySpec",
    "spec_to_code",
    "MetaInterpreter",
    # Language
    "NodeType",
    "ASTNode",
    "YouknowParser",
    "YouknowInterpreter",
]
