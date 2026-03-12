#!/usr/bin/env python3
"""
UARL Validator - Integration-ready validation wrapper

Usage:
    from uarl_validator import UARLValidator
    
    validator = UARLValidator()
    result = validator.validate_concept({
        "name": "MyPattern",
        "type": "EmbodimentClaim",
        "intuition": "some_idea",
        "compareFrom": "some_comparison",
        "mapsTo": "some_target",
        "analogicalPattern": "the_pattern"  # Required!
    })
    
    if result.valid:
        # Add to ONT layer
        print("Ready to program into Reality")
    else:
        # Add to SOUP layer with error metadata
        for error in result.errors:
            print(f"Hallucination: {error.message}")
"""

import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .owl_reasoner import OWLReasoner

# Lazy import dependencies
_rdflib = None
_pyshacl = None

def _ensure_deps():
    """Ensure dependencies are installed."""
    global _rdflib, _pyshacl
    
    if _rdflib is None:
        try:
            import rdflib
            _rdflib = rdflib
        except ImportError:
            import subprocess
            subprocess.check_call([sys.executable, "-m", "pip", "install", "rdflib", "-q"])
            import rdflib
            _rdflib = rdflib
    
    if _pyshacl is None:
        try:
            import pyshacl
            _pyshacl = pyshacl
        except ImportError:
            import subprocess
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyshacl", "-q"])
            import pyshacl
            _pyshacl = pyshacl
    
    return _rdflib, _pyshacl


@dataclass
class ValidationError:
    """A single validation error (Hallucination reason)."""
    focus_node: str
    property_path: str
    message: str
    severity: str = "Violation"
    
    def to_dict(self) -> Dict[str, str]:
        return {
            "focus_node": self.focus_node,
            "property_path": self.property_path,
            "message": self.message,
            "severity": self.severity
        }


@dataclass
class InclusionMapArgument:
    """Formal argument for why something is a hallucination.
    
    NOT vibes. A structured argument:
    "Entity X has inclusion map Y, therefore should map to Z,
     but the claim maps to W, and is missing morphism M"
    
    This is the bijective explanation required for hallucination.
    """
    entity: str  # The entity being evaluated
    entity_has: List[str]  # What the entity actually has (is_a, properties)
    therefore_should_map_to: str  # Where it SHOULD map given its inclusion map
    but_claim_maps_to: str  # Where the claim says it maps
    missing_morphism: str  # What morphism is missing (compareFrom, etc.)
    
    # Optional: what would fix it
    would_need: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity": self.entity,
            "entity_has": self.entity_has,
            "therefore_should_map_to": self.therefore_should_map_to,
            "but_claim_maps_to": self.but_claim_maps_to,
            "missing_morphism": self.missing_morphism,
            "would_need": self.would_need
        }
    
    def __str__(self) -> str:
        return (
            f"Entity '{self.entity}' has [{', '.join(self.entity_has)}], "
            f"therefore should map to '{self.therefore_should_map_to}', "
            f"but claim maps to '{self.but_claim_maps_to}'. "
            f"Missing morphism: {self.missing_morphism}"
        )


@dataclass
class ValidationResult:
    """Result of UARL validation."""
    valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    concept_uri: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "concept_uri": self.concept_uri,
            "errors": [e.to_dict() for e in self.errors]
        }
    
    @property
    def error_messages(self) -> List[str]:
        """Get just the error messages as strings."""
        return [e.message for e in self.errors]
    
    def bijective_hallucination(
        self, 
        reviewer_id: str, 
        inclusion_map_argument: 'InclusionMapArgument'
    ) -> Dict[str, Any]:
        """Create a bijective hallucination declaration.
        
        Requires a FORMAL ARGUMENT, not vibes.
        
        Args:
            reviewer_id: Who is declaring this a hallucination (e.g., agent ID, user ID)
            inclusion_map_argument: The formal argument for why this is a hallucination
            
        Example:
            result.bijective_hallucination(
                reviewer_id="antigravity_agent",
                inclusion_map_argument=InclusionMapArgument(
                    entity="Dog",
                    entity_has=["is_a: Animal", "has: fur", "has: loyalty"],
                    therefore_should_map_to="Pet_Domain",
                    but_claim_maps_to="Pirate",
                    missing_morphism="compareFrom",
                    would_need="Patchy (eye-patch connection)"
                )
            )
        
        When done to your own concepts = evolution (self-hallucination)
        """
        meta = self.hallucination_metadata
        meta["reviewer_pov"] = {
            "reviewer_id": reviewer_id,
            "inclusion_map_argument": inclusion_map_argument.to_dict(),
            "formal_explanation": str(inclusion_map_argument),
            "is_self_hallucination": False
        }
        return meta
    
    def self_hallucination(self, inclusion_map_argument: 'InclusionMapArgument') -> Dict[str, Any]:
        """Declare self-hallucination = requires_evolution.
        
        When you notice your OWN concept is missing something.
        This is how you mark a concept for evolution.
        
        Requires a FORMAL ARGUMENT, not vibes.
        
        Args:
            inclusion_map_argument: The formal argument for what needs to evolve
            
        Example:
            result.self_hallucination(
                InclusionMapArgument(
                    entity="My_Dog_Pirate_Claim",
                    entity_has=["intuition: Dog", "mapsTo: Pirate"],
                    therefore_should_map_to="Validated_Bridge",
                    but_claim_maps_to="Soup_Claim",
                    missing_morphism="compareFrom",
                    would_need="I need to add Patchy as the bridge"
                )
            )
        """
        meta = self.hallucination_metadata
        meta["reviewer_pov"] = {
            "reviewer_id": "self",
            "inclusion_map_argument": inclusion_map_argument.to_dict(),
            "formal_explanation": str(inclusion_map_argument),
            "is_self_hallucination": True
        }
        meta["requires_evolution"] = True
        meta["evolution_target"] = inclusion_map_argument.missing_morphism
        meta["would_need"] = inclusion_map_argument.would_need
        return meta

    @property
    def hallucination_metadata(self) -> Dict[str, Any]:
        """Get metadata to store with a Hallucination in SOUP.
        
        Hallucination requires BIJECTIVE explanation:
        "This is missing X from MY perspective, therefore hallucination TO ME"
        
        The entity isn't universally wrong - it's just not real for this reviewer.
        It might be perfectly valid in someone else's reality.
        
        When you do this to your OWN concepts = requires_evolution (self-hallucination)
        """
        return {
            # Core hallucination status
            "is_hallucination": not self.valid,
            "error_count": len(self.errors),
            
            # What's missing - the bijective explanation
            "missing_from_pov": [e.property_path for e in self.errors],
            "whats_missing": self.error_messages,
            
            # For later: who declared this a hallucination and why
            "reviewer_pov": None,  # Set by caller: whose reality is this not mapping to?
            "would_need_for_reality": self.error_messages,  # What would fix it
            
            # Self-hallucination = evolution
            "requires_evolution": not self.valid and len(self.errors) > 0,
            
            # Legacy compatibility
            "error_patterns": [e.property_path for e in self.errors],
        }


class UARLValidator:
    """
    UARL Validator - validates concepts against the UARL foundation ontology.
    
    Now with PERSISTENT DOMAIN ONTOLOGY:
        - Foundation OWL: uarl_v3.owl (static, base classes)
        - Domain OWL: domain.owl (growing, holds validated concepts)
        
    Integration with CartON:
        1. Create validator: validator = UARLValidator(domain_owl_path)
        2. Check existence: validator.concept_exists("Parent_Concept")
        3. Validate concept: result = validator.validate_concept(concept_data)
        4. If result.valid: validator.add_to_domain(concept_data) + add to Neo4j
        5. If not result.valid: add to SOUP layer with result.hallucination_metadata
    """
    
    UARL_NAMESPACE = "http://sanctuary.ai/uarl#"
    
    def __init__(self, uarl_dir: Optional[Path] = None, domain_owl_path: Optional[Path] = None):
        """
        Initialize the validator.
        
        Args:
            uarl_dir: Path to directory containing uarl_v3.owl and uarl_shapes.ttl
                      If None, uses the directory containing this script.
            domain_owl_path: Path to the persistent domain ontology.
                      If None, uses uarl_dir/domain.owl
        """
        _ensure_deps()
        
        if uarl_dir is None:
            uarl_dir = Path(__file__).parent
        
        self.uarl_dir = Path(uarl_dir)
        self.owl_path = self.uarl_dir / "uarl_v3.owl"
        self.shacl_path = self.uarl_dir / "uarl_shapes.ttl"
        
        # Domain ontology - this is where validated concepts are persisted
        if domain_owl_path is None:
            # Use HEAVEN_DATA_DIR if available, otherwise uarl_dir
            import os
            heaven_data = os.getenv('HEAVEN_DATA_DIR', '/tmp/heaven_data')
            self.domain_owl_path = Path(heaven_data) / "ontology" / "domain.owl"
        else:
            self.domain_owl_path = Path(domain_owl_path)
        
        # Verify foundation files exist
        if not self.owl_path.exists():
            raise FileNotFoundError(f"UARL OWL not found: {self.owl_path}")
        if not self.shacl_path.exists():
            raise FileNotFoundError(f"UARL SHACL not found: {self.shacl_path}")
        
        # Load foundation ontology and shapes
        self._load_foundation()
        
        # Load or create domain ontology
        self._load_or_create_domain()
    
    def _load_foundation(self):
        """Load the UARL foundation ontology and SHACL shapes."""
        rdflib, _ = _ensure_deps()
        
        self.ontology = rdflib.Graph()
        self.ontology.parse(str(self.owl_path), format="xml")
        
        self.shapes = rdflib.Graph()
        self.shapes.parse(str(self.shacl_path), format="turtle")
        
        # Create namespace
        self.UARL = rdflib.Namespace(self.UARL_NAMESPACE)
    
    # OWL-standard predicates that YOUKNOW maps to
    _OWL_PREDICATE_MAP = {
        "is_a": "rdfs:subClassOf",
        "description": "rdfs:comment",
    }

    def _load_or_create_domain(self):
        """Load existing domain ontology or create empty one."""
        rdflib, _ = _ensure_deps()
        
        self.domain = rdflib.Graph()
        self.domain.bind("uarl", self.UARL)
        self.domain.bind("rdfs", rdflib.namespace.RDFS)
        self.domain.bind("owl", rdflib.namespace.OWL)
        
        # Ensure directory exists
        self.domain_owl_path.parent.mkdir(parents=True, exist_ok=True)
        
        if self.domain_owl_path.exists():
            try:
                self.domain.parse(str(self.domain_owl_path), format="xml")
            except Exception:
                # If parse fails, start fresh
                pass
        
        # Cache of known concept names for fast lookup
        self._concept_cache = self._build_concept_cache()
    
    def _build_concept_cache(self) -> set:
        """Build cache of concept names in domain ontology."""
        rdflib, _ = _ensure_deps()
        
        concepts = set()
        for s in self.domain.subjects(rdflib.RDF.type, None):
            if str(s).startswith(self.UARL_NAMESPACE):
                name = str(s).replace(self.UARL_NAMESPACE, "")
                concepts.add(name)
        return concepts

    def _property_is_datatype(self, prop_uri) -> bool:
        """Check if a property is declared as an OWL DatatypeProperty."""
        rdflib, _ = _ensure_deps()
        from rdflib.namespace import OWL
        return (
            (prop_uri, rdflib.RDF.type, OWL.DatatypeProperty) in self.ontology
            or (prop_uri, rdflib.RDF.type, OWL.DatatypeProperty) in self.domain
        )
    
    def concept_exists(self, name: str) -> bool:
        """Check if a concept exists in the domain ontology."""
        return name in self._concept_cache
    
    def get_existing_concepts(self) -> set:
        """Get all concept names in the domain ontology."""
        return self._concept_cache.copy()
    
    def _resolve_predicate(self, key: str, rdflib):
        """Map YOUKNOW predicates to OWL-standard predicates where they overlap.

        Returns the proper RDF predicate URI for a given key.
        UARL-specific predicates stay in uarl: namespace.
        OWL-overlapping predicates use rdfs:/rdf: standards.
        """
        RDFS = rdflib.namespace.RDFS
        if key == "is_a":
            return RDFS.subClassOf
        elif key == "description":
            return RDFS.comment
        else:
            return rdflib.URIRef(f"{self.UARL_NAMESPACE}{key}")

    def add_to_domain(self, concept_data: Dict[str, Any]) -> bool:
        """
        Add a validated concept to the persistent domain ontology.

        OWL Alignment:
          - is_a      → rdfs:subClassOf
          - description → rdfs:comment
          - name       → rdfs:label
          - type       → rdf:type (already standard)
          - All others → uarl:* (UARL-specific predicates)
        
        Args:
            concept_data: The concept data (same format as validate_concept)
            
        Returns:
            True if successfully added and saved
        """
        rdflib, _ = _ensure_deps()
        RDFS = rdflib.namespace.RDFS
        
        name = concept_data.get("name", "unnamed_concept")
        concept_type = concept_data.get("type", "Concept")
        
        concept_uri = rdflib.URIRef(f"{self.UARL_NAMESPACE}{name}")
        type_uri = rdflib.URIRef(f"{self.UARL_NAMESPACE}{concept_type}")
        
        # rdf:type — already OWL standard
        self.domain.add((concept_uri, rdflib.RDF.type, type_uri))
        
        # rdfs:label — OWL standard for human-readable name
        self.domain.add((concept_uri, RDFS.label, rdflib.Literal(name)))
        
        # Add properties with OWL-aligned predicates
        for key, value in concept_data.items():
            if key in ("name", "type"):
                continue
            
            prop_uri = self._resolve_predicate(key, rdflib)
            is_datatype_prop = self._property_is_datatype(prop_uri)
            
            # For is_a, the value is the parent class — write as rdfs:subClassOf
            # For description, values are literals — write as rdfs:comment
            force_literal = (key == "description")

            if isinstance(value, bool):
                from rdflib.namespace import XSD
                self.domain.add((
                    concept_uri,
                    prop_uri,
                    rdflib.Literal(value, datatype=XSD.boolean)
                ))
            elif isinstance(value, (int, float)):
                from rdflib.namespace import XSD
                self.domain.add((
                    concept_uri, 
                    prop_uri, 
                    rdflib.Literal(value, datatype=XSD.integer if isinstance(value, int) else XSD.decimal)
                ))
            elif isinstance(value, str):
                if force_literal or is_datatype_prop:
                    self.domain.add((concept_uri, prop_uri, rdflib.Literal(value)))
                else:
                    value_uri = rdflib.URIRef(f"{self.UARL_NAMESPACE}{value}")
                    self.domain.add((concept_uri, prop_uri, value_uri))
            elif isinstance(value, list):
                for v in value:
                    if v is None:
                        continue
                    if isinstance(v, str):
                        if force_literal or is_datatype_prop:
                            self.domain.add((concept_uri, prop_uri, rdflib.Literal(v)))
                        else:
                            value_uri = rdflib.URIRef(f"{self.UARL_NAMESPACE}{v}")
                            self.domain.add((concept_uri, prop_uri, value_uri))
                    elif isinstance(v, bool):
                        from rdflib.namespace import XSD
                        self.domain.add((
                            concept_uri,
                            prop_uri,
                            rdflib.Literal(v, datatype=XSD.boolean)
                        ))
                    elif isinstance(v, (int, float)):
                        from rdflib.namespace import XSD
                        self.domain.add((
                            concept_uri,
                            prop_uri,
                            rdflib.Literal(v, datatype=XSD.integer if isinstance(v, int) else XSD.decimal)
                        ))
        
        # Update cache
        self._concept_cache.add(name)
        
        # Persist to file
        try:
            self.domain.serialize(destination=str(self.domain_owl_path), format="xml")
            return True
        except Exception as e:
            print(f"Failed to save domain ontology: {e}", file=sys.stderr)
            return False
    
    def remove_from_domain(self, name: str) -> bool:
        """Remove a concept from the domain ontology."""
        rdflib, _ = _ensure_deps()
        
        concept_uri = rdflib.URIRef(f"{self.UARL_NAMESPACE}{name}")
        
        # Remove all triples with this concept as subject
        for p, o in list(self.domain.predicate_objects(concept_uri)):
            self.domain.remove((concept_uri, p, o))
        
        # Update cache
        self._concept_cache.discard(name)
        
        # Persist
        try:
            self.domain.serialize(destination=str(self.domain_owl_path), format="xml")
            return True
        except Exception:
            return False
    
    def validate_concept(self, concept_data: Dict[str, Any]) -> ValidationResult:
        """
        Validate a concept against UARL.
        
        Args:
            concept_data: Dictionary with concept properties:
                - name: Unique identifier for this concept
                - type: UARL class (EmbodimentClaim, PatternLattice, etc.)
                - ...other properties depending on type
        
        Returns:
            ValidationResult with valid=True/False and error details
        """
        rdflib, pyshacl = _ensure_deps()
        
        name = concept_data.get("name", "unnamed_concept")
        concept_type = concept_data.get("type", "EmbodimentClaim")
        
        # Build RDF graph for this concept
        concept_graph = rdflib.Graph()
        concept_graph.bind("uarl", self.UARL)
        
        concept_uri = rdflib.URIRef(f"{self.UARL_NAMESPACE}{name}")
        type_uri = rdflib.URIRef(f"{self.UARL_NAMESPACE}{concept_type}")
        
        # Add type assertion
        concept_graph.add((concept_uri, rdflib.RDF.type, type_uri))
        
        # Add properties
        for key, value in concept_data.items():
            if key in ("name", "type"):
                continue

            prop_uri = rdflib.URIRef(f"{self.UARL_NAMESPACE}{key}")
            is_datatype_prop = self._property_is_datatype(prop_uri)

            if isinstance(value, bool):
                from rdflib.namespace import XSD
                concept_graph.add((
                    concept_uri,
                    prop_uri,
                    rdflib.Literal(value, datatype=XSD.boolean)
                ))
            elif isinstance(value, (int, float)):
                from rdflib.namespace import XSD
                concept_graph.add((
                    concept_uri, 
                    prop_uri, 
                    rdflib.Literal(value, datatype=XSD.integer if isinstance(value, int) else XSD.decimal)
                ))
            elif isinstance(value, str):
                if is_datatype_prop:
                    concept_graph.add((concept_uri, prop_uri, rdflib.Literal(value)))
                else:
                    # Assume it's a reference to another node
                    value_uri = rdflib.URIRef(f"{self.UARL_NAMESPACE}{value}")
                    concept_graph.add((concept_uri, prop_uri, value_uri))
            elif isinstance(value, list):
                for v in value:
                    if v is None:
                        continue
                    if isinstance(v, str):
                        if is_datatype_prop:
                            concept_graph.add((concept_uri, prop_uri, rdflib.Literal(v)))
                        else:
                            value_uri = rdflib.URIRef(f"{self.UARL_NAMESPACE}{v}")
                            concept_graph.add((concept_uri, prop_uri, value_uri))
                    elif isinstance(v, bool):
                        from rdflib.namespace import XSD
                        concept_graph.add((
                            concept_uri,
                            prop_uri,
                            rdflib.Literal(v, datatype=XSD.boolean)
                        ))
                    elif isinstance(v, (int, float)):
                        from rdflib.namespace import XSD
                        concept_graph.add((
                            concept_uri,
                            prop_uri,
                            rdflib.Literal(v, datatype=XSD.integer if isinstance(v, int) else XSD.decimal)
                        ))
        
        # Combine ontology + concept for validation
        data_graph = self.ontology + concept_graph
        
        # Run SHACL validation
        conforms, results_graph, results_text = pyshacl.validate(
            data_graph,
            shacl_graph=self.shapes,
            inference='rdfs',
            abort_on_first=False,
            meta_shacl=False,
            debug=False
        )
        
        # Parse errors if validation failed
        errors = []
        if not conforms:
            errors = self._parse_shacl_results(results_graph)
        
        return ValidationResult(
            valid=conforms,
            errors=errors,
            concept_uri=str(concept_uri)
        )

    def validate_with_reasoning(
        self,
        concept_data: Dict[str, Any],
        reasoner: Optional['OWLReasoner'] = None,
    ) -> ValidationResult:
        """
        Full validation: SHACL (structure) + Pellet (axiom consistency).

        Pipeline:
            1. SHACL validates structure (EMR phase - are required properties present?)
            2. If SHACL fails → return errors immediately
            3. If SHACL passes → run Pellet reasoning
            4. Pellet validates OWL axiom consistency (are restrictions satisfied?)
            5. Return combined result

        NOTE: This does NOT check Cat_of_Cat membership. That's handled by Python
        traversal in compiler.py. The reasoner's job is to PROVE axiom satisfaction
        (e.g., EmbodimentClaim has intuition, compareFrom, mapsTo, analogicalPattern),
        not to check OWL graph membership.

        Args:
            concept_data: The concept to validate
            reasoner: OWLReasoner instance (lazy-loaded if None)

        Returns:
            ValidationResult with SHACL errors OR reasoning errors
        """
        # Step 1: SHACL validation (structure)
        shacl_result = self.validate_concept(concept_data)

        if not shacl_result.valid:
            # SHACL failed - return meaningful errors, don't proceed to reasoning
            return shacl_result

        # Step 2: SHACL passed - now run reasoning
        if reasoner is None:
            # Lazy load reasoner
            from .owl_reasoner import OWLReasoner
            reasoner = OWLReasoner(foundation_owl_path=self.owl_path)

        name = concept_data.get("name", "unnamed_concept")
        concept_type = concept_data.get("type", "EmbodimentClaim")
        properties = {k: v for k, v in concept_data.items() if k not in ("name", "type")}

        # Add concept to reasoner
        try:
            reasoner.add_concept(name, concept_type, properties)
        except Exception as e:
            return ValidationResult(
                valid=False,
                errors=[ValidationError(
                    focus_node=name,
                    property_path="",
                    message=f"Reasoner failed to add concept: {e}",
                    severity="Violation"
                )],
                concept_uri=shacl_result.concept_uri
            )

        # Run inference
        reasoning_result = reasoner.run_inference()

        if not reasoning_result.consistent:
            # Ontology became inconsistent - axioms violated
            errors = [ValidationError(
                focus_node=name,
                property_path="",
                message=f"Reasoning inconsistency: {inc}",
                severity="Violation"
            ) for inc in reasoning_result.inconsistencies]
            return ValidationResult(valid=False, errors=errors, concept_uri=shacl_result.concept_uri)

        # NOTE: Cat_of_Cat chain check removed. That's Python's job (compiler.py).
        # Reasoner validates axiom satisfaction, not OWL graph membership.

        # All checks passed - SHACL structure OK + Pellet axioms OK
        return ValidationResult(
            valid=True,
            errors=[],
            concept_uri=shacl_result.concept_uri
        )

    def _parse_shacl_results(self, results_graph) -> List[ValidationError]:
        """Parse SHACL validation results into structured errors."""
        rdflib, _ = _ensure_deps()
        
        errors = []
        SH = rdflib.Namespace("http://www.w3.org/ns/shacl#")
        
        for result in results_graph.subjects(rdflib.RDF.type, SH.ValidationResult):
            focus_node = str(results_graph.value(result, SH.focusNode) or "unknown")
            result_path = str(results_graph.value(result, SH.resultPath) or "unknown")
            message = str(results_graph.value(result, SH.resultMessage) or "Validation failed")
            severity = str(results_graph.value(result, SH.resultSeverity) or "Violation")
            
            # Clean up URIs for readability
            focus_node = focus_node.replace(self.UARL_NAMESPACE, "uarl:")
            result_path = result_path.replace(self.UARL_NAMESPACE, "uarl:")
            
            errors.append(ValidationError(
                focus_node=focus_node,
                property_path=result_path,
                message=message,
                severity=severity.split("#")[-1] if "#" in severity else severity
            ))
        
        return errors
    
    def validate_embodiment_claim(
        self, 
        name: str,
        intuition: str,
        compare_from: str,
        maps_to: str,
        analogical_pattern: Optional[str] = None
    ) -> ValidationResult:
        """
        Convenience method for validating an EmbodimentClaim.
        
        Args:
            name: Unique identifier
            intuition: What you're thinking about (A)
            compare_from: What you're comparing from (B)
            maps_to: Where the pattern maps (C)
            analogical_pattern: THE ACTUAL PATTERN (D) - can be None if still discovering
        """
        concept_data = {
            "name": name,
            "type": "EmbodimentClaim",
            "intuition": intuition,
            "compareFrom": compare_from,
            "mapsTo": maps_to,
        }
        if analogical_pattern:
            concept_data["analogicalPattern"] = analogical_pattern
        
        return self.validate_concept(concept_data)
    
    def validate_pattern_lattice(
        self,
        name: str,
        abstraction_level: int,
        subsumes: Optional[List[str]] = None,
        instantiates_pattern_of_isa: bool = False
    ) -> ValidationResult:
        """
        Convenience method for validating a PatternLattice.
        
        Args:
            name: Unique identifier
            abstraction_level: How abstract (higher = more general)
            subsumes: List of child pattern names this subsumes
            instantiates_pattern_of_isa: If True, links to THE_PatternOfIsA
        """
        concept_data = {
            "name": name,
            "type": "ValidatedLattice" if instantiates_pattern_of_isa else "PatternLattice",
            "abstractionLevel": abstraction_level,
        }
        if subsumes:
            concept_data["subsumes"] = subsumes
        if instantiates_pattern_of_isa:
            concept_data["produces"] = "THE_PatternOfIsA"
        
        return self.validate_concept(concept_data)


# ============================================================
# CLI for testing
# ============================================================

def main():
    """Run some example validations."""
    print("="*60)
    print("UARL Validator - Integration Ready")
    print("="*60)
    
    validator = UARLValidator()
    
    # Test 1: Valid EmbodimentClaim
    print("\n📋 Test 1: Valid EmbodimentClaim")
    result = validator.validate_embodiment_claim(
        name="patchy_dog_claim",
        intuition="patchy",
        compare_from="dog",
        maps_to="pirate",
        analogical_pattern="eyepatch_pattern"
    )
    print(f"   Valid: {result.valid}")
    if not result.valid:
        for err in result.errors:
            print(f"   ❌ {err.message}")
    
    # Test 2: Invalid EmbodimentClaim (missing pattern)
    print("\n📋 Test 2: EmbodimentClaim WITHOUT analogicalPattern")
    result = validator.validate_embodiment_claim(
        name="incomplete_claim",
        intuition="some_idea",
        compare_from="something",
        maps_to="somewhere",
        analogical_pattern=None  # Missing!
    )
    print(f"   Valid: {result.valid}")
    if not result.valid:
        print(f"   Hallucination metadata: {result.hallucination_metadata}")
    
    # Test 3: PatternLattice
    print("\n📋 Test 3: PatternLattice without abstraction level")
    result = validator.validate_concept({
        "name": "bad_lattice",
        "type": "PatternLattice"
        # Missing: abstractionLevel
    })
    print(f"   Valid: {result.valid}")
    for err in result.errors:
        print(f"   ❌ {err.message}")
    
    print("\n" + "="*60)
    print("✅ Validator ready for CartON integration!")
    print("="*60)


if __name__ == "__main__":
    main()
