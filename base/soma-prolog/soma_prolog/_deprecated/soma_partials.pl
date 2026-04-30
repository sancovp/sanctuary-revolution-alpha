% SOMA Partials — The _Unnamed deduction chain
%
% Core insight: When you know a type's restrictions, you KNOW what partials
% must exist. Creating _Unnamed partials IS deduction: "X is_a T, T requires P,
% therefore X must have P, but P is unknown → create P_Unnamed."
%
% Filling _Unnamed partials is the compilation pipeline:
%   1. Observation fills it (someone tells us the value)
%   2. CA resolution fills it (code already exists, we find it)
%   3. LLM generation fills it (agent creates the value)
%   4. Inference fills it (Pellet/Prolog deduces the value)
%
% This IS the SOMA loop applied to structure:
%   SOUP = has _Unnamed partials
%   TYPED = _Unnamed replaced with real values
%   CODE = all values present + authorized + executable

:- discontiguous required_restriction/3.
:- discontiguous is_code_type/1.

:- dynamic partial/4.             % partial(ConceptName, Property, TargetType, Status)
                                   % Status: unnamed | resolved(Value) | ca_resolved(Value) | generated(Value)
:- dynamic concept_type/2.        % concept_type(ConceptName, TypeName)
:- dynamic has_rel/3.             % has_rel(Concept, Property, Target)
:- dynamic required_restriction/3. % required_restriction(Type, Property, TargetType)
:- dynamic is_code_type/1.        % is_code_type(TypeName)
:- dynamic validation_status/2.   % validation_status(Concept, soup|code|ont)
:- dynamic ca_entity/2.           % ca_entity(SearchTerm, ResolvedName) — cache of CA lookups
:- dynamic heal_log/4.            % heal_log(Concept, Property, TargetType, Result)

% ======================================================================
% CODE TYPES — Types that are "primitively real" (code exists without ONT)
% ======================================================================

is_code_type(code_file).
is_code_type(code_class).
is_code_type(code_method).
is_code_type(code_function).
is_code_type(code_attribute).
is_code_type(code_repository).

% ======================================================================
% GIINT PREFIX STRIPPING — Extract search term from GIINT concept names
% ======================================================================

giint_prefix('Giint_Project_').
giint_prefix('Giint_Feature_').
giint_prefix('Giint_Component_').
giint_prefix('Giint_Deliverable_').
giint_prefix('Giint_Task_').
giint_prefix('GIINT_Project_').
giint_prefix('GIINT_Feature_').
giint_prefix('GIINT_Component_').
giint_prefix('GIINT_Deliverable_').
giint_prefix('GIINT_Task_').

strip_giint_prefix(Name, SearchTerm) :-
    giint_prefix(Prefix),
    atom_concat(Prefix, Rest, Name),
    !,
    % Also strip _Unnamed suffix
    (   atom_concat(Base, '_Unnamed', Rest)
    ->  SearchTerm = Base
    ;   SearchTerm = Rest
    ).
strip_giint_prefix(Name, Name).  % No prefix → return as-is

% ======================================================================
% PARTIAL CREATION — Deduce what _Unnamed partials must exist
% ======================================================================

% "Given concept X of type T, create _Unnamed partials for all required restrictions"
create_partials(ConceptName, ConceptType) :-
    assert(concept_type(ConceptName, ConceptType)),
    forall(
        required_restriction(ConceptType, Prop, TargetType),
        create_one_partial(ConceptName, Prop, TargetType)
    ).

% Create one partial if it doesn't already exist
create_one_partial(ConceptName, Prop, TargetType) :-
    (   has_rel(ConceptName, Prop, _)
    ->  true  % Already has this relationship — skip
    ;   partial(ConceptName, Prop, TargetType, _)
    ->  true  % Already has a partial for this — skip
    ;   % Create the _Unnamed partial
        assert(partial(ConceptName, Prop, TargetType, unnamed)),
        % Log it
        assert(heal_log(ConceptName, Prop, TargetType, created_unnamed))
    ).

% ======================================================================
% PARTIAL RESOLUTION — Fill _Unnamed with real values
% ======================================================================

% Resolution method 1: Direct observation (someone tells us)
resolve_partial_from_observation(ConceptName, Prop, Value) :-
    partial(ConceptName, Prop, _TargetType, unnamed),
    retract(partial(ConceptName, Prop, _TargetType, unnamed)),
    assert(partial(ConceptName, Prop, _TargetType, resolved(Value))),
    assert(has_rel(ConceptName, Prop, Value)),
    assert(heal_log(ConceptName, Prop, _TargetType, resolved_from_observation(Value))).

% Resolution method 2: CA lookup (code already exists)
resolve_partial_from_ca(ConceptName, Prop, TargetType) :-
    partial(ConceptName, Prop, TargetType, unnamed),
    is_code_type(TargetType),
    strip_giint_prefix(ConceptName, SearchTerm),
    ca_entity(SearchTerm, ResolvedName),
    !,
    retract(partial(ConceptName, Prop, TargetType, unnamed)),
    assert(partial(ConceptName, Prop, TargetType, ca_resolved(ResolvedName))),
    assert(has_rel(ConceptName, Prop, ResolvedName)),
    assert(heal_log(ConceptName, Prop, TargetType, ca_resolved(ResolvedName))).

% Resolution method 3: LLM generation (dispatch to generate)
resolve_partial_via_llm(ConceptName, Prop, TargetType) :-
    partial(ConceptName, Prop, TargetType, unnamed),
    \+ is_code_type(TargetType),  % Code types use CA, not LLM
    create_dispatch(generate_rule, fill_partial(ConceptName, Prop, TargetType)),
    assert(heal_log(ConceptName, Prop, TargetType, dispatched_to_llm)).

% Resolution method 4: Inference (Pellet/Prolog deduced it)
resolve_partial_from_inference(ConceptName, Prop, TargetType, InferredValue) :-
    partial(ConceptName, Prop, TargetType, unnamed),
    retract(partial(ConceptName, Prop, TargetType, unnamed)),
    assert(partial(ConceptName, Prop, TargetType, resolved(InferredValue))),
    assert(has_rel(ConceptName, Prop, InferredValue)),
    assert(heal_log(ConceptName, Prop, TargetType, inferred(InferredValue))).

% ======================================================================
% RECURSIVE HEALING — Stamp out the whole required graph
% ======================================================================

% "Heal concept X: create all its partials, then recursively heal each partial"
heal_recursive(ConceptName, ConceptType, MaxDepth) :-
    heal_recursive(ConceptName, ConceptType, MaxDepth, 0, []).

heal_recursive(_, _, MaxDepth, Depth, _) :-
    Depth >= MaxDepth, !.  % Stop at max depth

heal_recursive(ConceptName, ConceptType, MaxDepth, Depth, Seen) :-
    \+ member(ConceptName, Seen),
    create_partials(ConceptName, ConceptType),
    NewDepth is Depth + 1,
    % For each created partial, try to resolve it
    forall(
        partial(ConceptName, Prop, TargetType, unnamed),
        (   % Try CA resolution first for code types
            (   is_code_type(TargetType),
                resolve_partial_from_ca(ConceptName, Prop, TargetType)
            ->  true
            ;   % Otherwise create an _Unnamed concept and recurse into IT
                format(atom(ChildName), '~w_~w_Unnamed', [TargetType, ConceptName]),
                assert(has_rel(ConceptName, Prop, ChildName)),
                retract(partial(ConceptName, Prop, TargetType, unnamed)),
                assert(partial(ConceptName, Prop, TargetType, resolved(ChildName))),
                heal_recursive(ChildName, TargetType, MaxDepth, NewDepth, [ConceptName|Seen])
            )
        )
    ).

% ======================================================================
% COMPLETENESS CHECK — How filled is this concept?
% ======================================================================

% "How many partials does this concept have?"
partial_count(ConceptName, Total, Unnamed, Resolved) :-
    findall(P, partial(ConceptName, P, _, _), AllPartials),
    length(AllPartials, Total),
    findall(P, partial(ConceptName, P, _, unnamed), UnnamedPartials),
    length(UnnamedPartials, Unnamed),
    Resolved is Total - Unnamed.

% "Is this concept complete? (all partials resolved)"
concept_complete(ConceptName) :-
    concept_type(ConceptName, _),
    \+ partial(ConceptName, _, _, unnamed).

% "What's still missing?"
missing_partials(ConceptName, Missing) :-
    findall(
        missing(Prop, TargetType),
        partial(ConceptName, Prop, TargetType, unnamed),
        Missing
    ).

% ======================================================================
% VALIDATION STATUS DEDUCTION
% ======================================================================

% "SOUP = has unnamed partials"
deduce_validation_status(ConceptName, soup) :-
    partial(ConceptName, _, _, unnamed), !.

% "CODE = all partials resolved (Pellet would confirm)"
deduce_validation_status(ConceptName, code) :-
    concept_type(ConceptName, _),
    \+ partial(ConceptName, _, _, unnamed),
    !.

% "ONT = code + derivation chain closes to CatOfCat"
% (placeholder: ONT requires Pellet confirmation)
deduce_validation_status(ConceptName, ont) :-
    deduce_validation_status(ConceptName, code),
    % TODO: check derivation chain via Pellet
    fail.  % For now, ONT requires explicit Pellet confirmation

% Default: unvalidated
deduce_validation_status(ConceptName, unvalidated) :-
    \+ concept_type(ConceptName, _).

% ======================================================================
% PROMOTION READINESS
% ======================================================================

% "Ready for promotion from SOUP to CODE when all partials are filled"
ready_for_promotion(ConceptName) :-
    deduce_validation_status(ConceptName, soup),
    % Check if we could fill all remaining partials
    findall(P, partial(ConceptName, P, _, unnamed), Remaining),
    Remaining = [].  % None remaining = ready

% Actually: ready when currently soup but ALL restrictions are met
ready_for_code_promotion(ConceptName) :-
    concept_type(ConceptName, Type),
    forall(
        required_restriction(Type, Prop, _),
        has_rel(ConceptName, Prop, _)
    ).

% ======================================================================
% PATTERN DETECTION — Recurring structures suggest new types
% ======================================================================

% "Find concepts that share the same set of relationship types"
shared_pattern(ConceptA, ConceptB, SharedProps) :-
    concept_type(ConceptA, TypeA),
    concept_type(ConceptB, TypeB),
    ConceptA \= ConceptB,
    TypeA = TypeB,
    findall(Prop, has_rel(ConceptA, Prop, _), PropsA),
    findall(Prop, has_rel(ConceptB, Prop, _), PropsB),
    intersection(PropsA, PropsB, SharedProps),
    SharedProps \= [].

% "Count how many concepts match a specific relationship pattern"
pattern_frequency(PropList, Count) :-
    findall(C, (
        concept_type(C, _),
        forall(member(P, PropList), has_rel(C, P, _))
    ), Matches),
    length(Matches, Count).

% "Suggest naming a pattern that appears 3+ times"
suggest_named_pattern(PropList, SuggestedName, Count) :-
    pattern_frequency(PropList, Count),
    Count >= 3,
    atomic_list_concat(PropList, '_and_', SuggestedName).

% ======================================================================
% EMANATION SCORE — Coverage across AI integration types
% ======================================================================

% The 6 AI integration types (from GIINT emanation scoring)
emanation_type(has_skill).
emanation_type(has_flight_config).
emanation_type(has_rule).
emanation_type(has_hook).
emanation_type(has_agent).
emanation_type(has_persona).

% "Emanation score = count of present emanation types / 6"
emanation_score(ConceptName, Score) :-
    findall(ET, (
        emanation_type(ET),
        has_rel(ConceptName, ET, _)
    ), Present),
    length(Present, Count),
    Score is Count / 6.

% "What emanation types are missing?"
missing_emanations(ConceptName, Missing) :-
    findall(ET, (
        emanation_type(ET),
        \+ has_rel(ConceptName, ET, _)
    ), Missing).

% ======================================================================
% JANUS WRAPPERS
% ======================================================================

get_partials_str(ConceptName, Str) :-
    partial_count(ConceptName, Total, Unnamed, Resolved),
    missing_partials(ConceptName, Missing),
    deduce_validation_status(ConceptName, Status),
    with_output_to(atom(Str),
        (   format('~w: ~w/~w filled (status=~w)~n', [ConceptName, Resolved, Total, Status]),
            forall(member(missing(P, T), Missing),
                format('  MISSING: ~w → ~w~n', [P, T])
            )
        )).

get_emanation_str(ConceptName, Str) :-
    emanation_score(ConceptName, Score),
    missing_emanations(ConceptName, Missing),
    with_output_to(atom(Str),
        (   format('~w: emanation=~2f~n', [ConceptName, Score]),
            forall(member(M, Missing),
                format('  MISSING: ~w~n', [M])
            )
        )).

% ======================================================================
% OBSERVATION-DRIVEN PARTIAL CREATION + TEMPLATE TYPING
% String values enter as universal (Aut). Template engineering types them
% into progressively restricted subclasses. Each restriction creates new
% partials. The cascade IS the deduction chain.
% ======================================================================

:- dynamic typed_as/3.            % typed_as(Value, OriginalType, TemplateType)
:- dynamic step_of/3.             % step_of(SequenceId, StepIndex, StepName)
:- dynamic property_matches_key/2. % property_matches_key(OWLProp, ObservationKey)

% --- Property-to-key matching: how observation keys map to OWL properties ---
property_matches_key(has_steps, steps).
property_matches_key(has_steps, process_steps).
property_matches_key(has_roles, roles).
property_matches_key(has_roles, assigned_to).
property_matches_key(has_inputs, inputs).
property_matches_key(has_inputs, input).
property_matches_key(has_outputs, outputs).
property_matches_key(has_outputs, output).
property_matches_key(has_duration, duration_minutes).
property_matches_key(has_duration, duration).
property_matches_key(has_frequency, frequency).
property_matches_key(has_description, description).
property_matches_key(has_sop, sop).
property_matches_key(has_name, name).

% --- Type compatibility: observation types compatible with OWL target types ---
type_compatible(string_value, _).          % Strings can be anything (universal)
type_compatible(int_value, int_value).
type_compatible(float_value, float_value).
type_compatible(bool_value, bool_value).
type_compatible(list_value, list_value).
type_compatible(dict_value, dict_value).

% ======================================================================
% PHASE 1: Observation creates concept + partials
% "I see a task observation → this is a Process → stamp out its required graph"
% ======================================================================

% When a new task observation arrives, create Process concept + partials
on_new_task_observation(EventId, TaskName) :-
    observation(EventId, task, TaskName, string_value),
    (   concept_type(TaskName, _)
    ->  true  % Already known — skip creation
    ;   % First time: create Process with all its partials
        create_partials(TaskName, process),
        assert(heal_log(TaskName, auto_created, process, from_observation(EventId)))
    ).

% ======================================================================
% PHASE 2: Observation fills existing partials
% "This observation's key matches an open partial → fill it"
% ======================================================================

% Check all observations in an event against all open partials
fill_partials_from_event(EventId) :-
    forall(
        observation(EventId, Key, Value, Type),
        try_fill_any_partial(Key, Value, Type)
    ).

% Try to fill any partial that matches this observation key
try_fill_any_partial(Key, Value, Type) :-
    (   % Find a matching partial
        partial(Concept, Prop, TargetType, unnamed),
        property_matches_key(Prop, Key),
        type_compatible(Type, TargetType)
    ->  % Fill it
        resolve_partial_from_observation(Concept, Prop, Value),
        % Now: template-type the value if it's a string
        (   Type = string_value
        ->  try_template_type(Concept, Prop, Value)
        ;   true
        )
    ;   true  % No matching partial — observation noted but doesn't fill anything yet
    ).

% ======================================================================
% PHASE 3: Template typing — strings become typed structures
% "This string looks like X → create typed partials for X's structure"
% ======================================================================

% Try to template-type a string value based on what property it fills
try_template_type(Concept, has_steps, Value) :-
    !,
    % String of comma-separated steps → TemplateSequence
    split_string(Value, ",", " ", StepStrings),
    assert(typed_as(Value, string_value, template_sequence)),
    % Create TemplateMethod partial for each step
    create_step_partials(Concept, StepStrings, 0).

try_template_type(Concept, has_roles, Value) :-
    !,
    % String of comma-separated roles → list of role partials
    split_string(Value, ",", " ", RoleStrings),
    assert(typed_as(Value, string_value, role_list)),
    forall(
        member(RoleStr, RoleStrings),
        (   atom_string(RoleAtom, RoleStr),
            assert(has_rel(Concept, has_role, RoleAtom))
        )
    ).

try_template_type(_Concept, _Prop, _Value).  % Default: no template typing needed

% Create TemplateMethod partials for each step in a sequence
create_step_partials(_, [], _).
create_step_partials(Concept, [StepStr|Rest], Index) :-
    atom_string(StepAtom, StepStr),
    % Record step in sequence
    assert(step_of(Concept, Index, StepAtom)),
    % Each step is a TemplateMethod that needs: body, parameters, return type
    format(atom(StepConceptName), '~w_Step_~w', [Concept, StepAtom]),
    create_partials(StepConceptName, template_method),
    % Link step to parent
    assert(has_rel(Concept, has_step, StepConceptName)),
    NextIndex is Index + 1,
    create_step_partials(Concept, Rest, NextIndex).

% ======================================================================
% PHASE 4: Cascade — template typing creates MORE partials
% "TemplateMethod needs body+params → those are partials too"
% This is the construct_hermes_config pattern: cascading creation
% ======================================================================

% Required restrictions for template types (cascade targets)
required_restriction(template_method, has_method_name, string_value).
required_restriction(template_method, has_method_body, string_value).
required_restriction(template_method, has_method_parameters, string_value).

required_restriction(template_sequence, has_step, template_method).

required_restriction(template_attribute, has_attribute_name, string_value).
required_restriction(template_attribute, has_attribute_type, string_value).

% Process restrictions (what a Process needs to become CodifiedProcess)
required_restriction(process, has_steps, template_sequence).
required_restriction(process, has_roles, role_list).
required_restriction(process, has_inputs, input_spec).
required_restriction(process, has_outputs, output_spec).

% CodifiedProcess adds SOP requirement
required_restriction(codified_process, has_sop, string_value).

% ProgrammedProcess adds code + authorization
required_restriction(programmed_process, has_executable_code, string_value).
required_restriction(programmed_process, authorized_by, authorized_personnel).

% ======================================================================
% PHASE 5: Full observation loop integration
% "Process an event through the partial system"
% ======================================================================

% Process an event: create concepts, fill partials, template-type, cascade
process_event_partials(EventId) :-
    % Phase 1: Create Process concepts from task observations
    forall(
        observation(EventId, task, TaskName, string_value),
        on_new_task_observation(EventId, TaskName)
    ),
    % Phase 2+3: Fill and template-type from ALL observations
    fill_partials_from_event(EventId).

% Janus wrapper
process_event_partials_str(EventId, Str) :-
    process_event_partials(EventId),
    % Report all concepts and their partial status
    findall(
        report(Concept, Total, Unnamed, Resolved, Status),
        (   concept_type(Concept, _),
            partial_count(Concept, Total, Unnamed, Resolved),
            deduce_validation_status(Concept, Status)
        ),
        Reports
    ),
    with_output_to(atom(Str),
        (   format('Event ~w processed. Concepts:~n', [EventId]),
            forall(member(report(C, T, U, R, S), Reports),
                format('  ~w: ~w/~w filled (status=~w)~n', [C, R, T, S])
            )
        )).

% ======================================================================
% TESTS
% ======================================================================

% Test: create partials for a concept with restrictions
test_create_partials :-
    % Set up a type with restrictions
    assert(required_restriction(test_widget, has_name, string_value)),
    assert(required_restriction(test_widget, has_parent, test_container)),
    % Create partials
    create_partials(test_w1, test_widget),
    % Should have 2 unnamed partials
    partial_count(test_w1, 2, 2, 0),
    % Should be SOUP
    deduce_validation_status(test_w1, soup),
    % Clean up
    retractall(required_restriction(test_widget, _, _)),
    retractall(partial(test_w1, _, _, _)),
    retractall(concept_type(test_w1, _)),
    retractall(heal_log(test_w1, _, _, _)).

% Test: resolve partial from observation
test_resolve_partial :-
    assert(required_restriction(test_r, needs_value, string_value)),
    create_partials(test_r1, test_r),
    partial(test_r1, needs_value, string_value, unnamed),
    % Resolve it
    resolve_partial_from_observation(test_r1, needs_value, 'hello_world'),
    % Should now be resolved
    has_rel(test_r1, needs_value, 'hello_world'),
    \+ partial(test_r1, _, _, unnamed),
    % Should be CODE now
    deduce_validation_status(test_r1, code),
    % Clean up
    retractall(required_restriction(test_r, _, _)),
    retractall(partial(test_r1, _, _, _)),
    retractall(concept_type(test_r1, _)),
    retractall(has_rel(test_r1, _, _)),
    retractall(heal_log(test_r1, _, _, _)).

% Test: CA resolution for code types
test_ca_resolution :-
    assert(required_restriction(test_comp, has_code_entity, code_file)),
    assert(ca_entity('Build_Receiver', 'CodeFile_Build_Receiver_Py')),
    create_partials('Giint_Component_Build_Receiver', test_comp),
    % Try CA resolution
    resolve_partial_from_ca('Giint_Component_Build_Receiver', has_code_entity, code_file),
    % Should be CA-resolved
    has_rel('Giint_Component_Build_Receiver', has_code_entity, 'CodeFile_Build_Receiver_Py'),
    % Clean up
    retractall(required_restriction(test_comp, _, _)),
    retractall(ca_entity(build_receiver, _)),
    retractall(partial('Giint_Component_Build_Receiver', _, _, _)),
    retractall(concept_type('Giint_Component_Build_Receiver', _)),
    retractall(has_rel('Giint_Component_Build_Receiver', _, _)),
    retractall(heal_log('Giint_Component_Build_Receiver', _, _, _)).

% Test: emanation scoring
test_emanation_scoring :-
    assert(has_rel(test_comp_e, has_skill, some_skill)),
    assert(has_rel(test_comp_e, has_flight_config, some_flight)),
    assert(has_rel(test_comp_e, has_rule, some_rule)),
    emanation_score(test_comp_e, Score),
    Score =:= 0.5,  % 3 out of 6
    missing_emanations(test_comp_e, Missing),
    length(Missing, 3),  % 3 missing
    % Clean up
    retractall(has_rel(test_comp_e, _, _)).

% Test: observation creates Process concept with partials
test_observation_creates_process :-
    get_time(T),
    format(atom(EId), 'test_obs_proc_~f', [T]),
    assert(event(EId, employee_1, '2026-04-06')),
    assert(observation(EId, task, test_invoice_proc, string_value)),
    assert(observation(EId, duration_minutes, '90', int_value)),
    % Process the event
    process_event_partials(EId),
    % Should have created a concept
    concept_type(test_invoice_proc, process),
    % Should have partials for process requirements
    partial(test_invoice_proc, has_steps, template_sequence, unnamed),
    partial(test_invoice_proc, has_roles, role_list, unnamed),
    % Should be SOUP (has unnamed partials)
    deduce_validation_status(test_invoice_proc, soup),
    % Clean up
    retractall(event(EId, _, _)),
    retractall(observation(EId, _, _, _)),
    retractall(concept_type(test_invoice_proc, _)),
    retractall(partial(test_invoice_proc, _, _, _)),
    retractall(has_rel(test_invoice_proc, _, _)),
    retractall(heal_log(test_invoice_proc, _, _, _)).

% Test: second observation fills a partial
test_observation_fills_partial :-
    % Set up a Process with partials
    create_partials(test_fill_proc, process),
    % Verify it has unnamed partials
    partial(test_fill_proc, has_steps, template_sequence, unnamed),
    % Simulate observation that fills has_steps
    get_time(T),
    format(atom(EId), 'test_fill_~f', [T]),
    assert(observation(EId, steps, 'check_po,verify_amounts,approve', string_value)),
    % Fill partials from this observation
    fill_partials_from_event(EId),
    % has_steps should now be resolved
    \+ partial(test_fill_proc, has_steps, template_sequence, unnamed),
    % Should have created step concepts via template typing
    has_rel(test_fill_proc, has_step, _SomeStep),
    % Clean up
    retractall(observation(EId, _, _, _)),
    retractall(concept_type(test_fill_proc, _)),
    retractall(partial(test_fill_proc, _, _, _)),
    retractall(has_rel(test_fill_proc, _, _)),
    retractall(heal_log(test_fill_proc, _, _, _)),
    retractall(typed_as(_, _, _)),
    retractall(step_of(test_fill_proc, _, _)),
    % Clean up step concepts
    forall(
        has_rel(test_fill_proc, has_step, StepC),
        (retractall(concept_type(StepC, _)), retractall(partial(StepC, _, _, _)))
    ).

% Test: template typing creates cascade of partials for steps
test_template_typing_cascade :-
    create_partials(test_cascade_proc, process),
    get_time(T),
    format(atom(EId), 'test_cascade_~f', [T]),
    assert(observation(EId, steps, 'step_a,step_b', string_value)),
    fill_partials_from_event(EId),
    % Each step should be a template_method concept with its own partials
    concept_type('test_cascade_proc_Step_step_a', template_method),
    concept_type('test_cascade_proc_Step_step_b', template_method),
    % Each step should have unnamed partials for body and params
    partial('test_cascade_proc_Step_step_a', has_method_body, string_value, unnamed),
    partial('test_cascade_proc_Step_step_b', has_method_body, string_value, unnamed),
    % Clean up
    retractall(observation(EId, _, _, _)),
    retractall(concept_type(test_cascade_proc, _)),
    retractall(partial(test_cascade_proc, _, _, _)),
    retractall(has_rel(test_cascade_proc, _, _)),
    retractall(heal_log(test_cascade_proc, _, _, _)),
    retractall(typed_as(_, _, _)),
    retractall(step_of(test_cascade_proc, _, _)),
    retractall(concept_type('test_cascade_proc_Step_step_a', _)),
    retractall(concept_type('test_cascade_proc_Step_step_b', _)),
    retractall(partial('test_cascade_proc_Step_step_a', _, _, _)),
    retractall(partial('test_cascade_proc_Step_step_b', _, _, _)),
    retractall(has_rel('test_cascade_proc_Step_step_a', _, _)),
    retractall(has_rel('test_cascade_proc_Step_step_b', _, _)),
    retractall(heal_log('test_cascade_proc_Step_step_a', _, _, _)),
    retractall(heal_log('test_cascade_proc_Step_step_b', _, _, _)).

% Test: completeness check
test_completeness :-
    assert(required_restriction(test_full, prop_a, type_a)),
    assert(required_restriction(test_full, prop_b, type_b)),
    create_partials(test_f1, test_full),
    \+ concept_complete(test_f1),  % Not complete (has unnamed)
    % Fill both
    resolve_partial_from_observation(test_f1, prop_a, val_a),
    resolve_partial_from_observation(test_f1, prop_b, val_b),
    concept_complete(test_f1),  % Now complete
    ready_for_code_promotion(test_f1),  % Ready for CODE
    % Clean up
    retractall(required_restriction(test_full, _, _)),
    retractall(partial(test_f1, _, _, _)),
    retractall(concept_type(test_f1, _)),
    retractall(has_rel(test_f1, _, _)),
    retractall(heal_log(test_f1, _, _, _)).
