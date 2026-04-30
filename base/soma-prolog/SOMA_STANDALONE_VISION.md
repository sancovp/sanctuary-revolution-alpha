# SOMA Standalone Business Application Vision

**Status**: Design document (2026-04-19)
**Context**: This describes the STANDALONE commercial product built ON the soma-prolog base system, once YOUKNOW is integrated as the OWL/SHACL reasoning layer.

---

## What This Is

SOMA-the-prototype (this directory) is the base system: a Prolog meta-interpreter + OWL + typed triple graph + conventions + codegen. Everything is an event. Convention rules self-organize the graph.

SOMA-the-product is a standalone business intelligence application where workers connect via mobile chat, enter observations about their work, and the system compiles those observations into a self-simulating geometry of the business — discovering SOPs, failure modes, and automation opportunities from the bottom up.

This document describes how to get from one to the other.

---

## The Blocker: YOUKNOW Integration (REVISED — see "The Geometry" section below)

The base system uses its own EXSHELL meta-interpreter for inference. YOUKNOW provides capabilities the MI does not have:

| Capability | Current MI | YOUKNOW |
|---|---|---|
| Backchaining + proof trees | YES | YES (different mechanism) |
| Certainty factors | YES | NO (uses compression instead) |
| Rules-as-OWL-individuals | YES | YES |
| EMR progression (embodies→manifests→reifies→programs) | NO | YES |
| ABCD grounding scaffold | NO | YES |
| SES typed-depth measurement | NO | YES |
| Cat_of_Cat chain validation | NO | YES |
| Strong/weak compression | NO (has SOUP/CODE) | YES |
| Aut system (automorphism detection) | NO | YES |
| PIO (polysemic entities) | NO | YES |
| Pellet open-world reasoning | Partial (owlready2) | YES (full) |
| SHACL shape validation | NO | YES |

The integration path: YOUKNOW becomes the reasoning layer UNDER the existing event architecture. `POST /event` stays as the single entrypoint. The Prolog MI stays for backchaining and proof trees. YOUKNOW handles EMR, compression, ABCD, and Pellet reasoning. They compose — MI for inference, YOUKNOW for validation and progression.

---

## Architecture: Standalone Product

```
WORKER (human, mobile app)
    ↓ text chat with Observer Agent
OBSERVER AGENT (LLM + youknow + actors filter)
    ↓ locally-valid entries (gradient climbed via ABCD)
ENTRY STORE (locally valid, not webbed)
    ↓
ALIGNER AGENT (open-world Pellet, metalanguage quining)
    ↓ fully webbed entries
PROCESSED ONTOLOGY (CODE-status only, queryable)
    ↓
QUERY TOOL (read-only, businesses see this)
```

All of this is programmable ON the base system via convention rules, PrologRule OWL individuals, and meta-observations. Nothing in the base system needs to change.

### Observer Agent = Convention Rules + YOUKNOW

The Observer is an LLM agent that talks to workers. When a worker describes an event, the Observer:

1. Translates natural language into typed observations (`POST /event`)
2. The base system processes them (triples, conventions, healing)
3. YOUKNOW validates the derivation chains (EMR, compression, ABCD)
4. If YOUKNOW returns errors → Observer asks worker ABCD questions (gradient climbing)
5. Repeat until local chain closes

Implementation: the Observer is a BaseHeavenAgent (from the Heaven framework, same as Twina) whose tools include `add_event` (this MCP tool) and YOUKNOW MCP tools. Convention rules in soma.owl constrain what the Observer can do based on the actors ontology filter.

### Actors Ontology Filter = Required Restrictions on Observers

```prolog
required_restriction(human_worker, has_role, role).
required_restriction(human_worker, has_department, department).
required_restriction(human_worker, authorized_to_observe, observation_domain).
```

When an event comes in, a convention rule checks: does the source actor have the right role/department to observe what they are claiming? Observations within domain get full confidence. Observations outside domain get flagged.

This is just more convention rules asserted into the existing system.

### Aligner Agent = Cross-Event Convention Rules + Aut System

The Aligner runs periodically (or on trigger) and:

1. Queries the triple graph for structural similarities across events
2. Constructs metalanguages about event clusters
3. Uses YOUKNOW Aut system to detect isomorphisms
4. When metalanguages are isomorphic → quines them → creates new SOP entity
5. Asserts discovered SOPs back via `POST /event {source: "aligner_agent"}`

Implementation: convention rules that fire during `run_all_conventions` but operate on cross-event patterns rather than single-event triples. Plus a Python process that triggers Aut detection and submits alignment events.

### Processed Ontology = Promotion Convention

A convention rule that fires when `deduce_validation_status(C, code)` becomes true:

```prolog
check_convention(promote_to_processed) :-
    forall(
        (   deduce_validation_status(C, code),
            \+ triple(C, promoted_to, processed_ontology)
        ),
        (   promote_concept(C),
            assert_triple_once(C, promoted_to, processed_ontology)
        )
    ).
```

The query tool reads ONLY from promoted concepts. Businesses never see SOUP.

### ABCD Grounding = Structured Unnamed Slots

When YOUKNOW returns "chain breaks at X," the Observer generates ABCD-structured unnamed slots:

```prolog
unnamed_slot(X, intuition, string_value).       % A: what do you think it is?
unnamed_slot(X, compare_from, known_concept).    % B: what is it like?
unnamed_slot(X, maps_to, category).              % C: what category?
unnamed_slot(X, analogical_pattern, pattern).    % D: what is the pattern?
```

The Observer Agent reads these unnamed slots and formulates natural-language questions for the worker. Worker answers → Observer fills slots → resubmits to YOUKNOW → gradient climbs.

---

## Self-Simulation: Terminal Condition

A SOMA(x) instance is self-simulated when:

1. **Single connected geometry** — no disconnected subgraphs in the processed ontology
2. **No unnamed slots** — every required restriction satisfied
3. **All CODE status** — no string_value leaves anywhere (SES first_arbitrary_string_depth = null)
4. **All is_a chains bounded** — every concept traces to Cat_of_Cat via YOUKNOW
5. **EMR at PROGRAMS** — the SOMA instance has reached `programs` level

At self-simulation, the system can generate automations (codegen already works in soma_compile.pl) and deploy them as new actors that feed observations back into the loop.

---

## Ontological Foundation

Businesses ARE meta-self-simulations of procedures. SOPs are the reifications. Profit is their proof.

To make something self-simulate, something else has to be meta-self-simulative — self-simulating in a way that can self-host inside another system agreeably. Currently that role is filled by specific humans (founders, ops managers). SOMA externalizes the meta-self-simulation into a persistent, self-maintaining geometry.

SOMA must compile ITSELF first. SOMA(PAIAB) — run on Isaacs own org — produces the geometry from which the constrained customer version is projected.

---

## Type System: OWL = Python = Code

Observations have typed fields on entry. Types are Python base types (string_value, int_value, etc. — already in the prototype as tv(Value, Type)) PLUS any valid type admitted to the ontology.

The ontology grows as new types get compiled. Each new type becomes available for future observations. More precise typing → better triangulation → faster convergence → more types. The type system IS the compounding mechanism.

OWL restrictions map to Python restrictions map to code restrictions. Pellet checks generated code for ontological consistency. This makes `programs` literal — the generated code IS type-checked by the ontology.

---

## Mobile App (Minimal)

Each user gets one Observer Agent. Persistent sessions. Chat portal always accessible.

**Mobile (Swift):**
- SOMACloudService.swift — singleton HTTP client, POST /v1/chat/message
- SOMAViewModel.swift — chat state management
- ChatView.swift — text input + message list

**Backend (Python):**
- server.py — Flask, receives messages, routes to Observer Agent per user
- dao.py — PostgreSQL (users, sessions, messages)
- soma_agent.py — BaseHeavenAgent with add_event + YOUKNOW tools

Pattern taken from Twina (Isaacs existing AI chat mobile app — Swift + Flask + BaseHeavenAgent + PostgreSQL).

---

## What Exists vs What Is New

| Component | Status |
|---|---|
| Base event system (POST /event, single entrypoint) | EXISTS (this dir) |
| Meta-interpreter (EXSHELL, backchaining, proof trees) | EXISTS (mi_core.pl) |
| Triple graph + conventions + healing | EXISTS (soma_partials.pl) |
| SOUP/CODE status + codegen | EXISTS (soma_compile.pl) |
| OWL type hierarchy + Pellet | EXISTS (soma.owl + utils.py) |
| Rules-as-OWL-individuals | EXISTS (soma_boot.pl loader) |
| YOUKNOW integration | BLOCKER — needs to be wired in |
| Observer Agent (LLM + chat + ABCD) | NEW — BaseHeavenAgent + YOUKNOW tools |
| Actors ontology filter | NEW — convention rules on human_worker type |
| Aligner Agent (metalanguage quining) | NEW — cross-event convention rules + Aut |
| Processed ontology (promotion) | NEW — promotion convention + query tool |
| Mobile app | NEW — Swift + Flask (Twina pattern) |

---

## Relationship to GNOSYS

This prototype lives inside gnosys-plugin-v2/base/ alongside crystal-ball-alpha (which contains YOUKNOW). In the GNOSYS compound system, SOMA is one component among many (CartON, starsystem, treeshell, etc.).

The standalone business product extracts SOMA + YOUKNOW as a deployable package that runs independently of the rest of GNOSYS. The GNOSYS monorepo is the development environment; the standalone product is the deployment artifact.

---

## Reference

Full design doc with all architectural details and Isaacs verbatim descriptions: `/Users/isaacwr/Desktop/claude_code/SOMA_DESIGN.md` (on host machine, not in container).

---

## Automation Surface: What Happens When Something Is Automatable

When enough observations about a process converge and it reaches CODE status (all typed, no unnamed slots, conventions satisfied, authorized), the system flags it as an automation candidate. This is where the base systems codegen (soma_compile.pl) meets the product UX.

### Two Paths

**Path A: Worker Vibe-Codes It (In-App)**

The worker who has been observing the process drops into a coding session inside the app. The agent already KNOWS the process (it compiled it from observations). The session looks like:

```
SOMA: "Invoice_Processing has reached automatable status. 
       It has 4 steps, 2 actors, 1 system dependency.
       Want to build the automation together?"

Worker: "Yeah"

SOMA: "Step 1 is receive_invoice — Alice receives PDF via email.
       I can generate a watcher that triggers on new emails 
       matching [invoice pattern]. Want to start there?"

Worker: "Yeah but it also comes through Slack sometimes"

SOMA: [adds observation: receive_invoice has_input slack_channel]
      [re-runs conventions, updates the process spec]
      "Got it — email OR Slack. Heres the updated spec.
       [shows generated Python from soma_compile]
       Want to modify anything or should I deploy this step?"
```

The worker is vibe-coding WITH the agent. The agent has the full typed process from observations. The worker provides the edge cases and domain knowledge the observations missed. soma_compile generates the code. Pellet type-checks it. Human authorizes deployment (`authorized_compilation(invoice_processing, alice)`).

**Path B: Spec Emitted to Consultancy (Us)**

For complex automations that workers cant vibe-code themselves, the system emits a structured spec back to SOMA-the-company (us as the consultancy):

```json
{
  "automation_candidate": "invoice_processing",
  "status": "code",
  "process_spec": {
    "steps": ["receive_invoice", "extract_fields", "validate_against_po", "route_for_approval"],
    "actors": ["alice", "finance_system"],
    "inputs": ["invoice_pdf", "purchase_order_db"],
    "outputs": ["approved_invoice", "rejection_notice"],
    "failure_modes": ["po_mismatch (observed 12 times)", "missing_field (observed 7 times)"],
    "estimated_automation_coverage": "3 of 4 steps automatable, step 4 requires human judgment"
  },
  "generated_code": "# from soma_compile...",
  "observations_used": 47,
  "observers": ["alice", "bob", "finance_system_logs"],
  "confidence": "CODE (no arbitrary strings, all typed)"
}
```

We receive this spec, review it, refine the generated code, and deploy the automation. The spec IS the deliverable — everything the consultancy needs to build and deploy without starting from scratch.

### The Agent Stack During Automation

The base system already has all of this:

- `deduce_validation_status(C, code)` → triggers automation candidacy
- `should_compile(C)` → checks CODE + authorized
- `compile_to_python(C, Code)` → generates Pydantic BaseModel with make()
- `run_compiled(C, Kwargs, Result)` → executes via Janus
- `authorized_compilation(C, Who)` → human gate

What the product adds:

- **In-app automation session** — chat interface where worker + agent refine the spec together, adding edge cases as new observations that re-trigger conventions and re-compile
- **Spec emission** — when automation is too complex for in-app vibe-coding, package the compiled process spec and send it to the consultancy API
- **Deployment pipeline** — generated code gets Pellet type-checked, human-authorized, deployed as a new Actor in the SOMA, which then generates its OWN observations (feedback loop)

### Revenue Model Implication

- **Subscription**: workers observe, system compiles → customers pay for the compilation runtime
- **Automation**: when processes reach CODE → either workers vibe-code it (included in subscription) or we build it (consulting fee)
- **Ongoing**: deployed automations ARE actors → generate observations → keep geometry current → subscription continues

The automation surface is where the subscription product meets the consulting product. Small automations self-serve (vibe-coding in app). Large automations become consulting engagements. Both come from the same compiled process spec.

---

## The Geometry: Both Under and Above

### The Pattern

CartON, SOMA, and YOUKNOW are NOT a stack. They are a loop where each system is simultaneously infrastructure for AND client of the others:

```
CartON ←→ SOMA ←→ YOUKNOW
  ↑_________________________↑

Each arrow goes BOTH directions.
Each system is both "under" and "above" the others.
```

| System | Infrastructure FOR (under) | Client OF (above) |
|---|---|---|
| CartON | Stores SOMAs data, persists concepts | Gets its concepts validated BY SOMA |
| SOMA | Processes events, runs conventions, promotes to ONT | Gets its claims validated BY YOUKNOW |
| YOUKNOW | Validates statements, SOUP/CODE layers, codegen | Gets its own ontology compiled BY SOMA |

This is not weird. This is homoiconic. The representation IS the thing. Self-simulation requires self-reference. The architecture IS self-simulating.

### Why YOUKNOW Goes Inside SOMA

The realization (2026-04): YOUKNOWs three layers have different operational requirements:

- **SOUP layer** — works fine standalone. Validate statements, return errors, LLM climbs gradient. No external dependencies.
- **CODE layer** — works fine standalone. Codegen for typed concepts (codeness_gen). Produces Python from compiled ontology.
- **ONT layer** — was only buildable inside SOMAs event architecture. ONT promotion requires cross-observation triangulation, convention rules, healing, the event processing pipeline that SOMA provides. You cannot do ONT outside SOMA.

Therefore:
1. Remove Prolog from YOUKNOW (the prolog_runtime.py attempt was trying to solve the ONT problem inside YOUKNOW — wrong place)
2. Put YOUKNOW inside SOMA (YOUKNOW operates through SOMAs POST /event entrypoint)
3. YOUKNOW does SOUP validation and CODE codegen
4. SOMA does ONT promotion (because ONT requires SOMAs event processing to work)
5. CartON persists everything and gets validated by the combined system

### The Double Helix (Again)

This "both under and above" pattern IS the UARL double helix:

- **Structural strand** (SOMA): provides the event infrastructure, conventions, healing, process that YOUKNOW runs on
- **Engineering strand** (YOUKNOW): provides the validation, EMR, compression, ABCD that proves SOMAs promotions are correct

Two strands intertwined. Neither one "on top." Both needed. The thing that works IS the ontology itself.

### What This Means For Integration

The integration is NOT "wire YOUKNOW into SOMA" (implies SOMA calls YOUKNOW as a library).
The integration is NOT "SOMA wraps YOUKNOW" (implies YOUKNOW is subordinate).
The integration IS: YOUKNOW operates THROUGH SOMAs entrypoint, SOMA operates ON YOUKNOWs validation. They compose bidirectionally.

Concretely:
- SOMAs POST /event entrypoint is THE way anything enters the system (including YOUKNOW validation requests)
- When SOMA processes an event, it calls YOUKNOW for SOUP validation and codegen
- When YOUKNOW needs to promote something to ONT, that happens through SOMAs convention rules and event processing
- CartON persists everything both systems produce and feeds it back to both

### Isaacs Verbatim

> "youknow is like testing out the codegen that needs to be happening generally in SOMA, but in a specific way by just allowing it to be coded and then we use it for the gnosys system types. But SOMA is that automated."

> "we realized we need to remove the prolog stuff from youknow, jam youknow INTO SOMA basically, and then make youknow operate thru SOMA entrypoint"

> "SOMA is both under and above youknow... but what makes this not weird is that carton is both under and above SOMA in the same way"
