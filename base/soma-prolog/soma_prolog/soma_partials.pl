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

% tv(Value, Type) — assert the relationship AND the value's type
assert_typed_value(Target, Pred, tv(Value, Type)) :- !,
    assert_triple_once(Target, Pred, Value),
    assert_triple_once(Value, is_a, Type).

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

heal_unnamed :-
    findall(slot(C, P, T), unnamed_slot(C, P, T), Slots),
    forall(member(slot(C, P, T), Slots), heal_one(C, P, T)).

heal_one(C, P, T) :-
    (   % Strategy 1: a neighbor of C that is of the right type
        triple(C, _OtherPred, V),
        triple(V, is_a, T),
        V \= C
    ->  assert_triple_once(C, P, V),
        retract(unnamed_slot(C, P, T)),
        assertz(heal_log(C, P, T, healed_from_neighbor(V)))
    ;   true  % leave as unnamed
    ).

% ======================================================================
% STATUS
% ======================================================================

% SOUP = any value on this concept is typed string_value (arbitrary, unverified).
% CODE = all values are typed as real types (non-string, progressively typed).
% This IS the core of SOMA. Everything else is plumbing around this.
concept_has_soup_value(C) :-
    triple(C, _Prop, V),
    V \= C,
    triple(V, is_a, string_value).

deduce_validation_status(C, code) :-
    triple(C, is_a, _),
    \+ concept_has_soup_value(C),
    \+ unnamed_slot(C, _, _), !.
deduce_validation_status(C, soup) :-
    triple(C, is_a, _),
    (concept_has_soup_value(C) ; unnamed_slot(C, _, _)), !.
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
