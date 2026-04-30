% SOMA Enumerate — Derive the entire product space from what Prolog knows
%
% Given a process with typed partials, Prolog knows:
%   - Which args need authorization (only specific agents can provide)
%   - Which args need reality events (must come from outside the system)
%   - Which args can be generated (LLM can fill from other args)
%   - Which args have defaults
%   - Which deployment targets are possible (web, mobile, electron, etc)
%   - Which agent patterns apply (pipeline, interactive, batch, etc)
%
% From ALL of this, enumerate every valid:
%   - Entrypoint function (which args human provides vs generated)
%   - Agent configuration (which agent pattern wraps the function)
%   - Deployment target (which platform renders the output)
%   - Dashboard/UI (what monitoring/control surfaces exist)
%
% The rules ARE the product catalog. No RAG. Pure deduction.

:- dynamic arg_source/4.          % arg_source(Domain, Concept, Arg, Source)
                                   % Source: human_required | reality_event(Who) |
                                   %         generated_from(OtherArg) | defaultable(Value) |
                                   %         authorized_only(Who)
:- dynamic generation_rule/4.      % generation_rule(Domain, FromArg, ToArg, Method)
:- dynamic deployment_target/2.    % deployment_target(Domain, Target) — web|mobile|electron|cli|api
:- dynamic agent_pattern/2.        % agent_pattern(Domain, Pattern) — pipeline|interactive|batch|streaming

% ======================================================================
% ARG SOURCE CLASSIFICATION
% ======================================================================

% Classify an arg based on what we know about it
classify_arg(Domain, Concept, Arg, authorized_only(Who)) :-
    authorized_compilation(Domain, Concept, Who),
    arg_needs_authorization(Arg),
    !.

classify_arg(Domain, _Concept, Arg, reality_event(source)) :-
    % Arg value must come from reality — can't be generated
    domain_observation(Domain, _, Arg, _, _),
    \+ generation_rule(Domain, _, Arg, _),
    !.

classify_arg(Domain, _Concept, Arg, generated_from(FromArg)) :-
    generation_rule(Domain, FromArg, Arg, _),
    !.

classify_arg(_, _, Arg, defaultable(none)) :-
    has_default(Arg),
    !.

classify_arg(_, _, _, human_required).

% Args that need authorization
arg_needs_authorization(authorized_by).
arg_needs_authorization(has_approval).

% Args with defaults
has_default(style).

% ======================================================================
% GENERATION RULES — "given X, we can generate Y"
% These get observed into existence as the system learns
% ======================================================================

% Bootstrap: common generation patterns
:- assert(generation_rule(default, topic, thesis, llm_inference)).
:- assert(generation_rule(default, thesis, supporting_points, llm_inference)).
:- assert(generation_rule(default, topic, style, llm_inference)).

% Domain-specific generation rules get asserted through observations
% e.g., "for five_paragraph_essay, given topic we can generate thesis"
add_generation_rule(Domain, FromArg, ToArg, Method) :-
    assert(generation_rule(Domain, FromArg, ToArg, Method)).

% Can we generate this arg from what we have?
can_generate(Domain, Arg, ProvidedArgs) :-
    generation_rule(Domain, FromArg, Arg, _),
    member(FromArg, ProvidedArgs).
can_generate(_, Arg, ProvidedArgs) :-
    generation_rule(default, FromArg, Arg, _),
    member(FromArg, ProvidedArgs).

% Transitive generation: can generate Z if can generate Y and Y generates Z
can_generate_transitive(Domain, Arg, ProvidedArgs) :-
    can_generate(Domain, Arg, ProvidedArgs).
can_generate_transitive(Domain, Arg, ProvidedArgs) :-
    generation_rule(Domain, MidArg, Arg, _),
    can_generate_transitive(Domain, MidArg, ProvidedArgs).
can_generate_transitive(_, Arg, ProvidedArgs) :-
    generation_rule(default, MidArg, Arg, _),
    can_generate_transitive(default, MidArg, ProvidedArgs).

% ======================================================================
% ENTRYPOINT ENUMERATION — all valid functions we can construct
% ======================================================================

% Get all args for a process
process_args(Domain, Concept, Args) :-
    domain_partial(Domain, Concept, has_inputs, _, resolved(InputsStr)),
    split_string(InputsStr, ",", " ", ArgStrs),
    maplist(str_to_atom, ArgStrs, Args).

% A valid entrypoint: human provides HumanArgs, system generates the rest
valid_entrypoint(Domain, Concept, HumanArgs, GeneratedArgs) :-
    process_args(Domain, Concept, AllArgs),
    % Enumerate non-empty subsets of args the human could provide
    powerset_nonempty(AllArgs, HumanArgs),
    % The rest must be generable from what human provides
    subtract(AllArgs, HumanArgs, Remaining),
    all_generable(Domain, Remaining, HumanArgs),
    GeneratedArgs = Remaining.

% Check all remaining args can be generated from provided args
all_generable(_, [], _).
all_generable(Domain, [Arg|Rest], ProvidedArgs) :-
    can_generate_transitive(Domain, Arg, ProvidedArgs),
    all_generable(Domain, Rest, [Arg|ProvidedArgs]).  % Generated arg becomes available

% Generate non-empty subsets of a list (proper powerset minus empty set)
powerset_nonempty(List, Subset) :-
    powerset(List, Subset),
    Subset \= [].

powerset([], []).
powerset([H|T], [H|Sub]) :- powerset(T, Sub).
powerset([_|T], Sub) :- powerset(T, Sub).

% ======================================================================
% ENTRYPOINT NAMING — derive function name from restriction
% ======================================================================

% Name an entrypoint based on what human provides
entrypoint_name(Concept, HumanArgs, Name) :-
    atomic_list_concat(HumanArgs, '_and_', ArgPart),
    format(atom(Name), 'do_~w_from_~w', [Concept, ArgPart]).

% ======================================================================
% AGENT PATTERN ENUMERATION — what agent types can wrap this function
% ======================================================================

% Possible agent patterns for a process
possible_agent_pattern(Domain, Concept, pipeline) :-
    domain_concept(Domain, Concept, process),
    domain_has_rel(Domain, Concept, has_step, _).  % Has steps = pipeline

possible_agent_pattern(Domain, Concept, interactive) :-
    domain_concept(Domain, Concept, process),
    % Has steps AND some args need human feedback mid-process
    domain_has_rel(Domain, Concept, has_step, _),
    process_args(Domain, Concept, Args),
    member(Arg, Args),
    classify_arg(Domain, Concept, Arg, human_required).

possible_agent_pattern(_, _, batch) :-
    true.  % Batch is always possible

possible_agent_pattern(_, _, api) :-
    true.  % API endpoint is always possible

% ======================================================================
% DEPLOYMENT TARGET ENUMERATION
% ======================================================================

% Universal deployment targets
possible_deployment(_, _, cli) :- true.
possible_deployment(_, _, api) :- true.
possible_deployment(_, _, web) :- true.

% Conditional deployment targets
possible_deployment(Domain, Concept, mobile) :-
    % Mobile if process has simple inputs (< 5 args)
    process_args(Domain, Concept, Args),
    length(Args, N), N =< 5.

possible_deployment(Domain, Concept, electron) :-
    % Electron if process produces documents
    domain_partial(Domain, Concept, has_outputs, _, resolved(OutputStr)),
    (sub_atom(OutputStr, _, _, _, essay) ;
     sub_atom(OutputStr, _, _, _, document) ;
     sub_atom(OutputStr, _, _, _, report)).

% ======================================================================
% FULL PRODUCT SPACE — enumerate everything
% ======================================================================

% One product = entrypoint + agent pattern + deployment target
enumerate_product(Domain, Concept, product(FuncName, HumanArgs, GeneratedArgs, AgentPattern, DeployTarget)) :-
    valid_entrypoint(Domain, Concept, HumanArgs, GeneratedArgs),
    entrypoint_name(Concept, HumanArgs, FuncName),
    possible_agent_pattern(Domain, Concept, AgentPattern),
    possible_deployment(Domain, Concept, DeployTarget).

% Count the product space (deduplicated)
product_space_size(Domain, Concept, Size) :-
    findall(P, enumerate_product(Domain, Concept, P), Products),
    sort(Products, Unique),
    length(Unique, Size).

% List unique entrypoints (sorted by arg count ascending)
list_entrypoints(Domain, Concept, Entrypoints) :-
    findall(
        entry(Name, Human, Generated),
        (   valid_entrypoint(Domain, Concept, Human, Generated),
            entrypoint_name(Concept, Human, Name)
        ),
        RawEntrypoints
    ),
    sort(2, @=<, RawEntrypoints, Entrypoints).

% ======================================================================
% JANUS WRAPPERS
% ======================================================================

enumerate_str(Domain, Concept, Str) :-
    list_entrypoints(Domain, Concept, Entrypoints),
    findall(AP, possible_agent_pattern(Domain, Concept, AP), AgentPatterns),
    sort(AgentPatterns, UniqueAP),
    findall(DT, possible_deployment(Domain, Concept, DT), DeployTargets),
    sort(DeployTargets, UniqueDT),
    product_space_size(Domain, Concept, TotalProducts),
    with_output_to(atom(Str),
        (   format('PRODUCT SPACE for ~w in ~w:~n~n', [Concept, Domain]),
            format('ENTRYPOINTS (~w):~n', [Entrypoints]),
            forall(member(entry(Name, Human, Generated), Entrypoints),
                format('  ~w~n    Human provides: ~w~n    System generates: ~w~n', [Name, Human, Generated])
            ),
            format('~nAGENT PATTERNS: ~w~n', [UniqueAP]),
            format('DEPLOYMENT TARGETS: ~w~n', [UniqueDT]),
            format('TOTAL PRODUCTS: ~w~n', [TotalProducts])
        )).

% ======================================================================
% TESTS
% ======================================================================

% Test: generation rules exist
test_generation_rules :-
    generation_rule(default, topic, thesis, llm_inference),
    generation_rule(default, thesis, supporting_points, llm_inference).

% Test: can_generate from provided args
test_can_generate :-
    can_generate(default, thesis, [topic]),
    can_generate(default, supporting_points, [thesis]).

% Test: transitive generation
test_transitive_generation :-
    % Given topic, can we generate supporting_points? (topic→thesis→points)
    can_generate_transitive(default, supporting_points, [topic]).

% Test: valid entrypoints enumeration
test_valid_entrypoints :-
    register_domain(test_enum, 'Test'),
    domain_create_partials(test_enum, test_process, process),
    domain_resolve_partial(test_enum, test_process, has_steps, 'a'),
    domain_resolve_partial(test_enum, test_process, has_roles, 'r'),
    domain_resolve_partial(test_enum, test_process, has_inputs, 'topic,thesis,style'),
    domain_resolve_partial(test_enum, test_process, has_outputs, 'result'),
    % Enumerate entrypoints
    list_entrypoints(test_enum, test_process, Entrypoints),
    % Should have at least: topic_only (thesis+style generated), topic+thesis, all three
    Entrypoints \= [],
    % Clean up
    retractall(domain_registered(test_enum, _)),
    retractall(domain_concept(test_enum, _, _)),
    retractall(domain_partial(test_enum, _, _, _, _)),
    retractall(domain_has_rel(test_enum, _, _, _)),
    retractall(domain_heal_log(test_enum, _, _, _, _)).

% Test: entrypoint naming
test_entrypoint_naming :-
    entrypoint_name(essay, [topic], Name),
    Name = 'do_essay_from_topic'.

% Test: deployment targets include cli and api always
test_deployment_targets :-
    possible_deployment(_, _, cli),
    possible_deployment(_, _, api),
    possible_deployment(_, _, web).
