"""
YOUKNOW Category of Categories (Cat of Cat)

THE FOUNDATIONAL ROOT OF THE ENTIRE ONTOLOGY.

!! CRITICAL: WHAT CatOfCat ACTUALLY MEANS !!

CatOfCat is NOT just "the root of the is_a tree." It is the mathematical
claim that: something can only BE a category if you can DEFINE IT LITERALLY
AS A CAT — meaning you can walk up through the derivation chain until you
mathematically define its semantics using the CORE SENTENCE.

The core sentence (all SPOs co-arise):
  from Reality and is(Reality):
  primitive_is_a IS a type of is_a
  is_a embodies part_of
  part_of (entailed by is_a, itself as a triple) entails instantiates
  instantiates necessitates produces (the new label)
  part_of manifests produces
  produces reifies as pattern_of_is_a
  pattern_of_is_a produces programs
  programs instantiates part_of Reality

"Traces to CatOfCat" means: you can decompose this entity's existence
through the core sentence until every relationship is justified by the
bootstrap mathematics. NOT just "there's a string path in a dict."

At each level of the walk, the entity must have derivation chain properties
that justify its membership. The Aut check: can you explain what this IS
and ISN'T via the bijective map about domain constraints?

Math: D:[D→D] endofunctor, domain as fixed point autology ABOUT is_a.
Stops when constraints are inferential in the logic.

State:
  trace_to_root() walks is_a parents in a Python dict. Checks if strings exist.
  Foundation entities (993) loaded from uarl.owl via _load_from_foundation_ontology().
  Hardcoded primitives remain as bootstrap seed, overridden by OWL loading.

  TODO: trace_to_root() should ask the reasoner "at each level, is the relationship
  between this entity and its parent justified through the core sentence?"
  via OWL property chains + Pellet inference.
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
    # Arbitrary relationships beyond the 4 structural ones
    # Keys are predicate names (e.g. "has_domain"), values are lists of targets
    relationships: Dict[str, List[str]] = field(default_factory=dict)
    y_layer: Optional[str] = None  # Which Y-strata layer
    created: datetime = field(default_factory=datetime.now)

    def is_primitive(self) -> bool:
        """Is this a primitive category?"""
        return self.name in [p.value for p in PrimitiveCategory]

    def all_relationships(self) -> Dict[str, List[str]]:
        """Get ALL relationships including structural ones."""
        result = {}
        if self.is_a: result["is_a"] = list(self.is_a)
        if self.part_of: result["part_of"] = list(self.part_of)
        if self.has_part: result["has_part"] = list(self.has_part)
        if self.produces: result["produces"] = list(self.produces)
        result.update(self.relationships)
        return result

    def all_targets(self) -> Set[str]:
        """Get ALL relationship targets for recursive resolution checks."""
        targets = set()
        targets.update(self.is_a)
        targets.update(self.part_of)
        targets.update(self.has_part)
        targets.update(self.produces)
        for rel_targets in self.relationships.values():
            targets.update(rel_targets)
        return targets


class CategoryOfCategories:
    """
    THE ROOT OF THE ONTOLOGY.
    
    Cat of Cat is self-referential: Cat_of_Cat IS_A Cat_of_Cat.
    Everything else traces back to here.
    """
    
    def __init__(self, domain: Optional[str] = None):
        self.entities: Dict[str, CatEntity] = {}
        self._declared_bounded: Set[str] = set()
        self.domain = domain
        self._reasoner = None  # Lazy-loaded OWL reasoner
        # ALL ontology knowledge comes from OWL via the reasoner.
        # Python dicts are ONLY a cache for chain-tracing performance.
        # The reasoner loads domain.owl which imports uarl.owl by URI.
        self._load_from_reasoner(domain)

    def _load_from_reasoner(self, domain: Optional[str] = None):
        """Load ALL ontology knowledge from OWL via owlready2.

        domain.owl imports uarl.owl by URI. owlready2 resolves the import.
        We query the loaded ontology for all individuals and classes,
        extracting ALL core sentence predicates (not just 3).
        """
        try:
            from .owl_reasoner import OWLReasoner
        except ImportError:
            return

        try:
            # The reasoner loads uarl.owl + starsystem.owl + domain.owl
            self._reasoner = OWLReasoner(domain_owl_path=self._get_domain_owl_path(domain))

            # Proxy path (daemon mode): load classes via HTTP BEFORE touching .foundation
            if hasattr(self._reasoner, 'get_classes'):
                for cls_data in self._reasoner.get_classes():
                    name = cls_data.get("name")
                    if not name or name in self.entities:
                        continue
                    is_a = cls_data.get("is_a") or ["Cat_of_Cat"]
                    self.entities[name] = CatEntity(name=name, is_a=is_a)
                    self._declared_bounded.add(name)
                # Bootstrap root entities — Cat_of_Cat is a terminal axiom, no is_a parent
                self.entities["Cat_of_Cat"] = CatEntity(name="Cat_of_Cat", is_a=[])
                self._declared_bounded.add("Cat_of_Cat")
                if "Entity" not in self.entities:
                    self.entities["Entity"] = CatEntity(name="Entity", is_a=["Cat_of_Cat"])
                self._declared_bounded.add("Entity")
                self._declared_bounded.add("Reality")
                return  # Proxy loaded all classes — skip owlready2 direct path

            # Collect ALL ontologies the reasoner loaded
            all_ontos = [self._reasoner.foundation]
            if hasattr(self._reasoner, '_starsystem'):
                all_ontos.append(self._reasoner._starsystem)
            if hasattr(self._reasoner, 'domain'):
                all_ontos.append(self._reasoner.domain)

            # Bootstrap: Cat_of_Cat is a terminal axiom — no is_a parent
            self.entities["Cat_of_Cat"] = CatEntity(
                name="Cat_of_Cat",
                is_a=[],
            )
            self._declared_bounded.add("Cat_of_Cat")

            # Load ALL individuals and classes from the ontology
            # Extract ALL core sentence predicates
            uarl_ns = "http://sanctuary.ai/uarl#"
            core_preds = ["isA", "partOf", "hasPart", "produces", "instantiates",
                          "embodies", "manifests", "reifies", "programs"]

            # If reasoner is a proxy (daemon mode), load classes via HTTP
            if hasattr(self._reasoner, 'get_classes'):
                for cls_data in self._reasoner.get_classes():
                    name = cls_data.get("name")
                    if not name or name in self.entities:
                        continue
                    is_a = cls_data.get("is_a") or ["SOUP_Unresolved"]
                    self.entities[name] = CatEntity(name=name, is_a=is_a)

            for onto in all_ontos:
                for ind in onto.individuals():
                    name = ind.name
                    if not name or name in self.entities:
                        continue

                    is_a = [getattr(t, 'name', str(t)) for t in getattr(ind, 'isA', [])]
                    part_of = [getattr(t, 'name', str(t)) for t in getattr(ind, 'partOf', [])]
                    produces = [getattr(t, 'name', str(t)) for t in getattr(ind, 'produces', [])]
                    has_part = [getattr(t, 'name', str(t)) for t in getattr(ind, 'hasPart', [])]

                    if not is_a:
                        for cls in ind.is_a:
                            if hasattr(cls, 'name') and cls.name not in ("NamedIndividual", "Thing"):
                                is_a.append(cls.name)
                                break
                        if not is_a:
                            is_a = ["Entity"]

                    rels = {}
                    for pred_name in ["instantiates", "embodies", "manifests", "reifies", "programs"]:
                        vals = [getattr(t, 'name', str(t)) for t in getattr(ind, pred_name, [])]
                        if vals:
                            rels[pred_name] = vals

                    self.entities[name] = CatEntity(
                        name=name,
                        is_a=is_a,
                        part_of=part_of,
                        produces=produces,
                        has_part=has_part,
                        relationships=rels,
                    )
                    self._declared_bounded.add(name)

                # Also load OWL Classes
                for cls in onto.classes():
                    name = getattr(cls, 'name', None)
                    if not name or name in self.entities or name.startswith("http"):
                        continue

                    is_a = []
                    for parent in cls.is_a:
                        if hasattr(parent, 'name') and parent.name not in ("Thing",):
                            is_a.append(parent.name)

                    if not is_a:
                        for eq in cls.equivalent_to:
                            if hasattr(eq, 'name') and eq.name in self.entities:
                                is_a.append(eq.name)
                        if not is_a:
                            is_a = ["SOUP_Unresolved"]
                    self.entities[name] = CatEntity(
                        name=name,
                        is_a=is_a,
                    )

            # Ensure Reality traces to Cat_of_Cat
            if "Reality" in self.entities:
                reality = self.entities["Reality"]
                if "Cat_of_Cat" not in reality.is_a:
                    reality.is_a.insert(0, "Cat_of_Cat")
            self._declared_bounded.add("Reality")

        except Exception as e:
            # Reasoner failure should not prevent cat_of_cat from existing
            # Fallback: just have Cat_of_Cat and Entity
            if "Entity" not in self.entities:
                self.entities["Entity"] = CatEntity(name="Entity", is_a=["Cat_of_Cat"])
                self._declared_bounded.add("Entity")

    def _get_domain_owl_path(self, domain: Optional[str] = None):
        """Get path to domain OWL file."""
        import os
        from pathlib import Path
        heaven_data = os.getenv("HEAVEN_DATA_DIR", "/tmp/heaven_data")
        ontology_dir = Path(heaven_data) / "ontology"
        if domain:
            return ontology_dir / f"{domain}.owl"
        return ontology_dir / "domain.owl"

# COMMENTED OUT 2026-03-30: Python reimplementation of OWL loading. The OWL IS the source of truth. Use owlready2/Pellet to query it directly. Do not reimplement OWL semantics in Python dicts.
    # def _load_from_foundation_ontology(self):
        # """Load all foundation entities from uarl.owl into the Python cat.

        # This bridges the OWL foundation with the Python dict so that
        # chain-tracing works for foundation types (Reality, IJEGU,
        # Compassion, WisdomMaverick, OVP, OVA, etc).

        # The OWL IS the source of truth — this just reads it.
        # """
        # from pathlib import Path
        # try:
            # import rdflib
        # except ImportError:
            # return

        # owl_path = Path(__file__).parent / "uarl.owl"
        # if not owl_path.exists():
            # return

        # try:
            # g = rdflib.Graph()
            # g.parse(str(owl_path), format="xml")
            # uarl_ns = "http://sanctuary.ai/uarl#"
            # UARL = rdflib.Namespace(uarl_ns)
            # OWL = rdflib.namespace.OWL

            # # Load all NamedIndividuals with their isA, partOf, produces
            # for s in g.subjects(rdflib.RDF.type, OWL.NamedIndividual):
                # name = str(s).replace(uarl_ns, "")
                # if not name or name.startswith("http") or name in self.entities:
                    # continue

                # is_a = [str(o).replace(uarl_ns, "") for o in g.objects(s, UARL.isA)]
                # part_of = [str(o).replace(uarl_ns, "") for o in g.objects(s, UARL.partOf)]
                # produces = [str(o).replace(uarl_ns, "") for o in g.objects(s, UARL.produces)]

                # # If no isA from uarl:isA, check rdf:type for the class
                # if not is_a:
                    # for o in g.objects(s, rdflib.RDF.type):
                        # type_name = str(o).replace(uarl_ns, "")
                        # if type_name not in ("NamedIndividual", "Class", "Entity") and not str(o).startswith("http://www.w3.org/"):
                            # is_a.append(type_name)
                            # break
                    # if not is_a:
                        # is_a = ["Entity"]

                # self.entities[name] = CatEntity(
                    # name=name,
                    # is_a=is_a,
                    # part_of=part_of,
                    # produces=produces,
                    # properties={"loaded_from": "uarl.owl", "foundation": True},
                # )
                # self._declared_bounded.add(name)

            # # Also load OWL Classes that have isA/partOf/produces (like IJEGU, Compassion, etc)
            # for s in g.subjects(rdflib.RDF.type, OWL.Class):
                # name = str(s).replace(uarl_ns, "")
                # if not name or name.startswith("http") or name in self.entities:
                    # continue

                # is_a = [str(o).replace(uarl_ns, "") for o in g.objects(s, UARL.isA)]
                # part_of = [str(o).replace(uarl_ns, "") for o in g.objects(s, UARL.partOf)]
                # produces = [str(o).replace(uarl_ns, "") for o in g.objects(s, UARL.produces)]

                # if not is_a and not part_of and not produces:
                    # # Check rdfs:subClassOf as fallback for is_a
                    # RDFS = rdflib.namespace.RDFS
                    # for o in g.objects(s, RDFS.subClassOf):
                        # parent = str(o).replace(uarl_ns, "")
                        # if not parent.startswith("http"):
                            # is_a.append(parent)

                # if is_a or part_of or produces:
                    # self.entities[name] = CatEntity(
                        # name=name,
                        # is_a=is_a if is_a else ["Entity"],
                        # part_of=part_of,
                        # produces=produces,
                        # properties={"loaded_from": "uarl.owl", "foundation": True},
                    # )
                    # self._declared_bounded.add(name)

            # # Ensure Reality traces to Cat_of_Cat (they're the same thing)
            # # Cat_of_Cat MUST be first in is_a so trace_to_root works
            # if "Reality" not in self.entities:
                # self.entities["Reality"] = CatEntity(
                    # name="Reality",
                    # is_a=["Cat_of_Cat"],
                    # properties={"foundation": True},
                # )
            # else:
                # reality = self.entities["Reality"]
                # # Ensure Cat_of_Cat is FIRST in is_a
                # if "Cat_of_Cat" in reality.is_a:
                    # reality.is_a.remove("Cat_of_Cat")
                # reality.is_a.insert(0, "Cat_of_Cat")
            # self._declared_bounded.add("Reality")

            # # Also ensure Ont and Soup trace to Cat_of_Cat
            # for layer_name in ("Ont", "Soup"):
                # if layer_name not in self.entities:
                    # self.entities[layer_name] = CatEntity(
                        # name=layer_name,
                        # is_a=["Cat_of_Cat"],
                        # properties={"foundation": True},
                    # )
                    # self._declared_bounded.add(layer_name)

        # except Exception:
            # # Foundation loading failure should not break Cat_of_Cat
            # pass
# COMMENTED OUT 2026-03-30: Python shadow loading of domain.owl into Python dicts. The OWL reasoner handles this. cat_of_cat should not have its own OWL parser.

    # def _load_from_domain_ontology(self, domain: Optional[str] = None):
        # """Load previously admitted entities from persistent domain OWL.

        # Per-domain OWL architecture:
          # Foundation (uarl.owl primitives) always loaded via _initialize_*.
          # Domain OWL ({domain}.owl) loaded on demand per starsystem/domain.
          # If no domain specified, loads legacy global domain.owl for backwards compat.

        # Persistence loop:
          # youknow() admits → _persist writes to {domain}.owl
          # → next get_cat(domain) loads it here → chains resolve
        # """
        # import os
        # from pathlib import Path

        # heaven_data = os.getenv("HEAVEN_DATA_DIR", "/tmp/heaven_data")
        # ontology_dir = Path(heaven_data) / "ontology"

        # if domain:
            # domain_owl_path = ontology_dir / f"{domain}.owl"
        # else:
            # domain_owl_path = ontology_dir / "domain.owl"

        # if not domain_owl_path.exists():
            # return

        # try:
            # import rdflib
        # except ImportError:
            # # rdflib not available — skip domain loading
            # return

        # try:
            # g = rdflib.Graph()
            # g.parse(str(domain_owl_path), format="xml")

            # uarl_ns = "http://sanctuary.ai/uarl#"

            # # Extract all entities with rdf:type assertions
            # for s, p, o in g.triples((None, rdflib.RDF.type, None)):
                # subject_str = str(s)
                # type_str = str(o)

                # if not subject_str.startswith(uarl_ns):
                    # continue

                # name = subject_str.replace(uarl_ns, "")
                # type_name = type_str.replace(uarl_ns, "")

                # # Skip if already in primitives
                # if name in self.entities:
                    # continue

                # # Skip OWL infrastructure types
                # if type_name in ("Class", "ObjectProperty", "DatatypeProperty",
                                  # "Ontology", "NamedIndividual"):
                    # continue

                # # Determine is_a from the type assertion
                # # Hallucination is a proper type — the dual of what was claimed
                # if type_name == "Hallucination" or type_name == "PIOEntity":
                    # is_a = ["Hallucination"]
                # elif type_name in self.entities:
                    # is_a = [type_name]
                # else:
                    # is_a = ["Entity"]

                # self.entities[name] = CatEntity(
                    # name=name,
                    # is_a=is_a,
                    # properties={
                        # "loaded_from": "domain.owl",
                        # "rdf_type": type_name,
                    # }
                # )
                # self._declared_bounded.add(name)

            # # Second pass: extract rdfs:subClassOf relationships
            # RDFS = rdflib.namespace.RDFS
            # for s, p, o in g.triples((None, RDFS.subClassOf, None)):
                # subject_str = str(s)
                # parent_str = str(o)

                # if not subject_str.startswith(uarl_ns):
                    # continue

                # name = subject_str.replace(uarl_ns, "")
                # parent_name = parent_str.replace(uarl_ns, "")

                # if name in self.entities and parent_name in self.entities:
                    # entity = self.entities[name]
                    # if parent_name not in entity.is_a:
                        # entity.is_a.append(parent_name)

        # except Exception:
            # # Domain loading failures should not prevent Cat_of_Cat from working.
            # # It just means we fall back to primitives only.
            # pass

# COMMENTED OUT 2026-03-30: Python hardcoding of primitives and GNOSYS types. ALL of this is in uarl.owl. YOUKNOW only loads domain.owl which imports uarl.owl by URI. No Python shadow of the ontology.
    
    # def _initialize_primitives(self):
        # """Initialize the primitive categories."""
        
        # # THE ROOT: Cat_of_Cat IS_A Cat_of_Cat (self-loop)
        # self.entities["Cat_of_Cat"] = CatEntity(
            # name="Cat_of_Cat",
            # is_a=["Cat_of_Cat"],  # SELF-REFERENTIAL
            # y_layer="Y1",
            # properties={
                # "description": "The Category of Categories. The root of all ontology.",
                # "primitive": True,
                # "self_referential": True,
            # }
        # )
        
        # # Entity - the most basic thing
        # self.entities["Entity"] = CatEntity(
            # name="Entity",
            # is_a=["Cat_of_Cat"],
            # y_layer="Y1",
            # properties={
                # "description": "The most basic thing that can exist.",
                # "primitive": True,
            # }
        # )
        
        # # Category - a grouping
        # self.entities["Category"] = CatEntity(
            # name="Category",
            # is_a=["Entity"],
            # y_layer="Y1",
            # properties={
                # "description": "A grouping of entities by shared properties.",
                # "primitive": True,
            # }
        # )
        
        # # Relationship - how things connect
        # self.entities["Relationship"] = CatEntity(
            # name="Relationship",
            # is_a=["Entity"],
            # y_layer="Y1",
            # properties={
                # "description": "A connection between entities.",
                # "primitive": True,
            # }
        # )
        
        # # Instance - a concrete thing
        # self.entities["Instance"] = CatEntity(
            # name="Instance",
            # is_a=["Entity"],
            # y_layer="Y4",
            # properties={
                # "description": "A concrete instantiation of a category.",
                # "primitive": True,
            # }
        # )
        
        # # Pattern - an abstract structure
        # self.entities["Pattern"] = CatEntity(
            # name="Pattern",
            # is_a=["Category"],
            # y_layer="Y5",
            # properties={
                # "description": "An abstract structure extracted from instances.",
                # "primitive": True,
            # }
        # )
        
        # # Implementation - a concrete realization
        # self.entities["Implementation"] = CatEntity(
            # name="Implementation",
            # is_a=["Instance"],
            # y_layer="Y6",
            # properties={
                # "description": "A concrete realization of a pattern as code/artifact.",
                # "primitive": True,
            # }
        # )
        
        # # Hallucination - dual of Entity
        # # Traces the LLM's failed ontological claims.
        # # Hallucination_X is_a Hallucination means "X was attempted but
        # # the chain didn't close". This IS data about the reasoning process.
        # self.entities["Hallucination"] = CatEntity(
            # name="Hallucination",
            # is_a=["Entity"],
            # y_layer="Y1",
            # properties={
                # "description": "The dual of a valid entity. Traces failed ontological claims — the negative space of the ontology.",
                # "primitive": True,
            # }
        # )
        
        # # YOUKNOW - the system itself
        # self.entities["YOUKNOW"] = CatEntity(
            # name="YOUKNOW",
            # is_a=["Category"],
            # part_of=["Cat_of_Cat"],
            # has_part=[
                # "Y_Strata", "O_Strata", "Validation", 
                # "Vendor", "Pipeline", "Cat_of_Cat"
            # ],
            # y_layer="Y1",
            # properties={
                # "description": "The ontology system itself. Homoiconic - describes itself.",
                # "self_describing": True,
            # }
        # )
        
        # # Y_Strata - the six layers
        # self.entities["Y_Strata"] = CatEntity(
            # name="Y_Strata",
            # is_a=["Category"],
            # part_of=["YOUKNOW"],
            # has_part=["Y1", "Y2", "Y3", "Y4", "Y5", "Y6"],
            # properties={
                # "description": "The six vertical layers of the ontology.",
            # }
        # )
        
        # # Individual Y layers
        # for i, (name, desc) in enumerate([
            # ("Y1", "Upper Ontology - observation types"),
            # ("Y2", "Domain Ontology - subject buckets"),
            # ("Y3", "Application Ontology - operations per domain"),
            # ("Y4", "Instance Ontology - actual things observed"),
            # ("Y5", "Pattern Ontology - patterns extracted from instances"),
            # ("Y6", "Implementation Ontology - code/artifacts implementing patterns"),
        # ], 1):
            # self.entities[name] = CatEntity(
                # name=name,
                # is_a=["Category"],
                # part_of=["Y_Strata"],
                # y_layer=f"Y{i}",
                # properties={"description": desc}
            # )
        
        # # O_Strata - the horizontal relationships
        # self.entities["O_Strata"] = CatEntity(
            # name="O_Strata",
            # is_a=["Category"],
            # part_of=["YOUKNOW"],
            # has_part=["IS_Loop", "HAS_Loop"],
            # properties={
                # "description": "The horizontal relationship loops (synapses).",
            # }
        # )
        
        # self.entities["IS_Loop"] = CatEntity(
            # name="IS_Loop",
            # is_a=["Relationship"],
            # part_of=["O_Strata"],
            # properties={
                # "description": "The is_a / inheritance relationship loop.",
                # "primitive_rel": "is_a",
            # }
        # )
        
        # self.entities["HAS_Loop"] = CatEntity(
            # name="HAS_Loop",
            # is_a=["Relationship"],
            # part_of=["O_Strata"],
            # properties={
                # "description": "The has_part / part_of mereological loop.",
                # "primitive_rel": "part_of",
            # }
        # )

        # # GNOSYS structural types (from uarl.owl)
        # self._initialize_gnosys_types()

        # # Foundation entities are explicitly declared bounded by default.
        # self._declared_bounded.update(self.entities.keys())

    # def _initialize_gnosys_types(self):
        # """Initialize GNOSYS structural types from uarl.owl.

        # These are NOT domain types — they are structural extensions of UARL
        # for project-based reasoning, agent emanation, and starsystem colonization.
        # OWL restrictions encode required relationships. CA provides code-level detail.
        # """

        # # === SEED SHIP ===
        # self.entities["Seed_Ship"] = CatEntity(
            # name="Seed_Ship", is_a=["Entity"], y_layer="Y1",
            # has_part=["Starsystem_Registry", "Kardashev_Map", "Sanctum"],
        # )
        # self.entities["Starsystem_Registry"] = CatEntity(
            # name="Starsystem_Registry", is_a=["Entity"], y_layer="Y2",
        # )

        # # === STARSYSTEM HIERARCHY ===
        # self.entities["Starsystem_Collection"] = CatEntity(
            # name="Starsystem_Collection", is_a=["Category"], y_layer="Y2",
            # has_part=["Collection_Category", "GIINT_Project"],
        # )
        # self.entities["Collection_Category"] = CatEntity(
            # name="Collection_Category", is_a=["Category"], y_layer="Y2",
        # )
        # self.entities["Hypercluster"] = CatEntity(
            # name="Hypercluster", is_a=["Category"], y_layer="Y3",
        # )

        # # === GIINT HIERARCHY ===
        # self.entities["GIINT_Project"] = CatEntity(
            # name="GIINT_Project", is_a=["Category"], y_layer="Y3",
            # has_part=["GIINT_Feature"],
        # )
        # self.entities["GIINT_Feature"] = CatEntity(
            # name="GIINT_Feature", is_a=["Category"], y_layer="Y3",
            # has_part=["GIINT_Component"],
            # part_of=["GIINT_Project"],
        # )
        # self.entities["GIINT_Component"] = CatEntity(
            # name="GIINT_Component", is_a=["Category"], y_layer="Y3",
            # has_part=["GIINT_Deliverable"],
            # part_of=["GIINT_Feature"],
        # )
        # self.entities["GIINT_Deliverable"] = CatEntity(
            # name="GIINT_Deliverable", is_a=["Category"], y_layer="Y3",
            # part_of=["GIINT_Component"],
        # )
        # self.entities["GIINT_Task"] = CatEntity(
            # name="GIINT_Task", is_a=["Instance"], y_layer="Y4",
            # part_of=["GIINT_Deliverable"],
        # )

        # # === GIINT AUXILIARY TYPES ===
        # self.entities["Bug"] = CatEntity(
            # name="Bug", is_a=["Entity"], y_layer="Y4",
            # part_of=["GIINT_Component"],
        # )
        # self.entities["Potential_Solution"] = CatEntity(
            # name="Potential_Solution", is_a=["Entity"], y_layer="Y4",
            # part_of=["Bug"],
        # )
        # self.entities["Design"] = CatEntity(
            # name="Design", is_a=["Entity"], y_layer="Y3",
            # part_of=["GIINT_Feature"],
        # )
        # self.entities["Idea"] = CatEntity(
            # name="Idea", is_a=["Entity"], y_layer="Y4",
            # part_of=["GIINT_Project"],
        # )
        # self.entities["Inclusion_Map"] = CatEntity(
            # name="Inclusion_Map", is_a=["Entity"], y_layer="Y4",
            # part_of=["GIINT_Deliverable"],
        # )

        # # === NAVY HIERARCHY ===
        # self.entities["Kardashev_Map"] = CatEntity(
            # name="Kardashev_Map", is_a=["Category"], y_layer="Y2",
        # )
        # self.entities["Navy_Fleet"] = CatEntity(
            # name="Navy_Fleet", is_a=["Category"], y_layer="Y2",
            # part_of=["Kardashev_Map"],
        # )
        # self.entities["Navy_Squadron"] = CatEntity(
            # name="Navy_Squadron", is_a=["Category"], y_layer="Y2",
        # )
        # self.entities["Navy_Starship"] = CatEntity(
            # name="Navy_Starship", is_a=["Instance"], y_layer="Y4",
            # part_of=["Kardashev_Map"],
        # )

        # # === SANCTUM ===
        # self.entities["Sanctum"] = CatEntity(
            # name="Sanctum", is_a=["Category"], y_layer="Y2",
        # )
        # self.entities["Sanctum_Ritual"] = CatEntity(
            # name="Sanctum_Ritual", is_a=["Entity"], y_layer="Y4",
            # part_of=["Sanctum"],
        # )
        # self.entities["Sanctum_Goal"] = CatEntity(
            # name="Sanctum_Goal", is_a=["Entity"], y_layer="Y4",
            # part_of=["Sanctum"],
        # )
        # self.entities["Sanctum_Boundary"] = CatEntity(
            # name="Sanctum_Boundary", is_a=["Entity"], y_layer="Y4",
            # part_of=["Sanctum"],
        # )

        # # === DISCOVERED / EMANATION TYPES ===
        # self.entities["Skill"] = CatEntity(
            # name="Skill", is_a=["Pattern"], y_layer="Y5",
        # )
        # self.entities["Flight_Config"] = CatEntity(
            # name="Flight_Config", is_a=["Pattern"], y_layer="Y5",
        # )
        # self.entities["Persona"] = CatEntity(
            # name="Persona", is_a=["Pattern"], y_layer="Y5",
        # )
        # self.entities["MCP_Server"] = CatEntity(
            # name="MCP_Server", is_a=["Implementation"], y_layer="Y6",
        # )
        # self.entities["Starship_Pilot"] = CatEntity(
            # name="Starship_Pilot", is_a=["Implementation"], y_layer="Y6",
            # part_of=["Navy_Starship"],
        # )
        # self.entities["Mission"] = CatEntity(
            # name="Mission", is_a=["Pattern"], y_layer="Y5",
            # has_part=["Flight_Config"],
        # )
        # self.entities["Starlog"] = CatEntity(
            # name="Starlog", is_a=["Instance"], y_layer="Y4",
            # part_of=["Starsystem_Collection"],
        # )
        # self.entities["Automation"] = CatEntity(
            # name="Automation", is_a=["Implementation"], y_layer="Y6",
        # )
        # self.entities["CAVE_Agent"] = CatEntity(
            # name="CAVE_Agent", is_a=["Implementation"], y_layer="Y6",
            # has_part=["Automation"],
        # )

    def add(self, name: str, is_a: List[str], **kwargs) -> CatEntity:
        """Add a new entity to the ontology."""
        declared_bounded = kwargs.pop("declared_bounded", False)
        # Extract arbitrary relationships from kwargs before passing to CatEntity
        extra_relationships = kwargs.pop("relationships", {})

        # Validate is_a - must trace back to Cat_of_Cat
        for parent in is_a:
            if parent not in self.entities:
                raise ValueError(f"Parent '{parent}' not in ontology. Must add it first.")

        entity = CatEntity(name=name, is_a=is_a, **kwargs)
        # Merge extra relationships
        if extra_relationships:
            for rel_type, targets in extra_relationships.items():
                if isinstance(targets, list):
                    entity.relationships.setdefault(rel_type, []).extend(targets)
                else:
                    entity.relationships.setdefault(rel_type, []).append(str(targets))
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

_DOMAIN_CATS: Dict[Optional[str], "CategoryOfCategories"] = {}

def get_cat(domain: Optional[str] = None) -> CategoryOfCategories:
    """Get Category of Categories instance for a domain.

    Per-domain caching: each domain gets its own Cat_of_Cat loaded with
    foundation types + that domain's OWL. None = legacy global domain.owl.
    """
    if domain not in _DOMAIN_CATS:
        _DOMAIN_CATS[domain] = CategoryOfCategories(domain=domain)
    return _DOMAIN_CATS[domain]


def reset_cat(domain: Optional[str] = None):
    """Reset Cat of Cat for a domain (or all if domain not specified)."""
    if domain is None:
        _DOMAIN_CATS.clear()
    else:
        _DOMAIN_CATS.pop(domain, None)


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
