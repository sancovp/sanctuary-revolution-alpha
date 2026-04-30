% SOMA Matching — Fuzzy→Exact matching that compiles through observation
%
% The system starts fuzzy (term matching, graph traversal) and gets MORE EXACT
% over time as observations create specific deduction chains.
% Each confirmed fuzzy match → Prolog rule → next time it's exact.
% The fuzziness compiles into exactness through observation.
%
% Three layers:
%   1. EXACT: direct rule exists (compiled from previous observation)
%   2. TERM MATCH: split query into terms, match against concept names
%   3. TYPED TRAVERSAL: IS_A, PART_OF, INSTANTIATES graph walk
%
% Confidence is PROOF DEPTH, not a float:
%   exact    = direct rule fired (depth 0)
%   term     = term overlap matched (depth 1)
%   traverse = graph traversal reached it (depth 2+)
%
% When a match is USED SUCCESSFULLY, it compiles to an exact rule.

:- discontiguous compiled_match/3.

:- dynamic compiled_match/3.      % compiled_match(QueryKey, ConceptName, Source)
                                   % Source: observed | term_compiled | traverse_compiled
:- dynamic concept_terms/2.       % concept_terms(ConceptName, TermList)
:- dynamic match_used/3.          % match_used(QueryKey, ConceptName, Timestamp)
:- dynamic match_compilation_log/4. % match_compilation_log(QueryKey, ConceptName, From, To)

% ======================================================================
% LAYER 0: EXACT MATCH — compiled rules from previous observations
% This is where the system converges. No fuzzy needed.
% ======================================================================

% "We already know what this query means"
match_exact(QueryKey, ConceptName, exact) :-
    compiled_match(QueryKey, ConceptName, _).

% ======================================================================
% LAYER 1: TERM MATCH — split query, match against concept names
% FP Layer 0 equivalent, but in Prolog
% ======================================================================

% Split an atom into lowercase atom terms on underscores and spaces
split_to_terms(Atom, AtomTerms) :-
    atom_string(Atom, Str),
    string_lower(Str, Lower),
    split_string(Lower, "_ ", "_ ", Parts),
    exclude(empty_string, Parts, NonEmpty),
    maplist(str_to_atom, NonEmpty, AtomTerms).

str_to_atom(Str, Atom) :- atom_string(Atom, Str).

empty_string("").
empty_string('').

% Index a concept's name into terms (call once per concept)
index_concept_terms(ConceptName) :-
    (   concept_terms(ConceptName, _)
    ->  true  % Already indexed
    ;   split_to_terms(ConceptName, Terms),
        assert(concept_terms(ConceptName, Terms))
    ).

% Index all domain concepts
index_domain_concepts(Domain) :-
    forall(
        domain_concept(Domain, ConceptName, _),
        index_concept_terms(ConceptName)
    ).

% Count term overlap between query terms and concept terms
term_overlap(QueryTerms, ConceptTerms, OverlapCount) :-
    intersection(QueryTerms, ConceptTerms, Overlap),
    length(Overlap, OverlapCount).

% Find concepts matching query by term overlap (sorted by overlap count)
match_by_terms(Domain, QueryAtom, Matches) :-
    split_to_terms(QueryAtom, QueryTerms),
    QueryTerms \= [],
    % Index all concepts in domain if not done
    index_domain_concepts(Domain),
    % Find all matches with overlap count
    findall(
        match(ConceptName, OverlapCount),
        (   domain_concept(Domain, ConceptName, _),
            concept_terms(ConceptName, ConceptTerms),
            term_overlap(QueryTerms, ConceptTerms, OverlapCount),
            OverlapCount > 0
        ),
        RawMatches
    ),
    % Sort by overlap count descending
    sort(2, @>=, RawMatches, Matches).

% Best term match for a query
match_term(Domain, QueryAtom, ConceptName, term(OverlapCount)) :-
    match_by_terms(Domain, QueryAtom, [match(ConceptName, OverlapCount)|_]),
    OverlapCount > 0.

% ======================================================================
% LAYER 2: TYPED TRAVERSAL — IS_A, PART_OF, INSTANTIATES graph walk
% Native Prolog backward chaining — this is what Prolog IS
% ======================================================================

% Traverse IS_A chain (concept → parent type → grandparent type → ...)
traverse_is_a(Domain, Concept, Target) :-
    domain_has_rel(Domain, Concept, is_a, Target).
traverse_is_a(Domain, Concept, Target) :-
    domain_has_rel(Domain, Concept, is_a, Mid),
    Mid \= Target,
    traverse_is_a(Domain, Mid, Target).

% Traverse PART_OF chain (concept → container → container's container → ...)
traverse_part_of(Domain, Concept, Target) :-
    domain_has_rel(Domain, Concept, part_of, Target).
traverse_part_of(Domain, Concept, Target) :-
    domain_has_rel(Domain, Concept, part_of, Mid),
    Mid \= Target,
    traverse_part_of(Domain, Mid, Target).

% Traverse INSTANTIATES
traverse_instantiates(Domain, Concept, Pattern) :-
    domain_has_rel(Domain, Concept, instantiates, Pattern).

% Match by traversal — find concepts reachable from query via typed edges
match_traverse(Domain, QueryAtom, ConceptName, traverse(Path)) :-
    % Find a concept whose name or type matches the query
    split_to_terms(QueryAtom, QueryTerms),
    QueryTerms \= [],
    domain_concept(Domain, ConceptName, _),
    % Check if any typed traversal connects this concept to the query
    (   % Direct IS_A match
        traverse_is_a(Domain, ConceptName, TypeName),
        concept_terms(TypeName, TypeTerms),
        term_overlap(QueryTerms, TypeTerms, N), N > 0,
        Path = [is_a, TypeName]
    ;   % PART_OF match
        traverse_part_of(Domain, ConceptName, ContainerName),
        concept_terms(ContainerName, ContTerms),
        term_overlap(QueryTerms, ContTerms, N), N > 0,
        Path = [part_of, ContainerName]
    ;   % INSTANTIATES match
        traverse_instantiates(Domain, ConceptName, PatternName),
        concept_terms(PatternName, PatTerms),
        term_overlap(QueryTerms, PatTerms, N), N > 0,
        Path = [instantiates, PatternName]
    ).

% ======================================================================
% UNIFIED MATCH — try all layers in order, return best
% ======================================================================

% Try exact first, then term, then traversal
resolve_match(Domain, QueryAtom, ConceptName, Confidence) :-
    (   match_exact(QueryAtom, ConceptName, Confidence)
    ->  true
    ;   match_term(Domain, QueryAtom, ConceptName, Confidence)
    ->  true
    ;   match_traverse(Domain, QueryAtom, ConceptName, Confidence)
    ->  true
    ;   ConceptName = not_found, Confidence = none
    ).

% Resolve and record usage (for compilation tracking)
resolve_and_track(Domain, QueryAtom, ConceptName, Confidence) :-
    resolve_match(Domain, QueryAtom, ConceptName, Confidence),
    ConceptName \= not_found,
    get_time(T),
    assert(match_used(QueryAtom, ConceptName, T)).

% ======================================================================
% COMPILATION — confirmed matches become exact rules
% The fuzzy→exact ratchet
% ======================================================================

% Compile a used match into an exact rule
% Call this when a match was CONFIRMED (the fill was used successfully)
compile_match_to_rule(QueryKey, ConceptName) :-
    \+ compiled_match(QueryKey, ConceptName, _),
    % Determine what layer found it
    (   match_used(QueryKey, ConceptName, _)
    ->  true
    ;   true  % Allow manual compilation too
    ),
    assert(compiled_match(QueryKey, ConceptName, compiled)),
    get_time(T),
    format(atom(Source), 'compiled_at_~f', [T]),
    assert(match_compilation_log(QueryKey, ConceptName, fuzzy, Source)).

% Auto-compile: if a match has been used N times, compile it
auto_compile_frequent_matches(Threshold) :-
    findall(
        key(Q, C),
        (   match_used(Q, C, _),
            findall(T, match_used(Q, C, T), Times),
            length(Times, N),
            N >= Threshold,
            \+ compiled_match(Q, C, _)
        ),
        ToCompile
    ),
    forall(
        member(key(Q, C), ToCompile),
        compile_match_to_rule(Q, C)
    ).

% ======================================================================
% DOMAIN INTEGRATION — matching fills partials
% ======================================================================

% Use matching to resolve an observation key to a domain partial
match_observation_to_partial(Domain, ObsKey, ObsValue, Concept, Prop) :-
    % Try to match the observation key to a known property
    resolve_match(Domain, ObsKey, MatchedProp, _Confidence),
    MatchedProp \= not_found,
    % Find a concept with this property unnamed
    domain_partial(Domain, Concept, MatchedProp, _TargetType, unnamed),
    % Fill it
    domain_resolve_partial(Domain, Concept, MatchedProp, ObsValue),
    % Track the match for compilation
    get_time(T),
    assert(match_used(ObsKey, MatchedProp, T)).

% ======================================================================
% JANUS WRAPPERS
% ======================================================================

resolve_match_str(Domain, Query, Str) :-
    resolve_match(Domain, Query, Concept, Confidence),
    with_output_to(atom(Str),
        format('~w → ~w [~w]', [Query, Concept, Confidence])).

list_compiled_matches_str(Str) :-
    findall(
        compiled(Q, C, S),
        compiled_match(Q, C, S),
        Compiled
    ),
    length(Compiled, N),
    with_output_to(atom(Str),
        (   format('~w compiled matches:~n', [N]),
            forall(member(compiled(Q, C, S), Compiled),
                format('  ~w → ~w (~w)~n', [Q, C, S])
            )
        )).

% ======================================================================
% TESTS
% ======================================================================

% Test: term splitting
test_term_splitting :-
    split_to_terms(five_paragraph_essay, Terms),
    member(five, Terms),
    member(paragraph, Terms),
    member(essay, Terms).

% Test: term overlap
test_term_overlap :-
    term_overlap([five, paragraph, essay], [five, paragraph, essay, step], 3).

% Test: exact match after compilation
test_exact_match :-
    assert(compiled_match(test_query, test_concept, observed)),
    match_exact(test_query, test_concept, exact),
    retract(compiled_match(test_query, test_concept, observed)).

% Test: term match in domain
test_domain_term_match :-
    register_domain(test_match_dom, 'Test'),
    domain_create_partials(test_match_dom, five_paragraph_essay, process),
    index_domain_concepts(test_match_dom),
    match_term(test_match_dom, essay, five_paragraph_essay, term(N)),
    N > 0,
    % Clean up
    retractall(domain_registered(test_match_dom, _)),
    retractall(domain_concept(test_match_dom, _, _)),
    retractall(domain_partial(test_match_dom, _, _, _, _)),
    retractall(domain_heal_log(test_match_dom, _, _, _, _)),
    retractall(concept_terms(five_paragraph_essay, _)).

% Test: compilation ratchet — fuzzy becomes exact
test_compilation_ratchet :-
    % First: no compiled match exists
    \+ compiled_match(my_fuzzy_query, my_concept, _),
    % Compile it
    compile_match_to_rule(my_fuzzy_query, my_concept),
    % Now exact match works
    match_exact(my_fuzzy_query, my_concept, exact),
    % Clean up
    retract(compiled_match(my_fuzzy_query, my_concept, _)),
    retractall(match_compilation_log(my_fuzzy_query, my_concept, _, _)).

% Test: resolve_match tries exact before fuzzy
test_resolve_order :-
    register_domain(test_resolve_dom, 'Test'),
    domain_create_partials(test_resolve_dom, invoice_processing, process),
    index_domain_concepts(test_resolve_dom),
    % No compiled match — should use term match
    resolve_match(test_resolve_dom, invoice, invoice_processing, Conf1),
    Conf1 = term(_),
    % Now compile it
    compile_match_to_rule(invoice, invoice_processing),
    % Should use exact match now
    resolve_match(test_resolve_dom, invoice, invoice_processing, Conf2),
    Conf2 = exact,
    % Clean up
    retractall(domain_registered(test_resolve_dom, _)),
    retractall(domain_concept(test_resolve_dom, _, _)),
    retractall(domain_partial(test_resolve_dom, _, _, _, _)),
    retractall(domain_heal_log(test_resolve_dom, _, _, _, _)),
    retractall(concept_terms(invoice_processing, _)),
    retract(compiled_match(invoice, invoice_processing, _)),
    retractall(match_compilation_log(invoice, invoice_processing, _, _)).
