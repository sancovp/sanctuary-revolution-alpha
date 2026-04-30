# SOMA Universal Patterns

This is the contract for what SOMA's foundation must support. Every
"feature" in SOMA is one of these patterns. Every domain-specific thing
(SOPs, philosophy essays, employees, mistakes, predictions, etc.) is a
USE of these patterns at runtime, entered through `add_event`.

If something cannot be done by composing these patterns, the foundation
is incomplete and the missing pattern must be added here BEFORE any
code is written. The Prolog and Python in this repo may only implement
patterns that appear in this list.

## The contract

1. There is exactly one entrypoint: **add_event**.
2. An event is `{source, observations}`. Each observation is a typed
   key-value pair where the type is either a primitive programming
   type (str/int/float/bool/list/dict, lifted into OWL as
   StringValue/IntValue/FloatValue/BoolValue/ListValue/DictValue) or
   an OWL kind (a class that exists or is being declared in this same
   event).
3. Every "single thing" stored by SOMA is typed. There are no untyped
   nodes, no untyped edges. Either the type is a primitive or it is
   an OWL class. Nothing else is allowed.
4. The OWL ontology is the source of truth. The Prolog runtime is the
   reasoning layer that walks the OWL graph. Pellet is the reasoner
   that classifies and checks consistency. The Python utils.py is the
   only bridge to owlready2 — it has no logic of its own beyond
   reading and writing OWL.
5. Every pattern below is invoked by submitting an event whose
   observations have a specific shape. The shape is universal: it
   names no domain entity. The observation values are arbitrary user
   data, typed.

## Patterns

### 1. PLAIN_OBSERVATION (already built)

**Purpose**: Record that something happened.

**Observation shape**: Any number of `{key, value, type}` triples
where each type is one of the 6 primitive TypedValue subclasses.

**OWL effect**: Creates an `Event` individual. For each observation,
creates an `Observation` individual linked via `hasObservation`,
sets `hasKey` to the literal key, sets `hasValue` to a `TypedValue`
individual of the right subtype, attaches the literal value as
`rdfs:label` on the TypedValue individual.

**Pellet**: Runs after the writes. Confirms consistency.

**Prolog**: No rule body required. The pattern is the bottom layer.

**Status**: BUILT (today).

---

### 2. CLASS_DECLARATION (not yet built)

**Purpose**: Introduce a new OWL class into the ontology so that
future observations can be typed by it.

**Observation shape**: A single observation with a known key like
`declares_class`. Its value is a structure (dict_value) containing
at minimum: the new class name, the parent class name (which must
already exist), and optionally a list of restrictions.

**OWL effect**: Creates a new `owl:Class` with the given name as a
subclass of the named parent. If restrictions are provided in the
same event, those are added to the new class via the
RESTRICTION_DECLARATION pattern below.

**Pellet**: Runs after the writes. Catches inconsistencies (e.g.
the new class is disjoint with one of its declared parents,
restrictions cannot be satisfied, etc.). The event response carries
Pellet's verdict.

**Prolog**: A universal rule fires when a class is declared,
asserting that the class exists and is queryable via `owl_class/1`.
No domain knowledge required.

**Why universal**: The mechanism does not name `Essay`, `SOP`,
`PhilosophyEssay`, etc. It names "the act of declaring a new class
of any kind, in any domain, by any user."

**Status**: NOT BUILT.

---

### 3. RESTRICTION_DECLARATION (not yet built)

**Purpose**: Add an OWL restriction to an existing class so that
Pellet enforces it on every individual claimed to be of that class.

**Observation shape**: One observation with key `declares_restriction`
whose value is a structure naming: the target class, the property
the restriction is on, the restriction kind (some/only/exactly/min/
max/has_value), and the cardinality or filler.

**OWL effect**: Adds the restriction to the target class. Future
individuals claimed as that class must satisfy it or Pellet will
either refuse to classify them or report an inconsistency.

**Pellet**: Runs after the writes. Re-checks every existing individual
of the target class. If any existing individual now violates the new
restriction, the event response carries the violation list.

**Prolog**: A universal rule fires when a restriction is added,
allowing rules loaded from OWL to query restrictions via
`owl_restriction/3`.

**Status**: NOT BUILT.

---

### 4. PROPERTY_DECLARATION (not yet built)

**Purpose**: Introduce a new OWL property (object or data) so that
future restrictions and observations can refer to it.

**Observation shape**: One observation with key `declares_property`
whose value is a structure naming: the property name, whether it is
an object property or a data property, the domain class, the range
class (or xsd type), and whether it is functional/transitive/etc.

**OWL effect**: Creates the property with the given characteristics.

**Pellet**: Runs to confirm the new property does not break
consistency.

**Prolog**: Universal `owl_property/3` queries pick it up.

**Status**: NOT BUILT.

---

### 5. INSTANCE_DECLARATION (not yet built — extension of pattern 1)

**Purpose**: Create an OWL individual of a user-declared class (not
just one of the 6 primitive TypedValue subclasses).

**Observation shape**: A `{key, value, type}` triple where `type` is
the snake_case name of any class that exists in the OWL — including
classes declared via pattern 2 in this same event or a previous
event.

**OWL effect**: Creates an individual of the named class instead of
falling back to a primitive TypedValue subclass. The literal value
is attached as `rdfs:label` (same convention as primitives).

**Pellet**: Runs to classify the new individual. If the literal value
fails any of the class's restrictions, the event response carries
the failure with the offending restriction named.

**Prolog**: No new rule needed beyond pattern 1.

**Why universal**: The current `add_observation_individual` hardcodes
the typed value class to one of the 6 primitive subclasses. Pattern
5 generalizes this to "any class," which is the actual universal.
Pattern 1 becomes a special case where the type happens to be
primitive.

**Status**: NOT BUILT (current build only handles primitives).

---

### 6. PROLOG_RULE_DECLARATION (not yet built)

**Purpose**: Add a new Prolog rule to the live runtime AND persist it
in the OWL as a `Prolog_Rule` individual so that future boots reload
it.

**Observation shape**: One observation with key `declares_rule` whose
value is a structure naming: the rule head, the rule body (as a
string of Prolog source), and a description.

**OWL effect**: Creates a `Prolog_Rule` individual whose `hasRuleHead`
and `hasRuleBody` carry the strings. The Prolog runtime parses the
body and `assertz`'s it into the live runtime.

**Pellet**: Runs after creation but does not check the rule body
(Pellet does not understand Prolog). The event response carries
whether the rule parsed and asserted successfully.

**Prolog**: A universal predicate `load_prolog_rules_from_owl/0`
walks every `Prolog_Rule` individual at boot time and asserts each
into the runtime. The same predicate can be called during ingest to
load rules declared in the current event.

**Why universal**: The mechanism does not name any specific rule. It
names "an event that declares a Prolog rule of any shape, in any
domain, by any user." Domain rules — "missing SOP detection,"
"philosophy content check," "Alice's mistake pattern" — are all
just `Prolog_Rule` individuals stored in the OWL.

**Status**: NOT BUILT.

---

### 7. QUERY (not yet built)

**Purpose**: Ask the system a question. The system's answer comes
from the meta-interpreter walking the loaded rules and the OWL
state.

**Observation shape**: One observation with key `query` whose value
is a Prolog goal as a string. (Or a higher-level question shape that
the foundation translates to a Prolog goal.)

**OWL effect**: Creates a `Query` individual recording the question
and timestamp. The result is recorded as a `Query_Result` individual
linked to the query.

**Pellet**: Runs before the query so the world is consistent.

**Prolog**: The meta-interpreter (`mi_core.pl solve/3`) runs the
goal and produces either a proof tree (success) or a failure-as-data
structure (what's missing and why). The result is recorded in OWL
and returned in the event response.

**Why universal**: Every question — "could we write a philosophy
essay about X," "why is process P slow," "what does Alice do wrong"
— is a Prolog goal asked through this same pattern.

**Status**: NOT BUILT (mi_core.pl exists but is not invoked from the
event path).

---

### 8. PREDICTION_DECLARATION (not yet built)

**Purpose**: Record a hypothesis about what should happen given a
proposed change. The system can later compare the prediction against
new observations and report whether it held.

**Observation shape**: One observation with key `declares_prediction`
whose value is a structure naming: the proposed change, the
predicted outcome, the predicted metric, the verification rule (a
Prolog goal that determines whether the prediction came true).

**OWL effect**: Creates a `Prediction` individual. Records the
proposed change, the predicted outcome, the verification rule.
Status starts as `pending`.

**Pellet**: Runs to confirm the prediction is well-formed.

**Prolog**: A universal rule fires periodically (or on each new
event) that re-checks pending predictions against the new state. If
the verification rule succeeds, the prediction's status flips to
`confirmed`; if it fails after a deadline, `disconfirmed`.

**Status**: NOT BUILT.

---

### 9. DISJOINTNESS_DECLARATION (not yet built)

**Purpose**: Declare that two classes have no shared instances.

**Observation shape**: One observation with key `declares_disjoint`
whose value names the two classes.

**OWL effect**: Adds an `owl:disjointWith` axiom. Any individual
later classified as both (directly or through inference) causes
Pellet to report inconsistency.

**Status**: NOT BUILT (but `owl_disjoint/2` query rule exists).

---

### 10. EQUIVALENCE_DECLARATION (not yet built)

**Purpose**: Declare that two classes have the same set of instances.

**Observation shape**: One observation with key `declares_equivalent`
whose value names the two classes.

**OWL effect**: Adds an `owl:equivalentClass` axiom. Pellet treats
instances of one as instances of the other.

**Status**: NOT BUILT.

---

### 11. CODE_INSPECTION_RULE (not yet built — load-bearing)

**Purpose**: Make the foundation incapable of accepting changes to
itself that violate the architecture. Every proposed change to the
SOMA codebase (from me or anyone) is itself an event whose handling
runs the universal coding rules over the proposed change and either
admits or rejects it.

**Observation shape**: One observation with key `proposes_change`
whose value is a structure naming: the file, the diff, the
intent. Plus optional observations naming the architectural patterns
the change claims to use.

**OWL effect**: Creates a `Proposed_Change` individual. The
verification step walks every `Coding_Rule` individual in the OWL
and runs each one against the proposed change. If any rule rejects
the change, the event response says no with the offending rule
named.

**Pellet**: Runs to confirm the change does not introduce
inconsistencies in the architecture itself.

**Prolog**: Universal predicate `check_proposed_change(Change,
Verdict)` walks all `Coding_Rule` and `Architectural_Pattern`
individuals and returns a verdict. The Coding_Rules themselves are
data — entered through pattern 6 (PROLOG_RULE_DECLARATION) and
pattern 2 (CLASS_DECLARATION).

**Why this is load-bearing**: This is the pattern that makes the
foundation unable to be contaminated. Without it, every other
pattern can be misused without consequence and the architecture
drifts. Isaac said this had to come first; I built nothing instead.

**Status**: NOT BUILT.

---

## Patterns that are aspirational (mentioned for completeness)

- **SES_LAYER computation**: a number attached to each user-declared
  class measuring how many layers of refinement separate it from a
  primitive TypedValue. Computed from the class hierarchy after the
  fact. Not part of the foundation mechanism.
- **Y_MESH**: the loop in which Prolog detects gaps and calls an LLM
  internally (via Janus) to fill them, then validates the result
  through patterns 6 and 11 before persisting. Built on top of the
  patterns above.
- **CONTEXT_ALIGNMENT integration**: pull source code into the OWL
  as `Code_Entity` individuals so Prolog rules can reason about the
  codebase the user is building. A separate set of patterns layered
  on top of patterns 1-11.
- **CULTURE_RULE pattern**: a higher-order pattern composed of
  prediction, rule, and instance patterns to express things like
  "if Alice always checks JD before SOP, error rate drops by X."
  Composed from the universals; not its own primitive.

## What this document is

A contract. The foundation MUST implement every pattern listed in
the "Patterns" section above, and MUST NOT implement anything that
isn't either a pattern in this list or a low-level mechanism that
serves these patterns (the OWL bridge, the HTTP shell, the
meta-interpreter, the Janus binding).

If a future feature request cannot be expressed as a composition of
these patterns, the request requires this document to be amended
FIRST, with a new pattern added in the same style (purpose,
observation shape, OWL effect, Pellet behavior, Prolog behavior,
why-universal, status). Only after the amendment may code be written.

## What this document is NOT

- It is NOT a list of features SOMA has built. Most patterns here are
  marked NOT BUILT.
- It is NOT a list of domain entities. There are no SOPs, essays,
  employees, mistakes, predictions about Alice, or business rules in
  this document. Those are user data that enter at runtime through
  the patterns described here.
- It is NOT final. As Isaac corrects my understanding of the
  architecture, this document gets edited. The document is the
  source of truth for what counts as universal in SOMA; I do not
  get to add code that doesn't appear here.
