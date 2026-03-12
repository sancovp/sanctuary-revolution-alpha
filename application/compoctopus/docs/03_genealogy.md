# Compoctopus Genealogy: From Evolution System to SCSPL

This document traces the lineage of every component that feeds into the Compoctopus architecture. Each section identifies the source code, what it does, and how it maps to a Compoctopus arm.

---

## 1. Evolution System (Proto-Compoctopus)

**Location**: `/home/GOD/core/computer_use_demo/tools/base/evolution_system/evolution_system.py`
**Status**: Legacy, not ported to heaven-framework-repo

### What It Is
A self-evolving agent framework where agents build new tools and agents for themselves. Three containers: mind_of_god (decides) → image_of_god (codes) → creation_of_god (executes).

### The Call Stack
```
EvolutionFlowTool.call(feature_description, is_tool|is_agent)
  → evolution_flow_request()
    → EvolutionFlow(feature_request, feature_type)
      → evolve()
        → evolve_feature() → use_hermes_dict(target="image_of_god", config)
          → image_of_god runs with system prompt + mermaid in goal
            → EvolveToolTool → use_hermes(target="creation_of_god", ToolMakerTool)
              → creation_of_god runs ToolMakerTool, reports success/block
```

### What It Teaches
The 5 geometric invariants. Mermaid diagrams as executable specs. State machines wrapping non-determinism. Container topology as trust boundaries. Polymorphic dispatch via feature type.

### Maps To
The **Abstract ES Syntax Base** — Phase 1 of Compoctopus.

---

## 2. Progenitor (System Prompt Compiler)

**Location**: `/home/GOD/core/computer_use_demo/tools/base/progenitor/`
**Library port**: Only `system_prompt_config.py` ported to `heaven_base/progenitor/`

### What It Is
A biological metaphor for system prompt generation. Species contain WorldSettings, EgregoreSettings, DeitySettings, ProgenitorSettings, and AgentSettings. Each is a Python class with `add_attribute()` and `add_method()`. Methods are added to a `template_sequence` that compiles in order.

### The Compilation Chain
```
Agent DNA (JSON, ~7 fields)
  → WorldSettings.format_world_section()       → [WORLD]...[/WORLD]
  → EgregoreSettings.format_egregore_section() → [EGREGORE]...[/EGREGORE]
  → AgentSettings.format_identity_section()    → [IDENTITY]...[/IDENTITY]
  → AgentSettings.format_rules_section()       → [RULES]...[/RULES]
  → ProfileMaker composes all sections
  → Complete system prompt with marker-token-bounded sections
```

### Key Insight
Seven JSON fields → complete system prompt. Every token traceable to a config field. Marker tokens enable LLM-parseable sections. The config surface is tiny but the output surface is massive.

### Species Examples
- `HeavenlyBeing` — divine agents with world/egregore/deity/progenitor layers
- `OmniAgent` — general-purpose agents
- Each species has `agent_dna/` directory with JSON configs per domain/process

### Maps To
**Phase 7** — System Prompt Compiler arm. Will be simplified and rebuilt using the Progenitor pattern but without the biological overhead.

---

## 3. Prompt Injection System (Input Prompt Compiler)

**Location**: `heaven_base/tool_utils/prompt_injection_system_vX1.py`
**Status**: ✅ Ported to library

### What It Is
An ordered sequence of Steps, each containing Blocks. Blocks are either:
- `FREESTYLE`: template strings with `{vars}` that get filled from `template_vars`
- `REFERENCE`: resolved from agent config's prompt_suffix_blocks

### The API
```python
pis = PromptInjectionSystemVX1(config)
system_prompt_part = pis.get_next_prompt()  # Step 1
input_prompt_part = pis.get_next_prompt()   # Step 2
```

### Key Insight
Input prompts are compiled artifacts, not hand-written text. `template_vars` is the KV dict. Blocks are the compilation units. Steps are the ordering. The PIS can be reset and re-run with different vars.

### Maps To
**Phase 4** — Input Prompt Compiler arm (PIS v2, now aware of geometric alignment).

---

## 4. Acolyte (HermesConfig Generator)

**Location**: `heaven_base/acolyte_v2/`
**Status**: ✅ Ported to library

### What It Is
An agent whose sole purpose is to generate HermesConfig objects. Given a user request, it outputs a properly formatted SDNA config with goal templates, variable_inputs, and agent references.

### Key Insight
The Acolyte is a one-arm proto-Compoctopus: it compiles task descriptions into executable agent configurations. The full Compoctopus replaces the single Acolyte with specialized arms.

### The Vision (Unfinished)
- One Acolyte per compiler arm
- Disciple = composed from all Acolyte outputs, runs the Acolytes
- Higher Disciples stack recursively
- GOD = terminal fixed point (SCSPL)

### Maps To
**Phase 2** — Agent Config Compiler arm (the first real Compoctopus arm).

---

## 5. Super Orchestrator / Onionmorph

**Location**: `/home/GOD/core/computer_use_demo/tools/base/agents/super_orchestrator_agent/`
**Status**: Legacy, not ported

### What It Is
Multi-layer routing system:
```
SuperOrchestrator (SearchOrchestratorsTool + CallOrchestratorTool)
  → DomainOrchestrator (SearchManagersTool + CallManagerTool)
    → SubdomainManager (ProduceXTool)
      → Worker (actual task execution)
```

Each layer's only job: find the right child, pass requirements down via standardized WORK REQUEST format.

### The Interface Contract
Every layer uses the same XML-bounded format:
```
=== WORK REQUEST ===
Requirements: {requirements}
[instructions for this layer]
=== /WORK REQUEST ===
```

### Key Insight
The topology IS the computation. Each routing decision is a compilation step (narrow the domain → narrow the subdomain → select the worker). The onion peels from general to specific.

### Maps To
**Phase 5** — Onionmorph Router arm.

---

## 6. Prompt Blocks (Reusable Prompt Fragments)

**Location**: `heaven_base/prompts/prompt_blocks/blocks/`
**Status**: ✅ Ported to library

### What It Is
JSON files with structured prompt fragments. Each has:
- `name`: dotted path (e.g., "coding.debugging.simple_code_issue")
- `text`: the actual prompt content
- `domain`: top-level domain
- `subdomain`: specialization

### Key Insight
Prompt blocks are the **atoms** that PIS (and the system prompt compiler) compose from. They're pre-validated, reusable, and domain-tagged. The Compoctopus can search, select, and compose blocks rather than generating prose from scratch.

### Maps To
Shared resource used by multiple compiler arms (Phases 4 and 7 especially).

---

## 7. Sophia-MCP (Current Chain Compiler)

**Location**: `/tmp/sophia-mcp/`
**Status**: Working (now fixed via SDNA MCP passthrough)

### What It Is
The current chain compiler. Watches a queue for jobs, constructs SDNA chains with agents configured via `default_config`. Now that the MCP fix is in, Sophia's agents correctly receive tools.

### Maps To
Sophia becomes the **Compoctopus Router** — the orchestrator that decides which compiler arms to invoke for a given task. In the final architecture, Sophia doesn't compile chains herself; she assembles a pipeline of arms and runs them.

---

## Lineage Summary

```
Evolution System (2025-04) ─── "The proof that geometric alignment works"
        │
        ├── 5 invariants extracted ──→ Abstract ES Syntax Base (Phase 1)
        │
Progenitor (2025-04) ──────── "System prompts are compiled from JSON"
        │
        ├── Species/Settings/DNA ──→ System Prompt Compiler (Phase 7)
        │
PIS vX1 (2025-05) ─────────── "Input prompts are compiled from blocks"
        │
        ├── Steps/Blocks/Vars ─────→ Input Prompt Compiler (Phase 4)
        │
Acolyte v2 (2025-05) ──────── "HermesConfigs are compiled from requests"
        │
        ├── Config generation ─────→ Agent Config Compiler (Phase 2)
        │
SuperOrchestrator (2025-04) ─ "Multi-domain routing via onion peeling"
        │
        ├── Search+Call layers ────→ Onionmorph Router (Phase 5)
        │
Sophia-MCP (2025-06+) ─────── "Chain compilation with MCP awareness"
        │
        ├── Router + queue ────────→ Compoctopus Router (Sophia)
        │
SDNA Bug Fix (2026-03-04) ── "The catastrophe that revealed the sheet structure"
        │
        └── All of the above converge → Compoctopus
```
