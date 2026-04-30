# SOMA HANDOFF — READ THIS BEFORE TOUCHING ANY FILE

## WHY SOMA EXISTS (read this BEFORE the contract)

The actual goal SOMA serves: **backwards reasoning over GIINT.**

GIINT is GNOSYS's version of SOPs — it is literally equivalent to an SOP in a business. GIINT_Project → GIINT_Feature → GIINT_Component → GIINT_Deliverable → GIINT_Task is the standing structure that says "this is the work, this is what depends on what, this is what's done and what's pending." In a business, that's "this is how invoices get processed, who does what, what depends on what." Same shape.

The problem GIINT has today: it goes stale. New intents (Ideas, Bugs, Designs, completed Tasks, new observations) come in, they ripple, but nothing walks the ripple to mark which existing GIINT nodes are now stale, blocked, unblocked, or contradicted. There's no "is everything current?" check. So the hierarchy drifts from reality. Ralph cannot be used because of this — ralph proposes a change, the change desyncs the rest of the graph, nobody catches it, the project collapses. This is the only broken thing in GNOSYS.

The fix is **an event/observation based backwards reasoning system that CONTROLS the forward reasoning depending on the backwards reasoning state**. That is what SOMA is being built for. Specifically:

- **Forward reasoning** = "since new observation O entered, walk all deduction chains whose premise mentions anything O touches, fire them, propagate the new facts." This is what `fire_all_deduction_chains` would do once wired through the MI.
- **Backwards reasoning** = "given a goal G (e.g. 'GIINT_Project_X is currently valid'), walk the rules backward via `solve/3`, find which premises must hold, check whether they actually hold given current observations, and produce either `proven` or `failure-as-data` with the exact missing premise." This is what `mi_core.pl solve/3` would do once wired through the event path.
- **The backwards state CONTROLS the forward state**: forward chains do NOT just fire freely. They fire under the supervision of a backward-chain query that decides which nodes need re-evaluation and in what order. The backward chain says "to keep GIINT_Project_X current, we need to re-verify these specific nodes because their derivations involve the predicates the new observation just changed." Then forward chains fire only on those nodes, not everywhere. This keeps propagation tractable and prevents the "fire everything on every event" combinatorial explosion.

**Two-phase plan:**

1. **Phase 1 (now): Build SOMA as the universal backwards-reasoning + forward-reasoning engine.** It must work over ARBITRARY events and observations from any domain. The contract below describes how. SOMA does not know about GIINT. It knows about Event, Observation, Deduction_Chain, Prolog_Rule, and the MI. GIINT is one specific application that gets defined later, after SOMA exists.

2. **Phase 2 (after SOMA is real): Point SOMA at GIINT.** Add Prolog_Rule individuals to soma.owl that describe GIINT semantics — what makes a GIINT_Project valid, what makes a GIINT_Task complete, what derivation a GIINT_Component has, what observations would invalidate it. Then "is GIINT current?" becomes a backward query: `solve(giint_current, R)`. If R is `proven`, GIINT is current. If R is `failure(X, missing_premise(...))`, GIINT is stale and the failure tells you exactly which node and why. Ralph can then propose changes, SOMA precomputes whether the change keeps GIINT current, and either authorizes or rejects with context.

The reason "SOMA points at the business" and "SOMA points at GIINT" are the same operation: in both cases, SOMA is given a set of observations from a domain and asked to compute the standing hierarchy + check whether it is current + reject changes that would break it. GIINT is the FIRST domain to apply SOMA to, because it is the domain that runs the rest of GNOSYS. Once GIINT is kept current by SOMA, every other GNOSYS feature works because the underlying project structure stops drifting.

**This is the only broken thing in GNOSYS.** Fix this and ralph works. Fix this and the autopoiesis loop works. Fix this and the Compoctopus pattern works. They are all blocked on "we cannot trust the GIINT hierarchy is current," and the keeping-current engine is SOMA's backwards-reasoning loop.

## WHAT SOMA ACTUALLY IS (Isaac's verbatim, read first, do not paraphrase)

> "It needs to **iteratively** put **every single line of disambiguated logic** into Prolog so it can fucking backtrace **every single supposition** that it gives going forward. So that you cannot *plan* to edit the code except by inputting observations about potentials, and you cannot **do it** to the program unless the program **authorizes it** because it can precompute if the shape of the change makes sense or not, and serve you the context to make it. When you point this at a system that is an impl of events and observations from agents in organizations, what happens is **when it is not about itself** it can still do this operation for xyz. So it can do this **for itself** and that **includes** anything you put in it. If you make this program **about a business** then it is verifying **what can happen in that business** at some level."

The two cases — "SOMA gates its own evolution" and "SOMA gates what can happen in a business it's pointed at" — are the SAME OPERATION. The only thing that changes is which observations get fed in. If you find yourself building one without the other being implied, you are building the wrong thing.

The thing that distinguishes SOMA from "a Prolog daemon that stores events" is the AUTHORIZATION + PRECOMPUTATION layer: the system computes the shape of any proposed change, decides whether the shape is valid given everything it has observed, and either authorizes the change or rejects it with the context the agent needs to make a valid one. A SOMA without this is not SOMA. It is the substrate SOMA runs on.

## STATUS
Daemon is stopped. The current code violates the contract. Do not start the daemon and do not edit code until you have read this entire file.

## THE CONTRACT (Isaac's verbatim, restated multiple times today)

1. There is exactly ONE entrypoint: `add_event(source, observations)`.
2. NO Python code ever does anything except `soma.add_event()`. Period. core.py contains exactly one Janus call.
3. ANY Prolog logic that runs MUST go through the meta-interpreter `solve/3` in mi_core.pl. Nothing in Prolog runs outside the MI.
4. The only allowed top-level event types are: an occurrent event, or a meta-observation that declares a Prolog_Rule. Zero other types. Zero other ways to call SOMA.
5. Every `Prolog_Rule` lives as an OWL individual in soma.owl. Rules are loaded from OWL into the MI on boot. Rules are added via `add_event` with a meta-observation, never by editing .pl files.
6. Editing a `.pl` file is forbidden EXCEPT when Base SOMA emits a structured failure error naming a missing core requirement that requires a .pl edit to bootstrap. That is the only case.

## WHAT IS BUILT (current state on disk, no claims)

- `api.py` — POST /event only. Compliant with rule 1.
- `mcp_server.py` — one MCP tool `add_event`. Compliant.
- `core.py` — calls `janus.query_once("ingest_event_str(...)")`. **VIOLATES rule 2.** Should call `mi_add_event` (which goes through MI), not `ingest_event_str` (which is a direct Prolog predicate).
- `soma_boot.pl ingest_event/3` — directly calls `py_call(... add_event_individual ...)`, `py_call(... add_observation_individual ...)`, `py_call(... save_owl ...)`, `py_call(... run_pellet ...)`, `fire_all_deduction_chains/1`. **VIOLATES rule 3** — none of these go through `solve/3`.
- `soma_boot.pl owl_class/owl_subclass/owl_property/owl_restriction/owl_disjoint` rules — direct `py_call` from Prolog to owlready2. **VIOLATES rule 3.**
- `soma_boot.pl boot_check` — direct Prolog logic, not via solve. **VIOLATES rule 3.**
- `soma_boot.pl fire_all_deduction_chains/1`, `requirement_can_call_llm/0`, `requirement_authorization_reasoning/0`, `requirement_failure_is_llm_call/0` — all direct Prolog predicates not invoked through solve. **VIOLATE rule 3.**
- `soma.owl` — contains Deduction_Chain class, CoreRequirement class (subClassOf Deduction_Chain), 3 seed CoreRequirement individuals, hasAuthorizedCreator/Writer/WritePrecondition vocab, cap_call_llm Capability, the_ontology_engineer individual, plus accumulated Event/Observation individuals from event submissions. The class structure is OK; the individuals are OK; the bootstrap of `Prolog_Rule` individuals representing every operation does NOT exist yet.
- `mi_core.pl` — EXSHELL meta-interpreter, has `solve/3`, `solve/5`, proof trees, failure-as-data. **NOT INVOKED BY THE EVENT PATH.**
- `_deprecated/` — 10 contaminated files quarantined. Do not load. Do not edit.
- `UNIVERSAL_PATTERNS.md` — outdated framing. Patterns are NOT separate API surfaces; they are observation shapes. Treat as historical, not as a spec.

## THE PLAN (execute in this order, do not skip)

The plan is the 10 steps I wrote in the conversation just before this handoff. Reproduced verbatim:

1. core.py becomes ONE function: `add_event(source, observations)`. It calls Janus exactly ONCE: `janus.query_once("mi_add_event(SourceStr, ObsStr, R)")`. That is the only line of Janus in core.py. Nothing else.

2. soma_boot.pl exposes ONE Prolog entry point that core.py is allowed to call: `mi_add_event/3`. That predicate's body is exactly: `solve(add_event(Source, Observations), Result)`. Nothing else.

3. The MI (`solve/3` in mi_core.pl) handles `add_event(Source, Observations)` by walking Prolog rules whose head matches that goal. Those rules are loaded from OWL on boot — they are `Prolog_Rule` individuals stored in soma.owl, NOT hardcoded clauses in soma_boot.pl.

4. The very FIRST `Prolog_Rule` individual in soma.owl is the one whose head is `add_event(Source, Observations)` and whose body fires forward chains, runs Pellet, persists OWL, and recursively calls `solve(active_goal(_), _)`. THIS rule is added directly to soma.owl as the bootstrap, because nothing exists yet that could enter it via an event. This is the ONLY direct .pl/.owl edit allowed.

5. After that first rule exists in soma.owl, every other rule is added via `add_event` whose observation is a meta-observation declaring a `Prolog_Rule` individual.

6. Pellet runs and OWL writes are NOT direct Janus calls from Prolog. They are Prolog predicates that the MI invokes when a rule says to. The Prolog predicates `pellet_run/0` and `owl_save/0` are themselves `Prolog_Rule` individuals in soma.owl with bodies that py_call into utils.py. The MI calls them via `solve(pellet_run, _)`.

7. The Janus rules `owl_class/owl_subclass/owl_property/owl_restriction/owl_disjoint` get DELETED from soma_boot.pl. They become `Prolog_Rule` individuals stored in OWL whose bodies are `py_call(...)`. The MI invokes them.

8. boot_check goes through the same path: `solve(boot_check, R)`. The boot_check predicate is a `Prolog_Rule` individual in OWL.

9. soma_boot.pl shrinks to: `consult(mi_core)`, the dynamic declarations, ONE bootstrap step that loads all `Prolog_Rule` individuals from soma.owl into the live MI, and the `mi_add_event/3` predicate that core.py calls. Nothing else.

10. After step 9: exactly one Janus call in core.py, exactly one path in soma_boot.pl from `mi_add_event` to `solve/3`, everything else is data (Prolog_Rule individuals in OWL) that the MI walks.

## VERIFICATION REQUIRED BEFORE CLAIMING ANY STEP DONE

- After step 1: `grep -c "janus\." core.py` returns 1.
- After step 2: `grep -E "py_call|janus" soma_boot.pl` returns ONLY the line inside `mi_add_event`'s solve invocation (which itself goes through solve).
- After step 9: `wc -l soma_boot.pl` returns < 100 lines.
- After step 10: POST /event still works end-to-end, and `grep "py_call" soma_boot.pl` returns ZERO lines (because all py_calls live in OWL Prolog_Rule individuals now).
- After step 10: a query like `add_event(isaac, [obs(task,foo,string_value)])` submitted via /event returns a proven/failure-as-data structure from the MI in the response.

## DO NOT

- Do not add new Janus calls anywhere in Prolog.
- Do not add new direct py_call lines anywhere in Prolog except inside Prolog_Rule individuals stored in OWL.
- Do not invent vocabulary. Use what's in soma.owl already (Event, Observation, TypedValue subtypes, Prolog_Rule, Deduction_Chain, CoreRequirement, Capability, OntologyEngineer, Source, hasObservation, hasKey, hasValue, hasCapability, hasAuthorizedCreator, hasAuthorizedWriter, hasWritePrecondition, hasDeductionPremise, hasDeductionConclusion, hasRequirementRemedy).
- Do not declare anything as "done" without showing the file diff and the actual /event response in the same turn the claim is made.
- Do not edit files in `_deprecated/`.
- Do not load files from `_deprecated/`.

## KEY ARTIFACTS PRESERVED FROM TODAY

- `~/.claude/rules/soma-only-entrypoint-is-add-event.md` — global rule, auto-loads.
- `~/.claude/rules/soma-foundation-vs-contamination.md` — global rule, auto-loads.
- `~/.claude/rules/verify-via-user-surface-before-done.md` — global rule, auto-loads.
- `~/.claude/rules/no-claims-about-prior-sessions.md` — global rule, auto-loads.
- `~/.claude/rules/architecture-doc-is-spec-not-state.md` — global rule, auto-loads.
- This file: `/home/GOD/gnosys-plugin-v2/base/soma-prolog/HANDOFF_READ_FIRST.md`
- The architecture doc Isaac wrote: `/home/GOD/gnosys-plugin-v2/base/crystal-ball-alpha/youknow_v225/youknow_kernel_current/ARCHITECTURE_4_5_2026.md` (632 lines, read it)

## THE THING ISAAC HAS BEEN MOST FRUSTRATED ABOUT

I keep building partial implementations and calling them done. Specifically I keep:
- Bypassing the MI when I write Prolog
- Adding direct py_call from Prolog instead of going through OWL Prolog_Rule individuals
- Treating the substrate as if it's the system instead of building rule-data on top of it
- Claiming "done" when integration steps remain

The plan above makes these impossible by routing everything through `solve/3` and storing every operation as data in OWL. Execute it in order. Verify each step on disk. Do not proceed past a step until verified.
