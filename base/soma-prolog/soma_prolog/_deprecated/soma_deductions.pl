% SOMA Deduction Chains — Universal reward/fitness/quality logic
%
% These are the UNIVERSAL patterns extracted from the legacy reward system.
% Domain-specific facts (event types, reward values, multipliers) are DATA.
% The deduction chains are RULES that work on any domain.
%
% The legacy system did all this in Python dicts + arithmetic.
% Now Prolog does it: facts + rules + backward chaining = deduction chains.
%
% To add a new domain: just assert new event_reward/2, zone_multiplier/2,
% and completion_signal/3 facts. The rules apply automatically.

:- discontiguous event_reward/2.
:- discontiguous zone_multiplier/2.
:- discontiguous completion_signal/3.
:- discontiguous penalty_signal/3.

:- dynamic event_reward/2.        % event_reward(EventType, BaseScore)
:- dynamic zone_multiplier/2.     % zone_multiplier(Zone, Multiplier)
:- dynamic completion_signal/3.   % completion_signal(SequenceType, StartEvent, EndEvent)
:- dynamic penalty_signal/3.      % penalty_signal(SequenceType, PenaltyEvent, Reason)
:- dynamic event_in_sequence/3.   % event_in_sequence(SequenceId, EventType, Timestamp)
:- dynamic sequence_zone/2.       % sequence_zone(SequenceId, Zone)
:- dynamic event_error/2.         % event_error(EventId, Reason)
:- dynamic authorization/2.       % authorization(Entity, AuthorizedBy)

% ======================================================================
% DOMAIN FACTS — Starsystem domain (from legacy scoring.py)
% New domains add their own facts below this section.
% ======================================================================

% --- Event base rewards ---
event_reward(mission_start, 100).
event_reward(mission_report_progress, 50).
event_reward(mission_complete, 500).
event_reward(mission_inject_step, -20).
event_reward(mission_request_extraction, -200).
event_reward(start_starlog, 20).
event_reward(end_starlog, 100).
event_reward(update_debug_diary, 5).
event_reward(start_waypoint_journey, 10).
event_reward(navigate_to_next_waypoint, 15).
event_reward(abort_waypoint_journey, -30).
event_reward(plot_course, 50).
event_reward(omnisanc_error, -10).
event_reward(validation_block, -5).

% --- Zone multipliers ---
zone_multiplier(home, 1.0).
zone_multiplier(session, 3.0).
zone_multiplier(mission, 10.0).

% --- Completion signals: what start+end means "complete" ---
completion_signal(session, start_starlog, end_starlog).
completion_signal(mission, mission_start, mission_complete).
completion_signal(waypoint, start_waypoint_journey, navigate_to_next_waypoint).

% --- Penalty signals: what events mean failure ---
penalty_signal(mission, mission_request_extraction, 'Mission abandoned').
penalty_signal(waypoint, abort_waypoint_journey, 'Waypoint abandoned').

% ======================================================================
% UNIVERSAL DEDUCTION RULES — Work on any domain
% ======================================================================

% --- R1: Event reward lookup ---
% "When event of type T occurs, its base reward is S"
deduce_reward(EventType, Score) :-
    event_reward(EventType, Score).

% Unknown event type → 0 reward (not an error, just unscored)
deduce_reward(EventType, 0) :-
    \+ event_reward(EventType, _).

% --- R2: Sequence completion ---
% "A sequence is complete when it has both its start and end signals"
sequence_complete(SequenceId, SequenceType) :-
    completion_signal(SequenceType, StartEvent, EndEvent),
    event_in_sequence(SequenceId, StartEvent, _T1),
    event_in_sequence(SequenceId, EndEvent, _T2).

% "A sequence is incomplete when it has start but no end"
sequence_incomplete(SequenceId, SequenceType) :-
    completion_signal(SequenceType, StartEvent, _EndEvent),
    event_in_sequence(SequenceId, StartEvent, _),
    \+ sequence_complete(SequenceId, SequenceType).

% "A sequence failed when it has a penalty signal"
sequence_failed(SequenceId, SequenceType, Reason) :-
    penalty_signal(SequenceType, PenaltyEvent, Reason),
    event_in_sequence(SequenceId, PenaltyEvent, _).

% --- R3: Completion bonus ---
% "Complete sequences get a bonus (100 for sessions, 500 for missions)"
completion_bonus(SequenceId, SequenceType, Bonus) :-
    sequence_complete(SequenceId, SequenceType),
    (   SequenceType = session -> Bonus = 100
    ;   SequenceType = mission -> Bonus = 500
    ;   Bonus = 50  % default
    ).

completion_bonus(SequenceId, SequenceType, 0) :-
    \+ sequence_complete(SequenceId, SequenceType).

% --- R4: Error counting ---
% "Count errors in a sequence"
count_errors_in_sequence(SequenceId, Count) :-
    findall(E, (event_in_sequence(SequenceId, E, _), event_error(E, _)), Errors),
    length(Errors, Count).

% "Count total events in a sequence"
count_events_in_sequence(SequenceId, Count) :-
    findall(E, event_in_sequence(SequenceId, E, _), Events),
    length(Events, Count).

% --- R5: Quality factor ---
% "Quality = 1 - error_rate. Quality is always between 0.0 and 1.0"
quality_factor(SequenceId, Quality) :-
    count_events_in_sequence(SequenceId, Total),
    count_errors_in_sequence(SequenceId, Errors),
    (   Total > 0
    ->  Quality is max(0.0, 1.0 - (Errors / Total))
    ;   Quality = 1.0
    ).

% --- R6: Base reward for a sequence ---
% "Sum all event rewards in a sequence"
sequence_base_reward(SequenceId, Total) :-
    findall(
        Score,
        (   event_in_sequence(SequenceId, EventType, _),
            deduce_reward(EventType, Score)
        ),
        Scores
    ),
    sum_list(Scores, Total).

% --- R7: Sequence reward (the full deduction chain) ---
% "Sequence reward = (base_reward + completion_bonus) * quality * zone_multiplier"
% THIS is the deduction chain: reward DEPENDS ON base, completion, quality, zone.
sequence_reward(SequenceId, SequenceType, Reward) :-
    sequence_base_reward(SequenceId, Base),
    completion_bonus(SequenceId, SequenceType, Bonus),
    quality_factor(SequenceId, Quality),
    sequence_zone(SequenceId, Zone),
    zone_multiplier(Zone, Multiplier),
    Reward is (Base + Bonus) * Quality * Multiplier.

% Fallback: no zone assigned → multiplier = 1
sequence_reward(SequenceId, SequenceType, Reward) :-
    \+ sequence_zone(SequenceId, _),
    sequence_base_reward(SequenceId, Base),
    completion_bonus(SequenceId, SequenceType, Bonus),
    quality_factor(SequenceId, Quality),
    Reward is (Base + Bonus) * Quality.

% --- R8: Fitness (aggregation across sequences) ---
% "Fitness = sum(all sequence rewards) * global quality"
fitness(Date, Fitness) :-
    findall(
        Reward,
        (   event_in_sequence(SeqId, _, _),
            sequence_zone(SeqId, _Zone),
            completion_signal(SeqType, _, _),
            sequence_reward(SeqId, SeqType, Reward)
        ),
        AllRewards
    ),
    sort(AllRewards, UniqueRewards),  % deduplicate
    sum_list(UniqueRewards, TotalReward),
    global_quality(Date, GQ),
    Fitness is TotalReward * GQ.

% "Global quality = quality across ALL events on a date"
global_quality(Date, GQ) :-
    findall(E, event_in_sequence(_, E, _), AllEvents),
    length(AllEvents, Total),
    findall(E, (event_in_sequence(_, E, _), event_error(E, _)), AllErrors),
    length(AllErrors, ErrorCount),
    (   Total > 0
    ->  GQ is max(0.0, 1.0 - (ErrorCount / Total))
    ;   GQ = 1.0
    ).

% --- R9: XP and Level ---
% "XP = total accumulated rewards. Level = floor(XP / 1000)"
xp(Date, XP) :-
    findall(
        Reward,
        (   event_in_sequence(SeqId, _, _),
            completion_signal(SeqType, _, _),
            sequence_reward(SeqId, SeqType, Reward)
        ),
        AllRewards
    ),
    sort(AllRewards, UniqueRewards),
    sum_list(UniqueRewards, XP).

level(Date, Level) :-
    xp(Date, XP),
    Level is floor(XP / 1000).

% ======================================================================
% PROCESS DEDUCTION — When observations become typed processes
% This connects SOMA events to the Process compilation pipeline.
% ======================================================================

% "When we see N observations about the same task, it's a Process"
deduce_process(TaskName, soup) :-
    findall(E, candidate_process(TaskName, E), Events),
    length(Events, N),
    N >= 3.

% "When a Process has an SOP, it becomes CodifiedProcess"
deduce_process(TaskName, codified) :-
    deduce_process(TaskName, soup),
    sop_candidate(TaskName).

% "When a CodifiedProcess is authorized, it becomes ProgrammedProcess"
deduce_process(TaskName, programmed) :-
    deduce_process(TaskName, codified),
    authorized_process(TaskName).

% "What stage is this process at?"
process_stage(TaskName, Stage) :-
    (   deduce_process(TaskName, programmed) -> Stage = programmed
    ;   deduce_process(TaskName, codified)   -> Stage = codified
    ;   deduce_process(TaskName, soup)       -> Stage = soup
    ;   Stage = unobserved
    ).

% ======================================================================
% AUTHORIZATION DEDUCTION — Human gate in the compilation pipeline
% ======================================================================

% "A process is authorized when an AuthorizedPersonnel approves it"
authorize_process(TaskName, AuthorizedBy) :-
    \+ authorized_process(TaskName),
    assert(authorized_process(TaskName)),
    assert(authorization(TaskName, AuthorizedBy)).

% "Who authorized this process?"
who_authorized(TaskName, Who) :-
    authorization(TaskName, Who).

% "Is authorization required for this process stage transition?"
requires_authorization(TaskName, codified_to_programmed) :-
    deduce_process(TaskName, codified),
    \+ authorized_process(TaskName).

% ======================================================================
% TEMPLATE DEDUCTION — When code entities become templatable
% ======================================================================

% "A code entity is templatable when all its deps are resolved"
deduce_templatable(ClassName) :-
    deep_analyzed(ClassName),
    \+ has_unresolved_deps(ClassName).

% "A templatable entity that configures others is a Configurator"
deduce_configurator(ClassName) :-
    deduce_templatable(ClassName),
    configures_other(ClassName, _).

% "What template engineering capabilities does this entity have?"
template_capabilities(ClassName, Caps) :-
    findall(Cap, (
        (deduce_templatable(ClassName) -> Cap = templatable ; fail),
        (deduce_configurator(ClassName) -> Cap = configurator ; fail)
    ), RawCaps),
    sort(RawCaps, Caps).

% Better version: collect capabilities individually
has_capability_of(ClassName, templatable) :- deduce_templatable(ClassName).
has_capability_of(ClassName, configurator) :- deduce_configurator(ClassName).
has_capability_of(ClassName, deep_analyzed) :- deep_analyzed(ClassName).

% ======================================================================
% SMALL WORLD NETWORK DEDUCTIONS — From the research
% "Temperature" controls exploration vs exploitation in inference
% ======================================================================

% "Exploration temperature" for a domain — how much to explore
% High temp = try more inference rules. Low temp = stick to proven ones.
:- dynamic domain_temperature/2.  % domain_temperature(Domain, Temp)

% Default temperatures
domain_temperature(default, 0.5).
domain_temperature(mission, 0.3).   % Low temp: missions need reliability
domain_temperature(exploration, 0.8). % High temp: exploration needs creativity

% "Should we explore this inference path?"
% Higher temperature = more likely to explore uncertain rules
should_explore(Domain, RuleName) :-
    domain_temperature(Domain, Temp),
    inference_rule(RuleName, _, _),
    % In real system: use Temp to probabilistically decide
    % For now: always explore (Prolog is deterministic)
    Temp > 0.0.

% ======================================================================
% CONFIGURATION SPACE SUBCLASSING
% The universal function restricts through observation into specific
% named functions. Each restriction IS a new word in TWILITELANG.
% The Human<->LLM observation flow IS the compiler.
% ======================================================================

:- dynamic universal_function/2.   % universal_function(Name, Arity)
:- dynamic restriction/4.          % restriction(UniversalName, RestrictedName, FilledPartials, Source)
:- dynamic named_function/3.       % named_function(Name, DerivedFrom, PartialSet)
:- dynamic word_in_lang/2.         % word_in_lang(WordName, Meaning)

% The root universal functions — everything starts here
universal_function(call_agent, 1).       % call_agent(X) — do anything via agent
universal_function(observe, 2).          % observe(Source, Data) — receive typed data
universal_function(template, 2).         % template(Spec, Config) — instantiate from spec
universal_function(render, 1).           % render(MetaStack) — produce output
universal_function(configure, 2).        % configure(Target, Config) — configure anything

% --- Rule: When a Process has enough filled partials, it restricts call_agent ---
% "call_agent(X)" + filled partials for invoice_processing
%   → "do_invoice_processing()" which IS call_agent restricted to this specific case
deduce_restriction(ProcessName) :-
    concept_type(ProcessName, process),
    partial_count(ProcessName, Total, Unnamed, Filled),
    Filled > 0,
    \+ restriction(call_agent, ProcessName, _, _),
    % Collect what we know (the filled partials)
    findall(
        filled(Prop, Value),
        (partial(ProcessName, Prop, _, resolved(Value)) ;
         partial(ProcessName, Prop, _, ca_resolved(Value))),
        FilledPartials
    ),
    format(atom(RestrictedName), 'do_~w', [ProcessName]),
    assert(restriction(call_agent, RestrictedName, FilledPartials, observation)),
    assert(named_function(RestrictedName, call_agent, FilledPartials)),
    assert(word_in_lang(RestrictedName, ProcessName)).

% --- Rule: When a restriction is fully specified, it becomes a callable word ---
% A named function with ALL partials filled = a complete word in the language
word_is_complete(WordName) :-
    named_function(WordName, _, _),
    restriction(_, WordName, _, _),
    % Check the underlying concept has no unnamed partials
    word_in_lang(WordName, ConceptName),
    \+ partial(ConceptName, _, _, unnamed).

% --- Rule: A complete word can ITSELF be restricted further ---
% "do_invoice_processing()" + more observations about subtypes
%   → "do_priority_invoice_processing()" which is do_invoice_processing restricted
deduce_sub_restriction(ParentWord, ChildConcept) :-
    word_is_complete(ParentWord),
    word_in_lang(ParentWord, ParentConcept),
    % ChildConcept is observed as a subtype of ParentConcept
    has_rel(ChildConcept, is_subtype_of, ParentConcept),
    \+ restriction(ParentWord, _, _, _),
    findall(
        filled(Prop, Value),
        (partial(ChildConcept, Prop, _, resolved(Value)) ;
         partial(ChildConcept, Prop, _, ca_resolved(Value))),
        ChildPartials
    ),
    format(atom(ChildWord), 'do_~w', [ChildConcept]),
    assert(restriction(ParentWord, ChildWord, ChildPartials, sub_observation)),
    assert(named_function(ChildWord, ParentWord, ChildPartials)),
    assert(word_in_lang(ChildWord, ChildConcept)).

% --- Rule: Template restriction — when we know the code form, template directly ---
% If a Process has been completed before (template exists), new instances
% of the same pattern use the template instead of building from scratch
deduce_template_restriction(ProcessName, TemplateName) :-
    concept_type(ProcessName, process),
    % Check if we have a completed template for this type of process
    named_function(ExistingWord, _, ExistingPartials),
    word_is_complete(ExistingWord),
    % Check if current process's filled partials match the existing template
    findall(
        filled(Prop, _),
        partial(ProcessName, Prop, _, resolved(_)),
        CurrentPartials
    ),
    % Same property names = same pattern
    findall(P, member(filled(P, _), ExistingPartials), ExistingProps),
    findall(P, member(filled(P, _), CurrentPartials), CurrentProps),
    subset(CurrentProps, ExistingProps),
    TemplateName = ExistingWord.

% --- Rule: Resolution routing based on what's known ---
% Three paths: template (already known), generate (agent can do it), ask (needs human)

% Path 1: Template — we already have a completed word for this pattern
resolution_path(ConceptName, template(TemplateName)) :-
    deduce_template_restriction(ConceptName, TemplateName).

% Path 2: Generate — enough context for an agent to fill the rest
resolution_path(ConceptName, generate(Context)) :-
    \+ deduce_template_restriction(ConceptName, _),
    concept_type(ConceptName, _),
    partial_count(ConceptName, Total, Unnamed, Filled),
    Total > 0,
    Filled > 0,  % We know SOMETHING
    Unnamed > 0, % But not everything
    % The filled partials ARE the context for the agent
    findall(
        context(Prop, Value),
        (partial(ConceptName, Prop, _, resolved(Value)) ;
         partial(ConceptName, Prop, _, ca_resolved(Value))),
        Context
    ),
    Context \= [].

% Path 3: Ask human — we know almost nothing, need reality
resolution_path(ConceptName, ask_human(Missing)) :-
    \+ deduce_template_restriction(ConceptName, _),
    concept_type(ConceptName, _),
    partial_count(ConceptName, Total, Unnamed, Filled),
    (   Filled =:= 0  % We know NOTHING
    ;   Total > 0, Unnamed > 0,
        % Can't generate — not enough context
        findall(
            context(Prop, Value),
            (partial(ConceptName, Prop, _, resolved(Value)) ;
             partial(ConceptName, Prop, _, ca_resolved(Value))),
            Context
        ),
        Context = []
    ),
    missing_partials(ConceptName, Missing).

% --- Rule: Language growth tracking ---
% How many words does the language have?
language_size(Count) :-
    findall(W, word_in_lang(W, _), Words),
    length(Words, Count).

% How many words are complete (callable)?
complete_words(Count) :-
    findall(W, word_is_complete(W), Words),
    length(Words, Count).

% What's the restriction depth? (how many levels of specialization)
restriction_depth(Word, 0) :-
    named_function(Word, UniversalName, _),
    universal_function(UniversalName, _), !.
restriction_depth(Word, Depth) :-
    named_function(Word, Parent, _),
    restriction_depth(Parent, ParentDepth),
    Depth is ParentDepth + 1.
restriction_depth(Word, 0) :-
    \+ named_function(Word, _, _).

% ======================================================================
% TESTS for configuration space subclassing
% ======================================================================

% Test: universal functions exist
test_universal_functions :-
    universal_function(call_agent, 1),
    universal_function(observe, 2),
    universal_function(template, 2),
    universal_function(render, 1),
    universal_function(configure, 2).

% Test: restriction creation from filled partials
test_restriction_creation :-
    % Create a process with some filled partials
    create_partials(test_restrict_proc, process),
    resolve_partial_from_observation(test_restrict_proc, has_steps, 'step_a,step_b'),
    resolve_partial_from_observation(test_restrict_proc, has_roles, 'operator'),
    % Deduce restriction
    deduce_restriction(test_restrict_proc),
    % Should have created a named function
    named_function('do_test_restrict_proc', call_agent, _),
    word_in_lang('do_test_restrict_proc', test_restrict_proc),
    % Should have a restriction record
    restriction(call_agent, 'do_test_restrict_proc', _, observation),
    % Clean up
    retractall(concept_type(test_restrict_proc, _)),
    retractall(partial(test_restrict_proc, _, _, _)),
    retractall(has_rel(test_restrict_proc, _, _)),
    retractall(heal_log(test_restrict_proc, _, _, _)),
    retractall(restriction(call_agent, 'do_test_restrict_proc', _, _)),
    retractall(named_function('do_test_restrict_proc', _, _)),
    retractall(word_in_lang('do_test_restrict_proc', _)).

% Test: resolution routing — generate path
test_resolution_generate :-
    create_partials(test_resolve_gen, process),
    resolve_partial_from_observation(test_resolve_gen, has_steps, 'some_steps'),
    % Has some filled, some unnamed → generate path
    resolution_path(test_resolve_gen, generate(Context)),
    Context \= [],
    % Clean up
    retractall(concept_type(test_resolve_gen, _)),
    retractall(partial(test_resolve_gen, _, _, _)),
    retractall(has_rel(test_resolve_gen, _, _)),
    retractall(heal_log(test_resolve_gen, _, _, _)).

% Test: resolution routing — ask human path
test_resolution_ask_human :-
    create_partials(test_resolve_ask, process),
    % Nothing filled → ask human
    resolution_path(test_resolve_ask, ask_human(Missing)),
    Missing \= [],
    % Clean up
    retractall(concept_type(test_resolve_ask, _)),
    retractall(partial(test_resolve_ask, _, _, _)),
    retractall(heal_log(test_resolve_ask, _, _, _)).

% ======================================================================
% JANUS-SAFE WRAPPERS
% ======================================================================

% Get all deductions for a sequence
get_sequence_deductions_str(SequenceId, Str) :-
    (   sequence_base_reward(SequenceId, Base) -> true ; Base = 0 ),
    (   quality_factor(SequenceId, Q) -> true ; Q = 1.0 ),
    findall(ST, sequence_complete(SequenceId, ST), CompletedTypes),
    findall(ST-R, sequence_failed(SequenceId, ST, R), FailedTypes),
    with_output_to(atom(Str),
        (   format('Sequence ~w: base_reward=~w, quality=~w~n', [SequenceId, Base, Q]),
            format('  completed: ~w~n', [CompletedTypes]),
            format('  failed: ~w~n', [FailedTypes])
        )).

% Get process stage
get_process_stage_str(TaskName, Str) :-
    process_stage(TaskName, Stage),
    (   requires_authorization(TaskName, What)
    ->  format(atom(Str), 'Process ~w: stage=~w, requires_authorization=~w', [TaskName, Stage, What])
    ;   format(atom(Str), 'Process ~w: stage=~w', [TaskName, Stage])
    ).

% ======================================================================
% TESTS
% ======================================================================

% Test: event rewards are facts
test_event_rewards :-
    event_reward(mission_start, 100),
    event_reward(end_starlog, 100),
    event_reward(omnisanc_error, -10).

% Test: completion signals exist
test_completion_signals :-
    completion_signal(session, start_starlog, end_starlog),
    completion_signal(mission, mission_start, mission_complete).

% Test: zone multipliers exist
test_zone_multipliers :-
    zone_multiplier(home, 1.0),
    zone_multiplier(session, 3.0),
    zone_multiplier(mission, 10.0).

% Test: deduction chain works end-to-end
test_deduction_chain :-
    % Set up a sequence
    assert(event_in_sequence(test_seq_1, start_starlog, '2026-04-06T10:00:00')),
    assert(event_in_sequence(test_seq_1, update_debug_diary, '2026-04-06T10:05:00')),
    assert(event_in_sequence(test_seq_1, update_debug_diary, '2026-04-06T10:10:00')),
    assert(event_in_sequence(test_seq_1, end_starlog, '2026-04-06T10:30:00')),
    assert(sequence_zone(test_seq_1, session)),
    % Check: sequence is complete
    sequence_complete(test_seq_1, session),
    % Check: base reward = 20 + 5 + 5 + 100 = 130
    sequence_base_reward(test_seq_1, Base),
    Base =:= 130,
    % Check: quality = 1.0 (no errors)
    quality_factor(test_seq_1, Q),
    Q =:= 1.0,
    % Check: completion bonus = 100
    completion_bonus(test_seq_1, session, Bonus),
    Bonus =:= 100,
    % Check: sequence reward = (130 + 100) * 1.0 * 3.0 = 690
    sequence_reward(test_seq_1, session, Reward),
    Reward =:= 690.0,
    % Clean up
    retractall(event_in_sequence(test_seq_1, _, _)),
    retractall(sequence_zone(test_seq_1, _)).

% Test: incomplete sequence has no completion bonus
test_incomplete_sequence :-
    assert(event_in_sequence(test_seq_2, start_starlog, '2026-04-06T11:00:00')),
    assert(sequence_zone(test_seq_2, session)),
    % Not complete (no end_starlog)
    \+ sequence_complete(test_seq_2, session),
    sequence_incomplete(test_seq_2, session),
    completion_bonus(test_seq_2, session, Bonus),
    Bonus =:= 0,
    % Clean up
    retractall(event_in_sequence(test_seq_2, _, _)),
    retractall(sequence_zone(test_seq_2, _)).

% Test: errors reduce quality
test_errors_reduce_quality :-
    assert(event_in_sequence(test_seq_3, start_starlog, '2026-04-06T12:00:00')),
    assert(event_in_sequence(test_seq_3, omnisanc_error, '2026-04-06T12:05:00')),
    assert(event_in_sequence(test_seq_3, end_starlog, '2026-04-06T12:30:00')),
    assert(event_error(omnisanc_error, 'test error')),
    assert(sequence_zone(test_seq_3, session)),
    % Quality should be < 1.0 (1 error out of 3 events)
    quality_factor(test_seq_3, Q),
    Q < 1.0,
    Q > 0.0,
    % Clean up
    retractall(event_in_sequence(test_seq_3, _, _)),
    retractall(event_error(omnisanc_error, _)),
    retractall(sequence_zone(test_seq_3, _)).

% Test: process stage deduction
test_process_stage_deduction :-
    % No observations → unobserved
    process_stage(nonexistent_task, Stage1),
    Stage1 = unobserved,
    % 3+ observations → soup
    assert(candidate_process(test_task_d, evt1)),
    assert(candidate_process(test_task_d, evt2)),
    assert(candidate_process(test_task_d, evt3)),
    process_stage(test_task_d, Stage2),
    Stage2 = soup,
    % With SOP → codified
    assert(sop_candidate(test_task_d)),
    process_stage(test_task_d, Stage3),
    Stage3 = codified,
    % With authorization → programmed
    assert(authorized_process(test_task_d)),
    process_stage(test_task_d, Stage4),
    Stage4 = programmed,
    % Clean up
    retractall(candidate_process(test_task_d, _)),
    retract(sop_candidate(test_task_d)),
    retract(authorized_process(test_task_d)).

% Test: authorization gate
test_authorization_gate :-
    assert(candidate_process(auth_test, e1)),
    assert(candidate_process(auth_test, e2)),
    assert(candidate_process(auth_test, e3)),
    assert(sop_candidate(auth_test)),
    % Should require authorization
    requires_authorization(auth_test, codified_to_programmed),
    % Authorize it
    authorize_process(auth_test, isaac),
    % Now should NOT require authorization
    \+ requires_authorization(auth_test, _),
    % Should be programmed
    process_stage(auth_test, programmed),
    % Who authorized?
    who_authorized(auth_test, isaac),
    % Clean up
    retractall(candidate_process(auth_test, _)),
    retract(sop_candidate(auth_test)),
    retract(authorized_process(auth_test)),
    retract(authorization(auth_test, isaac)).
