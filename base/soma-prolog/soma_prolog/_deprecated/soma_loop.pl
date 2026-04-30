% SOMA Runtime Loop — The Prolog rules that make the ontology LIVE
%
% The loop:
%   Event enters → Prolog inference rules fire ("when X also Y")
%   → dispatch to Pellet (OWL reasoning: subClassOf, restrictions, composition)
%   → Prolog closed-world check ("is everything consistent now?")
%   → YES → dispatch actions (assert, codegen, notify)
%   → NO → why not? → self-heal (internal LLM) or escalate (main LLM/user)
%
% This file is consulted by soma_boot.pl.

:- discontiguous inference_rule/3.
:- discontiguous closed_world_check/2.

% Dynamic predicates for inferred facts
:- dynamic candidate_process/2.   % candidate_process(TaskName, EventId)
:- dynamic process_accumulated/2. % process_accumulated(TaskName, Count)
:- dynamic source_registered/1.   % source_registered(SourceName)
:- dynamic has_proposed_rule/1.   % has_proposed_rule(RuleBody)
:- dynamic sop_candidate/1.       % sop_candidate(TaskName)
:- dynamic codegen_candidate/1.   % codegen_candidate(TaskName)
:- dynamic authorized_process/1.  % authorized_process(TaskName)
:- dynamic template_candidate/1.  % template_candidate(ClassName)
:- dynamic configurator_candidate/1.
:- dynamic deep_analyzed/1.       % deep_analyzed(ClassName)
:- dynamic configures_other/2.    % configures_other(Class, Other)
:- dynamic has_unresolved_deps/1. % has_unresolved_deps(ClassName)
:- dynamic has_property/2.        % has_property(Entity, Prop)

:- dynamic inferred_fact/2.       % inferred_fact(Fact, ByRule)
:- dynamic pellet_result/3.       % pellet_result(Subject, Predicate, Object)
:- dynamic consistency_issue/3.   % consistency_issue(What, Why, Severity)
:- dynamic heal_attempt/3.        % heal_attempt(Issue, Method, Result)
:- dynamic loop_state/2.          % loop_state(Key, Value)

% ======================================================================
% PHASE 1: INFERENCE RULES — "when X, also Y"
% These fire on new observations and assert inferred facts.
% ======================================================================

% --- Type inference: observation types imply OWL classes ---
inference_rule(type_implies_class,
    observation(EvId, _Key, _Val, Type),
    owl_class(Type)
) :- owl_class(Type).

% --- Source tracking: events from a source imply source exists ---
inference_rule(source_exists,
    event(EvId, Source, _Ts),
    source_registered(Source)
).

% --- Process detection: repeated observations about same topic = Process ---
inference_rule(process_detection,
    observation(EvId, task, TaskName, string_value),
    candidate_process(TaskName, EvId)
).

% --- Process accumulation: N observations about same task = Process ready ---
% NOTE: This rule checks EXISTING candidate_process facts, not the one being matched.
% It only fires when called explicitly after candidate_process facts exist.
inference_rule(process_ready,
    candidate_process(TaskName, _),
    process_accumulated(TaskName, Count)
) :-
    ground(TaskName),
    findall(E, candidate_process(TaskName, E), Events),
    length(Events, Count),
    Count >= 3.

% --- Rule observation: if someone tells us a rule, it's a rule ---
inference_rule(rule_from_observation,
    observation(_EvId, prolog_rule, RuleBody, string_value),
    has_proposed_rule(RuleBody)
).

% --- SOP detection: codified process + enough typed observations ---
inference_rule(sop_ready,
    process_accumulated(TaskName, Count),
    sop_candidate(TaskName)
) :- ground(TaskName), ground(Count), Count >= 5.

% --- Codegen detection: SOP exists + human authorized ---
inference_rule(codegen_ready,
    authorized_process(TaskName),
    codegen_candidate(TaskName)
) :- ground(TaskName), sop_candidate(TaskName).

% --- Template detection: code class with all deps resolved = templatable ---
inference_rule(templatable_class,
    deep_analyzed(ClassName),
    template_candidate(ClassName)
) :- ground(ClassName), \+ has_unresolved_deps(ClassName).

% --- Configurator detection: templated class that configures others ---
inference_rule(configurator_detection,
    template_candidate(ClassName),
    configurator_candidate(ClassName)
) :- ground(ClassName), configures_other(ClassName, _Other).

% Run all inference rules on a fact, return list of inferred facts
run_inference(Fact, Inferred) :-
    findall(
        inferred(NewFact, RuleName),
        (   inference_rule(RuleName, Pattern, NewFact),
            Pattern = Fact
        ),
        Inferred
    ).

% Assert all inferred facts, tracking provenance
assert_inferred(Fact, Inferred) :-
    forall(
        member(inferred(NewFact, RuleName), Inferred),
        (   \+ inferred_fact(NewFact, _)  % Don't duplicate
        ->  assert(inferred_fact(NewFact, RuleName)),
            assert(NewFact)
        ;   true
        )
    ).

% ======================================================================
% PHASE 2: OWL DISPATCH — REAL Pellet via owlready2 + Janus
% No simulation. The previous owl_inference/run_owl_reasoning predicates
% have been DELETED. Pellet runs in Java; we call it via py_call into
% soma_prolog.utils.run_pellet().
% ======================================================================

% Run Pellet sync_reasoner. Returns the status string from owlready2.
run_owl_reasoning(StatusAtom) :-
    py_call('soma_prolog.utils':run_pellet(), StatusStr),
    atom_string(StatusAtom, StatusStr).

% Pellet writes inferred facts directly into the in-memory ontology;
% there is nothing to "assert" on the Prolog side. This predicate exists
% only so the existing process_event_loop call sites continue to compile.
assert_owl_results(_StatusAtom) :- true.

% ======================================================================
% PHASE 3: CLOSED WORLD CHECK — "Is everything consistent now?"
% Given ALL facts (asserted + inferred + Pellet results), check
% that expected consequences hold and no contradictions exist.
% ======================================================================

% --- Check: every event must have a registered source ---
closed_world_check(orphan_event,
    issue(orphan_event, EvId, 'Event has no registered source')
) :-
    event(EvId, Source, _),
    \+ source_registered(Source).

% --- Check: every proposed rule must be syntactically valid ---
closed_world_check(invalid_rule,
    issue(invalid_rule, RuleBody, 'Proposed rule is not valid Prolog')
) :-
    has_proposed_rule(RuleBody),
    \+ catch((term_string(_, RuleBody), true), _, fail).

% --- Check: every SOP candidate must have sufficient typed observations ---
closed_world_check(premature_sop,
    issue(premature_sop, TaskName, 'SOP candidate has insufficient observations')
) :-
    sop_candidate(TaskName),
    \+ process_accumulated(TaskName, _).

% --- Check: no observation type is unknown to OWL ---
closed_world_check(unknown_type,
    issue(unknown_type, Type, 'Observation type not in OWL')
) :-
    observation(_, _, _, Type),
    \+ owl_class(Type).

% --- Check: codegen candidates must have human authorization ---
closed_world_check(unauthorized_codegen,
    issue(unauthorized_codegen, TaskName, 'Codegen candidate not authorized')
) :-
    codegen_candidate(TaskName),
    \+ authorized_process(TaskName).

% --- Check: active goals should have progress ---
closed_world_check(stale_goal,
    issue(stale_goal, GoalId, 'Active goal has no recent events')
) :-
    goal(GoalId, _Desc),
    goal_status(GoalId, active),
    \+ goal_has_recent_events(GoalId).

% Placeholder: check if goal has recent events
goal_has_recent_events(GoalId) :-
    % In real system: check if any events in last N minutes relate to this goal
    % For now: if any events exist, consider it active
    event(_, _, _).

% Run all closed-world checks, return issues
run_closed_world_checks(Issues) :-
    findall(
        Issue,
        (   closed_world_check(CheckName, Issue),
            call(Issue)  % Only include issues that actually hold
        ),
        AllIssues
    ),
    % Deduplicate
    sort(AllIssues, Issues).

% Alternate: collect issues that fire
collect_consistency_issues(Issues) :-
    findall(
        issue(Name, Subject, Reason),
        (   closed_world_check(Name, issue(Name, Subject, Reason)),
            % Check if the issue condition actually holds
            catch(
                (closed_world_check(Name, issue(Name, Subject, Reason))),
                _, fail
            )
        ),
        RawIssues
    ),
    sort(RawIssues, Issues).

% ======================================================================
% PHASE 4: DISPATCH — What to do with results
% Given inference results + OWL results + consistency check,
% decide what actions to take.
% ======================================================================

:- dynamic dispatch_queue/3.  % dispatch_queue(Id, Type, Payload)

% Dispatch types (from soma.owl):
%   assert_fact    — just assert, no further action
%   check_owl      — need OWL validation
%   generate_rule  — need LLM to generate a Prolog rule
%   generate_sop   — need LLM to generate an SOP
%   codegen        — need LLM to generate code (human-gated)
%   ask_source     — need more info from a source
%   question       — contradiction detected, need explanation

create_dispatch(Type, Payload) :-
    get_time(T),
    format(atom(Id), 'dispatch_~f', [T]),
    assert(dispatch_queue(Id, Type, Payload)).

% Route inferred facts to dispatches
route_inference_to_dispatch(inferred(candidate_process(Task, _), _)) :-
    create_dispatch(check_owl, process_candidate(Task)).

route_inference_to_dispatch(inferred(sop_candidate(Task), _)) :-
    create_dispatch(generate_sop, Task).

route_inference_to_dispatch(inferred(codegen_candidate(Task), _)) :-
    create_dispatch(codegen, Task).

route_inference_to_dispatch(inferred(has_proposed_rule(Body), _)) :-
    create_dispatch(generate_rule, validate_and_assert(Body)).

route_inference_to_dispatch(inferred(template_candidate(Class), _)) :-
    create_dispatch(check_owl, template_readiness(Class)).

route_inference_to_dispatch(inferred(configurator_candidate(Class), _)) :-
    create_dispatch(check_owl, configurator_readiness(Class)).

% Default: no dispatch needed
route_inference_to_dispatch(_).

% Route consistency issues to dispatches
route_issue_to_dispatch(issue(unknown_type, Type, _)) :-
    create_dispatch(check_owl, define_type(Type)).

route_issue_to_dispatch(issue(orphan_event, EvId, _)) :-
    event(EvId, Source, _),
    create_dispatch(ask_source, register_source(Source)).

route_issue_to_dispatch(issue(invalid_rule, Body, _)) :-
    create_dispatch(generate_rule, fix_rule(Body)).

route_issue_to_dispatch(issue(unauthorized_codegen, Task, _)) :-
    create_dispatch(ask_source, authorize(Task)).

route_issue_to_dispatch(issue(stale_goal, GoalId, _)) :-
    goal(GoalId, Desc),
    create_dispatch(question, stale_goal(GoalId, Desc)).

% Default: escalate unknown issues
route_issue_to_dispatch(issue(Name, Subject, Reason)) :-
    create_dispatch(question, unknown_issue(Name, Subject, Reason)).

% ======================================================================
% PHASE 5: SELF-HEAL — Try to fix issues without main LLM
% Uses deduction chain routing (internal LLM calls) for small fixes.
% Escalates to main LLM for complex issues.
% ======================================================================

% Severity classification
issue_severity(unknown_type, low).       % Can auto-create SOUP type
issue_severity(orphan_event, low).       % Can auto-register source
issue_severity(invalid_rule, medium).    % Needs LLM to fix syntax
issue_severity(premature_sop, low).      % Just wait for more observations
issue_severity(unauthorized_codegen, high). % Needs human
issue_severity(stale_goal, medium).      % Needs attention

% Can self-heal?
can_self_heal(issue(unknown_type, Type, _)) :-
    % Create the type as SOUP in OWL
    \+ owl_class(Type).

can_self_heal(issue(orphan_event, _EvId, _)) :-
    % Auto-register the source
    true.

can_self_heal(issue(premature_sop, _Task, _)) :-
    % Just wait — not really an issue
    true.

% Attempt self-heal
self_heal(issue(unknown_type, Type, _), Result) :-
    assert(owl_class(Type)),
    format(atom(Result), 'Auto-created SOUP type: ~w', [Type]),
    assert(heal_attempt(unknown_type, auto_create_soup, Result)).

self_heal(issue(orphan_event, EvId, _), Result) :-
    event(EvId, Source, _),
    assert(source_registered(Source)),
    format(atom(Result), 'Auto-registered source: ~w', [Source]),
    assert(heal_attempt(orphan_event, auto_register, Result)).

self_heal(issue(premature_sop, Task, _), Result) :-
    Result = 'Waiting for more observations',
    assert(heal_attempt(premature_sop, wait, Result)).

% Cannot self-heal → escalate
escalate(Issue, Dispatch) :-
    \+ can_self_heal(Issue),
    Issue = issue(Name, Subject, Reason),
    Dispatch = escalate_to_llm(Name, Subject, Reason).

% ======================================================================
% THE LOOP: Process one event through the full pipeline
% ======================================================================

% Main entry: process an event through the full SOMA loop
process_event_loop(EventId, Report) :-
    % Get all observations for this event
    findall(
        observation(EventId, Key, Val, Type),
        observation(EventId, Key, Val, Type),
        Observations
    ),

    % PHASE 1: Run inference on each observation
    findall(
        Inferred,
        (   member(Obs, Observations),
            run_inference(Obs, InferredList),
            member(Inferred, InferredList)
        ),
        AllInferred
    ),
    assert_inferred(event_loop, AllInferred),

    % Route inferred facts to dispatches
    forall(member(I, AllInferred), route_inference_to_dispatch(I)),

    % PHASE 2: Run REAL Pellet via owlready2 (Janus). Status is a string.
    run_owl_reasoning(OWLStatus),
    assert_owl_results(OWLStatus),

    % PHASE 3: Closed world check
    collect_consistency_issues(Issues),

    % PHASE 4+5: For each issue, try self-heal or escalate
    findall(
        action(IssueType, Action),
        (   member(Issue, Issues),
            Issue = issue(IssueType, _, _),
            (   can_self_heal(Issue)
            ->  self_heal(Issue, HealResult),
                Action = healed(HealResult)
            ;   escalate(Issue, EscalateDispatch),
                route_issue_to_dispatch(Issue),
                Action = escalated(EscalateDispatch)
            )
        ),
        Actions
    ),

    % Collect all dispatches
    findall(
        dispatch(Id, Type, Payload),
        dispatch_queue(Id, Type, Payload),
        Dispatches
    ),

    % Build report
    length(Observations, ObsCount),
    length(AllInferred, InferCount),
    length(Issues, IssueCount),
    length(Actions, ActionCount),
    length(Dispatches, DispatchCount),

    format(atom(Report),
        'Loop complete for ~w: ~w observations, ~w inferred, pellet=~w, ~w issues (~w acted on), ~w dispatches queued',
        [EventId, ObsCount, InferCount, OWLStatus, IssueCount, ActionCount, DispatchCount]
    ).

% Janus-safe wrapper
process_event_loop_str(EventId, ReportStr) :-
    (   process_event_loop(EventId, Report)
    ->  with_output_to(atom(ReportStr), write(Report))
    ;   ReportStr = 'Loop failed — no event found or error in processing'
    ).

% Process ALL pending events (events without loop_processed flag)
process_all_pending(Reports) :-
    findall(
        EventId,
        (event(EventId, _, _), \+ loop_state(processed, EventId)),
        PendingEvents
    ),
    findall(
        report(EventId, Report),
        (   member(EventId, PendingEvents),
            process_event_loop(EventId, Report),
            assert(loop_state(processed, EventId))
        ),
        Reports
    ).

process_all_pending_str(ReportStr) :-
    process_all_pending(Reports),
    length(Reports, N),
    with_output_to(atom(ReportStr),
        (   format('Processed ~w events.~n', [N]),
            forall(member(report(Id, R), Reports),
                format('  ~w: ~w~n', [Id, R])
            )
        )).

% Get all queued dispatches
get_dispatches(Dispatches) :-
    findall(
        dispatch(Id, Type, Payload),
        dispatch_queue(Id, Type, Payload),
        Dispatches
    ).

get_dispatches_str(Str) :-
    get_dispatches(Dispatches),
    length(Dispatches, N),
    with_output_to(atom(Str),
        (   format('~w dispatches queued:~n', [N]),
            forall(member(dispatch(Id, Type, Payload), Dispatches),
                format('  [~w] ~w: ~w~n', [Id, Type, Payload])
            )
        )).

% Clear dispatch queue (after main LLM has processed them)
clear_dispatches :-
    retractall(dispatch_queue(_, _, _)).

% ======================================================================
% TESTS for the loop
% ======================================================================

% Test: inference rules fire on matching facts
test_inference_fires :-
    assert(observation(test_evt_inf, task, invoice_processing, string_value)),
    run_inference(observation(test_evt_inf, task, invoice_processing, string_value), Inferred),
    Inferred \= [],
    retract(observation(test_evt_inf, task, invoice_processing, string_value)).

% Test: unknown type triggers consistency issue
test_unknown_type_issue :-
    assert(observation(test_evt_unk, status, active, totally_fake_type_xyz)),
    collect_consistency_issues(Issues),
    member(issue(unknown_type, totally_fake_type_xyz, _), Issues),
    retract(observation(test_evt_unk, status, active, totally_fake_type_xyz)).

% Test: self-heal creates SOUP type for unknown
test_self_heal_unknown_type :-
    \+ owl_class(auto_healed_test_type),
    self_heal(issue(unknown_type, auto_healed_test_type, 'test'), Result),
    owl_class(auto_healed_test_type),
    Result \= '',
    retract(owl_class(auto_healed_test_type)),
    retract(heal_attempt(unknown_type, auto_create_soup, _)).

% Test: full loop processes an event
test_full_loop :-
    get_time(T),
    format(atom(TestEvId), 'test_loop_~f', [T]),
    format(atom(Ts), '~f', [T]),
    assert(event(TestEvId, test_employee, Ts)),
    assert(observation(TestEvId, task, loop_test_task, string_value)),
    assert(observation(TestEvId, duration, '30', int_value)),
    process_event_loop(TestEvId, Report),
    Report \= '',
    % Clean up
    retract(event(TestEvId, _, _)),
    retractall(observation(TestEvId, _, _, _)),
    retractall(inferred_fact(_, _)),
    retractall(candidate_process(loop_test_task, _)),
    retractall(source_registered(test_employee)),
    retractall(dispatch_queue(_, _, _)),
    retractall(loop_state(_, _)),
    retractall(heal_attempt(_, _, _)).

% Test: dispatch queue works
test_dispatch_queue :-
    create_dispatch(test_type, test_payload),
    get_dispatches(Dispatches),
    length(Dispatches, N),
    N > 0,
    clear_dispatches,
    get_dispatches(Empty),
    length(Empty, 0).

% Test: escalation works for non-healable issues
test_escalation :-
    escalate(issue(unauthorized_codegen, test_task, 'Needs human'), Dispatch),
    Dispatch = escalate_to_llm(unauthorized_codegen, test_task, 'Needs human').
