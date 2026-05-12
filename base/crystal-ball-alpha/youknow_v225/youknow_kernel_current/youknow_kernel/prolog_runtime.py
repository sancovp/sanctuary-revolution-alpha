"""Prolog runtime wrapper for YOUKNOW.

Prolog is the outer runtime. It calls youknow() as a foreign function.
Prolog rules can be asserted at runtime — they're immediately live code.

Usage:
    from youknow_kernel.prolog_runtime import PrologRuntime

    rt = PrologRuntime()
    result = rt.validate("My_Concept is_a GIINT_Task, part_of GIINT_Deliverable_X")
    # Returns structured dict with SOUP report from Prolog's perspective

    # Add a rule at runtime — immediately executable
    rt.add_rule("needs_review(X) :- all_tasks_done(X), \\+ has_inclusion_map(X)")

    # Query
    results = rt.query("needs_review(X)")

DESIGN NOTES (Isaac, 2026-04-04):

1. CODEGEN = SIMULATION SYSTEM
   Every YOUKNOW concept compiles to a Python class via codeness_gen.
   Each class has an LLM agent embedded that simulates the entity's lifecycle
   according to its PatternOfIsA. Dog class → Dog.simulate() → Dog.wag().
   When simulation hits untyped parts, LLM is called to add code.
   EMR is fractal: EMR:[E[EMR]→M[EMR]→R[EMR]]. Progressive typing via
   SESLayer makes simulation better over time. ONT = simulation runs
   without LLM calls. Fully self-sufficient code.

2. PROLOG CONTROLS CODEGEN
   Ontology→code translation logic should be Prolog rules, not Python
   if/elif chains. Prolog defines HOW ontology maps to Python classes.
   Prolog generates Python but the LOGIC of what/when is Prolog rules.
   compiler.py's 2260 lines of Python logic → Prolog rules that output Python.

3. PELLET DETECTS NEW SUBTYPES AUTOMATICALLY
   Pellet classifies into anonymous classes for free (Skill ∩ ∃hasDescribesComponent.GIINT_Component).
   Prolog detects when anonymous classes should become named types.
   LLM provides labels when asked. YOUKNOW gives placeholder names
   (convention-based) and never blocks on naming. Renaming is async.
   Two error types: validation_error (blocks, SOUP) and new_type_request (async).

4. ONE ONTOLOGY, NOT THREE OWL FILES
   Currently: uarl.owl (foundation, loaded), starsystem.owl (loaded by Prolog),
   domain.owl (written dynamically, NOT loaded by reasoner). This is wrong.
   Should be one ontology that gets written to AND read from.
   JSON files in soup/ and ont/ dirs are shadow databases — should not exist.
   CartON is the persistence layer. YOUKNOW validates and returns results.

5. RESTRICTION VS SUBTYPE
   OWL restrictions on base class = UNIVERSAL (every instance MUST satisfy).
   Conditional logic = SUBTYPES with restrictions.
   hasDescribesComponent is NOT a restriction on Skill. It's a restriction
   on Emanation_Skill (a subtype). Scoring/reward handles "SHOULD have".

6. GRAND UNIFICATION: METACOMPILATION NOT REFACTOR
   Path to Prolog as logic backbone for CAVE/sancrev/OMNISANC:
   - Each system emits facts into Prolog as it works (observe, don't rewrite)
   - Prolog rules fire on accumulated facts across all systems
   - Prolog makes decisions none of the individual systems can make alone
   - Gradually more logic moves from Python/LLM into Prolog rules
   - Eventually Prolog IS the orchestrator, existing systems are execution substrates
   Example rules:
     should_dispatch(Agent, Task) :- has_ready_task(Task), agent_idle(Agent).
     needs_new_type(Pattern) :- concept_count(Pattern, N), N > 2, \\+ named_type(Pattern).
     simulation_ready(Concept) :- ses_depth(Concept, D), D >= 6.

7. CARTON EVOLUTION/SINKING = ONTOLOGY EVOLUTION
   CartON already has: sink (concept→concept_v1), REQUIRES_EVOLUTION marker,
   rename_concept (evolved_from/evolved_to). SOUP and ONT are the two most
   recent states of a concept's evolution history IN CARTON. The ontology
   should USE CartON's evolution machinery, not have its own.
"""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

_prolog_instance = None


def get_runtime() -> 'PrologRuntime':
    """Get or create the global PrologRuntime singleton."""
    global _prolog_instance
    if _prolog_instance is None:
        _prolog_instance = PrologRuntime()
    return _prolog_instance


class PrologRuntime:
    """Prolog runtime that wraps YOUKNOW as a foreign function."""

    def __init__(self):
        from pyswip import Prolog
        self.prolog = Prolog()
        self._owl_loaded = False
        self._register_youknow_foreign()
        self._load_base_rules()
        self._load_owl_on_init()
        self._load_rules_from_ontology()
        logger.info("PrologRuntime initialized")

    def _load_owl_on_init(self):
        """Load OWL restrictions at init so Prolog knows the schema."""
        import os
        owl_paths = [
            os.path.join(os.path.dirname(__file__), "starsystem.owl"),
        ]
        for p in owl_paths:
            if os.path.exists(p):
                count = self.load_owl_restrictions(p)
                logger.info(f"Loaded {count} OWL restrictions from {p}")
        self._owl_loaded = True

    def _register_youknow_foreign(self):
        """Register youknow() as a Prolog foreign function."""
        from pyswip import registerForeign

        def youknow_validate(statement, result):
            """Foreign function: call Python youknow() from Prolog."""
            from youknow_kernel.compiler import youknow
            # Prolog atoms come as bytes — decode to str
            statement_str = statement.decode('utf-8') if isinstance(statement, bytes) else str(statement)
            yk_result = youknow(statement_str)
            result.unify(yk_result)
            return True

        # Register as youknow_validate/2: youknow_validate(+Statement, -Result)
        registerForeign(youknow_validate, arity=2)
        logger.info("Registered youknow_validate/2 as Prolog foreign function")

    def _load_base_rules(self):
        """Load foundational Prolog rules."""
        # Basic SOUP/ONT detection from youknow result
        self.prolog.assertz('is_ont(Result) :- atom_string(Result, "OK")')
        self.prolog.assertz('is_soup(Result) :- atom_string(Result, S), sub_string(S, 0, _, _, "SOUP")')

        # Validate a statement and get structured result
        self.prolog.assertz(
            'validate(Statement, Status, Result) :- '
            'youknow_validate(Statement, Result), '
            '(is_ont(Result) -> Status = ont ; Status = soup)'
        )

        logger.info("Base Prolog rules loaded")

    def validate(self, statement: str) -> Dict[str, Any]:
        """Validate a YOUKNOW statement through Prolog.

        1. Parse statement to extract subject + relationships
        2. Assert them as Prolog facts (concept exists, has these rels)
        3. Call youknow() for full OWL/Pellet validation
        4. Assert the validation result as Prolog fact
        5. Return structured result

        This means every validation enriches Prolog's fact base.
        """
        try:
            # Call youknow through Prolog foreign function
            results = list(self.prolog.query(
                f'validate("{statement}", Status, Result)'
            ))
            if not results:
                return {"status": "error", "result": "No Prolog result"}

            status = results[0]["Status"]
            result = results[0]["Result"]
            if isinstance(status, bytes):
                status = status.decode('utf-8')
            if isinstance(result, bytes):
                result = result.decode('utf-8')

            # Assert the concept and its relationships into Prolog's fact base
            # so future Prolog queries can reason about what we've seen
            self._assert_from_statement(statement, str(status))

            # If this is a Prolog_Rule, assert the rule body into live runtime
            self._check_and_assert_rule(statement)

            return {
                "status": str(status),
                "result": str(result),
            }
        except Exception as e:
            logger.error(f"Prolog validate failed: {e}")
            from youknow_kernel.compiler import youknow
            result = youknow(statement)
            status = "ont" if result == "OK" else "soup"
            self._assert_from_statement(statement, status)
            self._check_and_assert_rule(statement)
            return {"status": status, "result": result, "fallback": True}

    def _check_and_assert_rule(self, statement: str) -> None:
        """If the statement defines a Prolog_Rule, assert its rule body into live Prolog.

        After _assert_from_statement has run, the concept's relationships are
        already in Prolog as has_rel/3 facts. Query those to find the rule body.
        """
        try:
            # Get subject from statement
            first = statement.strip().split()[0]
            if not first:
                return

            # Check if this is a Prolog_Rule (by prefix or by asserted is_a)
            is_prolog_rule = first.startswith("Prolog_Rule_")
            if not is_prolog_rule:
                results = list(self.prolog.query(
                    f'has_rel("{first}", "is_a", "Prolog_Rule")'
                ))
                is_prolog_rule = len(results) > 0
            if not is_prolog_rule:
                return

            # Get rule body from asserted facts
            safe_first = first.replace('"', '\\"')
            for pred in ["has_rule_body", "hasRuleBody"]:
                results = list(self.prolog.query(
                    f'has_rel("{safe_first}", "{pred}", Body)'
                ))
                if results:
                    body = results[0]["Body"]
                    if isinstance(body, bytes):
                        body = body.decode('utf-8')
                    body = str(body).strip()
                    # Rule bodies stored with single quotes to survive Prolog string storage
                    # Convert back to double quotes to match has_rel/3 fact format
                    body = body.replace("'", '"')
                    if body:
                        self.assert_rule_from_concept(first, body)
                        return
        except Exception as e:
            logger.debug(f"_check_and_assert_rule: {e}")

    def _assert_from_statement(self, statement: str, status: str) -> None:
        """Parse a YOUKNOW statement and assert its triples as Prolog facts."""
        try:
            parts = statement.strip().split(",")
            if not parts:
                return
            # First part: "Subject predicate Object"
            first = parts[0].strip().split()
            if len(first) < 3:
                return
            subject = first[0]
            safe_subj = subject.replace('"', '\\"')

            # Assert concept exists with its status
            self.prolog.assertz(f'concept("{safe_subj}")')
            self.prolog.assertz(f'validation_status("{safe_subj}", "{status}")')

            # Assert each triple
            for part in parts:
                tokens = part.strip().split()
                if len(tokens) >= 3:
                    pred = tokens[-2] if len(tokens) == 3 else tokens[1]
                    obj = tokens[-1]
                elif len(tokens) == 2:
                    pred = tokens[0]
                    obj = tokens[1]
                else:
                    continue
                safe_pred = pred.replace('"', '\\"')
                safe_obj = obj.replace('"', '\\"')
                self.prolog.assertz(f'has_rel("{safe_subj}", "{safe_pred}", "{safe_obj}")')
        except Exception as e:
            logger.debug(f"Could not assert statement triples: {e}")

    def inject_concept(self, name: str, relationships: Dict[str, list]) -> None:
        """Inject a concept's relationships into Prolog from external caller (e.g. add_concept).

        This lets the Prolog fact base grow as concepts are added through CartON,
        without waiting for a validate() call.
        """
        safe_name = name.replace('"', '\\"')
        self.prolog.assertz(f'concept("{safe_name}")')
        for rel_type, targets in relationships.items():
            safe_rel = rel_type.replace('"', '\\"')
            for target in targets:
                safe_target = str(target).replace('"', '\\"')
                self.prolog.assertz(f'has_rel("{safe_name}", "{safe_rel}", "{safe_target}")')
        logger.debug(f"Injected concept {name} with {sum(len(v) for v in relationships.values())} rels into Prolog")

    def add_rule(self, rule: str) -> bool:
        """Assert a new Prolog rule at runtime. Immediately executable."""
        try:
            self.prolog.assertz(rule)
            logger.info(f"Prolog rule added: {rule}")
            return True
        except Exception as e:
            logger.error(f"Failed to add Prolog rule: {e}")
            return False

    def query(self, goal: str) -> List[Dict[str, Any]]:
        """Query Prolog with a goal. Returns list of solution dicts."""
        try:
            return list(self.prolog.query(goal))
        except Exception as e:
            logger.error(f"Prolog query failed: {e}")
            return []

    def assert_fact(self, fact: str) -> bool:
        """Assert a fact into Prolog's fact base."""
        try:
            self.prolog.assertz(fact)
            return True
        except Exception as e:
            logger.error(f"Failed to assert fact: {e}")
            return False

    def retract_fact(self, fact: str) -> bool:
        """Retract a fact from Prolog's fact base."""
        try:
            list(self.prolog.query(f"retract({fact})"))
            return True
        except Exception as e:
            logger.error(f"Failed to retract fact: {e}")
            return False

    def load_owl_restrictions(self, owl_path: str) -> int:
        """Load OWL class restrictions as Prolog facts.

        For each OWL class with restrictions, asserts:
            required_rel(ClassName, PropertyName, RangeClass).

        Returns number of facts asserted.
        """
        try:
            import xml.etree.ElementTree as ET
            tree = ET.parse(owl_path)
            root = tree.getroot()
            ns = {
                'owl': 'http://www.w3.org/2002/07/owl#',
                'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
                'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
            }

            count = 0
            for cls in root.findall('.//owl:Class', ns):
                class_about = cls.attrib.get(f'{{{ns["rdf"]}}}about', '')
                class_name = class_about.replace('#', '')
                if not class_name:
                    continue

                # Find someValuesFrom restrictions
                for restriction in cls.findall('.//owl:Restriction', ns):
                    on_prop = restriction.find('owl:onProperty', ns)
                    some_from = restriction.find('owl:someValuesFrom', ns)
                    if on_prop is not None and some_from is not None:
                        prop_ref = on_prop.attrib.get(f'{{{ns["rdf"]}}}resource', '').replace('#', '')
                        range_ref = some_from.attrib.get(f'{{{ns["rdf"]}}}resource', '').replace('#', '')
                        if prop_ref and range_ref:
                            # Get label if available
                            fact = f'required_rel("{class_name}", "{prop_ref}", "{range_ref}")'
                            self.prolog.assertz(fact)
                            count += 1

            logger.info(f"Loaded {count} OWL restrictions as Prolog facts from {owl_path}")
            return count
        except Exception as e:
            logger.error(f"Failed to load OWL restrictions: {e}")
            return 0

    def _load_rules_from_ontology(self):
        """Load Prolog_Rule concepts from domain.owl into live Prolog runtime.

        Queries domain.owl for all individuals of type Prolog_Rule,
        extracts hasRuleBody, and asserts each rule into Prolog.
        Rules loaded here are LIVE FOREVER for the lifetime of this runtime.
        """
        try:
            from .owl_reasoner import OWLReasoner
            import os
            heaven_data = os.getenv("HEAVEN_DATA_DIR", "/tmp/heaven_data")
            domain_path = os.path.join(heaven_data, "ontology", "domain.owl")
            if not os.path.exists(domain_path):
                return

            reasoner = OWLReasoner(domain_owl_path=domain_path)
            count = 0
            # Search all ontologies for Prolog_Rule individuals
            for onto in [reasoner.foundation, getattr(reasoner, '_starsystem', None), getattr(reasoner, 'domain', None)]:
                if onto is None:
                    continue
                for ind in onto.individuals():
                    # Check if this individual is a Prolog_Rule
                    is_rule = any(
                        getattr(cls, 'name', '') == 'Prolog_Rule'
                        for cls in ind.is_a
                    )
                    if not is_rule:
                        continue
                    # Get rule body
                    rule_body = getattr(ind, 'hasRuleBody', None)
                    if rule_body:
                        # hasRuleBody may be a list
                        bodies = rule_body if isinstance(rule_body, list) else [rule_body]
                        for body in bodies:
                            body_str = str(body).strip()
                            # Single quotes → double quotes to match has_rel/3 format
                            body_str = body_str.replace("'", '"')
                            if body_str:
                                try:
                                    self.prolog.assertz(body_str)
                                    count += 1
                                    logger.info(f"Loaded Prolog rule from ontology: {ind.name}: {body_str[:80]}")
                                except Exception as e:
                                    logger.error(f"Failed to assert rule {ind.name}: {e}")
            logger.info(f"Loaded {count} Prolog rules from ontology")
        except Exception as e:
            logger.warning(f"Could not load Prolog rules from ontology: {e}")

    def assert_rule_from_concept(self, name: str, rule_body: str) -> bool:
        """Assert a Prolog rule from a newly created Prolog_Rule concept.

        Called by add_concept when a Prolog_Rule_ concept enters the system.
        The rule is immediately live in the Prolog runtime — forever.
        """
        try:
            self.prolog.assertz(rule_body)
            safe_name = name.replace('"', '\\"')
            self.prolog.assertz(f'concept("{safe_name}")')
            self.prolog.assertz(f'has_rel("{safe_name}", "is_a", "Prolog_Rule")')
            self.prolog.assertz(f'has_rel("{safe_name}", "has_rule_body", "{rule_body.replace(chr(34), chr(39))}")')
            logger.info(f"Prolog rule asserted LIVE from concept {name}: {rule_body[:80]}")
            return True
        except Exception as e:
            logger.error(f"Failed to assert rule from concept {name}: {e}")
            return False

    def load_carton_state(self, max_concepts: int = 1000) -> int:
        """Load CartON concepts as Prolog facts.

        For each concept, asserts:
            concept(Name).
            is_a(Name, Type).
            part_of(Name, Parent).

        Returns number of facts asserted.
        """
        try:
            import os
            from neo4j import GraphDatabase
            uri = os.environ.get("NEO4J_URI", "bolt://host.docker.internal:7687")
            user = os.environ.get("NEO4J_USER", "neo4j")
            pw = os.environ.get("NEO4J_PASSWORD", "password")
            driver = GraphDatabase.driver(uri, auth=(user, pw))

            count = 0
            with driver.session() as session:
                # Load concepts with their is_a and part_of
                result = session.run(
                    "MATCH (c:Wiki) "
                    "OPTIONAL MATCH (c)-[:IS_A]->(t:Wiki) "
                    "OPTIONAL MATCH (c)-[:PART_OF]->(p:Wiki) "
                    "RETURN c.n AS name, collect(DISTINCT t.n) AS types, collect(DISTINCT p.n) AS parents "
                    "LIMIT $limit",
                    limit=max_concepts,
                )
                for record in result:
                    name = record["name"]
                    if not name:
                        continue
                    # Escape quotes in names for Prolog
                    safe_name = name.replace('"', '\\"')
                    self.prolog.assertz(f'concept("{safe_name}")')
                    count += 1
                    for t in record["types"]:
                        if t:
                            safe_t = t.replace('"', '\\"')
                            self.prolog.assertz(f'is_a("{safe_name}", "{safe_t}")')
                    for p in record["parents"]:
                        if p:
                            safe_p = p.replace('"', '\\"')
                            self.prolog.assertz(f'part_of("{safe_name}", "{safe_p}")')

            driver.close()
            logger.info(f"Loaded {count} CartON concepts as Prolog facts")
            return count
        except Exception as e:
            logger.error(f"Failed to load CartON state: {e}")
            return 0
