"""
YOUKNOW Category of Categories (Cat of Cat)

THE FOUNDATIONAL ROOT OF THE ENTIRE ONTOLOGY.

This is where YOUKNOW describes itself. Without this, nothing else works.

The Category of Categories is:
1. The top of the is_a hierarchy
2. Self-referential (it IS_A itself)
3. The source of all other categories
4. The homoiconic root that enables self-description

Y-STRATA MAPPING:
  Cat_of_Cat IS_A Cat_of_Cat (self-loop at Y1)
  Everything else IS_A something in Cat_of_Cat's hierarchy

The primitive categories that Cat of Cat contains:
  - Entity (the most basic thing)
  - Relationship (how things connect)
  - Category (a grouping of things)
  - Instance (a concrete thing)
  - Pattern (an abstract structure)
  - Implementation (a concrete realization)

These map directly to Y-strata:
  Y1 (Upper): Entity, Relationship, Category
  Y2 (Domain): Domain-specific subtypes
  Y3 (Application): Operations on domains
  Y4 (Instance): Concrete instances
  Y5 (Pattern): Patterns extracted from instances
  Y6 (Implementation): Code/artifacts implementing patterns
"""

from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class PrimitiveCategory(Enum):
    """The primitive categories that exist in Cat of Cat."""
    ENTITY = "Entity"
    RELATIONSHIP = "Relationship"
    CATEGORY = "Category"
    INSTANCE = "Instance"
    PATTERN = "Pattern"
    IMPLEMENTATION = "Implementation"
    
    # Meta-categories
    CAT_OF_CAT = "Cat_of_Cat"  # The root
    YOUKNOW = "YOUKNOW"        # The system itself


class PrimitiveRelationship(Enum):
    """The primitive relationships in Cat of Cat."""
    IS_A = "is_a"           # Inheritance / taxonomy
    PART_OF = "part_of"     # Composition / mereology
    HAS_PART = "has_part"   # Inverse of part_of
    PRODUCES = "produces"         # What it generates
    INSTANCE_OF = "instance_of"    # Inverse of produces
    RELATES_TO = "relates_to"      # Generic association
    REIFIES = "reifies"            # Makes abstract concrete


@dataclass
class CatEntity:
    """An entity in the Category of Categories."""
    name: str
    description: str = ""
    is_a: List[str] = field(default_factory=list)
    part_of: List[str] = field(default_factory=list)
    has_part: List[str] = field(default_factory=list)
    produces: List[str] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)
    y_layer: Optional[str] = None  # Which Y-strata layer
    created: datetime = field(default_factory=datetime.now)
    
    def is_primitive(self) -> bool:
        """Is this a primitive category?"""
        return self.name in [p.value for p in PrimitiveCategory]


class CategoryOfCategories:
    """
    THE ROOT OF THE ONTOLOGY.
    
    Cat of Cat is self-referential: Cat_of_Cat IS_A Cat_of_Cat.
    Everything else traces back to here.
    """
    
    def __init__(self):
        self.entities: Dict[str, CatEntity] = {}
        self._declared_bounded: Set[str] = set()
        self._initialize_primitives()
        self._load_from_domain_ontology()

    def _load_from_domain_ontology(self):
        """Load previously admitted entities from the persistent domain OWL.

        This closes the persistence loop:
          youknow() admits → _persist writes to domain.owl
          → next get_cat() loads domain.owl here → chains resolve

        Without this, Cat_of_Cat knows only its ~18 hardcoded primitives
        and every chain breaks on second call.
        """
        import os
        from pathlib import Path

        heaven_data = os.getenv("HEAVEN_DATA_DIR", "/tmp/heaven_data")
        domain_owl_path = Path(heaven_data) / "ontology" / "domain.owl"

        if not domain_owl_path.exists():
            return

        try:
            import rdflib
        except ImportError:
            # rdflib not available — skip domain loading
            return

        try:
            g = rdflib.Graph()
            g.parse(str(domain_owl_path), format="xml")

            uarl_ns = "http://sanctuary.ai/uarl#"

            # Extract all entities with rdf:type assertions
            for s, p, o in g.triples((None, rdflib.RDF.type, None)):
                subject_str = str(s)
                type_str = str(o)

                if not subject_str.startswith(uarl_ns):
                    continue

                name = subject_str.replace(uarl_ns, "")
                type_name = type_str.replace(uarl_ns, "")

                # Skip if already in primitives
                if name in self.entities:
                    continue

                # Skip OWL infrastructure types
                if type_name in ("Class", "ObjectProperty", "DatatypeProperty",
                                  "Ontology", "NamedIndividual"):
                    continue

                # Determine is_a from the type assertion
                # Hallucination is a proper type — the dual of what was claimed
                if type_name == "Hallucination" or type_name == "PIOEntity":
                    is_a = ["Hallucination"]
                elif type_name in self.entities:
                    is_a = [type_name]
                else:
                    is_a = ["Entity"]

                self.entities[name] = CatEntity(
                    name=name,
                    is_a=is_a,
                    properties={
                        "loaded_from": "domain.owl",
                        "rdf_type": type_name,
                    }
                )
                self._declared_bounded.add(name)

            # Second pass: extract rdfs:subClassOf relationships
            RDFS = rdflib.namespace.RDFS
            for s, p, o in g.triples((None, RDFS.subClassOf, None)):
                subject_str = str(s)
                parent_str = str(o)

                if not subject_str.startswith(uarl_ns):
                    continue

                name = subject_str.replace(uarl_ns, "")
                parent_name = parent_str.replace(uarl_ns, "")

                if name in self.entities and parent_name in self.entities:
                    entity = self.entities[name]
                    if parent_name not in entity.is_a:
                        entity.is_a.append(parent_name)

        except Exception:
            # Domain loading failures should not prevent Cat_of_Cat from working.
            # It just means we fall back to primitives only.
            pass
    
    def _initialize_primitives(self):
        """Initialize the primitive categories."""
        
        # THE ROOT: Cat_of_Cat IS_A Cat_of_Cat (self-loop)
        self.entities["Cat_of_Cat"] = CatEntity(
            name="Cat_of_Cat",
            is_a=["Cat_of_Cat"],  # SELF-REFERENTIAL
            y_layer="Y1",
            properties={
                "description": "The Category of Categories. The root of all ontology.",
                "primitive": True,
                "self_referential": True,
            }
        )
        
        # Entity - the most basic thing
        self.entities["Entity"] = CatEntity(
            name="Entity",
            is_a=["Cat_of_Cat"],
            y_layer="Y1",
            properties={
                "description": "The most basic thing that can exist.",
                "primitive": True,
            }
        )
        
        # Category - a grouping
        self.entities["Category"] = CatEntity(
            name="Category",
            is_a=["Entity"],
            y_layer="Y1",
            properties={
                "description": "A grouping of entities by shared properties.",
                "primitive": True,
            }
        )
        
        # Relationship - how things connect
        self.entities["Relationship"] = CatEntity(
            name="Relationship",
            is_a=["Entity"],
            y_layer="Y1",
            properties={
                "description": "A connection between entities.",
                "primitive": True,
            }
        )
        
        # Instance - a concrete thing
        self.entities["Instance"] = CatEntity(
            name="Instance",
            is_a=["Entity"],
            y_layer="Y4",
            properties={
                "description": "A concrete instantiation of a category.",
                "primitive": True,
            }
        )
        
        # Pattern - an abstract structure
        self.entities["Pattern"] = CatEntity(
            name="Pattern",
            is_a=["Category"],
            y_layer="Y5",
            properties={
                "description": "An abstract structure extracted from instances.",
                "primitive": True,
            }
        )
        
        # Implementation - a concrete realization
        self.entities["Implementation"] = CatEntity(
            name="Implementation",
            is_a=["Instance"],
            y_layer="Y6",
            properties={
                "description": "A concrete realization of a pattern as code/artifact.",
                "primitive": True,
            }
        )
        
        # Hallucination - dual of Entity
        # Traces the LLM's failed ontological claims.
        # Hallucination_X is_a Hallucination means "X was attempted but
        # the chain didn't close". This IS data about the reasoning process.
        self.entities["Hallucination"] = CatEntity(
            name="Hallucination",
            is_a=["Entity"],
            y_layer="Y1",
            properties={
                "description": "The dual of a valid entity. Traces failed ontological claims — the negative space of the ontology.",
                "primitive": True,
            }
        )
        
        # YOUKNOW - the system itself
        self.entities["YOUKNOW"] = CatEntity(
            name="YOUKNOW",
            is_a=["Category"],
            part_of=["Cat_of_Cat"],
            has_part=[
                "Y_Strata", "O_Strata", "Validation", 
                "Vendor", "Pipeline", "Cat_of_Cat"
            ],
            y_layer="Y1",
            properties={
                "description": "The ontology system itself. Homoiconic - describes itself.",
                "self_describing": True,
            }
        )
        
        # Y_Strata - the six layers
        self.entities["Y_Strata"] = CatEntity(
            name="Y_Strata",
            is_a=["Category"],
            part_of=["YOUKNOW"],
            has_part=["Y1", "Y2", "Y3", "Y4", "Y5", "Y6"],
            properties={
                "description": "The six vertical layers of the ontology.",
            }
        )
        
        # Individual Y layers
        for i, (name, desc) in enumerate([
            ("Y1", "Upper Ontology - observation types"),
            ("Y2", "Domain Ontology - subject buckets"),
            ("Y3", "Application Ontology - operations per domain"),
            ("Y4", "Instance Ontology - actual things observed"),
            ("Y5", "Pattern Ontology - patterns extracted from instances"),
            ("Y6", "Implementation Ontology - code/artifacts implementing patterns"),
        ], 1):
            self.entities[name] = CatEntity(
                name=name,
                is_a=["Category"],
                part_of=["Y_Strata"],
                y_layer=f"Y{i}",
                properties={"description": desc}
            )
        
        # O_Strata - the horizontal relationships
        self.entities["O_Strata"] = CatEntity(
            name="O_Strata",
            is_a=["Category"],
            part_of=["YOUKNOW"],
            has_part=["IS_Loop", "HAS_Loop"],
            properties={
                "description": "The horizontal relationship loops (synapses).",
            }
        )
        
        self.entities["IS_Loop"] = CatEntity(
            name="IS_Loop",
            is_a=["Relationship"],
            part_of=["O_Strata"],
            properties={
                "description": "The is_a / inheritance relationship loop.",
                "primitive_rel": "is_a",
            }
        )
        
        self.entities["HAS_Loop"] = CatEntity(
            name="HAS_Loop",
            is_a=["Relationship"],
            part_of=["O_Strata"],
            properties={
                "description": "The has_part / part_of mereological loop.",
                "primitive_rel": "part_of",
            }
        )

        # Foundation entities are explicitly declared bounded by default.
        self._declared_bounded.update(self.entities.keys())

    def add(self, name: str, is_a: List[str], **kwargs) -> CatEntity:
        """Add a new entity to the ontology."""
        declared_bounded = kwargs.pop("declared_bounded", False)

        # Validate is_a - must trace back to Cat_of_Cat
        for parent in is_a:
            if parent not in self.entities:
                raise ValueError(f"Parent '{parent}' not in ontology. Must add it first.")

        entity = CatEntity(name=name, is_a=is_a, **kwargs)
        self.entities[name] = entity
        if declared_bounded:
            self.declare_bounded(name)
        return entity
    
    def get(self, name: str) -> Optional[CatEntity]:
        """Get an entity by name."""
        return self.entities.get(name)
    
    def trace_to_root(self, name: str) -> List[str]:
        """Trace is_a chain back to Cat_of_Cat."""
        if name not in self.entities:
            return []
        
        chain = [name]
        current = name
        visited = set()
        
        while current and current not in visited:
            visited.add(current)
            entity = self.entities.get(current)
            if not entity or not entity.is_a:
                break
            
            parent = entity.is_a[0]  # Primary parent
            if parent == current:  # Self-loop (Cat_of_Cat)
                break
            chain.append(parent)
            current = parent
        
        return chain
    
    def validate_traces_to_root(self, name: str) -> bool:
        """Does this entity trace back to Cat_of_Cat?"""
        chain = self.trace_to_root(name)
        return "Cat_of_Cat" in chain or name == "Cat_of_Cat"

    def declare_bounded(self, name: str) -> None:
        """Explicitly declare an entity as bounded for promotion gates."""
        if name not in self.entities:
            raise ValueError(f"Entity '{name}' not in ontology.")
        self._declared_bounded.add(name)

    def undeclare_bounded(self, name: str) -> None:
        """Remove explicit bounded declaration for an entity."""
        self._declared_bounded.discard(name)

    def is_declared_bounded(self, name: str) -> bool:
        """Is the full superclass chain explicitly declared bounded?"""
        if name not in self.entities:
            return False

        chain = self.trace_to_root(name)
        if not chain or "Cat_of_Cat" not in chain and name != "Cat_of_Cat":
            return False

        for node in chain:
            if node not in self._declared_bounded:
                return False
        return True
    
    def get_y_layer(self, name: str) -> Optional[str]:
        """What Y-layer is this entity in?"""
        entity = self.entities.get(name)
        if entity and entity.y_layer:
            return entity.y_layer
        
        # Infer from is_a chain
        chain = self.trace_to_root(name)
        for ancestor in chain:
            ancestor_entity = self.entities.get(ancestor)
            if ancestor_entity and ancestor_entity.y_layer:
                return ancestor_entity.y_layer
        
        return None
    
    def list_by_layer(self, layer: str) -> List[str]:
        """List all entities in a Y-layer."""
        return [
            name for name, entity in self.entities.items()
            if entity.y_layer == layer
        ]
    
    def stats(self) -> Dict[str, Any]:
        """Get statistics about the ontology."""
        by_layer = {}
        for layer in ["Y1", "Y2", "Y3", "Y4", "Y5", "Y6"]:
            by_layer[layer] = len(self.list_by_layer(layer))
        
        return {
            "total_entities": len(self.entities),
            "by_layer": by_layer,
            "primitives": len([e for e in self.entities.values() if e.is_primitive()]),
            "declared_bounded": len(self._declared_bounded),
        }


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_GLOBAL_CAT: Optional[CategoryOfCategories] = None

def get_cat() -> CategoryOfCategories:
    """Get the global Category of Categories instance."""
    global _GLOBAL_CAT
    if _GLOBAL_CAT is None:
        _GLOBAL_CAT = CategoryOfCategories()
    return _GLOBAL_CAT


def reset_cat():
    """Reset the global Cat of Cat (for testing)."""
    global _GLOBAL_CAT
    _GLOBAL_CAT = None


# =============================================================================
# DEMO
# =============================================================================

if __name__ == "__main__":
    print("=== CATEGORY OF CATEGORIES ===")
    print()
    
    cat = get_cat()
    
    # Show primitives
    print("1. Primitive categories:")
    for name, entity in cat.entities.items():
        if entity.is_primitive():
            print(f"   {name} IS_A {entity.is_a}")
    print()
    
    # Show Cat_of_Cat self-reference
    print("2. Cat_of_Cat self-reference:")
    root = cat.get("Cat_of_Cat")
    print(f"   Cat_of_Cat IS_A {root.is_a}")
    print(f"   This IS the foundational self-loop.")
    print()
    
    # Show YOUKNOW structure
    print("3. YOUKNOW has_part:")
    youknow = cat.get("YOUKNOW")
    print(f"   {youknow.has_part}")
    print()
    
    # Trace Entity to root
    print("4. Trace 'Entity' to root:")
    chain = cat.trace_to_root("Entity")
    print(f"   {' → '.join(chain)}")
    print()
    
    # Trace Pattern to root
    print("5. Trace 'Pattern' to root:")
    chain = cat.trace_to_root("Pattern")
    print(f"   {' → '.join(chain)}")
    print()
    
    # Add a custom entity
    print("6. Adding custom entity 'SkillSpec':")
    cat.add(
        "SkillSpec",
        is_a=["Category"],
        part_of=["YOUKNOW"],
        y_layer="Y3",
        properties={"description": "Specification for a PAIA skill."}
    )
    chain = cat.trace_to_root("SkillSpec")
    print(f"   Trace: {' → '.join(chain)}")
    print(f"   Y-layer: {cat.get_y_layer('SkillSpec')}")
    print()
    
    # Stats
    print("7. Ontology stats:")
    stats = cat.stats()
    print(f"   Total entities: {stats['total_entities']}")
    print(f"   By layer: {stats['by_layer']}")
