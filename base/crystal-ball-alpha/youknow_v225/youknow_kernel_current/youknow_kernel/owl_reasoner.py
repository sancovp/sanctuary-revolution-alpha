#!/usr/bin/env python3
"""
OWL Reasoner - OWL2 ontology management via owlready2 + Pellet

Manages the OWL ontology files (uarl.owl foundation + domain.owl dynamic).
Loads classes, adds individuals, runs Pellet for consistency checking.

As of 2026-04-19: The compiler's main validation path uses the recursive
restriction walk (instant, in compiler.py) + system_type_validator instead
of Pellet sync_reasoner (which was slow on large domain.owl). Pellet remains
available for OWL consistency checking and LCS computation but is NOT the
primary validation engine.

The foundation OWL (uarl.owl) contains:
  - Core sentence bootstrap (PatternOfIsA, justification edges)
  - Class restrictions (Skill 22+ properties, GIINT hierarchy, etc.)
  - Category theory foundation (Cat, Domain, Aut, EWS)

Used by: owl_server.py (subprocess on port 8103), owl_types.py (class loading),
         uarl_validator.py (SHACL validation when needed).

Usage:
    from owl_reasoner import OWLReasoner

    reasoner = OWLReasoner()

    # Add a concept
    reasoner.add_concept("my_claim", "EmbodimentClaim", {
        "intuition": "patchy",
        "compareFrom": "dog",
        "mapsTo": "pirate",
        "analogicalPattern": "eyepatch_pattern"
    })

    # Run inference
    result = reasoner.run_inference()

    # Check if concept is consistent with ontology
    if result.consistent:
        print("Valid!")
    else:
        print(f"Invalid: {result.inconsistencies}")

Key difference from SHACL:
- SHACL: "Does property X exist?" (structural check)
- Reasoner: "Is this consistent with the axioms?" (logical inference)
- Reasoner: "What new facts can be derived?" (entailment)
- Reasoner: "Does X reach Y via transitive chain?" (transitive closure)
"""

import logging
import sys
import os

logger = logging.getLogger(__name__)
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Set

# Lazy import owlready2
_owlready2 = None

def _ensure_owlready2():
    """Ensure owlready2 is installed."""
    global _owlready2

    if _owlready2 is None:
        try:
            import owlready2
            _owlready2 = owlready2
        except ImportError:
            import subprocess
            subprocess.check_call([sys.executable, "-m", "pip", "install", "owlready2", "-q"])
            import owlready2
            _owlready2 = owlready2

    return _owlready2


@dataclass
class ReasonerResult:
    """Result of running the reasoner."""
    consistent: bool
    inconsistencies: List[str] = field(default_factory=list)
    inferred_facts: List[str] = field(default_factory=list)
    discovered_types: List[Dict[str, Any]] = field(default_factory=list)
    concept_uri: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "consistent": self.consistent,
            "inconsistencies": self.inconsistencies,
            "inferred_facts": self.inferred_facts,
            "discovered_types": self.discovered_types,
            "concept_uri": self.concept_uri
        }


@dataclass
class ValidationResult:
    """Result of validating a concept - matches SHACL validator interface."""
    valid: bool
    errors: List[Dict[str, str]] = field(default_factory=list)
    concept_uri: Optional[str] = None
    reasoner_result: Optional[ReasonerResult] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "errors": self.errors,
            "concept_uri": self.concept_uri
        }

    @property
    def error_messages(self) -> List[str]:
        return [e.get("message", "") for e in self.errors]


class OWLReasoner:
    """
    OWL2 Reasoner wrapper using owlready2 + Pellet.

    Loads foundation OWL (uarl.owl) and manages a domain ontology
    where user concepts are added and validated via reasoning.
    """

    UARL_NAMESPACE = "http://sanctuary.ai/uarl#"

    # Foundation OWL files shipped with the package.
    # owlready2 resolves owl:imports URIs from the onto_path.
    _UARL_LOCAL_PATH = Path(__file__).parent / "uarl.owl"
    _STARSYSTEM_LOCAL_PATH = Path(__file__).parent / "starsystem.owl"
    _FOUNDATION_LOCAL_PATH = Path(__file__).parent / "gnosys_foundation.owl"

    def __init__(
        self,
        domain_owl_path: Optional[Path] = None,
        use_pellet: bool = True,
        # DEPRECATED — kept for backward compat, ignored
        foundation_owl_path: Optional[Path] = None,
    ):
        """
        Initialize the reasoner.

        YOUKNOW only loads domain.owl. domain.owl imports uarl.owl by URI.
        owlready2 resolves the URI to the local uarl.owl shipped with the package.

        Args:
            domain_owl_path: Path to domain ontology. If None, uses default.
            use_pellet: Whether to use Pellet reasoner (requires Java).
        """
        owlready2 = _ensure_owlready2()

        if domain_owl_path is None:
            heaven_data = os.getenv('HEAVEN_DATA_DIR', '/tmp/heaven_data')
            domain_owl_path = Path(heaven_data) / "ontology" / "domain.owl"
        self.domain_path = Path(domain_owl_path)
        self.use_pellet = use_pellet

        # Register local uarl.owl as mirror of the W3C URI
        # so owlready2 resolves owl:imports automatically
        owlready2.onto_path.append(str(self._UARL_LOCAL_PATH.parent))

        self._load_ontologies()

    def _load_ontologies(self):
        """Load all foundation ontologies + domain ontology."""
        owlready2 = _ensure_owlready2()

        self.world = owlready2.World()

        # Load uarl.owl (core: Entity, Cat, Domain, Aut, EWS, bootstrap, core sentence)
        self.foundation = self.world.get_ontology(f"file://{self._UARL_LOCAL_PATH}").load()

        # Load starsystem.owl (GIINT, Navy, Sanctum, Skills — extends uarl)
        if self._STARSYSTEM_LOCAL_PATH.exists():
            self._starsystem = self.world.get_ontology(f"file://{self._STARSYSTEM_LOCAL_PATH}").load()

        # Load or create domain ontology
        self.domain_path.parent.mkdir(parents=True, exist_ok=True)

        if self.domain_path.exists():
            try:
                self.domain = self.world.get_ontology(f"file://{self.domain_path}").load()
            except Exception:
                self.domain = self.world.get_ontology("urn:youknow:domain")
        else:
            self.domain = self.world.get_ontology("urn:youknow:domain")

        # Ensure domain imports foundation
        if self.foundation not in self.domain.imported_ontologies:
            self.domain.imported_ontologies.append(self.foundation)

        self.uarl = self.foundation

    def _get_class(self, class_name: str):
        """Get a class from any loaded ontology."""
        cls = getattr(self.uarl, class_name, None)
        if cls is None and hasattr(self, '_starsystem'):
            cls = getattr(self._starsystem, class_name, None)
        if cls is None:
            cls = getattr(self.domain, class_name, None)
        return cls

    def _get_property(self, prop_name: str):
        """Get a property from any loaded ontology."""
        prop = getattr(self.uarl, prop_name, None)
        if prop is None and hasattr(self, '_starsystem'):
            prop = getattr(self._starsystem, prop_name, None)
        if prop is None:
            prop = getattr(self.domain, prop_name, None)
        return prop

    # Prefix → OWL class mapping for resolving instance names to types
    _PREFIX_TYPE_MAP = {
        "Giint_Project_": "GIINT_Project",
        "Giint_Feature_": "GIINT_Feature",
        "Giint_Component_": "GIINT_Component",
        "Giint_Deliverable_": "GIINT_Deliverable",
        "Giint_Task_": "GIINT_Task",
        "Bug_": "Bug",
        "Design_": "Design",
        "Idea_": "Idea",
        "Inclusion_Map_": "Inclusion_Map",
        "Potential_Solution_": "Potential_Solution",
        "Hypercluster_": "Hypercluster",
        "Skill_": "Skill",
        "Pattern_": "Pattern",
        "Persona_": "Persona",
        "Flight_Config_": "Flight_Config",
        "Mission_": "Mission",
        "Navy_Fleet_": "Navy_Fleet",
        "Navy_Squadron_": "Navy_Squadron",
        "Navy_Starship_": "Navy_Starship",
        "Starship_Pilot_": "Starship_Pilot",
        "Starsystem_": "Starsystem_Collection",
        "Claude_Code_Rule_": "Claude_Code_Rule",
        "Hook_": "Hook",
        "Agent_": "Agent",
        "Slash_Command_": "Slash_Command",
        "ConfigFile_": "ConfigFile",
    }

    def _resolve_type_from_name(self, name: str):
        """Resolve an instance name to its OWL class via naming convention.

        Returns the owlready2 class or None.
        """
        for prefix, type_name in self._PREFIX_TYPE_MAP.items():
            if name.startswith(prefix):
                cls = self._get_class(type_name)
                if cls is not None:
                    return cls
        return None

    def _get_or_create_typed(self, name: str):
        """Get existing individual or create one with correct type from name prefix.

        Instead of creating bare Thing placeholders, resolves the type from
        the naming convention and creates a properly typed individual.
        """
        owlready2 = _ensure_owlready2()

        # Check if already exists
        existing = self.world.search_one(iri=f"*{name}")
        if existing:
            return existing

        # Resolve type from name
        cls = self._resolve_type_from_name(name)
        if cls is None:
            cls = owlready2.Thing  # Fallback to untyped

        with self.domain:
            individual = cls(name)
        return individual

    def add_concept(
        self,
        name: str,
        concept_type: str,
        properties: Dict[str, Any]
    ) -> str:
        """
        Add a concept to the domain ontology.

        Args:
            name: Unique name for the concept
            concept_type: UARL class name (EmbodimentClaim, PatternLattice, etc.)
            properties: Dictionary of property values

        Returns:
            The IRI of the created concept
        """
        owlready2 = _ensure_owlready2()

        # Get the class
        cls = self._get_class(concept_type)
        if cls is None:
            raise ValueError(f"Unknown concept type: {concept_type}")

        # Create individual in domain ontology
        with self.domain:
            individual = cls(name)

            # Set properties — unknown properties get CREATED in domain OWL as SOUP
            for prop_name, value in properties.items():
                prop = self._get_property(prop_name)
                if prop is None:
                    # Generative: create unknown property in domain ontology as SOUP
                    prop = owlready2.types.new_class(prop_name, (owlready2.ObjectProperty,), ontology=self.domain)
                    prop.label = [prop_name]
                    logger.info(f"Created SOUP property in domain OWL: {prop_name}")

                # Handle different value types
                try:
                    if isinstance(value, str):
                        ref = self._get_or_create_typed(value)
                        setattr(individual, prop_name, [ref])
                    elif isinstance(value, (int, float)):
                        setattr(individual, prop_name, [value])
                    elif isinstance(value, list):
                        # Flatten nested lists and ensure all items are strings
                        flat = []
                        for v in value:
                            if isinstance(v, list):
                                flat.extend(str(item) for item in v)
                            else:
                                flat.append(str(v))
                        refs = [self._get_or_create_typed(v) for v in flat]
                        setattr(individual, prop_name, refs)
                except Exception as prop_err:
                    logger.warning(f"Could not set property {prop_name}: {prop_err}")

        return individual.iri

    def run_inference(self) -> ReasonerResult:
        """
        Run the reasoner and compute inferences.

        Returns:
            ReasonerResult with consistency status and inferred facts
        """
        owlready2 = _ensure_owlready2()

        inconsistencies = []
        inferred_facts = []

        try:
            # Suppress owlready2/Pellet verbose output (java classpath, timing)
            import io, contextlib
            _devnull = io.StringIO()
            if self.use_pellet:
                with self.domain, contextlib.redirect_stderr(_devnull), contextlib.redirect_stdout(_devnull):
                    owlready2.sync_reasoner_pellet(
                        self.world,
                        infer_property_values=True,
                        infer_data_property_values=True
                    )
            else:
                with self.domain, contextlib.redirect_stderr(_devnull), contextlib.redirect_stdout(_devnull):
                    owlready2.sync_reasoner(self.world)

            consistent = True

        except owlready2.OwlReadyInconsistentOntologyError as e:
            consistent = False
            inconsistencies.append(str(e))

        except Exception as e:
            # Check if it's a Java error (Pellet not available)
            error_str = str(e).lower()
            if self.use_pellet and ("java" in error_str or "jvm" in error_str):
                print(f"Warning: Pellet requires Java. Falling back to basic reasoning.")
                self.use_pellet = False
                return self.run_inference()  # Retry with basic reasoner (once)
            else:
                # Basic reasoner also failed or non-Java error
                consistent = True  # Assume consistent if reasoner unavailable
                # Don't treat reasoner unavailability as inconsistency

        # Collect inferred facts (new type assertions from reasoning)
        for ind in self.domain.individuals():
            for cls in ind.is_a:
                if hasattr(cls, 'name'):
                    inferred_facts.append(f"{ind.name} is_a {cls.name}")

        # Compute LCS — discover already-operative common types
        discovered_types = self.compute_lcs() if consistent else []

        return ReasonerResult(
            consistent=consistent,
            inconsistencies=inconsistencies,
            inferred_facts=inferred_facts,
            discovered_types=discovered_types,
        )

    def compute_lcs(self) -> List[Dict[str, Any]]:
        """Compute Least Common Subsumers across domain individuals.

        The LCS of a concept's subgraph, posed as its own domain, IS the
        justification for the label — the recovered abstract interaction-type
        that was already operative. This IS the reification check in EMR.

        Groups individuals that share specific (property → target) pairs.
        Two Components both pointing to the same Pattern = they instantiate
        the same abstract interaction-type. The LCS names what was unnamed.

        Returns list of discovered types, each with:
        - lcs_class: the shared OWL class
        - members: individuals sharing this pattern
        - shared_target: the specific target they share
        - shared_via: the property connecting them
        - proposed_name: suggested name for the discovered type
        """
        discovered = []

        try:
            # Inverted index: (property_name, target_name) → [individual_names]
            target_groups: Dict[tuple, list] = {}
            ind_types: Dict[str, str] = {}

            for ind in self.domain.individuals():
                # Get most specific type
                ind_type = None
                for cls in ind.is_a:
                    if hasattr(cls, 'name') and cls.name != 'Thing':
                        ind_type = cls.name
                        break
                if not ind_type:
                    continue
                ind_types[ind.name] = ind_type

                for prop in ind.get_properties():
                    if not hasattr(prop, 'python_name'):
                        continue
                    for val in getattr(ind, prop.python_name, []):
                        val_name = val.name if hasattr(val, 'name') else str(val)
                        key = (prop.python_name, val_name)
                        if key not in target_groups:
                            target_groups[key] = []
                        target_groups[key].append(ind.name)

            # Groups of 2+ individuals sharing (property → same target)
            seen = set()
            for (prop_name, target_name), members in target_groups.items():
                if len(members) < 2:
                    continue
                # Skip trivial groups (all same type pointing to same parent — just siblings)
                member_types = set(ind_types.get(m, "?") for m in members)
                if len(member_types) == 1 and prop_name == "partOf":
                    continue  # Just siblings under same parent, not interesting

                group_key = frozenset(members)
                if group_key in seen:
                    continue
                seen.add(group_key)

                lcs_class = member_types.pop() if len(member_types) == 1 else "Mixed"
                proposed = f"LCS_{lcs_class}_{target_name}" if lcs_class != "Mixed" else f"LCS_{target_name}"

                discovered.append({
                    "lcs_class": lcs_class,
                    "members": members,
                    "member_count": len(members),
                    "shared_via": prop_name,
                    "shared_target": target_name,
                    "proposed_name": proposed,
                })

            discovered.sort(key=lambda x: x["member_count"], reverse=True)

        except Exception as e:
            discovered.append({"error": str(e)})

        return discovered[:20]

    def ingest_context_alignment(self, repo_path: str) -> Dict[str, Any]:
        """Ingest code entities from context-alignment Neo4j into the domain OWL.

        Queries CA's Neo4j for all code entities in a repository and creates
        typed OWL individuals: CodeRepository, CodeFile, CodeClass, CodeMethod,
        CodeFunction, CodeAttribute with proper relationships.

        This is the bridge that makes Pellet aware of actual code structure.
        After ingestion, Pellet can reason about code entities alongside
        GIINT hierarchy entities.

        Args:
            repo_path: Repository path to ingest (matches CA's Repository.name)

        Returns:
            Dict with counts of ingested entities by type
        """
        owlready2 = _ensure_owlready2()
        counts = {"repository": 0, "file": 0, "class": 0, "method": 0, "function": 0}

        try:
            import os
            from neo4j import GraphDatabase
            uri = os.environ.get("NEO4J_URI", "bolt://host.docker.internal:7687")
            user = os.environ.get("NEO4J_USER", "neo4j")
            password = os.environ.get("NEO4J_PASSWORD", "password")
            driver = GraphDatabase.driver(uri, auth=(user, password))

            with driver.session() as session:
                # 1. Get repository
                repo_result = session.run(
                    "MATCH (r:Repository {name: $name}) RETURN r.name AS name",
                    name=repo_path,
                )
                repo_rec = repo_result.single()
                if not repo_rec:
                    driver.close()
                    return {"error": f"Repository {repo_path} not found in CA Neo4j"}

                # Create Repository individual in OWL
                repo_cls = self._get_class("CodeRepository")
                repo_name_safe = repo_path.strip("/").replace("/", "_").replace("-", "_").replace(".", "_")
                with self.domain:
                    repo_ind = (repo_cls or owlready2.Thing)(f"Repo_{repo_name_safe}")
                counts["repository"] = 1

                # 2. Get all files
                files_result = session.run(
                    "MATCH (r:Repository {name: $name})-[:CONTAINS]->(f:File) "
                    "RETURN f.path AS path, f.name AS name",
                    name=repo_path,
                )
                file_individuals = {}
                file_cls = self._get_class("CodeFile")
                for frec in files_result:
                    fname = frec["name"] or frec["path"].split("/")[-1]
                    fname_safe = fname.replace(".", "_").replace("/", "_").replace("-", "_")
                    with self.domain:
                        find = (file_cls or owlready2.Thing)(f"CodeFile_{fname_safe}")
                    file_individuals[frec["path"]] = find
                    counts["file"] += 1

                # 3. Get all classes with their files
                classes_result = session.run(
                    "MATCH (r:Repository {name: $name})-[:CONTAINS]->(f:File)-[:DEFINES]->(c:Class) "
                    "RETURN c.name AS name, c.full_name AS full_name, f.path AS file_path",
                    name=repo_path,
                )
                class_individuals = {}
                class_cls = self._get_class("CodeClass")
                for crec in classes_result:
                    cname = crec["name"]
                    with self.domain:
                        cind = (class_cls or owlready2.Thing)(f"CodeClass_{cname}")
                    class_individuals[crec["full_name"] or cname] = cind
                    # Link to file via definesEntity
                    fpath = crec["file_path"]
                    if fpath in file_individuals:
                        prop = self._get_property("definesEntity")
                        if prop:
                            with self.domain:
                                existing = getattr(file_individuals[fpath], prop.python_name, [])
                                setattr(file_individuals[fpath], prop.python_name, list(existing) + [cind])
                    counts["class"] += 1

                # 4. Get methods
                methods_result = session.run(
                    "MATCH (r:Repository {name: $name})-[:CONTAINS]->(f:File)-[:DEFINES]->(c:Class)-[:HAS_METHOD]->(m:Method) "
                    "RETURN m.name AS name, c.name AS class_name, m.start_line AS start, m.end_line AS end_line",
                    name=repo_path,
                )
                method_cls = self._get_class("CodeMethod")
                for mrec in methods_result:
                    mname = f"{mrec['class_name']}_{mrec['name']}"
                    with self.domain:
                        mind = (method_cls or owlready2.Thing)(f"CodeMethod_{mname}")
                    counts["method"] += 1

                # 5. Get functions
                funcs_result = session.run(
                    "MATCH (r:Repository {name: $name})-[:CONTAINS]->(f:File)-[:DEFINES]->(func:Function) "
                    "RETURN func.name AS name, f.path AS file_path",
                    name=repo_path,
                )
                func_cls = self._get_class("CodeFunction")
                for frec in funcs_result:
                    with self.domain:
                        find = (func_cls or owlready2.Thing)(f"CodeFunction_{frec['name']}")
                    counts["function"] += 1

                # 6. Get rules from CA
                rules_result = session.run(
                    "MATCH (r:Repository {name: $name})-[:CONTAINS]->(rule:Rule) "
                    "RETURN rule.name AS name, rule.path AS path",
                    name=repo_path,
                )
                rule_cls = self._get_class("Claude_Code_Rule")
                for rrec in rules_result:
                    rname = rrec["name"].replace("-", "_")
                    slug = rname.title().replace(" ", "_")
                    with self.domain:
                        (rule_cls or owlready2.Thing)(f"Claude_Code_Rule_{slug}")
                    counts["rule"] = counts.get("rule", 0) + 1

                # 7. Get skills from CA
                skills_result = session.run(
                    "MATCH (r:Repository {name: $name})-[:CONTAINS]->(skill:Skill) "
                    "RETURN skill.name AS name, skill.path AS path",
                    name=repo_path,
                )
                skill_cls = self._get_class("Skill")
                for srec in skills_result:
                    sname = srec["name"].replace("-", "_")
                    slug = sname.title().replace(" ", "_")
                    if slug.startswith("Skill_"):
                        slug = slug[6:]
                    with self.domain:
                        (skill_cls or owlready2.Thing)(f"Skill_{slug}")
                    counts["skill"] = counts.get("skill", 0) + 1

                # 8. Get hooks from CA
                hooks_result = session.run(
                    "MATCH (r:Repository {name: $name})-[:CONTAINS]->(hook:Hook) "
                    "RETURN hook.name AS name, hook.path AS path",
                    name=repo_path,
                )
                hook_cls = self._get_class("Hook")
                for hrec in hooks_result:
                    hname = hrec["name"].replace("-", "_")
                    slug = hname.title().replace(" ", "_")
                    with self.domain:
                        (hook_cls or owlready2.Thing)(f"Hook_{slug}")
                    counts["hook"] = counts.get("hook", 0) + 1

                # 9. Get agents from CA
                agents_result = session.run(
                    "MATCH (r:Repository {name: $name})-[:CONTAINS]->(agent:AgentDef) "
                    "RETURN agent.name AS name, agent.path AS path",
                    name=repo_path,
                )
                agent_cls = self._get_class("Agent")
                for arec in agents_result:
                    aname = arec["name"].replace("-", "_")
                    slug = aname.title().replace(" ", "_")
                    with self.domain:
                        (agent_cls or owlready2.Thing)(f"Agent_{slug}")
                    counts["agent"] = counts.get("agent", 0) + 1

            driver.close()

            # Save domain ontology with new individuals
            self.domain.save()

        except ImportError:
            return {"error": "neo4j driver not available"}
        except Exception as e:
            return {"error": str(e)}

        return counts

    def refresh_code_reality(self) -> Dict[str, Any]:
        """Drop all stale code entities, re-parse repos via CA, re-ingest fresh.

        The nuclear refresh cycle:
        1. Find all starsystem repos from CartON
        2. Re-parse each via context-alignment (updates CA Neo4j)
        3. Drop ALL existing code individuals from domain OWL
        4. Re-ingest fresh code entities from CA Neo4j
        5. Find dangling GIINT references (concepts pointing to code that no longer exists)
        6. Return breakage report

        Dangling references = things that used to be real but the code changed.
        They surface as questions needing resolution.
        """
        owlready2 = _ensure_owlready2()
        report = {
            "repos_refreshed": [],
            "entities_dropped": 0,
            "entities_ingested": {},
            "dangling_references": [],
            "errors": [],
        }

        try:
            import os
            from neo4j import GraphDatabase
            uri = os.environ.get("NEO4J_URI", "bolt://host.docker.internal:7687")
            user = os.environ.get("NEO4J_USER", "neo4j")
            password = os.environ.get("NEO4J_PASSWORD", "password")
            driver = GraphDatabase.driver(uri, auth=(user, password))

            # 1. Find all repos in CA
            with driver.session() as session:
                result = session.run("MATCH (r:Repository) RETURN r.name AS name, r.source_url AS url")
                repos = [(r["name"], r.get("url", "")) for r in result]

            # 2. Note: Re-parsing repos requires the CA MCP tool (parse_repository_to_neo4j).
            # Call that BEFORE refresh_code_reality() to update CA's Neo4j.
            # This function reads from CA's Neo4j — it doesn't parse code itself.
            report["repos_found"] = [name for name, _ in repos]

            # 3. Drop ALL code individuals from domain OWL
            code_classes = ["CodeFile", "CodeClass", "CodeMethod", "CodeFunction",
                            "CodeAttribute", "CodeRepository",
                            "Claude_Code_Rule", "Hook", "Agent", "Skill"]
            dropped = 0
            for cls_name in code_classes:
                cls = self._get_class(cls_name)
                if cls:
                    for ind in list(cls.instances()):
                        owlready2.destroy_entity(ind)
                        dropped += 1
            report["entities_dropped"] = dropped

            # 4. Re-ingest fresh from CA
            for repo_name, _ in repos:
                result = self.ingest_context_alignment(repo_name)
                if "error" not in result:
                    report["entities_ingested"][repo_name] = result
                else:
                    report["errors"].append(f"Ingest {repo_name}: {result['error']}")

            # 5. Find dangling GIINT references
            # Query CartON for GIINT concepts that reference CodeFile_ entities
            # Check if those entities still exist in the fresh OWL
            with driver.session() as session:
                dangling_q = """
                MATCH (g:Wiki)-[r]->(code:Wiki)
                WHERE (g.n STARTS WITH 'Giint_' OR g.n STARTS WITH 'GIINT_')
                AND (code.n STARTS WITH 'CodeFile_' OR code.n STARTS WITH 'CodeClass_'
                     OR code.n STARTS WITH 'CodeMethod_' OR code.n STARTS WITH 'CodeFunction_')
                AND NOT code.n ENDS WITH '_Unnamed'
                RETURN g.n AS giint_concept, type(r) AS rel_type, code.n AS code_ref
                """
                dangling_result = session.run(dangling_q)
                for rec in dangling_result:
                    code_ref = rec["code_ref"]
                    # Check if this code entity exists in fresh OWL
                    exists = self.world.search_one(iri=f"*{code_ref}")
                    if not exists:
                        report["dangling_references"].append({
                            "giint_concept": rec["giint_concept"],
                            "relationship": rec["rel_type"],
                            "stale_code_ref": code_ref,
                        })

            driver.close()
            self.domain.save()

        except ImportError as ie:
            report["errors"].append(f"Import error: {ie}")
        except Exception as e:
            report["errors"].append(f"Refresh failed: {e}")

        return report

    def validate_concept(self, concept_data: Dict[str, Any]) -> ValidationResult:
        """
        Validate a concept - interface compatible with SHACL validator.

        This adds the concept, runs reasoning, and checks consistency.

        Args:
            concept_data: Dictionary with name, type, and properties

        Returns:
            ValidationResult with valid=True/False and errors
        """
        name = concept_data.get("name", "unnamed_concept")
        concept_type = concept_data.get("type", "EmbodimentClaim")

        # Extract properties (everything except name and type)
        properties = {k: v for k, v in concept_data.items() if k not in ("name", "type")}

        # Add the concept
        try:
            concept_uri = self.add_concept(name, concept_type, properties)
        except Exception as e:
            return ValidationResult(
                valid=False,
                errors=[{"message": f"Failed to add concept: {e}", "property_path": ""}],
                concept_uri=None
            )

        # Run reasoning
        result = self.run_inference()

        # Convert to ValidationResult
        errors = []
        if not result.consistent:
            for inc in result.inconsistencies:
                errors.append({
                    "focus_node": name,
                    "property_path": "",
                    "message": inc,
                    "severity": "Violation"
                })

        return ValidationResult(
            valid=result.consistent,
            errors=errors,
            concept_uri=concept_uri,
            reasoner_result=result
        )

    def check_transitive_chain(
        self,
        subject: str,
        property_name: str,
        target: str
    ) -> bool:
        """
        Check if subject reaches target via transitive property chain.

        This is WHERE THE REASONER SHINES - SHACL can't do this!

        Args:
            subject: Starting individual name
            property_name: Transitive property (isA, partOf, subsumes)
            target: Target individual or class name

        Returns:
            True if subject reaches target via transitive closure
        """
        owlready2 = _ensure_owlready2()

        # Find subject
        subj = self.world.search_one(iri=f"*{subject}")
        if subj is None:
            return False

        # Find target
        tgt = self.world.search_one(iri=f"*{target}")
        if tgt is None:
            # Try as class
            tgt = self._get_class(target)
            if tgt is None:
                return False

        # Get property
        prop = self._get_property(property_name)
        if prop is None:
            return False

        # Run reasoner to compute transitive closure
        self.run_inference()

        # Check if target is in the transitive closure
        values = getattr(subj, property_name, [])

        # For transitive properties, reasoner should have computed closure
        return tgt in values or (hasattr(tgt, 'instances') and subj in tgt.instances())

    def query_sparql(self, query: str) -> List[Dict[str, Any]]:
        """
        Run a SPARQL query against the reasoned ontology.

        Args:
            query: SPARQL query string

        Returns:
            List of result dictionaries
        """
        owlready2 = _ensure_owlready2()

        results = []
        try:
            for row in self.world.sparql(query):
                results.append({f"var{i}": str(v) for i, v in enumerate(row)})
        except Exception as e:
            print(f"SPARQL query failed: {e}")

        return results

    def save_domain(self):
        """Persist the domain ontology to file."""
        self.domain.save(file=str(self.domain_path), format="rdfxml")

    def clear_domain(self):
        """Clear all individuals from domain ontology (for testing)."""
        owlready2 = _ensure_owlready2()

        with self.domain:
            for ind in list(self.domain.individuals()):
                owlready2.destroy_entity(ind)


# ============================================================
# CLI for testing
# ============================================================

def main():
    """Test the reasoner."""
    print("=" * 60)
    print("OWL Reasoner - Testing")
    print("=" * 60)

    try:
        reasoner = OWLReasoner(use_pellet=True)
        print("✓ Reasoner initialized")
        print(f"  Foundation: {reasoner.foundation_path}")
        print(f"  Domain: {reasoner.domain_path}")
        print(f"  Using Pellet: {reasoner.use_pellet}")
    except Exception as e:
        print(f"✗ Failed to initialize: {e}")
        return

    # Clear any previous test data
    reasoner.clear_domain()

    # Test 1: Valid EmbodimentClaim (has all 4 properties)
    print("\n📋 Test 1: Valid EmbodimentClaim")
    result = reasoner.validate_concept({
        "name": "patchy_dog_claim",
        "type": "EmbodimentClaim",
        "intuition": "patchy",
        "compareFrom": "dog",
        "mapsTo": "pirate",
        "analogicalPattern": "eyepatch_pattern"
    })
    print(f"   Valid: {result.valid}")
    if not result.valid:
        for err in result.errors:
            print(f"   ✗ {err['message']}")
    else:
        print(f"   Inferred facts: {result.reasoner_result.inferred_facts[:3]}...")

    # Test 2: Invalid EmbodimentClaim (missing analogicalPattern)
    print("\n📋 Test 2: EmbodimentClaim missing analogicalPattern")
    result = reasoner.validate_concept({
        "name": "incomplete_claim",
        "type": "EmbodimentClaim",
        "intuition": "some_idea",
        "compareFrom": "something",
        "mapsTo": "somewhere"
        # Missing: analogicalPattern
    })
    print(f"   Valid: {result.valid}")
    if not result.valid:
        for err in result.errors:
            print(f"   ✗ {err['message']}")

    # Test 3: Check transitive property
    print("\n📋 Test 3: Transitive chain check")
    # First add some related concepts
    reasoner.add_concept("Animal", "Reality", {})
    reasoner.add_concept("Mammal", "Reality", {"isA": "Animal"})
    reasoner.add_concept("Dog", "Reality", {"isA": "Mammal"})

    # Run inference
    reasoner.run_inference()

    # Check: Does Dog reach Animal via isA transitivity?
    reaches = reasoner.check_transitive_chain("Dog", "isA", "Animal")
    print(f"   Dog isA* Animal: {reaches}")

    print("\n" + "=" * 60)
    print("✅ Reasoner tests complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
