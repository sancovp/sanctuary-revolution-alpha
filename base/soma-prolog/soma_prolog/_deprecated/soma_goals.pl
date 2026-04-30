% SOMA Goals — Goal-driven enforcement gate
%
% A goal is a set of constraints. Once a goal is active, every subsequent
% event/observation gets checked against the goal's constraints BEFORE
% being asserted into the ledger. Violations REJECT the entire event.
%
% Constraint kinds:
%   forbidden_value(Key, Value) — observation with this key=value is forbidden
%   forbidden_key(Key)          — observation with this key is forbidden
%   required_key(Key)           — events must include this key
%   required_value(Key, Value)  — events must include this key=value
%
% This is the goal-driven loop the user wants: set a goal, then no future
% event can violate it. The check runs BEFORE process_event_partials,
% process_event_loop, and deduction_chain routing.

:- dynamic active_goal/2.        % active_goal(GoalId, Description)
:- dynamic goal_constraint/3.    % goal_constraint(GoalId, ConstraintType, ConstraintData)
:- dynamic goal_violation_log/4. % goal_violation_log(EventId, GoalId, Reason, Timestamp)

% ======================================================================
% GOAL MANAGEMENT
% ======================================================================

% Activate a goal
add_active_goal(GoalId, Description) :-
    retractall(active_goal(GoalId, _)),
    assert(active_goal(GoalId, Description)).

deactivate_goal(GoalId) :-
    retractall(active_goal(GoalId, _)),
    retractall(goal_constraint(GoalId, _, _)).

% Add constraints
add_forbidden_value(GoalId, Key, Value) :-
    (   goal_constraint(GoalId, forbidden_value, kv(Key, Value))
    ->  true
    ;   assert(goal_constraint(GoalId, forbidden_value, kv(Key, Value)))
    ).

add_forbidden_key(GoalId, Key) :-
    (   goal_constraint(GoalId, forbidden_key, Key)
    ->  true
    ;   assert(goal_constraint(GoalId, forbidden_key, Key))
    ).

add_required_key(GoalId, Key) :-
    (   goal_constraint(GoalId, required_key, Key)
    ->  true
    ;   assert(goal_constraint(GoalId, required_key, Key))
    ).

add_required_value(GoalId, Key, Value) :-
    (   goal_constraint(GoalId, required_value, kv(Key, Value))
    ->  true
    ;   assert(goal_constraint(GoalId, required_value, kv(Key, Value)))
    ).

% ======================================================================
% VIOLATION DETECTION — per observation
% ======================================================================

% Single observation violates a goal?
obs_violates_goal(Key, Value, GoalId, Reason) :-
    active_goal(GoalId, _),
    goal_constraint(GoalId, forbidden_value, kv(Key, Value)),
    format(atom(Reason), 'Goal ~w forbids ~w=~w', [GoalId, Key, Value]).

obs_violates_goal(Key, _, GoalId, Reason) :-
    active_goal(GoalId, _),
    goal_constraint(GoalId, forbidden_key, Key),
    format(atom(Reason), 'Goal ~w forbids key ~w', [GoalId, Key]).

% ======================================================================
% VIOLATION DETECTION — per event (whole observation list)
% ======================================================================

% Event-level: required keys must be present
event_violates_required(ObsList, GoalId, Reason) :-
    active_goal(GoalId, _),
    goal_constraint(GoalId, required_key, ReqKey),
    \+ member(obs(ReqKey, _, _), ObsList),
    format(atom(Reason), 'Goal ~w requires key ~w which is missing', [GoalId, ReqKey]).

% Event-level: required key=value must be present
event_violates_required(ObsList, GoalId, Reason) :-
    active_goal(GoalId, _),
    goal_constraint(GoalId, required_value, kv(ReqKey, ReqVal)),
    \+ member(obs(ReqKey, ReqVal, _), ObsList),
    format(atom(Reason), 'Goal ~w requires ~w=~w which is missing', [GoalId, ReqKey, ReqVal]).

% ======================================================================
% MAIN ENTRY: check whole event admissibility under all active goals
% ======================================================================

% Returns list of violations. Empty list = admissible.
check_goal_admissibility(ObsList, AllViolations) :-
    findall(
        violation(GoalId, Reason),
        (   member(obs(K, V, _), ObsList),
            obs_violates_goal(K, V, GoalId, Reason)
        ),
        ObsViolations
    ),
    findall(
        violation(GoalId, Reason),
        event_violates_required(ObsList, GoalId, Reason),
        ReqViolations
    ),
    append(ObsViolations, ReqViolations, RawViolations),
    sort(RawViolations, AllViolations).

% Janus-safe wrapper: returns string report
check_goal_admissibility_str(ObsListStr, ResultStr) :-
    term_string(ObsList, ObsListStr),
    check_goal_admissibility(ObsList, Violations),
    (   Violations = []
    ->  ResultStr = 'ADMISSIBLE'
    ;   length(Violations, N),
        with_output_to(atom(ResultStr),
            (   format('REJECTED (~w violations):~n', [N]),
                forall(member(violation(G, R), Violations),
                    format('  [~w] ~w~n', [G, R])
                )
            ))
    ).

% Janus-safe wrapper: returns LIST of "GoalId|Reason" strings (empty if admissible)
check_goal_admissibility_strlist(ObsListStr, StrList) :-
    term_string(ObsList, ObsListStr),
    check_goal_admissibility(ObsList, Violations),
    findall(
        S,
        (   member(violation(G, R), Violations),
            with_output_to(atom(S), format('~w|~w', [G, R]))
        ),
        StrList
    ).

% Log a violation
log_violation(EventId, GoalId, Reason) :-
    get_time(T),
    assert(goal_violation_log(EventId, GoalId, Reason, T)).

% ======================================================================
% STATUS REPORTING
% ======================================================================

list_active_goals_str(Str) :-
    findall(g(Id, Desc), active_goal(Id, Desc), Goals),
    length(Goals, N),
    with_output_to(atom(Str),
        (   format('Active goals: ~w~n', [N]),
            forall(member(g(Id, Desc), Goals),
                (   format('  ~w: ~w~n', [Id, Desc]),
                    forall(goal_constraint(Id, CType, CData),
                        format('    ~w: ~w~n', [CType, CData])
                    )
                )
            )
        )).

% ======================================================================
% TESTS
% ======================================================================

test_add_goal :-
    add_active_goal(test_goal_g1, 'Test goal'),
    active_goal(test_goal_g1, 'Test goal'),
    deactivate_goal(test_goal_g1),
    \+ active_goal(test_goal_g1, _).

test_forbidden_value :-
    add_active_goal(test_goal_fv, 'Forbid poison drinks'),
    add_forbidden_value(test_goal_fv, drink, poison),
    obs_violates_goal(drink, poison, test_goal_fv, _),
    \+ obs_violates_goal(drink, water, test_goal_fv, _),
    deactivate_goal(test_goal_fv).

test_forbidden_key :-
    add_active_goal(test_goal_fk, 'Forbid secret data'),
    add_forbidden_key(test_goal_fk, secret),
    obs_violates_goal(secret, anything, test_goal_fk, _),
    \+ obs_violates_goal(safe_data, anything, test_goal_fk, _),
    deactivate_goal(test_goal_fk).

test_required_key :-
    add_active_goal(test_goal_rk, 'Require source'),
    add_required_key(test_goal_rk, source),
    event_violates_required([obs(other, val, string_value)], test_goal_rk, _),
    \+ event_violates_required([obs(source, alice, string_value)], test_goal_rk, _),
    deactivate_goal(test_goal_rk).

test_admissibility_clean :-
    add_active_goal(test_adm_clean, 'Clean test'),
    add_forbidden_value(test_adm_clean, drink, poison),
    check_goal_admissibility([obs(drink, water, string_value)], []),
    deactivate_goal(test_adm_clean).

test_admissibility_violation :-
    add_active_goal(test_adm_viol, 'Violation test'),
    add_forbidden_value(test_adm_viol, drink, poison),
    check_goal_admissibility([obs(drink, poison, string_value)], Violations),
    Violations = [_|_],  % non-empty
    deactivate_goal(test_adm_viol).
