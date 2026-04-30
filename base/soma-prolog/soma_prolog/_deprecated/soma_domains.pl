% SOMA Domains — User domains are separate from foundation
%
% Foundation types (TWI, template engineering, system actors, etc) are IMMUTABLE.
% User domains are namespaced — all user facts/rules/partials carry a domain tag.
% A user can't pollute the foundation. Foundation is its own thing.
%
% Domain scoping:
%   domain_observation(Domain, EventId, Key, Value, Type)
%   domain_concept(Domain, ConceptName, ConceptType)
%   domain_partial(Domain, ConceptName, Property, TargetType, Status)
%   domain_rule(Domain, RuleName, Head, Body)

:- dynamic domain_registered/2.     % domain_registered(DomainName, Description)
:- dynamic domain_observation/5.    % domain_observation(Domain, EventId, Key, Value, Type)
:- dynamic domain_concept/3.        % domain_concept(Domain, ConceptName, ConceptType)
:- dynamic domain_partial/5.        % domain_partial(Domain, Concept, Prop, TargetType, Status)
:- dynamic domain_has_rel/4.        % domain_has_rel(Domain, Concept, Prop, Target)
:- dynamic domain_rule/4.           % domain_rule(Domain, RuleName, Head, Body)
:- dynamic domain_word/3.           % domain_word(Domain, WordName, Meaning)
:- dynamic domain_restriction/4.    % domain_restriction(Domain, Type, Prop, TargetType)
:- dynamic domain_heal_log/5.       % domain_heal_log(Domain, Concept, Prop, TargetType, Result)
:- dynamic active_domain/1.         % active_domain(DomainName) — current working domain

% ======================================================================
% DOMAIN REGISTRATION
% ======================================================================

register_domain(Name, Description) :-
    (   domain_registered(Name, _)
    ->  true  % Already exists
    ;   assert(domain_registered(Name, Description))
    ).

set_active_domain(Name) :-
    domain_registered(Name, _),
    retractall(active_domain(_)),
    assert(active_domain(Name)).

get_active_domain(Name) :-
    active_domain(Name), !.
get_active_domain(none).

% ======================================================================
% DOMAIN-SCOPED PARTIAL CREATION
% ======================================================================

domain_create_partials(Domain, ConceptName, ConceptType) :-
    assert(domain_concept(Domain, ConceptName, ConceptType)),
    forall(
        (   % Check domain-specific restrictions first, then fall back to foundation
            (domain_restriction(Domain, ConceptType, Prop, TargetType) ;
             required_restriction(ConceptType, Prop, TargetType))
        ),
        domain_create_one_partial(Domain, ConceptName, Prop, TargetType)
    ).

domain_create_one_partial(Domain, Concept, Prop, TargetType) :-
    (   domain_has_rel(Domain, Concept, Prop, _)
    ->  true
    ;   domain_partial(Domain, Concept, Prop, TargetType, _)
    ->  true
    ;   assert(domain_partial(Domain, Concept, Prop, TargetType, unnamed)),
        assert(domain_heal_log(Domain, Concept, Prop, TargetType, created_unnamed))
    ).

% ======================================================================
% DOMAIN-SCOPED PARTIAL RESOLUTION
% ======================================================================

domain_resolve_partial(Domain, Concept, Prop, Value) :-
    domain_partial(Domain, Concept, Prop, TargetType, unnamed),
    retract(domain_partial(Domain, Concept, Prop, TargetType, unnamed)),
    assert(domain_partial(Domain, Concept, Prop, TargetType, resolved(Value))),
    assert(domain_has_rel(Domain, Concept, Prop, Value)).

% ======================================================================
% DOMAIN-SCOPED EVENT PROCESSING
% ======================================================================

% Process an event in a domain
domain_process_event(Domain, EventId, Source, Observations) :-
    get_time(T),
    format(atom(Timestamp), '~f', [T]),
    % Assert domain-scoped observations
    forall(
        member(obs(Key, Value, Type), Observations),
        assert(domain_observation(Domain, EventId, Key, Value, Type))
    ),
    % Create concepts from task observations
    forall(
        domain_observation(Domain, EventId, task, TaskName, string_value),
        (   domain_concept(Domain, TaskName, _)
        ->  true
        ;   domain_create_partials(Domain, TaskName, process)
        )
    ),
    % Fill partials from observations
    forall(
        domain_observation(Domain, EventId, Key, Value, Type),
        domain_try_fill(Domain, Key, Value, Type)
    ).

% Try to fill a domain partial from an observation
% If key is "concept.property" format, target specific concept
% Otherwise match any concept with that unnamed partial
domain_try_fill(Domain, Key, Value, Type) :-
    (   % Check for targeted format: "ConceptName.property"
        atomic_list_concat([TargetConcept, Prop], '.', Key),
        domain_partial(Domain, TargetConcept, Prop, TargetType, unnamed),
        type_compatible(Type, TargetType)
    ->  domain_resolve_partial(Domain, TargetConcept, Prop, Value),
        (Type = string_value -> domain_try_template_type(Domain, TargetConcept, Prop, Value) ; true)
    ;   % Fallback: match any concept with this property unnamed
        (   domain_partial(Domain, Concept, Prop, TargetType, unnamed),
            (property_matches_key(Prop, Key) ; Prop = Key),
            type_compatible(Type, TargetType)
        ->  domain_resolve_partial(Domain, Concept, Prop, Value),
            (Type = string_value -> domain_try_template_type(Domain, Concept, Prop, Value) ; true)
        ;   true
        )
    ).

% Domain-scoped template typing
domain_try_template_type(Domain, Concept, has_steps, Value) :-
    !,
    split_string(Value, ",", " ", StepStrings),
    domain_create_step_partials(Domain, Concept, StepStrings, 0).

domain_try_template_type(Domain, Concept, has_roles, Value) :-
    !,
    split_string(Value, ",", " ", RoleStrings),
    forall(
        member(RoleStr, RoleStrings),
        (   atom_string(RoleAtom, RoleStr),
            assert(domain_has_rel(Domain, Concept, has_role, RoleAtom))
        )
    ).

domain_try_template_type(_, _, _, _).

% Create step partials in domain
domain_create_step_partials(_, _, [], _).
domain_create_step_partials(Domain, Concept, [StepStr|Rest], Index) :-
    atom_string(StepAtom, StepStr),
    format(atom(StepName), '~w_Step_~w', [Concept, StepAtom]),
    domain_create_partials(Domain, StepName, template_method),
    assert(domain_has_rel(Domain, Concept, has_step, StepName)),
    NextIndex is Index + 1,
    domain_create_step_partials(Domain, Concept, Rest, NextIndex).

% ======================================================================
% DOMAIN-SCOPED STATUS
% ======================================================================

domain_partial_count(Domain, Concept, Total, Unnamed, Filled) :-
    findall(P, domain_partial(Domain, Concept, P, _, _), All),
    length(All, Total),
    findall(P, domain_partial(Domain, Concept, P, _, unnamed), UnnamedList),
    length(UnnamedList, Unnamed),
    Filled is Total - Unnamed.

domain_concept_complete(Domain, Concept) :-
    domain_concept(Domain, Concept, _),
    \+ domain_partial(Domain, Concept, _, _, unnamed).

domain_validation_status(Domain, Concept, soup) :-
    domain_partial(Domain, Concept, _, _, unnamed), !.
domain_validation_status(Domain, Concept, code) :-
    domain_concept(Domain, Concept, _),
    \+ domain_partial(Domain, Concept, _, _, unnamed), !.
domain_validation_status(_, _, unvalidated).

% ======================================================================
% DOMAIN-SCOPED Y_MESH
% ======================================================================

domain_deduction_chain_step(Domain, Concept, Result) :-
    findall(
        Prop,
        domain_partial(Domain, Concept, Prop, _, unnamed),
        UnnamedProps
    ),
    (   UnnamedProps = []
    ->  Result = complete
    ;   findall(
            result(Prop, Method),
            (   member(Prop, UnnamedProps),
                domain_deduction_chain_resolve(Domain, Concept, Prop, Method)
            ),
            FillResults
        ),
        Result = filling(FillResults)
    ).

% Resolution: TWO CASES ONLY
%
% 1. TYPED STRING — the deduction chain constrains what the value must be.
%    An internal LLM CAN fill this because the type tells it what goes there.
%    Dispatch: fill_typed(Concept, Prop, Constraint, Context)
%
% 2. ARBITRARY STRING — target type is unconstrained string_value.
%    Could be literally anything. Only the main LLM (talking to user) can
%    determine what goes here from conversation context.
%    Dispatch: fill_arbitrary(Concept, Prop, Context)
%
% Prolog KNOWS which case it is from the partial's target type.

% Case 1: TYPED — the partial target type is NOT bare string_value
% (it's a named type from the deduction chain: role_list, template_sequence, etc)
domain_deduction_chain_resolve(Domain, Concept, Prop, fill_typed(Constraint, Context)) :-
    domain_partial(Domain, Concept, Prop, TargetType, unnamed),
    TargetType \= string_value,
    % The target type IS the constraint
    Constraint = TargetType,
    % Collect context from self + parent
    collect_domain_context(Domain, Concept, Context),
    !.

% Case 2: ARBITRARY — target type is bare string_value, no constraint
% Returns to main LLM because only conversation context can fill it
domain_deduction_chain_resolve(Domain, Concept, Prop, fill_arbitrary(Context)) :-
    domain_partial(Domain, Concept, Prop, string_value, unnamed),
    collect_domain_context(Domain, Concept, Context),
    !.

% Fallback: no context available at all yet
domain_deduction_chain_resolve(_, _, _, needs_more_observations).

% Collect context from concept itself + any parent that links to it
collect_domain_context(Domain, Concept, Context) :-
    findall(
        ctx(P, V),
        domain_partial(Domain, Concept, P, _, resolved(V)),
        OwnContext
    ),
    findall(
        ctx(ParentC, P, V),
        (   domain_has_rel(Domain, ParentC, has_step, Concept),
            domain_partial(Domain, ParentC, P, _, resolved(V))
        ),
        ParentContext
    ),
    append(OwnContext, ParentContext, Context).

% ======================================================================
% DOMAIN-SCOPED INGEST (called from Python)
% ======================================================================

% Full domain event processing — returns structured report
domain_ingest_event(Domain, Source, ObservationsList, Report) :-
    get_time(T),
    format(atom(EventId), 'evt_~w_~f', [Domain, T]),
    % Process the event in domain scope
    domain_process_event(Domain, EventId, Source, ObservationsList),
    % Collect concept status
    findall(
        concept_info(C, Type, Total, Unnamed, Filled, Status),
        (   domain_concept(Domain, C, Type),
            domain_partial_count(Domain, C, Total, Unnamed, Filled),
            domain_validation_status(Domain, C, Status)
        ),
        Concepts
    ),
    % Run deduction chain routing on concepts with unnamed partials (deduplicated)
    findall(C,
        (domain_concept(Domain, C, _), domain_partial(Domain, C, _, _, unnamed)),
        RawConcepts
    ),
    sort(RawConcepts, UniqueConcepts),
    findall(
        ymesh(C, Result),
        (member(C, UniqueConcepts), domain_deduction_chain_step(Domain, C, Result)),
        YMeshResults
    ),
    % Check admissibility of each observation against accumulated rules
    findall(
        repair(Key, Value, Reason, Suggestion, AuthLevel),
        (   member(obs(Key, Value, _Type), ObservationsList),
            Key \= prolog_fact, Key \= prolog_rule, Key \= compile,
            Key \= enumerate, Key \= status, Key \= query,
            check_admissibility(Domain, Key, Value, Reason),
            once(suggest_repair(Domain, Key, Value, Reason, Suggestion, AuthLevel))
        ),
        RawRepairs
    ),
    sort(2, @<, RawRepairs, Repairs),  % Dedup by value

    % Handle reflexive observations (user using the system IS an event)
    findall(
        reflexive(Key, ResultStr),
        (   member(obs(Key, Value, string_value), ObservationsList),
            domain_reflexive_action(Domain, Key, Value, ResultStr)
        ),
        ReflexiveResults
    ),
    % Build report
    with_output_to(atom(Report),
        (   format('DOMAIN: ~w~nEVENT: ~w from ~w~n~n', [Domain, EventId, Source]),
            format('CONCEPTS:~n'),
            forall(member(concept_info(C, Type, Total, Unnamed, Filled, Status), Concepts),
                format('  ~w (~w): ~w/~w filled [~w]~n', [C, Type, Filled, Total, Status])
            ),
            (   YMeshResults \= []
            ->  format('~nDISPATCHES:~n'),
                forall(member(ymesh(C, filling(Results)), YMeshResults),
                    forall(member(result(Prop, Method), Results),
                        format_dispatch(C, Prop, Method)
                    )
                ),
                forall(member(ymesh(C, complete), YMeshResults),
                    format('  ~w: COMPLETE~n', [C])
                )
            ;   true
            ),
            (   Repairs \= []
            ->  format('~nADMISSIBILITY:~n'),
                forall(member(repair(RK, RV, RReason, RSugg, RAuth), Repairs),
                    format('  ✗ ~w=~w~n    WHY: ~w~n    FIX: ~w~n    AUTH: ~w~n', [RK, RV, RReason, RSugg, RAuth])
                )
            ;   true
            ),
            (   ReflexiveResults \= []
            ->  format('~nRESULTS:~n'),
                forall(member(reflexive(RKey, RResult), ReflexiveResults),
                    format('  [~w]~n~w~n', [RKey, RResult])
                )
            ;   true
            )
        )).

% ======================================================================
% REFLEXIVE ACTIONS — user using the system IS an event
% ======================================================================

% compile: user wants to compile a concept in this domain
domain_reflexive_action(Domain, compile, ConceptName, Result) :-
    (   compile_to_python(Domain, ConceptName, Code)
    ->  format(atom(Result), '~w', [Code])
    ;   % Diagnose why
        (   \+ domain_concept(Domain, ConceptName, process)
        ->  format(atom(Result), 'Cannot compile ~w: not a process in domain ~w', [ConceptName, Domain])
        ;   \+ domain_validation_status(Domain, ConceptName, code)
        ->  domain_validation_status(Domain, ConceptName, ActualStatus),
            format(atom(Result), 'Cannot compile ~w: status is ~w, needs code', [ConceptName, ActualStatus])
        ;   \+ is_authorized(Domain, ConceptName)
        ->  format(atom(Result), 'Cannot compile ~w: not authorized. Use prolog_fact observation: authorized_compilation(~w, ~w, YourName)', [ConceptName, Domain, ConceptName])
        ;   compiled_program(Domain, ConceptName, ExistingCode)
        ->  format(atom(Result), '~w', [ExistingCode])  % Already compiled — return it
        ;   format(atom(Result), 'Cannot compile ~w: unknown error', [ConceptName])
        )
    ).

% enumerate: user wants to see the product space
domain_reflexive_action(Domain, enumerate, ConceptName, Result) :-
    (   enumerate_str(Domain, ConceptName, Result)
    ->  true
    ;   format(atom(Result), 'Cannot enumerate ~w: process not found or no inputs defined', [ConceptName])
    ).

% status: user wants to see concept status
domain_reflexive_action(Domain, status, ConceptName, Result) :-
    (   domain_partial_count(Domain, ConceptName, Total, Unnamed, Filled),
        domain_validation_status(Domain, ConceptName, Status),
        missing_domain_partials(Domain, ConceptName, Missing),
        with_output_to(atom(Result),
            (   format('~w: ~w/~w filled [~w]~n', [ConceptName, Filled, Total, Status]),
                forall(member(M, Missing), format('  MISSING: ~w~n', [M]))
            ))
    ;   format(atom(Result), '~w not found in domain ~w', [ConceptName, Domain])
    ).

% query: arbitrary Prolog query (reflexive — the system queries itself)
domain_reflexive_action(_, query, QueryStr, Result) :-
    catch(
        (   term_string(Query, QueryStr),
            with_output_to(atom(Result), (call(Query), write(Query)))
        ),
        Error,
        (   term_to_atom(Error, ErrAtom),
            format(atom(Result), 'Query error: ~w', [ErrAtom])
        )
    ).

% ======================================================================
% ADMISSIBILITY — "the specific way you said this makes it inadmissible"
% These rules accumulate from observations. The more the system sees,
% the more it catches. Each rule says WHY something is inadmissible.
% ======================================================================

:- dynamic inadmissible_pattern/3.   % inadmissible_pattern(Pattern, Context, Reason)
:- dynamic known_test_name/1.        % known_test_name(Name) — names seen in test contexts
:- dynamic known_placeholder/1.      % known_placeholder(Name) — known placeholder values
:- dynamic domain_value_constraint/4. % domain_value_constraint(Domain, Property, Constraint, Reason)

% Bootstrap: common inadmissible patterns
known_test_name(foo).
known_test_name(bar).
known_test_name(baz).
known_test_name(test).
known_test_name(example).
known_test_name(dummy).
known_test_name(xxx).
known_test_name(asdf).
known_test_name(temp).

known_placeholder(todo).
known_placeholder(tbd).
known_placeholder(placeholder).
known_placeholder(fixme).
known_placeholder(changeme).
known_placeholder('...').
known_placeholder(none).
known_placeholder(null).
known_placeholder(undefined).

% Check: is this value a test name being used in a non-test context?
check_admissibility(Domain, Key, Value, Reason) :-
    atom_string(ValueAtom, Value),
    downcase_atom(ValueAtom, LowerValue),
    known_test_name(LowerValue),
    \+ sub_atom(Domain, _, _, _, test),  % Domain is not a test domain
    format(atom(Reason),
        'Value "~w" for ~w is a known test/placeholder name. Use a real value for production domain "~w".',
        [Value, Key, Domain]).

% Check: is this value a placeholder?
check_admissibility(Domain, Key, Value, Reason) :-
    atom_string(ValueAtom, Value),
    downcase_atom(ValueAtom, LowerValue),
    known_placeholder(LowerValue),
    format(atom(Reason),
        'Value "~w" for ~w is a placeholder. Provide actual content for domain "~w".',
        [Value, Key, Domain]).

% Check: does this value contain a test name as a component?
check_admissibility(Domain, Key, Value, Reason) :-
    atom_string(_, Value),
    split_to_terms(Value, Terms),
    member(Term, Terms),
    known_test_name(Term),
    \+ sub_atom(Domain, _, _, _, test),
    format(atom(Reason),
        'Value "~w" for ~w contains test name "~w". This makes it a test-type value which is inadmissible in production domain "~w".',
        [Value, Key, Term, Domain]).

% Check: domain-specific value constraints
check_admissibility(Domain, Key, Value, Reason) :-
    % Property name matches a constraint
    (   atomic_list_concat([_Concept, Prop], '.', Key)
    ->  true
    ;   Prop = Key
    ),
    domain_value_constraint(Domain, Prop, Constraint, BaseReason),
    \+ satisfies_constraint(Value, Constraint),
    format(atom(Reason),
        '~w: value "~w" does not satisfy constraint ~w',
        [BaseReason, Value, Constraint]).

% Check: is the LLM claiming authorization it doesn't have?
check_admissibility(Domain, Key, Value, Reason) :-
    Key = authorized_by,
    \+ authorized_compilation(Domain, _, Value),
    format(atom(Reason),
        '"~w" is not a recognized authorized agent for domain "~w". Authorization must come from an established authorized source.',
        [Value, Domain]).

% Check: contradiction with existing observation from authorized source
check_admissibility(Domain, Key, Value, Reason) :-
    % There's an existing observation for this key with a different value
    domain_observation(Domain, _PriorEvent, Key, PriorValue, _),
    PriorValue \= Value,
    % And the prior one came from an authorized source (not soma_agent)
    % For now: any prior observation counts
    format(atom(Reason),
        'Contradicts prior observation: ~w was previously "~w". New claim is "~w". Prior value takes precedence unless explicitly overridden.',
        [Key, PriorValue, Value]).

% Constraint satisfaction (extensible)
satisfies_constraint(Value, min_length(N)) :-
    atom_string(_, Value),
    atom_length(Value, Len), Len >= N.
satisfies_constraint(Value, not_empty) :-
    Value \= '', Value \= "".

% ======================================================================
% DOGFOOD: observe new inadmissible patterns
% ======================================================================

% When Isaac corrects something, observe the correction as a new rule
observe_inadmissible_pattern(Pattern, Context, Reason) :-
    assert(inadmissible_pattern(Pattern, Context, Reason)).

% Check user-observed patterns
check_admissibility(_, Key, Value, Reason) :-
    inadmissible_pattern(Pattern, Context, BaseReason),
    atom_string(ValueAtom, Value),
    downcase_atom(ValueAtom, LowerValue),
    downcase_atom(Pattern, LowerPattern),
    sub_atom(LowerValue, _, _, _, LowerPattern),
    format(atom(Reason), '~w (in context: ~w, key: ~w)', [BaseReason, Context, Key]).

% ======================================================================
% CORRECTIVE SYNTHESIS — inadmissible → suggested fix → who approves
% ======================================================================

:- dynamic repair_pattern/4.  % repair_pattern(BadPattern, GoodPattern, Reason, AuthLevel)
                               % AuthLevel: auto | agent | human | admin

% --- Test name → suggest descriptive name ---
suggest_repair(Domain, Key, Value, _Reason, Suggestion, agent) :-
    atom_string(ValueAtom, Value),
    downcase_atom(ValueAtom, LowerValue),
    known_test_name(LowerValue),
    format(atom(Suggestion),
        'Replace "~w" with a descriptive name for what this ~w actually does in domain "~w"',
        [Value, Key, Domain]).

% --- Placeholder → suggest real content ---
suggest_repair(Domain, Key, Value, _Reason, Suggestion, human) :-
    atom_string(ValueAtom, Value),
    downcase_atom(ValueAtom, LowerValue),
    known_placeholder(LowerValue),
    format(atom(Suggestion),
        'Provide actual ~w content. "~w" is a placeholder that must be replaced with real data from domain "~w"',
        [Key, Value, Domain]).

% --- Contains test name component → suggest specific replacement ---
suggest_repair(Domain, Key, Value, _Reason, Suggestion, agent) :-
    split_to_terms(Value, Terms),
    member(Term, Terms),
    known_test_name(Term),
    format(atom(Suggestion),
        'Replace test component "~w" in "~w" with a real ~w name for domain "~w"',
        [Term, Value, Key, Domain]).

% --- Contradiction with prior → suggest keeping prior or explicit override ---
suggest_repair(Domain, Key, Value, _Reason, Suggestion, admin) :-
    domain_observation(Domain, _, Key, PriorValue, _),
    PriorValue \= Value,
    format(atom(Suggestion),
        'Prior value "~w" exists. To change to "~w", submit with authorized override for domain "~w"',
        [PriorValue, Value, Domain]).

% --- Unauthorized compilation attempt → tell who to ask ---
suggest_repair(Domain, Key, _Value, _Reason, Suggestion, admin) :-
    Key = authorized_by,
    (   authorized_compilation(Domain, _, AuthPerson)
    ->  format(atom(Suggestion),
            'Request authorization from ~w who is authorized for domain "~w"',
            [AuthPerson, Domain])
    ;   format(atom(Suggestion),
            'No one is authorized for domain "~w" yet. An admin must run: authorized_compilation(~w, ConceptName, YourName)',
            [Domain, Domain])
    ).

% --- User-observed repair patterns (dogfooded) ---
suggest_repair(_, Key, Value, _Reason, Suggestion, AuthLevel) :-
    repair_pattern(BadPattern, GoodPattern, PatternReason, AuthLevel),
    atom_string(ValueAtom, Value),
    downcase_atom(ValueAtom, LowerValue),
    downcase_atom(BadPattern, LowerBad),
    sub_atom(LowerValue, _, _, _, LowerBad),
    format(atom(Suggestion),
        '~w → Replace with pattern "~w" (key: ~w)',
        [PatternReason, GoodPattern, Key]).

% --- Fallback: no specific suggestion, just flag it ---
suggest_repair(_, Key, Value, Reason, Suggestion, human) :-
    format(atom(Suggestion),
        'Value "~w" for ~w was flagged: ~w. A human must provide the correct value.',
        [Value, Key, Reason]).

% Observe new repair patterns (Isaac corrects → becomes permanent rule)
observe_repair_pattern(BadPattern, GoodPattern, Reason, AuthLevel) :-
    assert(repair_pattern(BadPattern, GoodPattern, Reason, AuthLevel)).

% Helper: missing partials in domain
missing_domain_partials(Domain, Concept, Missing) :-
    findall(
        missing(Prop, TargetType),
        domain_partial(Domain, Concept, Prop, TargetType, unnamed),
        Missing
    ).

format_dispatch(C, Prop, fill_typed(Constraint, Context)) :-
    format('  [INTERNAL] ~w.~w (type: ~w)~n', [C, Prop, Constraint]),
    format('    Context: ~w~n', [Context]).
format_dispatch(C, Prop, fill_arbitrary(Context)) :-
    format('  [EXTERNAL] ~w.~w~n', [C, Prop]),
    format('    Context: ~w~n', [Context]).
format_dispatch(C, Prop, needs_more_observations) :-
    format('  [WAITING] ~w.~w~n', [C, Prop]).

% Janus-safe wrapper
domain_ingest_event_str(Domain, Source, ObsStr, ReportStr) :-
    term_string(ObsList, ObsStr),
    domain_ingest_event(Domain, Source, ObsList, ReportStr).

% ======================================================================
% DOMAIN-SCOPED PROLOG RULES (dogfooding)
% ======================================================================

% Assert a domain-specific Prolog rule
domain_assert_rule(Domain, RuleBody) :-
    catch(
        (   term_string(Rule, RuleBody),
            assert(Rule),
            assert(domain_rule(Domain, RuleBody, _, _))
        ),
        _, true
    ).

% ======================================================================
% TESTS
% ======================================================================

test_domain_registration :-
    register_domain(test_domain, 'Test domain'),
    domain_registered(test_domain, 'Test domain'),
    retract(domain_registered(test_domain, _)).

test_domain_partials :-
    register_domain(test_dp, 'Test'),
    domain_create_partials(test_dp, test_proc, process),
    domain_concept(test_dp, test_proc, process),
    domain_partial(test_dp, test_proc, has_steps, template_sequence, unnamed),
    domain_partial_count(test_dp, test_proc, 4, 4, 0),
    domain_validation_status(test_dp, test_proc, soup),
    % Fill one
    domain_resolve_partial(test_dp, test_proc, has_steps, 'a,b,c'),
    domain_partial_count(test_dp, test_proc, 4, 3, 1),
    % Clean up
    retractall(domain_registered(test_dp, _)),
    retractall(domain_concept(test_dp, _, _)),
    retractall(domain_partial(test_dp, _, _, _, _)),
    retractall(domain_has_rel(test_dp, _, _, _)),
    retractall(domain_heal_log(test_dp, _, _, _, _)).

test_domain_isolation :-
    register_domain(domain_a, 'Domain A'),
    register_domain(domain_b, 'Domain B'),
    domain_create_partials(domain_a, proc_a, process),
    domain_create_partials(domain_b, proc_b, process),
    % A's concepts don't appear in B
    domain_concept(domain_a, proc_a, process),
    \+ domain_concept(domain_b, proc_a, _),
    domain_concept(domain_b, proc_b, process),
    \+ domain_concept(domain_a, proc_b, _),
    % Clean up
    retractall(domain_registered(domain_a, _)),
    retractall(domain_registered(domain_b, _)),
    retractall(domain_concept(domain_a, _, _)),
    retractall(domain_concept(domain_b, _, _)),
    retractall(domain_partial(domain_a, _, _, _, _)),
    retractall(domain_partial(domain_b, _, _, _, _)),
    retractall(domain_heal_log(domain_a, _, _, _, _)),
    retractall(domain_heal_log(domain_b, _, _, _, _)).
