% SOMA Deduction Chains — partial resolution routing
%
% WHAT THIS FILE ACTUALLY DOES:
% Takes a concept with unnamed partials and routes each partial into one of
% three buckets based on what the deduction chain can provide:
%   - from_context: existing observations / CA / sibling concepts can fill it
%   - from_llm: enough filled partials exist as context for an LLM to generate
%   - from_human: requires reality (authorization, identity, deadline, etc.)
% Creates dispatches accordingly.
%
% HISTORICAL NOTE — this file was originally named soma_y_mesh.pl and labeled
% as "y-mesh". That was wrong. The real y-mesh is the Y1→Y6 climb driven by
% SES typed depth + Griess phase transitions (lives in YOUKNOW Python as
% yo_strata.py + universal_pattern.py + griess_constructor.py). None of that
% is implemented here. What this file does is deduction chain routing, not
% stratum climbing. The stratum_type / classify_stratum / concept_stratum /
% next_stratum / assign_stratum / get_stratum_str predicates below are
% commented out — they were pasted y-mesh labels that never drove any
% decision (the resolve logic uses property presence + hardcoded reality
% property names, not stratum). Real y-mesh will be built when SES typed
% depth and Griess are ported to Prolog.

:- dynamic generation_attempt/4.   % generation_attempt(Concept, Stratum, Method, Result)
:- dynamic reality_required/3.     % reality_required(Concept, Stratum, WhatNeeded)

% === COMMENTED OUT: fake stratum labels that never drove anything ===
% :- discontiguous stratum_type/2.
% :- dynamic concept_stratum/2.      % concept_stratum(ConceptName, Stratum) — Y1-Y6
% :- dynamic stratum_partial/4.      % stratum_partial(Concept, Stratum, Prop, Status)
% :- dynamic y_mesh_state/3.         % y_mesh_state(ConceptName, CurrentStratum, Action)

% ======================================================================
% COMMENTED OUT — FAKE STRATUM LABELS (was written wrong)
%
% Original intent: Y1-Y6 stratum climbing driven by SES typed depth +
% Griess phase. What actually got written is presence-check labeling
% that never drives any decision. The real resolve logic below uses
% property presence + hardcoded reality property names, not stratum.
% Real y-mesh will be built when SES typed depth and Griess are ported
% from YOUKNOW Python (yo_strata.py, universal_pattern.py,
% griess_constructor.py) into Prolog.
% ======================================================================

% stratum_type(y1, foundation).
% stratum_type(y2, universal).
% stratum_type(y3, methods).
% stratum_type(y4, implementation).
% stratum_type(y5, restricted).
% stratum_type(y6, generator).
%
% stratum_order(y1, 1).
% stratum_order(y2, 2).
% stratum_order(y3, 3).
% stratum_order(y4, 4).
% stratum_order(y5, 5).
% stratum_order(y6, 6).
%
% next_stratum(y1, y2).
% next_stratum(y2, y3).
% next_stratum(y3, y4).
% next_stratum(y4, y5).
% next_stratum(y5, y6).
%
% classify_stratum(Concept, y1) :-
%     (   has_rel(Concept, is_a, aut)
%     ;   has_rel(Concept, is_a, twi)
%     ;   has_rel(Concept, is_a, twilitelang)
%     ;   concept_type(Concept, owl_class)
%     ;   concept_type(Concept, owl_property)
%     ;   concept_type(Concept, owl_restriction)
%     ), !.
% classify_stratum(Concept, y2) :-
%     (   concept_type(Concept, abstract_class)
%     ;   concept_type(Concept, base_type)
%     ;   has_rel(Concept, is_a, renderable_piece)
%     ;   has_rel(Concept, is_a, system_actor)
%     ;   has_rel(Concept, is_a, template_attribute)
%     ;   has_rel(Concept, is_a, template_method)
%     ;   (concept_type(Concept, _), \+ has_rel(Concept, has_method_body, _),
%          has_rel(Concept, is_a, _AbstractParent))
%     ), !.
% classify_stratum(Concept, y3) :-
%     (   concept_type(Concept, template_method)
%     ;   has_rel(Concept, is_a, template_method)
%     ;   has_rel(_, has_template_method, Concept)
%     ), !.
% classify_stratum(Concept, y4) :-
%     (   concept_type(Concept, code_class)
%     ;   concept_type(Concept, code_function)
%     ;   has_rel(Concept, has_method_body, _)
%     ;   has_rel(Concept, has_executable_code, _)
%     ), !.
% classify_stratum(Concept, y5) :-
%     (   named_function(Concept, _, Partials),
%         Partials \= []
%     ;   concept_type(Concept, codified_process)
%     ), !.
% classify_stratum(Concept, y6) :-
%     (   concept_type(Concept, configurator)
%     ;   concept_type(Concept, maker)
%     ;   has_rel(Concept, generates_maker, _)
%     ;   concept_type(Concept, programmed_process)
%     ), !.
% classify_stratum(_, unclassified).
%
% assign_stratum(Concept) :-
%     classify_stratum(Concept, Stratum),
%     (   concept_stratum(Concept, _)
%     ->  retract(concept_stratum(Concept, _))
%     ;   true
%     ),
%     assert(concept_stratum(Concept, Stratum)).

% ======================================================================
% DEDUCTION CHAIN: The decision engine for routing partials
% ======================================================================

% Can this partial be filled from existing context? (deduction chains)
can_fill_from_context(Concept, Prop) :-
    partial(Concept, Prop, TargetType, unnamed),
    % Check: is there an inference rule that can fill this?
    (   % CA resolution available for code types
        is_code_type(TargetType),
        strip_giint_prefix(Concept, SearchTerm),
        ca_entity(SearchTerm, _)
    ;   % Existing observation matches this property
        observation(_, Key, _, _),
        property_matches_key(Prop, Key)
    ;   % Another concept already has this value (copy from sibling)
        concept_type(Sibling, SameType),
        concept_type(Concept, SameType),
        Sibling \= Concept,
        has_rel(Sibling, Prop, Value),
        ground(Value)
    ).

% Can this partial be generated by LLM? (enough context exists)
can_generate_from_llm(Concept, Prop) :-
    partial(Concept, Prop, _TargetType, unnamed),
    \+ can_fill_from_context(Concept, Prop),
    % Need at least SOME filled partials as context for LLM
    partial_count(Concept, Total, Unnamed, Filled),
    Filled > 0,
    % Not a reality-requiring type
    \+ requires_reality(Concept, Prop).

% Does this partial require reality (human observation)?
requires_reality(Concept, Prop) :-
    partial(Concept, Prop, _TargetType, unnamed),
    % Properties that MUST come from reality:
    (   Prop = authorized_by          % Human authorization
    ;   Prop = has_identity           % Source identity
    ;   Prop = has_approval           % Business approval
    ;   Prop = has_threshold          % Business thresholds
    ;   Prop = has_budget             % Budget amounts
    ;   Prop = has_deadline           % Real deadlines
    ;   Prop = has_contact            % Contact info
    ).

% ======================================================================
% DEDUCTION CHAIN STEP: Route one concept's partials
% ======================================================================

% Main entry: for a concept with unnamed partials, route each one
deduction_chain_step(Concept, Result) :-
    findall(
        Prop,
        partial(Concept, Prop, _, unnamed),
        UnnamedProps
    ),
    (   UnnamedProps = []
    ->  Result = complete
    ;   deduction_chain_fill_step(Concept, UnnamedProps, FillResults),
        Result = filling(FillResults)
    ).

% Try to fill each unnamed partial using the three-path resolution
deduction_chain_fill_step(Concept, Props, Results) :-
    findall(
        result(Prop, Method),
        (   member(Prop, Props),
            deduction_chain_resolve_one(Concept, Prop, Method)
        ),
        Results
    ).

% Resolve one partial — choose method
deduction_chain_resolve_one(Concept, Prop, from_context(Value)) :-
    can_fill_from_context(Concept, Prop),
    !,
    % Actually fill it
    (   % Try CA first
        partial(Concept, Prop, TargetType, unnamed),
        is_code_type(TargetType),
        resolve_partial_from_ca(Concept, Prop, TargetType)
    ->  Value = ca_resolved
    ;   % Try matching observation
        observation(_, Key, Value, _),
        property_matches_key(Prop, Key),
        resolve_partial_from_observation(Concept, Prop, Value)
    ->  true
    ;   Value = context_deduced
    ),
    assert(generation_attempt(Concept, Prop, context, success)).

deduction_chain_resolve_one(Concept, Prop, from_llm(dispatch)) :-
    can_generate_from_llm(Concept, Prop),
    !,
    % Dispatch to LLM with filled partials as context
    findall(
        ctx(P, V),
        (partial(Concept, P, _, resolved(V)) ; partial(Concept, P, _, ca_resolved(V))),
        Context
    ),
    create_dispatch(generate_rule, deduction_chain_fill(Concept, Prop, Context)),
    assert(generation_attempt(Concept, Prop, llm, dispatched)).

deduction_chain_resolve_one(Concept, Prop, from_human(Reason)) :-
    requires_reality(Concept, Prop),
    !,
    format(atom(Reason), 'Property ~w on ~w requires human observation (reality-level event)', [Prop, Concept]),
    create_dispatch(ask_source, deduction_chain_needs_reality(Concept, Prop)),
    assert(reality_required(Concept, Prop, Reason)),
    assert(generation_attempt(Concept, Prop, human, requested)).

% Fallback: can't resolve — need more observations
deduction_chain_resolve_one(Concept, Prop, needs_more_observations) :-
    assert(generation_attempt(Concept, Prop, none, insufficient_context)).

% ======================================================================
% DEDUCTION CHAIN LOOP: Keep running until stuck or complete
% ======================================================================

% Run deduction chain routing until it can't proceed
deduction_chain_run(Concept, FinalResult) :-
    deduction_chain_step(Concept, StepResult),
    (   StepResult = complete
    ->  FinalResult = StepResult
    ;   StepResult = filling(FillResults)
    ->  % Check if any fills succeeded from context
        include(is_context_fill, FillResults, ContextFills),
        (   ContextFills \= []
        ->  % Some filled from context — try again
            deduction_chain_run(Concept, FinalResult)
        ;   % All remaining need LLM or human — stop here
            FinalResult = blocked(FillResults)
        )
    ).

is_context_fill(result(_, from_context(_))).

% ======================================================================
% JANUS WRAPPERS
% ======================================================================

deduction_chain_step_str(Concept, Str) :-
    deduction_chain_step(Concept, Result),
    with_output_to(atom(Str),
        (   format('deduction chain step for ~w: ~w~n', [Concept, Result])
        )).

deduction_chain_run_str(Concept, Str) :-
    deduction_chain_run(Concept, Result),
    with_output_to(atom(Str),
        (   format('deduction chain result for ~w: ~w~n', [Concept, Result])
        )).

% ======================================================================
% TESTS
% ======================================================================

% Test: reality-requiring properties identified
test_reality_required :-
    create_partials(test_reality, process),
    assert(partial(test_reality, authorized_by, authorized_personnel, unnamed)),
    requires_reality(test_reality, authorized_by),
    % Clean up
    retractall(concept_type(test_reality, _)),
    retractall(partial(test_reality, _, _, _)),
    retractall(heal_log(test_reality, _, _, _)).

% Test: deduction chain step on a concept with partials
test_deduction_chain_step :-
    create_partials(test_dchain, process),
    deduction_chain_step(test_dchain, Result),
    % Should be filling (has unnamed partials)
    Result = filling(_),
    % Clean up
    retractall(concept_type(test_dchain, _)),
    retractall(partial(test_dchain, _, _, _)),
    retractall(heal_log(test_dchain, _, _, _)),
    retractall(generation_attempt(test_dchain, _, _, _)),
    retractall(reality_required(test_dchain, _, _)),
    retractall(dispatch_queue(_, _, _)).

% COMMENTED OUT — tests for the fake stratum classification
% test_classify_code_y4 :-
%     assert(concept_type(test_code_cls, code_class)),
%     classify_stratum(test_code_cls, y4),
%     retract(concept_type(test_code_cls, code_class)).
%
% test_classify_configurator_y6 :-
%     assert(concept_type(test_cfg, configurator)),
%     classify_stratum(test_cfg, y6),
%     retract(concept_type(test_cfg, configurator)).
