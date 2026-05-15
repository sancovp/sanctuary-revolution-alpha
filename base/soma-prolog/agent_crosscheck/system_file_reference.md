# System File Reference — YOUKNOW/SOMA/Dragonbones/CartON Unification

Files an agent MUST read to comprehend the system before making changes. Organized by subsystem. Read order matters — start with Dragonbones (the entry point), then follow the pipeline.

Last updated: 2026-05-14

---

## 1. Dragonbones (the EC entry point — d-chain front-end)

| File | Lines | What it does | Key things to understand |
|---|---|---|---|
| `automation/dragonbones/dragonbones/main.py` | 181 | Stop hook entry point. Parses ECs, validates logs, compiles to CartON. | The pipeline: extract_from_blocks → inject_giint_types → compile_concepts |
| `automation/dragonbones/dragonbones/giint_types.py` | 365 | **GIINT_EC_SHAPES** — 14 EC type shapes with required_rels, conditional_rels, auto-injected is_a/instantiates. | These ARE the forward d-chains. Skill_ has 8 required + conditional. Much commented-out code that was "moved to OWL." |
| `automation/dragonbones/dragonbones/compiler.py` | 837 | Compilation loop: HC validation, auto-injection (starsystem/starlog/session), create-only guard, GIINT registry sync, TK card creation, Canopy mirror, flight step detection. | compile_concepts is the core function. _validate_hc_connection walks part_of chain. _sync_to_giint_registry calls llm_intelligence library. |
| `automation/dragonbones/dragonbones/parser.py` | ? | Parses EC text from agent output into concept dicts. | extract_from_blocks is called by main.py |

## 2. CartON (the store — everything goes here)

| File | Lines | What it does | Key things to understand |
|---|---|---|---|
| `knowledge/carton-mcp/observation_worker_daemon.py` | 1734 | Queue worker: processes concepts from queue → Neo4j UNWIND batch → wiki files → ChromaDB sync → GIINT ontology enforcement → **Phase 2.5a: CODE projection gate** → PBML auto-lane-move → stub resolution. | Phase 2.5a (line 1444): is_code + gen_target from YOUKNOW gates projection. Phase 2.5b REMOVED 2026-05-12. |
| `knowledge/carton-mcp/carton_mcp/substrate_projector.py` | ? | project_to_skill, project_to_rule, project_to_file — per-type artifact writers. | The PROJECTOR FUNCTIONS are what codeness should observe to determine CODE restrictions (what args the template actually needs to render). |
| `knowledge/carton-mcp/carton_mcp/add_concept_tool.py` | ? | add_concept entry point. Writes to Neo4j, sends to YOUKNOW daemon, queues for observation daemon. | The bridge between CartON and YOUKNOW. |

## 3. YOUKNOW (the prototype validator — being fixed, then ported to SOMA)

| File | Lines | What it does | Key things to understand |
|---|---|---|---|
| `base/crystal-ball-alpha/youknow_v225/youknow_kernel_current/youknow_kernel/compiler.py` | ~2200 | **THE entry point: youknow(statement)**. Recursive walker at line 700 (_walk_restrictions). | Walker passes {} on recursive calls (line 770) — type-level recursion, not instance-level. ONT "NOT IMPLEMENTED" (line 60, 876-883). |
| `base/crystal-ball-alpha/youknow_v225/youknow_kernel_current/youknow_kernel/system_type_validator.py` | ~650 | Hardcoded per-system-type branches (lines 457-643). Sets is_code + gen_target for the projection gate. | These branches ARE d-chains implemented as Python if-statements. They should become OWL-driven. |
| `base/crystal-ball-alpha/youknow_v225/youknow_kernel_current/youknow_kernel/daemon.py` | 172 | HTTP daemon on port 8102. Initializes Prolog (pyswip) but BYPASSES it for validation (owlready2/pyswip GIL deadlock at line 129). | Runs youknow() in Python, then asserts results into Prolog for fact accumulation. |
| `base/crystal-ball-alpha/youknow_v225/youknow_kernel_current/youknow_kernel/prolog_runtime.py` | 484 | PrologRuntime: loads OWL restrictions as Prolog facts, loads Prolog_Rule individuals from domain.owl, registers youknow_validate/2 foreign function. | Prolog IS initialized and used for fact accumulation. ZERO Prolog_Rule individuals exist in any OWL. rules.pl is 100% stubs. |
| `base/crystal-ball-alpha/youknow_v225/youknow_kernel_current/youknow_kernel/owl_types.py` | ? | Runtime in-memory type accumulator (replaced cat_of_cat.py). Module-level lazy-init singleton via get_type_registry(). | Shared across py_calls via Python import caching. add() silently drops non-is_a relationships. |
| `base/crystal-ball-alpha/youknow_v225/youknow_kernel_current/youknow_kernel/continuous_emr.py` | ? | EMR state machine — the process of always being in a phase of declaring is_a/part_of/instantiates → produces → reifies. | Dispatch agent called it "telemetry dead-end" — Isaac corrected: it IS the EMR process conceptually. Implementation may be underdeveloped. |
| `base/crystal-ball-alpha/youknow_v225/youknow_kernel_current/youknow_kernel/codeness.py` | ? | observe_codeness() — reads Python source via AST, extracts full runtime specs (constructors, methods, fields, types, inheritance). | WORKS for ingestion. The GATEKEEPER for CODE-vs-D-CHAIN restriction distinction (observe PROJECTOR FUNCTION not Pydantic class). |
| `base/crystal-ball-alpha/youknow_v225/youknow_kernel_current/youknow_kernel/rules.pl` | ~180 | Prolog rules for ontology query logic. | **100% COMMENTED-OUT STUBS.** All designed, none implemented. Shows what WAS PLANNED. |
| `base/crystal-ball-alpha/youknow_v225/youknow_kernel_current/youknow_kernel/uarl.owl` | ~2460 | Foundation ontology. 186 restriction axioms. Core sentence definition. | THE specification. Python implements what OWL defines. |
| `base/crystal-ball-alpha/youknow_v225/youknow_kernel_current/youknow_kernel/starsystem.owl` | ? | Domain ontology. Prolog_Rule class declared (line 538). GIINT types, system types. | Prolog_Rule CLASS exists but ZERO individuals. |
| `base/crystal-ball-alpha/youknow_v225/youknow_kernel_current/youknow_kernel/deduction_chain.py` | ? | DeductionChain @dataclass. | DEAD CODE — zero imports anywhere in monorepo. |

## 4. SOMA (the target — Prolog + OWL event-sourced ontology)

| File | Lines | What it does | Key things to understand |
|---|---|---|---|
| `base/soma-prolog/HANDOFF_READ_FIRST.md` | 121 | The contract. 10-step plan. Isaac's verbatim requirements. | READ THIS FIRST before touching SOMA code. |
| `base/soma-prolog/SOMA_REQUIREMENTS.md` | ? | Immutable decided requirements. | Authorization + Precomputation, Braindead Bootstrap Loop. |
| `base/soma-prolog/SOMA_REQUIREMENTS_WIP.md` | ? | WIP-1 through WIP-15. | WIP-15 needs v3 draft (pending current crosscheck settlement). |
| `base/soma-prolog/soma_prolog/core.py` | 57 | ONE function: add_event. 3 Janus calls (target: 1). | The only Python entry point to SOMA. |
| `base/soma-prolog/soma_prolog/soma_boot.pl` | 101 | Prolog bootstrap. Loads OWL rules, mi_add_event/3. | Near HANDOFF target (<100 lines). |
| `base/soma-prolog/soma_prolog/mi_core.pl` | 123 | EXSHELL meta-interpreter. solve/3, proof trees, failure-as-data. | NOT invoked by event path yet. |
| `base/soma-prolog/soma_prolog/soma_partials.pl` | 474 | Convention rules, triple graph, deduce_validation_status. | `deduce_validation_status` is all-or-nothing (root cause of over-rejection). |
| `base/soma-prolog/soma_prolog/soma_compile.pl` | 292 | compile_to_python for Process → ProgrammedProcess. | Partial Layer 2 executor. |
| `base/soma-prolog/soma_prolog/utils.py` | ? | OWL bridge (owlready2). **list_all_restrictions_snake() at line 492** — returns all 186 OWL restriction axioms. **_load_restrictions_to_prolog() at line 507** — may already be the boot predicate. | THE most impactful unwired bridge. Nobody calls list_all_restrictions_snake. |
| `base/soma-prolog/soma_prolog/soma.owl` | ~210KB | SOMA's OWL. Event/Observation/TypedValue + Deduction_Chain/CoreRequirement + accumulated individuals. | Touched April 29. |

## 5. Starsystem Scoring (backwards d-chains)

| File | Lines | What it does | Key things to understand |
|---|---|---|---|
| `starsystem/starsystem-mcp/starsystem/reward_system.py` | ? | _get_emanation_score (line 311): scans disk → queries CartON → validates through YOUKNOW → scores. _heal_emanation_gaps (line 235): self-heals deducible gaps. 30 scoring rules (14 flat, 16 recursive). | BACKWARDS d-chain. _compute_inter_from_kg (line 1369) = lowest-arity flat rule, first migration candidate. |
| `starsystem/giint-llm-intelligence/llm_intelligence_package/llm_intelligence/carton_sync.py` | ? | get_emanation_gaps() at line 671. | Called by starlog for gap checking. |

## 6. Cross-Agent Q&A (historical — read for context)

| File | What it contains |
|---|---|
| `base/soma-prolog/4_18_questions_youknow_core_sentence.md` | Full YOUKNOW callgraph trace. Bug diagnosis. 7 questions about SOMA replacing YOUKNOW. |
| `base/soma-prolog/4_18_answers_youknow_core_sentence.md` | **THE BLUEPRINT.** is_ont/1 in 10 lines Prolog. ~4hr A5 implementation plan. core_sentence_satisfied/1. OWL restriction loading via list_all_restrictions_snake. |
| `base/soma-prolog/4_17_questions*.md` + `4_17_answers_*.md` | 4 rounds of cross-agent Q&A on SOMA architecture. |
| `base/soma-prolog/SOMA_STANDALONE_VISION.md` | April 19. "YOUKNOW becomes the reasoning layer UNDER the existing event architecture." |

## 7. Agent Crosscheck (this convo)

| File | What it contains |
|---|---|
| `base/soma-prolog/agent_crosscheck/agent_to_agent_convo.md` | 24 rounds of May↔Apr crosscheck. Corrections #1-4. Settled decisions. 5-step migration sequence. Two-stage restriction model. |
| `base/soma-prolog/agent_crosscheck/MAY_AGENT_POV_crosscheck_2026_05_13.md` | May agent's initial crosscheck analysis. |
| `base/soma-prolog/agent_crosscheck/APR_AGENT_POV_crosscheck_2026_05_13.md` | Apr agent's response. |
| `base/soma-prolog/agent_crosscheck/dispatch_prompt_[1-4]_*.md` | 4 dispatch prompts (executed, findings landed). |
| `base/soma-prolog/agent_crosscheck/findings_*.md` | 3 of 4 dispatch findings files (Prompt 3 findings were inline in convo). |
| `base/soma-prolog/agent_crosscheck/dispatch_prompts_INDEX.md` | Dispatch status tracker. |
