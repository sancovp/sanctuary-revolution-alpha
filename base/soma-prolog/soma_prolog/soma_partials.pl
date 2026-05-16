% SOMA Partials — Graph + Conventions + Healing
%
% The correct mental model:
%
% 1. Every event is a carton add_concept call (or several) constrained so that
%    the one top-level thing being filled is always an Event.
% 2. Each carton observation has shape: obs(Target, [rel(Pred, [Obj1, Obj2]), ...])
%    where every Object is primitively typed or a reference to a known type.
% 3. Observations dump triples into an accumulated graph: triple(S, P, O).
% 4. A PARTIAL is any graph-logic convention that means something in a sense.
%    E.g. "if X is_a starsystem, X must have a .claude dir and every skill in
%    .claude/skills must be a file describing a dev flow; every such file must
%    have a rule that invokes the skill when the LLM cd's into the dir."
%    Each of those sub-facts is a small partial — a building block of a
%    deduction chain that self-organizes the graph.
% 5. The _UNNAMED marker is emitted when a convention says "X must have Y"
%    and Y is missing in the graph.
% 6. Healing walks derivations of related triples to try to DEDUCE what the
%    _Unnamed should be. If it can, it asserts the derived triple. If not,
%    the _Unnamed stands and the next event (or an LLM) may close it.
% 7. Codegen fires when accumulated conventions close a deduction chain whose
%    result IS a program shape — compile_to_python then emits Python.
%
% The mechanism is universal: add a convention rule as a Prolog_Rule OWL
% individual whose body calls `assert_unnamed_slot/3` or asserts new triples,
% and from that moment on every future event is subject to it. Self-organizing.

:- discontiguous required_restriction/3.
:- discontiguous is_code_type/1.
:- discontiguous check_convention/1.

% The accumulated triple graph (SOMA's knowledge web)
:- dynamic triple/3.              % triple(Subject, Predicate, Object)
:- dynamic dep_violation/2.       % dep_violation(Module, Dependency) — arch dep check

% Gaps detected by convention rules
:- dynamic unnamed_slot/3.        % unnamed_slot(Subject, MissingProperty, ExpectedType)

% Convention rules (partials) — stored here as dynamic facts, loaded from
% Prolog_Rule OWL individuals at boot and via meta-observations
:- dynamic convention_rule/2.     % convention_rule(Name, Description)

% Carry-over: old slot-filling scaffolding (kept to not break existing bindings)
:- dynamic partial/4.
:- dynamic concept_type/2.
:- dynamic has_rel/3.
:- dynamic validation_status/2.
:- dynamic ca_entity/2.
:- dynamic heal_log/4.
:- dynamic is_code_type/1.

% Bridge: old has_rel(S, P, O) reads pick up triples from the new graph.
% This lets the existing soma_compile.pl assemble_program walk the accumulated
% triple graph without being rewritten.
has_rel(S, P, O) :- triple(S, P, O).

% Bridge: concept_type(C, T) reads pick up is_a triples from the new graph.
concept_type(C, T) :- triple(C, is_a, T).

% ======================================================================
% CODE TYPES — seed bootstrap (kept from before)
% ======================================================================

is_code_type(code_file).
is_code_type(code_class).
is_code_type(code_method).
is_code_type(code_function).
is_code_type(code_attribute).
is_code_type(code_repository).

% ======================================================================
% TRIPLE INGESTION — every carton observation's relationships become triples
% ======================================================================

% Assert triples from a carton observation's relationships.
% Each related entry is tv(Value, Type) — a typed value.
% We assert BOTH the relationship triple AND the is_a type triple,
% giving SOMA the programming-level type at observation time for
% progressive model building.
assert_triples_from_carton(Target, Rels) :-
    forall(
        member(rel(Pred, TVs), Rels),
        forall(
            member(TV, TVs),
            assert_typed_value(Target, Pred, TV)
        )
    ).

% tv(Value, Type) — assert the relationship AND deduce the value's type.
% If Value is already a known type (seed triple, OWL class, primitive),
% do NOT assert the programming type — the real type already exists.
% Only assert the programming type for genuinely unknown values.
% This prevents "process is_a string_value" contamination when "process"
% is actually a DOLCE stative.
assert_typed_value(Target, Pred, tv(Value, Type)) :- !,
    assert_triple_once(Target, Pred, Value),
    (   is_known_type(Value)
    ->  true
    ;   assert_triple_once(Value, is_a, Type)
    ).

% Plain atom fallback (backward compat if tv wrapper missing)
assert_typed_value(Target, Pred, Value) :-
    assert_triple_once(Target, Pred, Value).

assert_triple_once(S, P, O) :-
    (   triple(S, P, O)
    ->  true  % already in the graph
    ;   assertz(triple(S, P, O))
    ).

% ======================================================================
% LEGACY FLAT-KV INGESTION — for backward-compat with obs(K, V, T) events
% Each flat observation is interpreted as a single triple where the subject
% is the source (we use 'event' as a placeholder) and the object is the value.
% This is a degraded mode; prefer carton obs/2 shape.
% ======================================================================

ingest_flat_obs(EventId, K, V, _Type) :-
    assert_triple_once(EventId, K, V).

% ======================================================================
% CONVENTION RULES — partials that mean something in a sense
%
% Each convention_rule is a Prolog predicate that inspects the triple graph
% and either:
%   (a) asserts new derived triples (forward inference)
%   (b) asserts unnamed_slot/3 facts where a required thing is missing
%
% Convention rules come from two places:
%   1. Seed conventions below (minimum universal set)
%   2. Prolog_Rule OWL individuals loaded via the load_prolog_rules_from_owl
%      bootstrap — any rule whose head is `check_convention(RuleName)` gets
%      invoked during run_all_conventions/0.
% ======================================================================

% Universal convention: for every concept of type T, every required_restriction
% of T must be satisfied by a triple — otherwise mark as unnamed_slot.
check_convention(missing_required_restriction) :-
    forall(
        (   triple(C, is_a, T),
            required_restriction(T, Prop, TargetType),
            \+ triple(C, Prop, _)
        ),
        assert_unnamed_slot_once(C, Prop, TargetType)
    ).

% Mereological convention: if property EXISTS but value has WRONG type.
% "X has_foo V, but V is not is_a ExpectedType" = structural violation.
check_convention(structural_type_mismatch) :-
    forall(
        (   triple(C, is_a, T),
            required_restriction(T, Prop, ExpectedType),
            triple(C, Prop, V),
            V \= C,
            ExpectedType \= string_value,
            \+ triple(V, is_a, ExpectedType),
            atomic_list_concat([Prop, '_should_be_', ExpectedType], MismatchTag)
        ),
        assert_unnamed_slot_once(C, MismatchTag, ExpectedType)
    ).

% Recursive instantiation: for each part V that C claims via required
% property Prop, V must itself satisfy all required_restrictions of
% ExpectedType. This walks depth — parts of parts of parts.
check_convention(recursive_instantiation) :-
    forall(
        (   triple(C, is_a, T),
            triple(C, has_observation_source, _),
            required_restriction(T, Prop, ExpectedType),
            triple(C, Prop, V),
            V \= C,
            triple(V, is_a, ExpectedType),
            required_restriction(ExpectedType, SubProp, SubExpected),
            \+ triple(V, SubProp, _)
        ),
        assert_unnamed_slot_once(V, SubProp, SubExpected)
    ).

% Universal convention: if something is an instance of a subclass of T,
% it's also an instance of T (transitive is_a closure).
check_convention(transitive_is_a) :-
    forall(
        (   triple(C, is_a, Sub),
            triple(Sub, is_a, Super),
            Sub \= Super,
            \+ triple(C, is_a, Super)
        ),
        assert_triple_once(C, is_a, Super)
    ).

% Run every convention rule we know about.
% Clear unnamed_slot first so gaps reflect current graph state (not stale
% marks from prior events where the slot has since been filled).
run_all_conventions :-
    retractall(unnamed_slot(_, _, _)),
    forall(
        clause(check_convention(Name), _),
        catch(check_convention(Name), _, true)
    ),
    % Second pass in case transitive_is_a revealed new is_a triples
    forall(
        clause(check_convention(Name), _),
        catch(check_convention(Name), _, true)
    ).

assert_unnamed_slot_once(S, P, T) :-
    (   unnamed_slot(S, P, T)
    ->  true
    ;   assertz(unnamed_slot(S, P, T))
    ).

% ======================================================================
% HEALING — try to deduce values for unnamed slots by walking derivations
%
% Strategies applied in order:
%   1. Direct neighbor: if C is already linked to some V via any predicate,
%      and V is_a TargetType, use V as the filler.
%   2. Type membership: if there is exactly one concept in the graph of type
%      TargetType that is also connected to C via any path of length <= 2,
%      use it.
%   3. Co-occurrence in same event: if another triple(C, _, V) exists and V
%      is the right type, use it.
% If no strategy works, leave the unnamed_slot in place.
% ======================================================================

% heal_unnamed — DISABLED: auto-fill cross-contaminates when multiple
% slots require the same type (e.g. deduction_chain needs two string_value
% slots). Healing should REPORT gaps with neighborhood options, not auto-fill.
% The agent reads the report and submits add_event to repair.
% Re-enable once LLM-based traceback interaction healing is stable.
%
% heal_unnamed :-
%     findall(slot(C, P, T), unnamed_slot(C, P, T), Slots),
%     forall(member(slot(C, P, T), Slots), heal_one(C, P, T)).
%
% heal_one(C, P, T) :-
%     (   triple(C, _OtherPred, V),
%         triple(V, is_a, T),
%         V \= C
%     ->  assert_triple_once(C, P, V),
%         retract(unnamed_slot(C, P, T)),
%         assertz(heal_log(C, P, T, healed_from_neighbor(V)))
%     ;   true
%     ).

heal_unnamed :- true.

% ======================================================================
% STATUS
% ======================================================================

% ======================================================================
% SOUP/CODE — recursive subgraph reference resolution
%
% SOUP = the concept's subgraph contains a reference at ANY depth to an
% entity whose type is not found (not primitive, not seed, not OWL class).
% The COMPLEX itself is SOUP qua itself — its parts may be fine, but the
% composition references something undefined so it cannot cohere.
%
% CODE = all references at all depths resolve to known types + no unnamed slots.
% ======================================================================

is_known_type(T) :-
    member(T, [string_value, int_value, float_value, bool_value,
               list_value, dict_value, typed_value]), !.
is_known_type(T) :-
    seed_triple(T, is_a, _), !.
is_known_type(T) :-
    seed_triple(_, is_a, T), !.
is_known_type(T) :-
    atom_string(T, TStr),
    py_call('soma_prolog.utils':is_class(TStr), @(true)), !.

has_undefined_reference(C) :-
    has_undefined_reference(C, []).

has_undefined_reference(C, Visited) :-
    member(C, Visited), !, fail.
has_undefined_reference(C, _Visited) :-
    triple(C, is_a, Type),
    \+ is_known_type(Type), !.
has_undefined_reference(C, Visited) :-
    triple(C, Pred, V),
    Pred \= is_a, Pred \= dolce_category, Pred \= promoted_to_owl,
    Pred \= has_observation_source, Pred \= has_description,
    V \= C,
    \+ member(V, Visited),
    triple(V, is_a, VType),
    \+ is_known_type(VType), !.
has_undefined_reference(C, Visited) :-
    triple(C, Pred, V),
    Pred \= is_a, Pred \= dolce_category, Pred \= promoted_to_owl,
    Pred \= has_observation_source, Pred \= has_description,
    V \= C,
    \+ member(V, Visited),
    triple(V, is_a, _),
    has_undefined_reference(V, [C|Visited]).

find_undefined_reference(C, Pred, Value, Type) :-
    find_undefined_reference(C, Pred, Value, Type, []).

find_undefined_reference(C, is_a, C, Type, _Visited) :-
    triple(C, is_a, Type),
    \+ is_known_type(Type), !.
find_undefined_reference(C, Pred, V, VType, Visited) :-
    triple(C, Pred, V),
    Pred \= is_a, Pred \= dolce_category, Pred \= promoted_to_owl,
    Pred \= has_observation_source, Pred \= has_description,
    V \= C,
    \+ member(V, Visited),
    triple(V, is_a, VType),
    \+ is_known_type(VType), !.
find_undefined_reference(C, Pred, Value, Type, Visited) :-
    triple(C, _P, V),
    _P \= is_a, _P \= dolce_category, _P \= promoted_to_owl,
    _P \= has_observation_source, _P \= has_description,
    _P \= has_deduction_premise, _P \= has_deduction_conclusion,
    _P \= has_rule_head, _P \= has_rule_body,
    _P \= has_cor_template,
    V \= C,
    \+ member(V, Visited),
    triple(V, is_a, _),
    find_undefined_reference(V, Pred, Value, Type, [C|Visited]).

deduce_validation_status(C, code) :-
    triple(C, is_a, _),
    \+ has_undefined_reference(C),
    \+ unnamed_slot(C, _, _), !.
deduce_validation_status(C, soup) :-
    triple(C, is_a, _),
    (has_undefined_reference(C) ; unnamed_slot(C, _, _)), !.
deduce_validation_status(_, unvalidated).

concept_complete(C) :-
    triple(C, is_a, _),
    \+ unnamed_slot(C, _, _).

missing_required(C, Missing) :-
    findall(
        missing(Prop, TargetType),
        unnamed_slot(C, Prop, TargetType),
        Missing
    ).

% ======================================================================
% MAIN ENTRY — process an event's observations through graph + conventions
% ======================================================================

process_event_partials(EventId) :-
    % Phase 1a: ingest SOMA observations. An Event has a list of observations;
    % each one has its own source + the ontology graph about the sub-part of
    % the event it's talking about (carton add_concept shape: name,
    % description, relationships). No categories — the category IS observation.
    % obs_concept(Source, Name, Description, Relationships)
    forall(
        event_observation(EventId, obs_concept(Source, Name, Description, Rels)),
        ingest_obs_concept(EventId, Source, Name, Description, Rels)
    ),
    % Phase 1b: ingest older carton obs(Target, Rels) shape
    forall(
        event_observation(EventId, obs(Target, Rels)),
        assert_triples_from_carton(Target, Rels)
    ),
    % Phase 1c: ingest legacy flat obs(K, V, T)
    forall(
        event_observation(EventId, obs(K, V, T)),
        ingest_flat_obs(EventId, K, V, T)
    ),
    % Phase 2: run all convention rules over the accumulated graph
    run_all_conventions,
    % Phase 3: try to heal unnamed slots
    heal_unnamed,
    % Phase 4: run conventions again in case healing revealed new gaps
    run_all_conventions.

% Ingest one SOMA observation: assert triples from its relationships, record
% its per-observation source and link it into the event. An observation is
% the sub-graph describing one part of the event; the event is the top-level
% ontology graph composed of these sub-graphs.
ingest_obs_concept(EventId, Source, Name, Description, Rels) :-
    assert_triples_from_carton(Name, Rels),
    assert_triple_once(Name, has_observation_source, Source),
    assert_triple_once(EventId, has_observation, Name),
    (   Description == ''
    ->  true
    ;   assert_triple_once(Name, has_description, Description)
    ).

% event_observation/2 — per-event access to this event's observations.
% Populated by the add_event body before process_event_partials runs.
:- dynamic event_observation/2.

% ======================================================================
% DOLCE FOUNDATIONAL ONTOLOGY — ground floor categories
%
% Taken verbatim from DOLCE (Descriptive Ontology for Linguistic and
% Cognitive Engineering). These are the top-level universals that every
% domain entity inherits from. SOMA's convention rules use these to
% automatically classify realizations and stamp appropriate requirements.
%
% A universal (pattern) is ABOVE the endurant/perdurant distinction.
% When a universal is INSTANTIATED (realized in spacetime), the instance
% inherits the DOLCE category of its parent universal's branch.
% ======================================================================

% Top level: particular
seed_triple(endurant, is_a, particular).
seed_triple(perdurant, is_a, particular).
seed_triple(quality, is_a, particular).
seed_triple(abstract, is_a, particular).

% Endurant subtypes
seed_triple(physical_endurant, is_a, endurant).
seed_triple(non_physical_endurant, is_a, endurant).
seed_triple(amount_of_matter, is_a, physical_endurant).
seed_triple(feature, is_a, physical_endurant).
seed_triple(physical_object, is_a, physical_endurant).
seed_triple(mental_object, is_a, non_physical_endurant).
seed_triple(social_object, is_a, non_physical_endurant).
seed_triple(agentive_social_object, is_a, social_object).
seed_triple(non_agentive_social_object, is_a, social_object).

% Perdurant subtypes
seed_triple(event, is_a, perdurant).
seed_triple(stative, is_a, perdurant).
seed_triple(achievement, is_a, event).
seed_triple(accomplishment, is_a, event).
seed_triple(state, is_a, stative).
seed_triple(process, is_a, stative).

% Quality subtypes
seed_triple(temporal_quality, is_a, quality).
seed_triple(physical_quality, is_a, quality).
seed_triple(abstract_quality, is_a, quality).

% Abstract subtypes
seed_triple(set, is_a, abstract).
seed_triple(region, is_a, abstract).
seed_triple(fact, is_a, abstract).
seed_triple(temporal_region, is_a, region).
seed_triple(physical_region, is_a, region).
seed_triple(abstract_region, is_a, region).

% Programming primitives map to abstract
seed_triple(typed_value, is_a, abstract).
seed_triple(string_value, is_a, typed_value).
seed_triple(int_value, is_a, typed_value).
seed_triple(float_value, is_a, typed_value).
seed_triple(bool_value, is_a, typed_value).
seed_triple(list_value, is_a, typed_value).
seed_triple(dict_value, is_a, typed_value).

% GNOSYS structural universals mapped into DOLCE
seed_triple(organization, is_a, agentive_social_object).
seed_triple(agent, is_a, agentive_social_object).
seed_triple(role, is_a, social_object).
seed_triple(artifact, is_a, non_agentive_social_object).

% Compilable shapes mapped into DOLCE — these are artifacts (non-physical,
% non-agentive things that exist because someone made them)
seed_triple(template_method, is_a, artifact).
seed_triple(template_sequence, is_a, artifact).
seed_triple(template_attribute, is_a, artifact).
seed_triple(renderable_piece, is_a, artifact).
seed_triple(meta_stack, is_a, artifact).
seed_triple(role_list, is_a, artifact).
seed_triple(input_spec, is_a, artifact).
seed_triple(output_spec, is_a, artifact).
seed_triple(production_output, is_a, artifact).

% System types mapped into DOLCE — rules and chains are artifacts
seed_triple(prolog_rule, is_a, artifact).
seed_triple(deduction_chain, is_a, artifact).
seed_triple(core_requirement, is_a, artifact).
seed_triple(codified_process, is_a, artifact).
seed_triple(programmed_process, is_a, artifact).
seed_triple(business_process, is_a, artifact).
seed_triple(process_step, is_a, artifact).

% DOLCE classifications are AUTOMATIC — not requirements.
% Every entry is a perdurant (observation in time by an agent).
% CODE promotion = universal (class/configuration).
% transitive_is_a propagates the full DOLCE chain automatically.
% Convention rules USE these classifications for dispatch:

check_convention(dolce_perdurant_dispatch) :-
    forall(
        (   triple(C, is_a, T),
            triple(T, is_a, perdurant),
            \+ triple(C, dolce_category, perdurant)
        ),
        assert_triple_once(C, dolce_category, perdurant)
    ).

check_convention(dolce_endurant_dispatch) :-
    forall(
        (   triple(C, is_a, T),
            triple(T, is_a, endurant),
            \+ triple(C, dolce_category, endurant)
        ),
        assert_triple_once(C, dolce_category, endurant)
    ).

check_convention(dolce_abstract_dispatch) :-
    forall(
        (   triple(C, is_a, T),
            triple(T, is_a, abstract),
            \+ triple(C, dolce_category, abstract)
        ),
        assert_triple_once(C, dolce_category, abstract)
    ).

check_convention(dolce_quality_dispatch) :-
    forall(
        (   triple(C, is_a, T),
            triple(T, is_a, quality),
            \+ triple(C, dolce_category, quality)
        ),
        assert_triple_once(C, dolce_category, quality)
    ).

% ======================================================================
% PATTERN 5: PROMOTE TO OWL — bridge Prolog triples to OWL individuals
%
% When a concept in the triple graph has is_a pointing to a known OWL
% class AND reaches CODE status (no unnamed slots), create an OWL
% individual of that class. This closes the Prolog→OWL loop.
% ======================================================================

% Mark SOUP concepts — runs BEFORE promote_to_owl so concept_complete blocks them
check_convention(soup_undefined_refs) :-
    forall(
        (   triple(Name, is_a, Class),
            Class \= string_value, Class \= int_value, Class \= float_value,
            Class \= bool_value, Class \= list_value, Class \= dict_value,
            Class \= typed_value,
            \+ seed_triple(Class, is_a, _),
            \+ seed_triple(_, is_a, Class),
            \+ triple(Class, has_observation_source, _),
            triple(Name, has_observation_source, _),
            find_undefined_reference(Name, _Pred, _Value, UndefType)
        ),
        assert_unnamed_slot_once(Name, undefined_type_ref, UndefType)
    ).

:- dynamic promoted_to_owl/1.

% Seed types that ARE promotable (users create instances of these)
promotable_seed_type(deduction_chain).
promotable_seed_type(prolog_rule).
promotable_seed_type(core_requirement).
promotable_seed_type(codified_process).
promotable_seed_type(programmed_process).
promotable_seed_type(business_process).

check_convention(promote_to_owl) :-
    findall(Name-Class,
        (   triple(Name, is_a, Class),
            Class \= string_value, Class \= int_value, Class \= float_value,
            Class \= bool_value, Class \= list_value, Class \= dict_value,
            Class \= typed_value,
            (\+ seed_triple(Class, is_a, _) ; promotable_seed_type(Class)),
            \+ seed_triple(_, is_a, Class),
            \+ promoted_to_owl(Name),
            triple(Name, has_observation_source, _),
            concept_complete(Name)
        ),
        Candidates),
    forall(
        member(Name-Class, Candidates),
        (   atom_string(Class, ClassStr),
            (   py_call('soma_prolog.utils':is_class(ClassStr), @(true))
            ->  promote_one_to_owl(Name, Class)
            ;   true
            )
        )
    ).

promote_one_to_owl(Name, Class) :-
    findall(RelStr,
        (   triple(Name, Pred, Value),
            Pred \= is_a,
            Pred \= has_observation_source,
            Pred \= has_description,
            Pred \= dolce_category,
            atom_concat(Pred, '|', T1),
            atom_concat(T1, Value, RelStr)
        ),
        Rels),
    atom_string(Name, NameStr),
    atom_string(Class, ClassStr),
    catch(
        (   py_call('soma_prolog.utils':create_typed_individual(NameStr, ClassStr, Rels), Status),
            assertz(promoted_to_owl(Name)),
            format(user_error, '[SOMA] Promoted ~w to OWL class ~w: ~w~n', [Name, Class, Status])
        ),
        Err,
        format(user_error, '[SOMA] promote_to_owl failed for ~w: ~w~n', [Name, Err])
    ),
    maybe_reload_if_rule(Name).

maybe_reload_if_rule(Name) :-
    (   triple(Name, is_a, prolog_rule)
    ->  (   load_prolog_rules_from_owl,
            format(user_error, '[SOMA] Reloaded PrologRules after promoting ~w~n', [Name])
        )
    ;   true
    ).

% ======================================================================
% GEOMETRY CLOSURE — every observed concept must be classifiable
%
% Three things must be known about every observed concept:
%   1. dolce_category — WHERE it sits in the foundational ontology
%   2. instantiates — WHAT universal pattern it realizes
%   3. part_of — WHAT contains it
%
% DOLCE dispatch conventions automatically stamp dolce_category IF the
% is_a chain connects to a DOLCE branch. If it doesn't, the concept
% stays unclassified and this convention flags it.
%
% The LLM must provide is_a + part_of + instantiates on every observation.
% SOMA deduces dolce_category from is_a. All four = geometry closed.
% ======================================================================

check_convention(geometry_closure) :-
    forall(
        (   triple(C, has_observation_source, _),
            \+ triple(C, dolce_category, _)
        ),
        assert_unnamed_slot_once(C, dolce_category, dolce_branch)
    ),
    forall(
        (   triple(C, has_observation_source, _),
            \+ triple(C, instantiates, _)
        ),
        assert_unnamed_slot_once(C, instantiates, universal_pattern)
    ),
    forall(
        (   triple(C, has_observation_source, _),
            \+ triple(C, part_of, _)
        ),
        assert_unnamed_slot_once(C, part_of, containing_context)
    ),
    forall(
        (   triple(C, has_observation_source, _),
            \+ triple(C, produces, _)
        ),
        assert_unnamed_slot_once(C, produces, production_output)
    ).

% ======================================================================
% AUTHORIZATION — detect authorization observations and trigger compilation
%
% When an observation has `authorizes` relationship pointing to a concept,
% and that concept has no unnamed_slots, authorize it for compilation.
% This bridges the observation graph to the compilation gate.
% ======================================================================

check_convention(detect_authorization) :-
    forall(
        (   triple(AuthObs, authorizes, Target),
            triple(AuthObs, has_observation_source, _),
            concept_complete(Target),
            \+ authorized_compilation(Target, _)
        ),
        (   assert(authorized_compilation(Target, observed_authorization)),
            format(user_error, '[SOMA] Authorized ~w for compilation~n', [Target])
        )
    ).

% ======================================================================
% AUTO-COMPILE — after authorization, try to compile ready concepts
% ======================================================================

:- dynamic compiled_program/2.    % compiled_program(Concept, Code)
:- dynamic authorized_compilation/2.  % authorized_compilation(Concept, Source)

check_convention(try_compile) :-
    forall(
        (   authorized_compilation(Concept, _),
            \+ compiled_program(Concept, _)
        ),
        (   deduce_validation_status(Concept, Status),
            format(user_error, '[SOMA] ~w validation=~w~n', [Concept, Status]),
            (   Status == code
            ->  (   should_compile(Concept)
                ->  format(user_error, '[SOMA] should_compile=true for ~w~n', [Concept]),
                    (   assemble_program(Concept, Program)
                    ->  format(user_error, '[SOMA] assembled: ~w~n', [Program]),
                        catch(
                            (   compile_to_python(Concept, Code)
                            ->  format(user_error, '[SOMA] COMPILED ~w: ~w chars~n', [Concept, Code])
                            ;   format(user_error, '[SOMA] compile_to_python FAILED for ~w~n', [Concept])
                            ),
                            Err,
                            format(user_error, '[SOMA] Compile threw ~w: ~w~n', [Concept, Err])
                        )
                    ;   format(user_error, '[SOMA] assemble_program FAILED for ~w~n', [Concept])
                    )
                ;   format(user_error, '[SOMA] should_compile=false for ~w~n', [Concept])
                )
            ;   (   find_undefined_reference(Concept, Pred, Value, UType)
                ->  format(user_error, '[SOMA] ~w blocked: ~w->~w is_a ~w (unknown)~n',
                        [Concept, Pred, Value, UType])
                ;   format(user_error, '[SOMA] ~w blocked, no undef ref found~n', [Concept])
                )
            )
        )
    ).

% ======================================================================
% SES DEPTH — progressive typing metric
%
% For every observed concept, count how many of its relationship values
% are still at string_value (depth 0) vs properly typed (depth 1+).
% A value is depth-0 if its ONLY is_a is string_value.
% A value is depth-1+ if it has is_a pointing to a non-primitive type.
%
% This feeds the state machine:
%   SHORT loop: pick one concept, type its depth-0 values
%   MEDIUM loop: the new types need their OWN depth-0 values typed
%   LONG loop: endeavors — which concept to close first
% ======================================================================

:- dynamic ses_report/3.  % ses_report(Concept, StrCount, TypedCount)

% The transitive chain from string_value through DOLCE.
% If a value's ONLY is_a types are in this set, it's depth-0 (untyped string).
string_value_chain(string_value).
string_value_chain(typed_value).
string_value_chain(abstract).
string_value_chain(particular).
string_value_chain(int_value).
string_value_chain(float_value).
string_value_chain(bool_value).
string_value_chain(list_value).
string_value_chain(dict_value).

% Check if a value is at depth 0 (all its is_a types are just the string_value chain)
is_depth_zero(V) :-
    triple(V, is_a, string_value),
    \+ (triple(V, is_a, T), \+ string_value_chain(T)).

% Count depth-0 values for a concept's relationships
ses_string_count(C, StrCount) :-
    findall(V,
        (   triple(C, Prop, V),
            Prop \= is_a, Prop \= part_of, Prop \= instantiates,
            Prop \= produces, Prop \= has_observation_source,
            Prop \= has_description, Prop \= dolce_category,
            Prop \= promoted_to_owl,
            V \= C,
            is_depth_zero(V)
        ),
        StrValues),
    length(StrValues, StrCount).

ses_typed_count(C, TypedCount) :-
    findall(V,
        (   triple(C, Prop, V),
            Prop \= is_a, Prop \= part_of, Prop \= instantiates,
            Prop \= produces, Prop \= has_observation_source,
            Prop \= has_description, Prop \= dolce_category,
            Prop \= promoted_to_owl,
            V \= C,
            \+ is_depth_zero(V),
            triple(V, is_a, _)
        ),
        TypedValues),
    length(TypedValues, TypedCount).

check_convention(ses_depth) :-
    retractall(ses_report(_, _, _)),
    forall(
        (   triple(C, has_observation_source, _),
            \+ atom_concat('tc_', _, C),
            ses_string_count(C, SC),
            ses_typed_count(C, TC),
            SC > 0
        ),
        (   assertz(ses_report(C, SC, TC)),
            format(user_error,
                '[SOMA SES] ~w: ~w str-depth-0, ~w typed. Needs progressive typing.~n',
                [C, SC, TC])
        )
    ).

% Compose SES gap sentence listing WHICH values are at depth 0
compose_ses_sentence(C, _SC, _TC, Sentence) :-
    findall(PV,
        (   triple(C, Prop, V),
            Prop \= is_a, Prop \= part_of, Prop \= instantiates,
            Prop \= produces, Prop \= has_observation_source,
            Prop \= has_description, Prop \= dolce_category,
            Prop \= promoted_to_owl,
            V \= C,
            is_depth_zero(V),
            format(atom(PV), '~w=~w', [Prop, V])
        ),
        PVList),
    atomic_list_concat(PVList, ', ', PVStr),
    format(atom(Sentence),
        '~w has untyped strings: ~w. Type them to close this view.',
        [C, PVStr]).

% ======================================================================
% ENDEAVOR TRACKING — state machine for progressive work
%
% An endeavor is a named unit of work with a goal (close a view, type
% a concept, fill gaps). The state machine:
%   open_endeavor(Name, Goal, StartTime) — currently active
%   closed_endeavor(Name, Goal, StartTime, EndTime) — completed
%   dropped_endeavor(Name, Goal, StartTime, DropTime) — abandoned
%
% Every tool call observation should relate to an open endeavor.
% If it doesn't, SOMA flags potential drift.
% When an endeavor's goal is met (e.g., unnamed_slots=0 for its target),
% it auto-closes.
% ======================================================================

:- dynamic open_endeavor/3.     % open_endeavor(Name, Goal, StartTime)
:- dynamic closed_endeavor/4.   % closed_endeavor(Name, Goal, StartTime, EndTime)
:- dynamic dropped_endeavor/4.  % dropped_endeavor(Name, Goal, StartTime, DropTime)
:- dynamic current_focus/1.     % current_focus(EndeavorName) — singular, only one

% Start a new endeavor (from observation with has_endeavor relationship)
% New endeavors automatically become the focus
check_convention(detect_endeavor_start) :-
    forall(
        (   triple(Obs, has_endeavor, EndName),
            \+ open_endeavor(EndName, _, _),
            \+ closed_endeavor(EndName, _, _, _)
        ),
        (   (   triple(Obs, has_endeavor_goal, Goal)
            ->  true
            ;   Goal = unspecified
            ),
            get_time(T),
            assertz(open_endeavor(EndName, Goal, T)),
            (   current_focus(OldFocus)
            ->  log_focus_switch(OldFocus, EndName)
            ;   true
            ),
            retractall(current_focus(_)),
            assertz(current_focus(EndName))
        )
    ).

% Explicit focus switch: has_focus observation changes the focused endeavor
check_convention(detect_focus_change) :-
    forall(
        (   triple(Obs, has_focus, EndName),
            open_endeavor(EndName, _, _),
            (current_focus(Cur) -> Cur \= EndName ; true)
        ),
        (   (   current_focus(OldFocus)
            ->  log_focus_switch(OldFocus, EndName)
            ;   true
            ),
            retractall(current_focus(_)),
            assertz(current_focus(EndName))
        )
    ).

% Tag every new non-internal concept with the current focus
% Uses is_a as proxy for "real concept" since has_observation_source
% is only set on tool call observations from the hook
check_convention(tag_focus_context) :-
    (   current_focus(Focus)
    ->  forall(
            (   triple(C, is_a, _),
                \+ atom_concat('tc_', _, C),
                \+ atom_concat('evt_', _, C),
                \+ triple(C, part_of_endeavor, _)
            ),
            assert_triple_once(C, part_of_endeavor, Focus)
        )
    ;   true
    ).

% Auto-close endeavors whose target concept has no remaining gaps
check_convention(auto_close_endeavors) :-
    forall(
        (   open_endeavor(EndName, Goal, StartT),
            Goal \= unspecified,
            triple(Goal, has_observation_source, _),
            \+ unnamed_slot(Goal, _, _),
            \+ ses_report(Goal, _, _)
        ),
        (   get_time(EndT),
            retract(open_endeavor(EndName, Goal, StartT)),
            assertz(closed_endeavor(EndName, Goal, StartT, EndT))
        )
    ).

% Report open endeavors — mark which one is FOCUSED
compose_endeavor_status(Sentences) :-
    findall(S,
        (   open_endeavor(Name, Goal, _),
            (   current_focus(Name)
            ->  format(atom(S), 'FOCUS: ~w (goal: ~w)', [Name, Goal])
            ;   format(atom(S), 'ENDEAVOR OPEN: ~w (goal: ~w)', [Name, Goal])
            )
        ),
        Sentences).

% ======================================================================
% HIERARCHY RESOLUTION — CWA check on tool call metadata
%
% Every tool call states domain/subdomain/target. Each must resolve to
% a previously-observed concept or a seed type. Unknown = "I don't know
% what that is. Explain it via add_event."
% ======================================================================

is_resolved_concept(X) :-
    triple(X, has_observation_source, _), !.
is_resolved_concept(X) :-
    seed_triple(X, is_a, _), !.
is_resolved_concept(X) :-
    seed_triple(_, is_a, X), !.
is_resolved_concept(X) :-
    atom_string(X, XStr),
    py_call('soma_prolog.utils':is_class(XStr), @(true)), !.

check_convention(tool_call_hierarchy) :-
    forall(
        (   triple(C, has_observation_source, _),
            atom_concat('tc_', _, C),
            triple(C, part_of, Domain),
            Domain \= C,
            \+ is_resolved_concept(Domain)
        ),
        assert_unnamed_slot_once(C, unknown_domain, Domain)
    ),
    forall(
        (   triple(C, has_observation_source, _),
            atom_concat('tc_', _, C),
            triple(C, has_subdomain, Sub),
            Sub \= C,
            \+ is_resolved_concept(Sub)
        ),
        assert_unnamed_slot_once(C, unknown_subdomain, Sub)
    ).

% Domain composition: every tc_* domain must be part_of soma_projects
check_convention(domain_composition) :-
    forall(
        (   triple(C, has_observation_source, _),
            atom_concat('tc_', _, C),
            triple(C, part_of, Domain),
            Domain \= C,
            is_resolved_concept(Domain),
            \+ triple(Domain, part_of, soma_projects)
        ),
        assert_unnamed_slot_once(C, domain_not_in_project, Domain)
    ).

% Subdomain composition: every tc_* subdomain must be part_of its domain
check_convention(subdomain_composition) :-
    forall(
        (   triple(C, has_observation_source, _),
            atom_concat('tc_', _, C),
            triple(C, has_subdomain, Sub),
            triple(C, part_of, Domain),
            Sub \= C, Sub \= Domain,
            is_resolved_concept(Sub),
            is_resolved_concept(Domain),
            \+ triple(Sub, part_of, Domain)
        ),
        assert_unnamed_slot_once(C, subdomain_not_in_domain, Sub)
    ).

% Drift detection: only flag concepts in the FOCUSED endeavor
% Skip endeavor declarations, human answers, internal concepts
check_convention(drift_detection) :-
    (   current_focus(Focus)
    ->  forall(
            (   ses_report(OpenConcept, _, _),
                \+ atom_concat('tc_', _, OpenConcept),
                \+ atom_concat('evt_', _, OpenConcept),
                \+ triple(OpenConcept, has_endeavor, _),
                \+ atom_concat('human_answer_', _, OpenConcept),
                \+ atom_concat('endeavor_', _, OpenConcept),
                triple(OpenConcept, part_of_endeavor, Focus)
            ),
            assert_unnamed_slot_once(drift_warning, drift_from_open_work, OpenConcept)
        )
    ;   true   % no focus set — no drift warnings
    ).

compose_hierarchy_sentence(C, subdomain_not_in_domain, Value, Sentence) :-
    !,
    (   triple(C, part_of, Domain)
    ->  format(atom(Sentence),
            'Tool call ~w uses subdomain ~w but ~w is not part_of domain ~w. Register it.',
            [C, Value, Value, Domain])
    ;   format(atom(Sentence),
            'Tool call ~w uses subdomain ~w but ~w is not registered under its domain.',
            [C, Value, Value])
    ).

compose_hierarchy_sentence(_C, drift_from_open_work, Value, Sentence) :-
    !,
    format(atom(Sentence),
        'DRIFT: ~w has unfinished typing work. Close ~w depth-0 values before working on other things.',
        [Value, Value]).

compose_hierarchy_sentence(C, domain_not_in_project, Value, Sentence) :-
    !,
    format(atom(Sentence),
        'Tool call ~w uses domain ~w but ~w is not part_of soma_projects. Register it as a project first.',
        [C, Value, Value]).

compose_hierarchy_sentence(C, Type, Value, Sentence) :-
    (   Type == unknown_domain
    ->  format(atom(Sentence),
            'Tool call ~w uses domain ~w but ~w has never been explained. Describe this domain via add_event.',
            [C, Value, Value])
    ;   Type == unknown_subdomain
    ->  format(atom(Sentence),
            'Tool call ~w uses subdomain ~w but ~w has never been explained. Describe this subdomain via add_event.',
            [C, Value, Value])
    ;   format(atom(Sentence),
            'Tool call ~w references unknown ~w: ~w. Explain it.',
            [C, Type, Value])
    ).

% ======================================================================
% AUTHORIZATION DISPATCH — who can fill what, and why
%
% authorized_source(SlotType, Source, Reason)
% Maps the TYPE of missing info to WHO can provide it and WHY.
% compose_gap_sentence uses this to say "ask X for Y because Z"
% ======================================================================

:- discontiguous authorized_source/3.

% Process step logic can only come from domain experts (humans who do the work)
authorized_source(has_method_body, human_domain_expert,
    'process step logic only comes from humans who do the actual work').
authorized_source(has_method_parameters, human_domain_expert,
    'method parameters describe real-world inputs that only the worker knows').
authorized_source(has_role, human_domain_expert,
    'roles are assigned by the organization, only humans know the structure').
authorized_source(has_field, human_domain_expert,
    'document fields describe real-world artifacts only the user knows').

% Process-level structure comes from whoever is describing the process
authorized_source(has_steps, human_domain_expert,
    'the step sequence of a process can only come from someone who does or observes the work').
authorized_source(has_roles, human_domain_expert,
    'roles in a process are organizational facts only the worker or manager knows').
authorized_source(has_inputs, human_domain_expert,
    'process inputs describe real-world requirements only the worker knows').
authorized_source(has_outputs, human_domain_expert,
    'process outputs describe real-world deliverables only the worker knows').

% DOLCE classification can be deduced by the system itself
authorized_source(dolce_category, system_deduction,
    'DOLCE classification is deduced from the is_a chain automatically').

% Domain/subdomain structure comes from the project architect
authorized_source(unknown_domain, human_architect,
    'domain structure is a project decision requiring human judgment').
authorized_source(unknown_subdomain, human_architect,
    'subdomain organization requires human architectural decision').

% Geometry closure fields default to the observing agent
authorized_source(instantiates, observing_agent,
    'what pattern this instantiates should be stated by whoever is observing').
authorized_source(part_of, observing_agent,
    'containment relationships should be stated by whoever is observing').
authorized_source(produces, observing_agent,
    'what something produces should be stated by whoever is observing').

% ======================================================================
% VERIFICATION DISPATCH — detect unverified runs, classify, dispatch
%
% After a compiled concept is run, it needs verification. SOMA detects
% this and dispatches to the right source based on output type.
% ======================================================================

check_convention(verification_needed) :-
    forall(
        (   compiled_program(Concept, _),
            runtime_result(Concept, _),
            \+ triple(Concept, verified_by, _)
        ),
        assert_unnamed_slot_once(Concept, needs_verification, verification_source)
    ).

% Verification authorization — who verifies what
authorized_source(needs_verification, human_end_user,
    'only the human who requested this knows if the output matches their intent').

% ======================================================================
% INTEGRATION DISCOVERY — for each "produces", what system delivers it?
%
% When a process produces something, SOMA asks: HOW does this get
% delivered? Is there an API? A bridge service? An existing MCP?
% The tree: produces → has_delivery_method → (api/bridge/custom/human)
% ======================================================================

:- dynamic known_bridge/3.  % known_bridge(Domain, ServiceName, MCP)

% Known bridges (seed data — grows from observations)
known_bridge(banking, plaid, 'plaid-mcp').
known_bridge(payments, stripe, 'stripe-mcp').
known_bridge(communications, twilio, 'twilio-mcp').
known_bridge(email, gmail, 'gmail-mcp').
known_bridge(calendar, google_calendar, 'google-calendar-mcp').
known_bridge(file_storage, google_drive, 'google-drive-mcp').
known_bridge(saas_integration, zapier, 'zapier-mcp').

% When a concept produces output but has no delivery method → flag
check_convention(integration_discovery) :-
    forall(
        (   compiled_program(Concept, _),
            triple(Concept, produces, Output),
            Output \= '',
            \+ triple(Concept, has_delivery_method, _)
        ),
        assert_unnamed_slot_once(Concept, has_delivery_method, integration_type)
    ).

authorized_source(has_delivery_method, human_domain_expert,
    'only the human knows how this output gets delivered in their business. Ask: is there an API? which service? do you have it connected?').

% Compose integration discovery sentence with known bridges
compose_integration_sentence(Concept, Sentence) :-
    triple(Concept, produces, Output),
    (   known_bridge(_, Service, MCP),
        format(atom(Sentence),
            '~w produces ~w. Known bridges: ~w (~w). Ask human: does your system use ~w or similar?',
            [Concept, Output, Service, MCP, Service])
    ;   format(atom(Sentence),
            '~w produces ~w but has no delivery method. Ask human: how does ~w get delivered?',
            [Concept, Output, Output])
    ).

% ======================================================================
% RUN COMPILED — invoke registered runtime objects through observations
%
% When an observation has has_run_target relationship, invoke the compiled
% runtime with all other relationship values as kwargs. Result stored as
% triple(RunObs, has_runtime_result, ResultJson).
% ======================================================================

:- dynamic runtime_result/2.  % runtime_result(ObsName, ResultJson)

check_convention(run_compiled_on_request) :-
    forall(
        (   triple(Obs, has_run_target, Target),
            triple(Obs, has_observation_source, _),
            \+ runtime_result(Obs, _)
        ),
        run_and_store_result(Obs, Target)
    ).

run_and_store_result(Obs, Target) :-
    findall(KV,
        (   triple(Obs, Prop, Value),
            Prop \= is_a, Prop \= part_of, Prop \= instantiates,
            Prop \= produces, Prop \= has_observation_source,
            Prop \= has_description, Prop \= dolce_category,
            Prop \= has_run_target, Prop \= has_endeavor,
            Prop \= has_endeavor_goal, Prop \= promoted_to_owl,
            format(atom(KV), '"~w":"~w"', [Prop, Value])
        ),
        KVList),
    atomic_list_concat(KVList, ',', KVStr),
    format(atom(KwargsJson), '{~w}', [KVStr]),
    atom_string(Target, TargetStr),
    atom_string(KwargsJson, KwargsStr),
    catch(
        (   py_call('soma_prolog.utils':call_soma_runtime(TargetStr, KwargsStr), ResultJson),
            assertz(runtime_result(Obs, ResultJson)),
            assert_triple_once(Obs, has_runtime_result, ResultJson),
            format(user_error, '[SOMA RUN] ~w(~w) = ~w~n', [Target, KwargsStr, ResultJson])
        ),
        Err,
        format(user_error, '[SOMA RUN ERROR] ~w: ~w~n', [Target, Err])
    ).

% ======================================================================
% CALENDAR SPEC EMISSION — when compiled, emit schedulable JSON spec
%
% After compilation, generate a Calendar JSON spec for the compiled
% concept. Write to /tmp/heaven_data/soma_calendar_specs/ for pickup.
% SOMA tells the caller: "SCHEDULABLE: concept at path"
% ======================================================================

:- dynamic calendar_spec_emitted/1.

check_convention(emit_calendar_spec) :-
    forall(
        (   compiled_program(Concept, _),
            \+ calendar_spec_emitted(Concept)
        ),
        emit_calendar_spec_for(Concept)
    ).

emit_calendar_spec_for(Concept) :-
    assertz(calendar_spec_emitted(Concept)),
    assert_triple_once(Concept, has_calendar_spec, ready),
    format(user_error, '[SOMA CALENDAR] ~w ready to schedule~n', [Concept]).

compose_calendar_sentence(Concept, SpecPath, Sentence) :-
    format(atom(Sentence),
        'SCHEDULABLE: ~w is compiled and ready to schedule. Spec at ~w. Set the schedule cron and call Calendar.schedule_sync().',
        [Concept, SpecPath]).

% ======================================================================
% SURF SCORE — metric for how well the agent tracks endeavors
%
% Wave = endeavor. Surfing = on track. Wipeout = blocked, needs user.
% Recovery = swap to another open endeavor while blocked one waits.
%
% Score per endeavor: 0-100
%   +20 endeavor exists and is open
%   +20 no blocking unnamed_slots for its domain
%   +20 no drift from its concepts
%   +20 all domains resolved
%   +20 SES depth >= 1 for all concepts in endeavor
%   = 0 when BLOCKED (needs user observation)
%
% Blocked endeavors go to user queue. Agent can swap to another wave.
% ======================================================================

:- dynamic blocked_endeavor/2.  % blocked_endeavor(Name, Reason)
:- dynamic surf_streak/2.       % surf_streak(EndeavorName, ConsecutiveEvents)

% === SURF ANALYTICS — history for pattern detection ===
:- dynamic wipeout_log/4.       % wipeout_log(Endeavor, StreakBefore, Cause, Timestamp)
:- dynamic focus_switch_log/3.  % focus_switch_log(From, To, Timestamp)
:- dynamic streak_peak_log/3.   % streak_peak_log(Endeavor, PeakValue, Timestamp)

% Surf = concentration on the FOCUSED endeavor only
% Non-focused endeavors freeze (no increment, no reset)
check_convention(compute_surf_score) :-
    (   current_focus(Focus),
        open_endeavor(Focus, _, _)
    ->  (   blocked_endeavor(Focus, Reason)
        ->  log_wipeout(Focus, Reason),
            reset_surf_streak(Focus)
        ;   increment_surf_streak(Focus)
        )
    ;   true  % no focus — no scoring
    ).

increment_surf_streak(Name) :-
    (   retract(surf_streak(Name, N))
    ->  N1 is N + 1,
        assertz(surf_streak(Name, N1))
    ;   assertz(surf_streak(Name, 1))
    ).

reset_surf_streak(Name) :-
    retractall(surf_streak(Name, _)),
    assertz(surf_streak(Name, 0)).

log_wipeout(Name, Reason) :-
    (   surf_streak(Name, N), N > 0
    ->  get_time(T),
        assertz(wipeout_log(Name, N, Reason, T)),
        assertz(streak_peak_log(Name, N, T))
    ;   true
    ).

log_focus_switch(From, To) :-
    get_time(T),
    assertz(focus_switch_log(From, To, T)),
    (   surf_streak(From, N), N > 0
    ->  assertz(streak_peak_log(From, N, T))
    ;   true
    ).

% Detect blocked endeavors — when human-required gaps exist
check_convention(detect_blocked_endeavors) :-
    forall(
        (   open_endeavor(Name, Goal, _),
            unnamed_slot(Goal, Prop, _),
            authorized_source(Prop, human_domain_expert, _),
            \+ blocked_endeavor(Name, _)
        ),
        (   format(atom(Reason), 'Needs human observation for ~w on ~w', [Prop, Goal]),
            assertz(blocked_endeavor(Name, Reason))
        )
    ).

% Compose surf status — only focused endeavor is SURFING, others PAUSED
compose_surf_status(Sentences) :-
    findall(S,
        (   open_endeavor(Name, _, _),
            (   current_focus(Name)
            ->  (   blocked_endeavor(Name, Reason)
                ->  format(atom(S), 'WAVE ~w: WIPEOUT. ~w. Swap focus or wait for user.', [Name, Reason])
                ;   (   surf_streak(Name, N)
                    ->  format(atom(S), 'WAVE ~w: SURFING (streak=~w). Concentrated.', [Name, N])
                    ;   format(atom(S), 'WAVE ~w: SURFING (streak=0). Just focused.', [Name])
                    )
                )
            ;   (   surf_streak(Name, N), N > 0
                ->  format(atom(S), 'WAVE ~w: PAUSED (streak=~w frozen).', [Name, N])
                ;   format(atom(S), 'WAVE ~w: PAUSED.', [Name])
                )
            )
        ),
        Sentences).

% === SURF ANALYTICS COMPOSE — metrics from accumulated history ===
compose_surf_analytics(Sentences) :-
    % Wipeout count and mean streak
    findall(N, wipeout_log(_, N, _, _), Peaks),
    length(Peaks, WipeoutCount),
    (   WipeoutCount > 0
    ->  sumlist(Peaks, Sum),
        MeanStreak is Sum / WipeoutCount,
        format(atom(S1), 'ANALYTICS: ~w wipeouts, mean streak before wipeout: ~1f', [WipeoutCount, MeanStreak]),
        % Most common cause
        findall(Cause, wipeout_log(_, _, Cause, _), Causes),
        msort(Causes, SortedCauses),
        clumped(SortedCauses, CauseCounts),
        sort(2, @>=, CauseCounts, RankedCauses),
        (   RankedCauses = [TopCause-TopN|_]
        ->  format(atom(S2), 'ANALYTICS: top blocker: ~w (~w times)', [TopCause, TopN])
        ;   S2 = 'ANALYTICS: no dominant blocker'
        )
    ;   S1 = 'ANALYTICS: 0 wipeouts',
        S2 = 'ANALYTICS: clean run'
    ),
    % Focus switch count
    findall(_, focus_switch_log(_, _, _), Switches),
    length(Switches, SwitchCount),
    format(atom(S3), 'ANALYTICS: ~w focus switches', [SwitchCount]),
    % Best streak ever
    findall(P, streak_peak_log(_, P, _), AllPeaks),
    (   AllPeaks \= []
    ->  max_list(AllPeaks, BestPeak),
        format(atom(S4), 'ANALYTICS: best streak peak: ~w', [BestPeak])
    ;   (   current_focus(F), surf_streak(F, Cur)
        ->  format(atom(S4), 'ANALYTICS: current streak is best so far: ~w', [Cur])
        ;   S4 = 'ANALYTICS: no streak data yet'
        )
    ),
    Sentences = [S1, S2, S3, S4].

% ======================================================================
% PERSONA DOMAIN ENFORCEMENT — active persona must match tool domain
%
% Each persona covers specific domains (has_persona_domain).
% When a tool call's domain doesn't match the active persona's domain,
% the system raises a persona mismatch warning.
% ======================================================================

:- dynamic active_persona/1.        % active_persona(Name)
:- dynamic persona_domain/2.        % persona_domain(PersonaName, DomainName)
:- dynamic persona_process/2.       % persona_process(PersonaName, ProcessName)
:- dynamic persona_cor_value/3.     % persona_cor_value(PersonaName, Key, Value) — latest CoR

% Sync persona state from triples (uses LAST has_active_persona found)
check_convention(sync_persona_state) :-
    % Find all active persona triples, take the last (most recent)
    findall(Name, triple(_, has_active_persona, Name), AllNames),
    (   AllNames \= []
    ->  last(AllNames, LatestName),
        (   active_persona(LatestName)
        ->  true
        ;   retractall(active_persona(_)),
            assertz(active_persona(LatestName))
        )
    ;   true
    ),
    % Sync persona-domain assignments
    forall(
        (   triple(Persona, has_persona_domain, Domain),
            \+ persona_domain(Persona, Domain)
        ),
        assertz(persona_domain(Persona, Domain))
    ),
    % Sync persona-process assignments
    forall(
        (   triple(Persona, has_persona_process, Process),
            \+ persona_process(Persona, Process)
        ),
        assertz(persona_process(Persona, Process))
    ).

% Convention: check UNIQUE domains from tool calls against active persona
% Only flags each mismatched DOMAIN once (not per tool call)
check_convention(persona_domain_match) :-
    (   active_persona(Persona),
        persona_domain(Persona, _)
    ->  findall(Domain,
            (   triple(_, part_of, Domain),
                \+ persona_domain(Persona, Domain),
                \+ persona_domain(Persona, all),
                triple(Domain, is_a, domain)
            ),
            MismatchedDomains),
        sort(MismatchedDomains, UniqueMismatches),
        forall(
            member(D, UniqueMismatches),
            assert_unnamed_slot_once(Persona, persona_mismatch, D)
        )
    ;   true
    ).

% Sync CoR values from flat persona_metadata observations into dynamic facts
check_convention(sync_persona_cor) :-
    (   active_persona(Persona)
    ->  retractall(persona_cor_value(_, _, _)),
        forall(
            (   triple(Evt, is_a, persona_metadata),
                triple(Evt, persona, Persona),
                triple(Evt, Key, Value),
                Key \= is_a, Key \= persona, Key \= has_observation_source,
                Key \= dolce_category, Key \= part_of, Key \= instantiates, Key \= produces
            ),
            assertz(persona_cor_value(Persona, Key, Value))
        )
    ;   true
    ).

% Convention: validate CoR KV values against persona-specific chains
check_convention(persona_cor_validation) :-
    (   active_persona(Persona)
    ->  forall(
            (   persona_cor_value(Persona, Key, Value),
                persona_cor_chain(Persona, Key, Value, GapType, GapValue)
            ),
            assert_unnamed_slot_once(Persona, GapType, GapValue)
        )
    ;   true
    ).

% Default chain: if component is given, it should be a known concept
:- discontiguous persona_cor_chain/5.
persona_cor_chain(_, component, Value, unknown_component, Value) :-
    Value \= '',
    \+ triple(Value, is_a, _),
    \+ triple(Value, has_observation_source, _).

% === SOMA DEVELOPER PERSONA CHAINS ===
% These detect when the system needs new skills, rules, or conventions.

% Chain: component worked on has no skill → suggest creating one
persona_cor_chain(soma_developer, component, Value, needs_skill, Value) :-
    Value \= '', Value \= idle,
    triple(Value, has_observation_source, _),
    \+ triple(Value, has_skill, _),
    findall(_, (triple(V2, is_a, _), V2 = Value), Obs),
    length(Obs, N), N > 3.

% Chain: approach mentions a pattern that has no convention → suggest adding one
persona_cor_chain(soma_developer, approach, Value, needs_convention, Value) :-
    Value \= '',
    atom_string(Value, VStr),
    (   sub_string(VStr, _, _, _, "convention")
    ;   sub_string(VStr, _, _, _, "validate")
    ;   sub_string(VStr, _, _, _, "enforce")
    ),
    \+ triple(Value, is_a, _).

% Chain: rationale contains "always" or "never" → suggests a rule
persona_cor_chain(soma_developer, rationale, Value, needs_rule, Value) :-
    Value \= '',
    atom_string(Value, VStr),
    (   sub_string(VStr, _, _, _, "always")
    ;   sub_string(VStr, _, _, _, "never")
    ;   sub_string(VStr, _, _, _, "must")
    ),
    \+ triple(Value, is_a, _).

% Chain: risk mentions "fragility" or "break" → needs defensive convention
persona_cor_chain(soma_developer, risk, Value, needs_defensive_chain, Value) :-
    Value \= '', Value \= none,
    atom_string(Value, VStr),
    (   sub_string(VStr, _, _, _, "fragil")
    ;   sub_string(VStr, _, _, _, "break")
    ;   sub_string(VStr, _, _, _, "crash")
    ;   sub_string(VStr, _, _, _, "silent")
    ).

% Compose sentences for dev persona chain gaps
compose_hierarchy_sentence(_C, unknown_component, Value, Sentence) :-
    !,
    format(atom(Sentence),
        'DEV: Component ~w is not yet observed in SOMA. Consider observing it via add_event.',
        [Value]).
compose_hierarchy_sentence(_C, needs_skill, Value, Sentence) :-
    !,
    format(atom(Sentence),
        'DEV: Component ~w has been observed 3+ times but has no skill. Consider creating understand-soma reference or standalone skill.',
        [Value]).
compose_hierarchy_sentence(_C, needs_convention, Value, Sentence) :-
    !,
    format(atom(Sentence),
        'DEV: Approach ~w suggests validation/enforcement but no convention exists. Consider adding a Prolog convention via add_rule.',
        [Value]).
compose_hierarchy_sentence(_C, needs_rule, Value, Sentence) :-
    !,
    format(atom(Sentence),
        'DEV: Rationale ~w contains invariant language (always/never/must). Consider writing a Claude Code rule.',
        [Value]).
compose_hierarchy_sentence(_C, needs_defensive_chain, Value, Sentence) :-
    !,
    format(atom(Sentence),
        'DEV: Risk ~w mentions fragility/breakage. Consider adding a defensive deduction chain.',
        [Value]).

% Compose persona mismatch sentence
compose_hierarchy_sentence(_C, persona_mismatch, Domain, Sentence) :-
    !,
    (   active_persona(Persona)
    ->  format(atom(Sentence),
            'PERSONA MISMATCH: Active persona ~w does not cover domain ~w. Switch persona or assign domain.',
            [Persona, Domain])
    ;   Sentence = 'PERSONA MISMATCH: No active persona but domain check triggered.'
    ).

% ======================================================================
% SKILL ENDEAVOR TEMPLATES — skills trigger workflow endeavors
%
% Universal: no specific skill names, only structural patterns.
% When Skill tool fires and that skill has has_endeavor_template,
% auto-open the endeavor. When skills lack templates, flag them.
% ======================================================================

% Auto-open endeavor when skill with template is activated
check_convention(skill_endeavor_activation) :-
    forall(
        (   triple(Evt, tool_name, skill),
            triple(Evt, skill_name, SkillName),
            triple(SkillName, has_endeavor_template, Template),
            \+ open_endeavor(Template, _, _)
        ),
        (   get_time(T),
            assertz(open_endeavor(Template, SkillName, T)),
            retractall(current_focus(_)),
            assertz(current_focus(Template))
        )
    ).

% Flag skills without endeavor templates
check_convention(skill_completion_request) :-
    forall(
        (   triple(Skill, is_a, skill),
            triple(Skill, has_observation_source, _),
            \+ triple(Skill, has_endeavor_template, _)
        ),
        assert_unnamed_slot_once(Skill, needs_endeavor_template, workflow_spec)
    ).

% Flag skills without domain assignments
check_convention(skill_domain_request) :-
    forall(
        (   triple(Skill, is_a, skill),
            triple(Skill, has_observation_source, _),
            \+ triple(Skill, has_domains, _)
        ),
        assert_unnamed_slot_once(Skill, needs_domains, domain_list)
    ).

% Compose sentences for skill completion gaps
compose_hierarchy_sentence(_C, needs_endeavor_template, _, Sentence) :-
    !,
    Sentence = 'SKILL: No endeavor template. Define workflow via has_endeavor_template.'.
compose_hierarchy_sentence(_C, needs_domains, _, Sentence) :-
    !,
    Sentence = 'SKILL: No domain assignment. Assign via has_domains.'.

% Boot: assert all seed triples into the live graph on consult
:- forall(seed_triple(S, P, O), assert_triple_once(S, P, O)).

% ======================================================================
% SEED T-BOX — structural conventions for GNOSYS types
%
% These are the smallest universal shapes. More conventions accumulate via
% meta-observations that assert new required_restriction/3 facts or new
% check_convention/1 clauses.
% ======================================================================

% A process: whatever an agent does with inputs and outputs, realized as steps.
required_restriction(process, has_steps, template_sequence).
required_restriction(process, has_roles, role_list).
required_restriction(process, has_inputs, input_spec).
required_restriction(process, has_outputs, output_spec).

% A template method: a callable function shape.
required_restriction(template_method, has_method_name, string_value).
required_restriction(template_method, has_method_body, string_value).
required_restriction(template_method, has_method_parameters, string_value).

% A template sequence: an ordered list of template methods.
required_restriction(template_sequence, has_step, template_method).

% Codified / programmed process — the compilable shapes.
required_restriction(codified_process, has_sop, string_value).
required_restriction(programmed_process, has_executable_code, string_value).
required_restriction(programmed_process, authorized_by, authorized_personnel).

% A deduction chain: premise (Prolog goal) + conclusion (what fires if premise fails).
required_restriction(deduction_chain, has_deduction_premise, string_value).
required_restriction(deduction_chain, has_deduction_conclusion, string_value).

% A Prolog rule: head + body as Prolog source strings.
required_restriction(prolog_rule, has_rule_head, string_value).
required_restriction(prolog_rule, has_rule_body, string_value).

% ======================================================================
% JANUS-FRIENDLY REPORT WRAPPERS
% ======================================================================

get_graph_str(Str) :-
    findall(triple(S, P, O), triple(S, P, O), Triples),
    length(Triples, NT),
    findall(unnamed(C, P, T), unnamed_slot(C, P, T), Unnamed),
    length(Unnamed, NU),
    with_output_to(atom(Str),
        (   format('graph: ~w triples, ~w unnamed slots~n', [NT, NU]),
            forall(member(triple(S, P, O), Triples),
                format('  ~w ~w ~w~n', [S, P, O])
            ),
            forall(member(unnamed(C, P, T), Unnamed),
                format('  UNNAMED: ~w needs ~w (expected ~w)~n', [C, P, T])
            )
        )).

% Specialized: integration discovery uses known_bridge info
compose_gap_sentence(C, has_delivery_method, _, Sentence) :-
    !,
    (   compose_integration_sentence(C, Sentence)
    ->  true
    ;   format(atom(Sentence),
            '~w needs has_delivery_method. Ask human: how does the output get delivered?',
            [C])
    ).

% Compose a natural language error sentence from an unnamed_slot.
% The sentence is DERIVED from the logic: what you claimed + what the
% universal requires + what's missing.
compose_gap_sentence(C, Prop, ExpectedType, Sentence) :-
    (   sub_atom(Prop, Before, _, _, '_should_be_')
    ->  sub_atom(Prop, 0, Before, _, RealProp),
        (   triple(C, RealProp, WrongValue)
        ->  (   triple(WrongValue, is_a, WrongType)
            ->  format(atom(Sentence),
                    '~w has ~w=~w but that is ~w, not ~w. Create a ~w concept instead.',
                    [C, RealProp, WrongValue, WrongType, ExpectedType, ExpectedType])
            ;   format(atom(Sentence),
                    '~w has ~w=~w but it should be a ~w. Create a ~w concept instead.',
                    [C, RealProp, WrongValue, ExpectedType, ExpectedType])
            )
        ;   format(atom(Sentence),
                '~w needs ~w as ~w (wrong type given). Provide it.',
                [C, RealProp, ExpectedType])
        )
    ;   (   triple(C, is_a, ClaimedType),
            ClaimedType \= string_value, ClaimedType \= int_value,
            ClaimedType \= float_value, ClaimedType \= bool_value,
            ClaimedType \= list_value, ClaimedType \= dict_value
        ->  (   authorized_source(Prop, Source, Reason)
            ->  format(atom(Sentence),
                    '~w claims to be ~w. ~w requires ~w (~w). Ask ~w for ~w because ~w.',
                    [C, ClaimedType, ClaimedType, Prop, ExpectedType, Source, Prop, Reason])
            ;   format(atom(Sentence),
                    '~w claims to be ~w. ~w requires ~w (~w). ~w does not have ~w. Provide it.',
                    [C, ClaimedType, ClaimedType, Prop, ExpectedType, C, Prop])
            )
        ;   (   authorized_source(Prop, Source, Reason)
            ->  format(atom(Sentence),
                    '~w needs ~w (~w). Ask ~w because ~w.',
                    [C, Prop, ExpectedType, Source, Reason])
            ;   format(atom(Sentence),
                    '~w needs ~w (~w). Provide it.',
                    [C, Prop, ExpectedType])
            )
        )
    ).

% Build all gap sentences for current unnamed_slots.
compose_all_gap_sentences(Sentences) :-
    findall(S,
        (   unnamed_slot(C, P, T),
            P \= unknown_domain, P \= unknown_subdomain, P \= domain_not_in_project,
            P \= subdomain_not_in_domain, P \= drift_from_open_work, P \= persona_mismatch,
            P \= needs_skill, P \= needs_convention, P \= needs_rule, P \= needs_defensive_chain,
            P \= unknown_component, P \= needs_endeavor_template, P \= needs_domains,
            compose_gap_sentence(C, P, T, S)
        ),
        GapSentences
    ),
    findall(S,
        (   unnamed_slot(C, P, T),
            (P = unknown_domain ; P = unknown_subdomain ; P = domain_not_in_project ; P = subdomain_not_in_domain ; P = drift_from_open_work ; P = persona_mismatch ; P = needs_skill ; P = needs_convention ; P = needs_rule ; P = needs_defensive_chain ; P = unknown_component ; P = needs_endeavor_template ; P = needs_domains),
            compose_hierarchy_sentence(C, P, T, S)
        ),
        HierSentences
    ),
    findall(S,
        (ses_report(C, SC, TC), compose_ses_sentence(C, SC, TC, S)),
        SESSentences
    ),
    compose_endeavor_status(EndSentences),
    findall(S,
        (   calendar_spec_emitted(Concept),
            triple(Concept, has_calendar_spec, Path),
            compose_calendar_sentence(Concept, Path, S)
        ),
        CalSentences
    ),
    compose_surf_status(SurfSentences),
    compose_surf_analytics(AnalyticsSentences),
    append(GapSentences, HierSentences, S1),
    append(S1, SESSentences, S2),
    append(S2, EndSentences, S3),
    append(S3, CalSentences, S4),
    append(S4, SurfSentences, S5),
    append(S5, AnalyticsSentences, Sentences).

% ======================================================================
% TESTS — universal mechanism
% ======================================================================

test_graph_ingestion :-
    retractall(triple(_, _, _)),
    assert_triples_from_carton(alice, [rel(is_a, [agent]), rel(part_of, [org_one])]),
    triple(alice, is_a, agent),
    triple(alice, part_of, org_one),
    retractall(triple(_, _, _)).

test_convention_missing :-
    retractall(triple(_, _, _)),
    retractall(unnamed_slot(_, _, _)),
    assert_triples_from_carton(my_proc, [rel(is_a, [process])]),
    run_all_conventions,
    unnamed_slot(my_proc, has_steps, template_sequence),
    unnamed_slot(my_proc, has_roles, role_list),
    unnamed_slot(my_proc, has_inputs, input_spec),
    unnamed_slot(my_proc, has_outputs, output_spec),
    retractall(triple(_, _, _)),
    retractall(unnamed_slot(_, _, _)).

test_healing_from_neighbor :-
    retractall(triple(_, _, _)),
    retractall(unnamed_slot(_, _, _)),
    retractall(heal_log(_, _, _, _)),
    % Claim foo is a process with a linked object bar that's a role_list
    assert_triples_from_carton(foo, [rel(is_a, [process]), rel(related, [bar])]),
    assert_triples_from_carton(bar, [rel(is_a, [role_list])]),
    run_all_conventions,
    heal_unnamed,
    % has_roles should have been healed to bar via neighbor strategy
    triple(foo, has_roles, bar),
    retractall(triple(_, _, _)),
    retractall(unnamed_slot(_, _, _)),
    retractall(heal_log(_, _, _, _)).

