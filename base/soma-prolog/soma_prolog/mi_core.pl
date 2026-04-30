% SOMA Meta-Interpreter Core
% Based on EXSHELL (Luger, UNM) adapted for SOMA dispatch architecture.
% Removes: user interaction (askuser), certainty factors, automotive KB
% Adds: typed facts, structured dispatch, failure-as-data
%
% Original: https://www.cs.unm.edu/~luger/ai-final/code/PROLOG.exshell_full

:- dynamic known/2.
:- dynamic rule/2.

% solve/3 - Main entry point
%   Goal: what to prove
%   Result: dispatch(Agent, Action, Params) | proven(Goal, ProofTree) | failure(Goal, Reason)
solve(Goal, Result) :-
    solve(Goal, _CF, [], 20, Result).

% solve/5 - Core inference engine
%   Goal, CF, RuleStack, Threshold, Result

% Case 1: truth value already known
solve(Goal, CF, _, Threshold, proven(Goal, ((Goal,CF) :- known))) :-
    known(Goal, CF), !,
    above_threshold(CF, Threshold).

% Case 2a: negated goal — inner goal was proven, negate its CF
solve(not(Goal), CF, Rules, Threshold, proven(not(Goal), not(Proof))) :-
    invert_threshold(Threshold, NewThreshold),
    solve(Goal, CF_goal, Rules, NewThreshold, proven(_, Proof)), !,
    negate_cf(CF_goal, CF).

% Case 2b: negated goal — inner goal FAILED, so not(Goal) succeeds with CF=100
solve(not(Goal), 100, Rules, _, proven(not(Goal), not(failed(Goal)))) :-
    invert_threshold(20, NewThreshold),
    solve(Goal, _, Rules, NewThreshold, failure(_, _)), !.

% Case 3: conjunctive goals
solve((Goal1, Goal2), CF, Rules, Threshold, proven((Goal1,Goal2), (Proof1, Proof2))) :- !,
    solve(Goal1, CF1, Rules, Threshold, proven(_, Proof1)),
    above_threshold(CF1, Threshold),
    solve(Goal2, CF2, Rules, Threshold, proven(_, Proof2)),
    above_threshold(CF2, Threshold),
    and_cf(CF1, CF2, CF).

% Case 4: backchain on a rule
solve(Goal, CF, Rules, Threshold, proven(Goal, ((Goal,CF) :- Proof))) :-
    rule((Goal :- Premise), CF_rule),
    solve(Premise, CF_premise,
        [rule((Goal :- Premise), CF_rule)|Rules], Threshold, proven(_, Proof)),
    rule_cf(CF_rule, CF_premise, CF),
    above_threshold(CF, Threshold).

% Case 5: fact in knowledge base
solve(Goal, CF, _, Threshold, proven(Goal, ((Goal,CF) :- fact))) :-
    rule(Goal, CF),
    above_threshold(CF, Threshold).

% Case 6: removed — dispatch goals resolve through rules like everything else

% Case 7: native Prolog call
solve(Goal, 100, _, _, proven(Goal, ((Goal,100) :- call))) :-
    catch(call(Goal), _, fail).

% Case 8: FAILURE-AS-DATA - nothing matched
solve(Goal, 0, Rules, _, failure(Goal, missing_rule(Goal, RuleStack))) :-
    copy_term(Rules, RuleStack).

% CF algebra (simplified - keep for weighted rules)
negate_cf(CF, Neg) :- Neg is -1 * CF.
and_cf(A, B, A) :- A =< B.
and_cf(A, B, B) :- B < A.
rule_cf(CF_rule, CF_premise, CF) :- CF is CF_rule * CF_premise / 100.
above_threshold(CF, T) :- T >= 0, CF >= T.
above_threshold(CF, T) :- T < 0, CF =< T.
invert_threshold(T, NT) :- NT is -1 * T.

% Build proof tree (separate from solve - for inspection after the fact)
build_proof(Goal, CF, ((Goal,CF) :- known)) :-
    known(Goal, CF), !.
build_proof(not(Goal), CF, not(Proof)) :- !,
    build_proof(Goal, CF_goal, Proof),
    negate_cf(CF_goal, CF).
build_proof((Goal1, Goal2), CF, (Proof1, Proof2)) :- !,
    build_proof(Goal1, CF1, Proof1),
    build_proof(Goal2, CF2, Proof2),
    and_cf(CF1, CF2, CF).
build_proof(Goal, CF, ((Goal,CF) :- Proof)) :-
    rule((Goal :- Premise), CF_rule),
    build_proof(Premise, CF_premise, Proof),
    rule_cf(CF_rule, CF_premise, CF).
build_proof(Goal, CF, ((Goal,CF) :- fact)) :-
    rule(Goal, CF).
build_proof(Goal, 100, ((Goal,100) :- call)) :-
    catch(call(Goal), _, fail).

% solve_str/2 - Janus-safe wrapper: serializes result to atom before returning
solve_str(Goal, ResultStr) :-
    solve(Goal, R),
    with_output_to(atom(ResultStr), write(R)).

% solve_succeeds/1 - True iff solve(Goal, _) returns proven(_, _).
% Janus-safe: returns nothing but the success/fail of the goal, so the
% proof tree (which may contain @none/@true from py_call returns) is
% never serialized back to Python.
solve_succeeds(Goal) :-
    solve(Goal, Outcome),
    Outcome = proven(_, _),
    !.

% Proof tree to JSON-like term (for Janus serialization)
proof_to_term(((Goal,CF) :- known), json{goal: GoalStr, cf: CF, via: "known"}) :-
    term_string(Goal, GoalStr).
proof_to_term(((Goal,CF) :- fact), json{goal: GoalStr, cf: CF, via: "fact"}) :-
    term_string(Goal, GoalStr).
proof_to_term(((Goal,CF) :- call), json{goal: GoalStr, cf: CF, via: "call"}) :-
    term_string(Goal, GoalStr).
proof_to_term(((Goal,CF) :- SubProof), json{goal: GoalStr, cf: CF, via: "rule", proof: SubTerm}) :-
    term_string(Goal, GoalStr),
    proof_to_term(SubProof, SubTerm).
proof_to_term((Proof1, Proof2), json{type: "and", left: T1, right: T2}) :-
    proof_to_term(Proof1, T1),
    proof_to_term(Proof2, T2).
proof_to_term(not(Proof), json{type: "not", proof: T}) :-
    proof_to_term(Proof, T).
