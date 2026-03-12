"""
YOUKNOW Hyperedge Validator

This validates is_a CLAIMS against hyperedge CONTEXT.

NOT: "Does is_a edge exist in a graph?"
YES: "Is the user's is_a claim supported by the hyperedge context?"

A hyperedge is the relational context around a concept:
  - part_of relationships
  - produces relationships  
  - primitive_is_a relationships
  - has_part relationships
  - y_layer, properties, etc.

The pattern_of_is_a is the WITNESS that says:
  "Given this hyperedge context, the claim 'X is_a Y' is valid/invalid"

Validation process:
1. User presents: "X is_a Y" (a claim)
2. Extract hyperedge context for X
3. Check: Does the pattern of relationships TOGETHER support this claim?
4. Return: Valid (with witness) or Invalid (with what's missing)
"""

from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class ClaimStrength(Enum):
    """How strongly the hyperedge context supports the claim."""
    INVALID = "invalid"           # Claim contradicts context
    WEAK = "weak"                 # Claim has minimal support
    MODERATE = "moderate"         # Claim has some support
    STRONG = "strong"             # Claim has strong support
    WITNESSED = "witnessed"       # Claim is fully witnessed by pattern


@dataclass
class HyperedgeContext:
    """The relational context around a concept (the hyperedge)."""
    name: str
    
    # The relationships that form the hyperedge
    is_a_primitive: List[str] = field(default_factory=list)  # Raw is_a assertions
    part_of: List[str] = field(default_factory=list)
    has_part: List[str] = field(default_factory=list)
    produces: List[str] = field(default_factory=list)
    
    # Metadata
    y_layer: Optional[str] = None
    properties: Dict[str, Any] = field(default_factory=dict)
    description: Optional[str] = None
    
    def is_empty(self) -> bool:
        """Is this hyperedge empty (no relationships)?"""
        return (
            not self.is_a_primitive and 
            not self.part_of and 
            not self.has_part and 
            not self.produces
        )
    
    def relationship_count(self) -> int:
        """How many relationships form this hyperedge?"""
        return (
            len(self.is_a_primitive) + 
            len(self.part_of) + 
            len(self.has_part) + 
            len(self.produces)
        )


@dataclass
class ClaimValidation:
    """Result of validating an is_a claim against hyperedge context."""
    # The claim being validated
    subject: str          # X
    predicate: str        # is_a
    object: str           # Y
    
    # Validation result
    valid: bool
    strength: ClaimStrength
    
    # The hyperedge context used for validation
    context: HyperedgeContext
    
    # What supports the claim
    supporting_evidence: List[str] = field(default_factory=list)
    
    # What's missing or contradicts
    missing_evidence: List[str] = field(default_factory=list)
    contradicting_evidence: List[str] = field(default_factory=list)
    
    # The pattern_of_is_a witness (if valid)
    witness: Optional[str] = None
    
    def explain(self) -> str:
        """Generate human-readable explanation."""
        lines = [f"Claim: {self.subject} is_a {self.object}"]
        lines.append(f"Valid: {self.valid} ({self.strength.value})")
        
        if self.supporting_evidence:
            lines.append("Supporting:")
            for e in self.supporting_evidence:
                lines.append(f"  + {e}")
        
        if self.missing_evidence:
            lines.append("Missing:")
            for e in self.missing_evidence:
                lines.append(f"  - {e}")
        
        if self.contradicting_evidence:
            lines.append("Contradicting:")
            for e in self.contradicting_evidence:
                lines.append(f"  ! {e}")
        
        if self.witness:
            lines.append(f"Witness: {self.witness}")
        
        return "\n".join(lines)


@dataclass
class JustificationCoverage:
    """Coverage report for required relationships vs available justifications."""
    required_relationships: List[str]
    justifies_tokens: List[str]
    justified_relationships: List[str]
    required_rel_count: int
    justified_rel_count: int
    all_required_justified: bool


class HyperedgeValidator:
    """
    Validates is_a claims against hyperedge context.
    
    This is the pattern_of_is_a witness generator.
    """
    
    def __init__(self, cat=None):
        """
        Args:
            cat: CategoryOfCategories instance (for ontology lookups)
        """
        self.cat = cat
    
    def extract_context(self, concept: Dict[str, Any]) -> HyperedgeContext:
        """Extract hyperedge context from a concept dict."""
        return HyperedgeContext(
            name=concept.get("name", "unknown"),
            is_a_primitive=concept.get("is_a", []),
            part_of=concept.get("part_of", []),
            has_part=concept.get("has_part", []),
            produces=concept.get("produces", []),
            y_layer=concept.get("y_layer"),
            properties=concept.get("properties", {}),
            description=concept.get("description"),
        )
    
    def extract_context_from_cat(self, name: str) -> Optional[HyperedgeContext]:
        """Extract hyperedge context from Cat of Cat."""
        if not self.cat or name not in self.cat.entities:
            return None
        
        entity = self.cat.entities[name]
        return HyperedgeContext(
            name=entity.name,
            is_a_primitive=entity.is_a,
            part_of=entity.part_of,
            has_part=entity.has_part,
            produces=entity.produces,
            y_layer=entity.y_layer,
            properties=entity.properties,
            description=entity.properties.get("description"),
        )
    
    def validate_claim(
        self, 
        subject: str, 
        object_: str,
        context: Optional[HyperedgeContext] = None,
        concept: Optional[Dict[str, Any]] = None,
    ) -> ClaimValidation:
        """
        Validate the claim: "subject is_a object_"
        
        Args:
            subject: The thing being classified (X)
            object_: The category being claimed (Y)
            context: Pre-extracted hyperedge context
            concept: Raw concept dict (will extract context)
        
        Returns:
            ClaimValidation with validity, strength, and witness
        """
        # Get context
        if context is None:
            if concept is not None:
                context = self.extract_context(concept)
            elif self.cat is not None:
                context = self.extract_context_from_cat(subject)
            else:
                context = HyperedgeContext(name=subject)
        
        # Initialize validation
        validation = ClaimValidation(
            subject=subject,
            predicate="is_a",
            object=object_,
            valid=False,
            strength=ClaimStrength.INVALID,
            context=context,
        )
        
        # Check 1: Is object_ in primitive is_a?
        if object_ in context.is_a_primitive:
            validation.supporting_evidence.append(
                f"primitive_is_a: {subject} is_a {object_}"
            )
        
        # Check 2: Does part_of support this?
        # If X part_of Y, and Y is_a Z, then X might be_a Z
        for parent in context.part_of:
            if self.cat and parent in self.cat.entities:
                parent_entity = self.cat.entities[parent]
                if object_ in parent_entity.is_a:
                    validation.supporting_evidence.append(
                        f"part_of_chain: {subject} part_of {parent}, {parent} is_a {object_}"
                    )
        
        # Check 3: Does instantiates support this?
        # If X produces Y, and Y is_a Z, then X might produce Z-things
        for product in context.produces:
            if self.cat and product in self.cat.entities:
                product_entity = self.cat.entities[product]
                if object_ in product_entity.is_a:
                    validation.supporting_evidence.append(
                        f"produces_chain: {subject} instantiates {product}, {product} is_a {object_}"
                    )
        
        # Check 4: Transitive is_a through Cat of Cat
        if self.cat:
            trace = self.cat.trace_to_root(subject)
            if object_ in trace:
                validation.supporting_evidence.append(
                    f"transitive_is_a: {' → '.join(trace[:trace.index(object_)+1])}"
                )
        
        # Check 5: Y-layer compatibility
        if context.y_layer:
            expected_layers = self._get_expected_layers(object_)
            if context.y_layer in expected_layers:
                validation.supporting_evidence.append(
                    f"y_layer_compatible: {context.y_layer} expected for {object_}"
                )
            elif expected_layers:
                validation.missing_evidence.append(
                    f"y_layer_mismatch: {context.y_layer} not in expected {expected_layers}"
                )
        
        # Calculate strength based on evidence
        evidence_count = len(validation.supporting_evidence)
        contradiction_count = len(validation.contradicting_evidence)
        
        if contradiction_count > 0:
            validation.valid = False
            validation.strength = ClaimStrength.INVALID
        elif evidence_count == 0:
            validation.valid = False
            validation.strength = ClaimStrength.INVALID
            validation.missing_evidence.append(
                f"No evidence: {subject} has no relationships supporting is_a {object_}"
            )
        elif evidence_count == 1:
            validation.valid = True
            validation.strength = ClaimStrength.WEAK
        elif evidence_count == 2:
            validation.valid = True
            validation.strength = ClaimStrength.MODERATE
        elif evidence_count >= 3:
            validation.valid = True
            validation.strength = ClaimStrength.STRONG
        
        # Generate witness if valid
        if validation.valid:
            validation.witness = self._generate_witness(validation)
            if validation.strength == ClaimStrength.STRONG:
                validation.strength = ClaimStrength.WITNESSED
        
        return validation

    def relationship_justification_coverage(
        self,
        required_relationships: List[str],
        concept: Optional[Dict[str, Any]] = None,
        context: Optional[HyperedgeContext] = None,
    ) -> JustificationCoverage:
        """Compute `justifies` coverage for required derivation relationships."""
        justifies_tokens = self._extract_justifies_tokens(concept, context)
        justified: List[str] = []

        for relation in required_relationships:
            relation_key = relation.split(":", 2)[1] if ":" in relation else relation
            if relation in justifies_tokens or relation_key in justifies_tokens:
                justified.append(relation)

        return JustificationCoverage(
            required_relationships=list(required_relationships),
            justifies_tokens=sorted(justifies_tokens),
            justified_relationships=justified,
            required_rel_count=len(required_relationships),
            justified_rel_count=len(justified),
            all_required_justified=(
                len(required_relationships) > 0 and len(justified) == len(required_relationships)
            ),
        )
    
    def _get_expected_layers(self, category: str) -> List[str]:
        """Get expected Y-layers for a category."""
        layer_map = {
            "Cat_of_Cat": ["Y1"],
            "Entity": ["Y1", "Y2", "Y3", "Y4"],
            "Category": ["Y1", "Y2", "Y3"],
            "Relationship": ["Y1"],
            "Instance": ["Y4"],
            "Pattern": ["Y5"],
            "Implementation": ["Y6"],
        }
        return layer_map.get(category, [])
    
    def _generate_witness(self, validation: ClaimValidation) -> str:
        """Generate the pattern_of_is_a witness."""
        parts = []
        
        for evidence in validation.supporting_evidence:
            if evidence.startswith("primitive_is_a:"):
                parts.append("primitive")
            elif evidence.startswith("part_of_chain:"):
                parts.append("part_of")
            elif evidence.startswith("produces_chain:"):
                parts.append("produces")
            elif evidence.startswith("transitive_is_a:"):
                parts.append("transitive")
            elif evidence.startswith("y_layer_compatible:"):
                parts.append("y_layer")
        
        pattern = "+".join(parts)
        return f"pattern_of_is_a({pattern}) → {validation.subject} is_a {validation.object}"

    def _extract_justifies_tokens(
        self,
        concept: Optional[Dict[str, Any]],
        context: Optional[HyperedgeContext],
    ) -> Set[str]:
        """Normalize justifies declarations into lookup tokens."""
        raw_justifies: Any = []
        if concept is not None:
            raw_justifies = concept.get("justifies")
            if raw_justifies is None:
                raw_justifies = concept.get("properties", {}).get("justifies", [])
        elif context is not None:
            raw_justifies = context.properties.get("justifies", [])

        if raw_justifies is None:
            raw_justifies = []

        tokens: Set[str] = set()
        values = raw_justifies if isinstance(raw_justifies, list) else [raw_justifies]
        for item in values:
            if isinstance(item, str):
                tokens.add(item)
            elif isinstance(item, dict):
                subject = item.get("subject")
                predicate = item.get("predicate")
                object_ = item.get("object")
                if predicate:
                    tokens.add(str(predicate))
                if subject and predicate and object_:
                    tokens.add(f"{subject}:{predicate}:{object_}")
        return tokens


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def validate_is_a_claim(
    subject: str,
    object_: str,
    concept: Optional[Dict[str, Any]] = None,
    cat=None,
) -> ClaimValidation:
    """
    Validate the claim: "subject is_a object_"
    
    This is the main entry point for hyperedge validation.
    """
    validator = HyperedgeValidator(cat=cat)
    return validator.validate_claim(subject, object_, concept=concept)


# =============================================================================
# DEMO
# =============================================================================

if __name__ == "__main__":
    print("=== HYPEREDGE VALIDATOR ===")
    print()
    
    validator = HyperedgeValidator()
    
    # Test 1: Claim with primitive is_a only
    print("1. Claim with primitive is_a:")
    concept = {
        "name": "Dog",
        "is_a": ["Animal"],
    }
    result = validator.validate_claim("Dog", "Animal", concept=concept)
    print(result.explain())
    print()
    
    # Test 2: Claim with no evidence
    print("2. Claim with no evidence:")
    concept = {
        "name": "RandomThing",
        "is_a": ["Something"],
    }
    result = validator.validate_claim("RandomThing", "Animal", concept=concept)
    print(result.explain())
    print()
    
    # Test 3: Rich hyperedge context
    print("3. Rich hyperedge context:")
    concept = {
        "name": "SkillSpec",
        "is_a": ["Category"],
        "part_of": ["YOUKNOW"],
        "produces": ["SkillPackage"],
        "y_layer": "Y3",
    }
    result = validator.validate_claim("SkillSpec", "Category", concept=concept)
    print(result.explain())
    print()
    
    # Test 4: With Cat of Cat
    print("4. With Cat of Cat integration:")
    try:
        from cat_of_cat import get_cat
        cat = get_cat()
        validator_with_cat = HyperedgeValidator(cat=cat)
        
        result = validator_with_cat.validate_claim("Pattern", "Entity")
        print(result.explain())
    except ImportError:
        print("   (Cat of Cat not available in standalone mode)")
