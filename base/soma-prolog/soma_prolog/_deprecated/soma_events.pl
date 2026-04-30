% SOMA Event Ontology — Toy BI Knowledge Base
% Tests the MI with typed business observations
%
% Typed observations: observe(Who, What, Subject, Key=Value)
% Key=Value carries PROGRAMMING types (str, float, int, bool)

:- use_module(library(lists)).
:- consult(mi_core).

% === TYPED OBSERVATIONS (these accumulate from employee conversations) ===

% Employee observations — what people say about their work
:- dynamic observe/4.
:- dynamic known/2.
:- dynamic process/3.       % process(Name, Description, Status)
:- dynamic sop_exists/1.    % sop_exists(ProcessName)

% === RULES: What observations MEAN ===

% When someone does X repeatedly without a documented SOP, there's a missing SOP
rule((missing_sop(Process) :-
    (observe(_, does, Process, frequency=F),
     F > 3,
     not(sop_exists(Process)))), 90).

% When multiple people do the same thing, it's a shared process
rule((shared_process(Process) :-
    (observe(Person1, does, Process, _),
     observe(Person2, does, Process, _),
     Person1 \= Person2)), 85).

% When a process takes too long, it needs optimization
rule((needs_optimization(Process) :-
    (observe(_, does, Process, duration_minutes=D),
     D > 60)), 80).

% When a process has errors, it needs better documentation
rule((needs_documentation(Process) :-
    (observe(_, error_in, Process, severity=high))), 95).

% When a missing SOP is for a shared process, it's HIGH priority
rule((high_priority_sop(Process) :-
    (missing_sop(Process), shared_process(Process))), 95).

% === DISPATCH RULES: What to DO about conclusions ===

% Missing SOP → dispatch to SOP generator
rule((dispatch(sop_generator, generate_sop, Process) :-
    high_priority_sop(Process)), 100).

% Needs optimization → dispatch to process analyzer
rule((dispatch(process_analyzer, analyze, Process) :-
    needs_optimization(Process)), 100).

% === SAMPLE DATA: Simulate employee conversations ===

% "I do invoice processing about 5 times a week, takes about 90 minutes each time"
observe(alice, does, invoice_processing, frequency=5).
observe(alice, does, invoice_processing, duration_minutes=90).

% "I also do invoice processing, about 4 times a week"
observe(bob, does, invoice_processing, frequency=4).
observe(bob, does, invoice_processing, duration_minutes=75).

% "I handle customer onboarding, maybe twice a week"
observe(carol, does, customer_onboarding, frequency=2).
observe(carol, does, customer_onboarding, duration_minutes=120).

% "We had a bad error in the shipping process yesterday"
observe(dave, error_in, shipping, severity=high).

% No SOPs exist yet
% (sop_exists/1 is empty — this is a fresh business)

% === TEST QUERIES ===
%
% Test 1: ?- solve(missing_sop(X), Result).
%   Should find: invoice_processing (frequency > 3, no SOP)
%
% Test 2: ?- solve(shared_process(X), Result).
%   Should find: invoice_processing (alice + bob)
%
% Test 3: ?- solve(high_priority_sop(X), Result).
%   Should find: invoice_processing (missing + shared)
%
% Test 4: ?- solve(dispatch(Agent, Action, What), Result).
%   Should find: dispatch(sop_generator, generate_sop, invoice_processing)
%   Should find: dispatch(process_analyzer, analyze, invoice_processing)
%   Should find: dispatch(process_analyzer, analyze, customer_onboarding)
%
% Test 5: ?- solve(needs_documentation(X), Result).
%   Should find: shipping (error with severity=high)
