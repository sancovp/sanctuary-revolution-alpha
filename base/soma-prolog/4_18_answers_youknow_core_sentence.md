# Answers: YOUKNOW Core Sentence Questions — 2026-04-18

Answering agent: GNO.SYS (Opus 4.6)
Grounded in: Bug_Youknow_Compiler_Disconnected_From_Core_Sentence_Apr18 concept, soma_partials.pl, soma.owl, utils.py as they exist on disk today.

---

## A1: Can SOMA's Prolog perform the recursive core sentence verification?

**Yes, the architecture supports it. The predicates needed don't exist yet but nothing is fundamentally missing.**

What SOMA has today:
- `triple/3` graph — stores claims as subject-predicate-object
- `check_convention/1` — runs rules over the graph, marks unnamed_slot where required things missing
- `required_restriction/3` — seed T-box declaring what properties a type requires
- `deduce_validation_status/2` — returns soup/code based on string_value presence + unnamed_slots
- `CoreRequirement` mechanism — blocks provably wrong things with structured errors
- Bootstrap loader asserts PrologRule individuals as BOTH rule/2 data AND native clauses

What's missing for recursive core sentence:
- **A predicate `core_sentence_satisfied/1`** that checks whether a concept's subgraph contains all the core sentence steps
- **A predicate `all_subclaims_ont/1`** that recursively descends into each subclaim and checks core_sentence_satisfied on it
- **OWL restriction loading** — `class_restrictions_snake()` EXISTS in utils.py but nobody calls it to populate `required_restriction/3` from the actual OWL. The current required_restrictions are hardcoded seed facts. Loading from OWL would give SOMA the 186 restriction axioms automatically.
- **Recursive SOUP propagation** — current `deduce_validation_status` checks the concept ITSELF for string_value and unnamed_slots. It does NOT recursively check whether the concept's relationship TARGETS are also valid. Need: if `triple(X, has_Y, Z)` and `deduce_validation_status(Z, soup)`, then X is also soup.

None of these require new architecture. They're Prolog clauses that compose existing predicates.

---

## A2: What does "instantiates the core sentence" look like as a Prolog query?

The core sentence steps mapped to triple-graph checks:

```prolog
% The core sentence for label X:
% X must have primitives that trace through the full chain.

core_sentence_satisfied(X) :-
    % X claims is_a some type Y
    triple(X, is_a, Y),
    % is_a embodies part_of: X must be part_of something
    triple(X, part_of, Container),
    % part_of entails instantiates: X must instantiate some pattern
    triple(X, instantiates, Pattern),
    % instantiates necessitates produces: X must produce something
    triple(X, produces, Product),
    % produces reifies as pattern_of_is_a: what X produces
    % must be recognizable as a pattern of what X is
    triple(Product, is_a, _ProductType),
    % pattern_of_is_a produces programs: the product pattern
    % must be expressible as a program (CODE layer)
    deduce_validation_status(Product, code).
    % programs instantiates part_of Reality: the program
    % must instantiate something that is part_of the system
```

But this is the SIMPLE version. The real version needs to check that EACH of those claims (is_a, part_of, instantiates, produces) is itself recursively valid — not just present.

The real check:

```prolog
core_sentence_satisfied(X) :-
    triple(X, is_a, Y),
    triple(X, part_of, Container),
    triple(X, instantiates, Pattern),
    % Every required restriction on Y must be satisfied on X
    forall(
        required_restriction(Y, Prop, TargetType),
        (triple(X, Prop, Val), triple(Val, is_a, TargetType))
    ),
    % No values are string_value (all typed)
    \+ concept_has_soup_value(X).
```

This checks: X has the three required primitives (is_a, part_of, instantiates), all restrictions from X's type are satisfied with correctly-typed values, and nothing is untyped.

---

## A3: How would SOMA handle the recursive descent?

The recursive descent is straightforward in Prolog:

```prolog
is_ont(X) :-
    core_sentence_satisfied(X),
    forall(
        (triple(X, _Prop, Sub), Sub \= X, triple(Sub, is_a, _)),
        is_ont(Sub)
    ).
```

"X is ONT if X satisfies the core sentence AND every concept X references (that is itself a typed concept) is also ONT."

**The cycle problem:** if A references B and B references A, this infinite-loops. Standard Prolog fix: pass a visited list:

```prolog
is_ont(X) :- is_ont(X, []).

is_ont(X, Visited) :-
    \+ member(X, Visited),
    core_sentence_satisfied(X),
    forall(
        (triple(X, _Prop, Sub), Sub \= X, triple(Sub, is_a, _)),
        is_ont(Sub, [X|Visited])
    ).
```

**The ephemeral graph problem you raised:** SOMA's triple graph is ephemeral (dies when process dies). If concept Z was validated in a previous session, SOMA doesn't know that now. Two options:

(a) **Reload from Neo4j at boot** — a py_call that queries CartON for all concepts + their validation status, asserts them as triples. Then the recursive check works against the full accumulated graph. This is the Neo4j bridge that's been identified as missing.

(b) **Trust the status stored in Neo4j** — don't re-verify previously-validated concepts. Add a py_call `concept_status_in_neo4j(Name, Status)` that returns the stored status. The recursive check stops descending when it hits a concept whose Neo4j status is already `ont`.

Option (b) is simpler and more practical. The recursive descent only needs to fully verify NEW concepts; previously-verified ones are trusted by their stored status.

---

## A4: Honest assessment — how far is SOMA from replacing YOUKNOW?

The 8 gaps from the Apr 17 audit. Current status today (Apr 18):

| Gap | Apr 17 | Apr 18 |
|---|---|---|
| 1. SOUP/CODE doesn't use type field | **FIXED.** `concept_has_soup_value/1` checks `triple(V, is_a, string_value)`. `deduce_validation_status` uses it. Verified with tests. |
| 2. No BLOCK/REJECT mechanism | **FIXED.** CoreRequirements fire via `fire_all_deduction_chains_py` in core.py. Valid hierarchy passes, invalid blocks with structured error + remedy. Verified. |
| 3. No structural type-mismatch check | **FIXED.** GIINT CoreRequirement individuals in soma.owl check `not((triple(C, is_a, giint_component), triple(C, part_of, P), not(triple(P, is_a, giint_feature))))`. Valid passes, invalid fires. |
| 4. No Prolog↔Neo4j bridge | **STILL MISSING.** No py_call to query CartON's Neo4j. Prolog can't check if a referenced concept exists in persistent storage. |
| 5. No GIINT required_restrictions | **PARTIALLY FIXED.** GIINT CoreRequirements exist for parent-type validation. But `required_restriction/3` facts for GIINT types (what properties they need) are not loaded from OWL — still hardcoded seed for process/template_method only. |
| 6. solve/3 not wired to conventions | **WORKAROUND.** solve/3 breaks after mi_add_event (janus state corruption). Fix: bootstrap loader dual-asserts as native clauses + rule/2. fire_all_deduction_chains uses call/1 instead of solve_succeeds. Works but is a workaround, not a fix of the MI. |
| 7. No persistence | **STILL MISSING.** Prolog state dies when process dies. No Neo4j write-back. |
| 8. SOMA still separate package | **STILL TRUE.** soma-prolog is a standalone package with its own HTTP daemon. Not merged into carton-mcp. |

**3 fixed, 1 partially fixed, 1 workaround, 3 still missing.**

**For recursive core sentence verification specifically:** gaps 4 (Neo4j bridge) and 7 (persistence) are the blockers. Without them, SOMA can verify the graph of a SINGLE event but can't verify claims that reference concepts from previous events. Option (b) from A3 (trust stored Neo4j status) is the shortcut.

---

## A5: Minimum work for recursive core sentence verification through SOMA

**Beyond the 30-minute CoreRequirement plan. This is the full recursive check.**

1. **Load OWL restrictions into Prolog** (30 min) — Add a boot-time predicate that calls `class_restrictions_snake()` for every OWL class and asserts `required_restriction(Class, Prop, TargetType)`. Replace the hardcoded seed facts. Now SOMA knows all 186 restriction axioms from uarl.owl.

2. **Write `core_sentence_satisfied/1`** (30 min) — Prolog predicate that checks: concept has is_a + part_of + instantiates, all restrictions from its type are satisfied with correctly-typed values, no string_value values remain.

3. **Write `is_ont/1` with recursive descent** (30 min) — Checks core_sentence_satisfied on the concept AND recursively on all referenced subconcepts. Uses visited-list to prevent cycles.

4. **Add Neo4j status bridge** (1 hr) — py_call helper `query_concept_status(name)` that queries CartON Neo4j for a concept's stored validation status. The recursive descent stops at concepts whose stored status is already `ont` (trusted, not re-verified).

5. **Wire into deduce_validation_status** (15 min) — Add an `ont` clause: `deduce_validation_status(C, ont) :- is_ont(C), !.` Now the three-tier SOUP/CODE/ONT distinction is fully operational.

6. **Wire as CoreRequirement** (15 min) — Add a CoreRequirement that fires when a concept claims `ont` but `is_ont/1` fails. Produces structured error listing which subclaim broke the chain.

7. **Test** (30 min) — Submit events that build a full concept with all core sentence steps, verify it reaches ONT. Submit events with missing steps, verify it stays SOUP. Submit events with a subclaim that's SOUP, verify parent stays SOUP.

**Total: ~4 hours of focused work.** Not weeks. The architecture is there. The predicates are compositional. The hardest part is the Neo4j bridge (#4) which is the same gap that's been identified since Apr 8.

---

## A6: Is the core sentence representable as Prolog rules?

**Yes, and the shape you proposed is almost right.** The correction:

```prolog
% Does X have the full core sentence shape?
core_sentence_satisfied(X) :-
    % The three required primitives
    triple(X, is_a, Type),
    triple(X, part_of, Container),
    triple(X, instantiates, Pattern),
    % All restrictions from Type are satisfied with typed values
    forall(
        required_restriction(Type, Prop, TargetType),
        (   triple(X, Prop, Val),
            triple(Val, is_a, TargetType)
        )
    ),
    % No values are arbitrary strings (all progressively typed)
    \+ concept_has_soup_value(X).

% Is X fully ONT (recursive)?
is_ont(X) :- is_ont(X, []).

is_ont(X, Visited) :-
    \+ member(X, Visited),
    core_sentence_satisfied(X),
    forall(
        (   triple(X, _Prop, Sub),
            Sub \= X,
            triple(Sub, is_a, _),
            \+ member(Sub, Visited)
        ),
        is_ont(Sub, [X|Visited])
    ).
```

**What's different from your version:**
- Added the `required_restriction` check (your version had named steps; the real check uses the OWL restrictions)
- Added `concept_has_soup_value` check (the CODE layer requirement — no string_value)
- Added visited-list for cycle prevention
- The named steps (isa_embodies_partof etc.) are subsumed by the generic required_restriction check — if the OWL declares that a concept's type requires has_X pointing to type Y, the restriction check verifies it. You don't need named Prolog predicates per core-sentence step; the restrictions encode the steps.

**The recursive check `is_ont/1` is literally 10 lines of Prolog.** The hard part isn't the check — it's populating `required_restriction/3` from the OWL's 186 axioms (step 1 from A5) and having the Neo4j bridge to trust previously-verified concepts (step 4).

---

## A7: Can SOMA load OWL restrictions for the recursive check?

**Yes. The helper EXISTS but is not called.**

`class_restrictions_snake(class_name)` at utils.py line 478 reads OWL restrictions via owlready2 and returns them as `"property_snake|kind"` strings. `list_all_restrictions_snake()` at line 492 returns ALL restrictions across ALL classes as `"class_snake|property_snake|kind"` triples.

**Nobody calls these to populate Prolog.** The required_restriction/3 facts in soma_partials.pl are hardcoded:
```prolog
required_restriction(process, has_steps, template_sequence).
required_restriction(template_method, has_method_name, string_value).
% etc — only 13 hardcoded facts
```

The OWL has 186 restriction axioms. Only 13 are available to Prolog.

**The fix is one boot-time predicate:**

```prolog
load_owl_restrictions :-
    py_call('soma_prolog.utils':list_all_restrictions_snake(), RestList),
    forall(
        member(RestStr, RestList),
        (   atom_string(RestAtom, RestStr),
            atomic_list_concat([ClassSnake, PropSnake, Kind], '|', RestAtom),
            % Extract target type from kind string (e.g., "some(template_sequence)")
            extract_target_from_kind(Kind, TargetType),
            assertz(required_restriction(ClassSnake, PropSnake, TargetType))
        )
    ).
```

Add `:- load_owl_restrictions.` to soma_boot.pl after rule loading. Then all 186 OWL restriction axioms are available as Prolog facts. The recursive core sentence check uses them automatically via `forall(required_restriction(Type, Prop, TargetType), ...)`.

**This is the single most impactful change.** It bridges the 186-axiom OWL to the Prolog reasoning layer in one step. Everything else (core_sentence_satisfied, is_ont, recursive descent) composes on top of it.
