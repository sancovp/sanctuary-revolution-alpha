# Questions for SOMA Agent — 2026-04-18

## Context: YOUKNOW's Compiler Is Fundamentally Broken

Today (Apr 18) we traced the ENTIRE youknow() callgraph — every single line of compiler.py (2216 lines), cat_of_cat.py (1014), derivation.py (506), hyperedge.py (460), owl_reasoner.py (906), griess_constructor.py (671), universal_pattern.py (556), system_type_validator.py (579), uarl_validator.py (key sections), daemon.py (170), owl_server.py (119), and uarl.owl (2460 lines, 186 restriction axioms).

The full bug report is in CartON: `Bug_Youknow_Compiler_Disconnected_From_Core_Sentence_Apr18`. Read it with `get_concept("Bug_Youknow_Compiler_Disconnected_From_Core_Sentence_Apr18")`.

### What YOUKNOW Is Supposed To Do (Isaac's exact words)

Every label X claims to exist by having a subgraph of triples. Every triple must be a valid primitive claim. Every primitive claim must ITSELF have a subgraph that instantiates the complete core sentence for ITS label. If ANY subclaim is SOUP, X is SOUP too. X is ONT only when every subclaim recursively has the complete core sentence shape.

The core sentence (from uarl.owl):

```
from Reality and is(Reality):
primitive_is_a IS a type of is_a → is_a embodies part_of →
part_of (as triple) entails instantiates → instantiates necessitates
produces → part_of manifests produces → produces reifies as
pattern_of_is_a → pattern_of_is_a produces programs →
programs instantiates part_of Reality
```

For is_a: X is_a Y requires X to have AS PART OF ITSELF every single part required to instantiate Y. For instantiates: X must HAVE parts that are implementations of the constraint patterns of Y. They are deeply tied: having the parts abstractly produces the pattern that makes instantiates true.

OWL relationships are NEVER declared. They are DERIVATIONS ONLY that get RESOLVED from primitive subgraphs. Something has a subgraph of primitive claims, each primitive claim has its own admissibility graph. Primitives roll up / resolve into higher-level terms that TOKENIZE the subgraph.

NOTHING is allowed to exist without having a subgraph of primitives and each primitive has logic (a subgraph that it itself requires). Everything must recursively error back at you until you build the subgraph that admits the claim.

The compiler CALLS Pellet, SHACL, and OWL to do this. OWL is the language. Pellet is the reasoner (consistency checker). SHACL validates structure. The compiler orchestrates all three to verify recursive core sentence decomposition.

### What YOUKNOW Actually Does (The Broken State)

1. **cat_of_cat.py was removed last week but is still imported at compiler.py line 492.** Every `get_cat()` call throughout the compiler depends on dead code. The entire derivation chain (L0-L6), hyperedge validation, spiral building, and chain completeness checking all use cat_of_cat.

2. **The admission gate is disconnected.** compiler.py line 655: `admit_to_ont = pellet_says_ont`. pellet_says_ont checks if Pellet INFERRED `is_a Reality` (uarl_validator.py line 1097-1103). But the OWL has NO axiom that causes Pellet to infer Reality membership. So pellet_says_ont is ALWAYS False. NOTHING ever gets admitted to ONT through the compiler.

3. **DerivationValidator HAS the recursive check but it's ignored.** derivation.py L4 (`for_promotion`) checks all is_a/part_of/produces targets exist and trace to Cat_of_Cat. L6 (`for_programs`) checks all targets have complete derivation chains via SES typed depth. This IS the recursive subgraph check. But the result (derivation_state at line 521) is used only for EMR state and diagnostics — NOT for the admission decision.

4. **uarl_validator._build_restriction_index only extracts someValuesFrom restrictions** (line 363). All minCardinality restrictions (which is what Skill, Bug, GIINT types use) are invisible to it. system_type_validator.py correctly parses both — but it's a parallel system.

5. **Validation checks property PRESENCE, not recursive target VALIDITY.** uarl_validator._validate_chain line 466: if `val is not None` → `continue` (restriction satisfied). It never checks if the VALUE is itself a valid ONT concept with its own complete subgraph.

6. **compiler.py line 53 says it explicitly:** "PARTIAL: Reasoner wired for SHACL but Pellet sync_reasoner not called during compilation (only structural SHACL, not full inference)"

7. **The OWL has 186 restriction axioms** including full Skill template (22+ restrictions), Cat/Domain/Aut/EWS foundations, GIINT hierarchy, Bug, Claude_Code_Rule. The axioms exist but the compiler doesn't use them for recursive verification.

### The Core Problem In One Sentence

The YOUKNOW compiler computes the recursive derivation level (L0-L6) but throws it away at the admission gate, which instead asks Pellet a question Pellet can never answer (infer is_a Reality) because the OWL has no axiom for that inference. The recursive core sentence verification that Isaac designed exists as dead logic in derivation.py while the actual gate is a broken Pellet query that always returns False.

## Questions

### Q1: Can SOMA's Prolog perform the recursive core sentence verification?

The core requirement: for every label X, recursively verify that X's subgraph decomposes into primitive claims that each instantiate the core sentence. If any subclaim is SOUP (doesn't have complete core sentence shape), X is SOUP.

SOMA already has:
- Triple graph for storing claims
- Convention rules that check restrictions
- CoreRequirements that block on structural violations
- solve/3 backward chaining
- deduce_validation_status (code/soup/unvalidated)

Can these be composed to implement the recursive core sentence check? Or is something fundamentally missing from SOMA's architecture?

### Q2: What does "instantiates the core sentence" look like as a Prolog query?

The core sentence has specific steps: is_a → embodies → part_of → instantiates → produces → reifies → pattern_of_is_a → programs. For a label X to be ONT, its subgraph must contain triples that map to each of these steps. What would the Prolog predicate look like that checks "does label X's subgraph instantiate the core sentence"?

### Q3: How would SOMA handle the recursive descent?

For X is_a Y: X must have all parts required by Y. Each part must ITSELF have a complete core sentence. So checking X requires checking each of X's parts, which requires checking each of THEIR parts, etc.

Does SOMA's triple graph + convention rules support this recursive descent? Or does the ephemeral nature of the triple graph (no persistence, no Neo4j bridge) prevent checking whether referenced concepts have been previously validated?

### Q4: The "response to questions" file (4_17_response_to_questions.md) says SOMA replaces YOUKNOW entirely. Given what we found today about YOUKNOW being fundamentally broken, what is the HONEST assessment of how far SOMA is from being able to replace it?

The honest audit at the bottom of that file lists 8 gaps (no BLOCK mechanism, no structural type-mismatch check, no Neo4j bridge, no GIINT restrictions, solve/3 not wired to conventions, no persistence, SOMA still separate package, SOUP/CODE distinction not using type field). How many of those are still true today? Have any been fixed since Apr 17?

### Q5: If we decided TODAY to make SOMA the validation layer instead of trying to fix YOUKNOW, what is the minimum work to get recursive core sentence verification running through SOMA's Prolog?

Not the 30-minute plan from Round 4 (that was for basic CoreRequirement validation). This is the FULL recursive check: every claim decomposes to core sentence instances, every subclaim is recursively verified, SOUP propagates upward. What does that take?

### Q6: Is the core sentence itself representable as Prolog rules?

The core sentence is a specific sequence of derivation steps. Can each step be a Prolog clause that, given a concept, checks if that step is satisfied? And can the full core sentence check be a conjunction of all steps? Like:

```prolog
core_sentence_satisfied(X) :-
    has_primitive_isa(X),
    isa_embodies_partof(X),
    partof_entails_instantiates(X),
    instantiates_necessitates_produces(X),
    produces_reifies_pattern_of_isa(X),
    pattern_of_isa_produces_programs(X),
    programs_instantiates_partof_reality(X).
```

And then the recursive check is:

```prolog
is_ont(X) :-
    core_sentence_satisfied(X),
    forall(
        subclaim(X, Sub),
        is_ont(Sub)
    ).
```

Is this the right shape? What's wrong with it? What would actually work?

### Q7: The OWL has 186 restriction axioms (Cat requires objects+morphisms+identity+composition, Skill requires 22+ properties, etc.). These ARE the "what parts are required" definitions. Can SOMA load these restrictions and use them in the recursive check?

The 4_17 answers said `class_restrictions_snake()` exists in utils.py but nobody calls it to assert required_restriction facts. Is this still the case? If SOMA could load all OWL restrictions as Prolog facts, would that give it enough information to perform the recursive core sentence check?

File: /home/GOD/gnosys-plugin-v2/base/soma-prolog/4_18_questions_youknow_core_sentence.md

## Relationships
- IS_A: File
- INSTANTIATES: File_Template