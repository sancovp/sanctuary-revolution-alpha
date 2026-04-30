% SOMA Bootstrap — Foundation Only
%
% This file is the entire Prolog side of the foundation. It contains
% NOTHING except the minimum needed to bootstrap the rule-as-data
% architecture:
%
%   1. consult(mi_core)               — load the meta-interpreter
%   2. dynamic decls                  — clause space for asserted rules
%   3. load_prolog_rules_from_owl/0   — bootstrap loader: walks every
%                                        PrologRule individual in
%                                        soma.owl, parses head+body as
%                                        ONE clause (so vars are shared),
%                                        and assertz's it as
%                                        rule((Head :- Body), 100) into
%                                        the MI's clause space.
%   4. ensure_rules_loaded/0          — idempotent gate around the loader
%   5. mi_add_event/3                 — THE one entrypoint core.py is
%                                        allowed to call. Routes through
%                                        solve/3 in mi_core.pl. Every
%                                        operation that follows comes
%                                        from a PrologRule individual
%                                        loaded from OWL.
%
% Every other rule (Pellet runs, OWL writes, persisting events,
% reporting, deduction chains, boot checks, OWL queries) lives as a
% PrologRule individual in soma.owl and enters the live runtime via
% the loader above. There are no other Prolog clauses in this file.
%
% The ONLY py_call in this file is the one inside the loader that
% reads PrologRule individuals out of OWL on boot. Without it, no
% rule could ever enter the system. Every other py_call lives inside
% PrologRule individuals stored in soma.owl.

:- use_module(library(lists)).
:- use_module(library(janus)).
:- consult(mi_core).
:- consult(soma_partials).
:- consult(soma_compile).

:- dynamic rules_loaded_flag/0.
:- dynamic unmet_requirement/1.

% ======================================================================
% BOOTSTRAP LOADER
% ======================================================================

load_prolog_rules_from_owl :-
    py_call('soma_prolog.utils':list_prolog_rules_snake(), Rules),
    forall(
        member(RuleStr, Rules),
        (   atom_string(RuleAtom, RuleStr),
            atomic_list_concat([_Name, HeadStr, BodyStr], '|', RuleAtom),
            catch(
                (   % Parse head+body as ONE clause so variable names
                    % shared between head and body refer to the SAME
                    % Prolog variable. Parsing them separately creates
                    % distinct vars even when names match, which breaks
                    % binding propagation through solve/3.
                    format(atom(ClauseAtom), '(~w) :- (~w)', [HeadStr, BodyStr]),
                    term_to_atom(Clause, ClauseAtom),
                    assertz(rule(Clause, 100)),
                    % Also assert as native clause so call/1 can find it
                    % (fire_all_deduction_chains uses call/1 not solve/3
                    % because solve/3 breaks after mi_add_event)
                    assertz(Clause)
                ),
                Err,
                format(user_error,
                    'load_prolog_rule failed: ~w~n  err: ~w~n',
                    [RuleStr, Err])
            )
        )
    ).

ensure_rules_loaded :-
    rules_loaded_flag, !.
ensure_rules_loaded :-
    load_prolog_rules_from_owl,
    assertz(rules_loaded_flag).

% ======================================================================
% mi_add_event/3 — THE ONE entrypoint core.py is allowed to call.
% Routes everything through solve/3 in mi_core.pl. The actual work
% happens in the prolog_rule_add_event PrologRule individual loaded
% from soma.owl.
% ======================================================================

mi_add_event(SourceStr, ObsListStr, ResultStr) :-
    ensure_rules_loaded,
    atom_string(Source, SourceStr),
    term_string(ObsList, ObsListStr),
    solve(add_event(Source, ObsList, Result), _Outcome),
    with_output_to(atom(ResultStr), write(Result)).

% mi_boot_check/1 — verify the system booted by routing through solve/3.
% The boot_check rule body is loaded from the prolog_rule_boot_check
% PrologRule individual in soma.owl. Same wiring discipline as add_event.
mi_boot_check(ResultStr) :-
    ensure_rules_loaded,
    solve(boot_check(Result), _Outcome),
    with_output_to(atom(ResultStr), write(Result)).
