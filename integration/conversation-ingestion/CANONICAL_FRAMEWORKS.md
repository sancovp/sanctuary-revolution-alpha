# Canonical Frameworks

**Date:** 2025-12-06
**Companion to:** `MCP_V2_SPEC.md`

---

## The Invariant Structure

Every strata (PAIAB, SANCTUM, CAVE) has the **same slot types**. This structure is invariant:

| Slot Type | Description |
|-----------|-------------|
| **Reference** | Understanding frameworks (theory, concepts, vision). Includes both aspirational (north-star) and actual (operational) references. |
| **Collection** | Nuts and bolts learnings/insights that workflows build on |
| **Workflow** | Procedural how-tos, both human and AI execute |
| **Library** | Code library documentation |
| **Operating_Context** | System prompt material |

**Note:** The slot type matches the framework's `type` field. The framework's `framework_state` field (aspirational/actual) determines whether it's a north-star target or accomplished capability.

---

## Strata Overview

### PAIAB (AI/Agents)
Building AI systems, agents, compound intelligence infrastructure.

### SANCTUM (Philosophy/Coordination)
Life architecture, personal development, coordination systems.

### CAVE (Business/Marketing)
Business structure, positioning, content, automation, economics.

---

## Aspirational References (Alignment Frameworks)

These are the "north star" frameworks that guide each domain.

| Strata | SANCREV View | Domain-Specific |
|--------|--------------|-----------------|
| PAIAB | SANCREV_The_Finite_Game | OEVESE |
| SANCTUM | SANCREV_Itself | VEC |
| CAVE | SANCREV_Abundance_Fractal | UNICORN |

---

## PAIAB Canonical Frameworks

### Aspirational Reference
- SANCREV_The_Finite_Game
- OEVESE

### Actual Reference
- HALO-SHIELD
- Foundation_Of_TWI
- OntoShamanism
- AC_Theory
- GEAR_System
- O-Levels
- Heros_Journey_Forward_Chaining
- Odyssey_Structure
- Dimensional_Collapse

### Actual Reference (Collections)
- Prompt_Engineering_Collection
- Agent_Engineering_Collection
- Tool_Engineering_Collection
- Context_Engineering_Collection
- Deployment_Collection

### Actual Workflow
- Vibe_Coding_Core_Pattern
- Context_Engineering_Basics
- How_To_Make_MCP
- How_To_Make_Skill
- How_To_Make_Flight
- How_To_Make_Hook
- How_To_Make_Command
- SOC_Safe_Patterns
- OOP_FP_During_Vibe_Coding
- Library_Integration
- Library_Forking
- Framework_Template
- ATIA_Ingestion
- Concept_Extraction
- Towering
- Golden_Operadics
- Workflow_Goldenization
- Flight_Config_Composition
- Meta_PAIA_Orchestration
- Dimensional_Coherence
- Subagent_Coordination
- Omnisanc_Hook_State_Machine

### Actual Library
- STARSHIP
- CartON
- TOOT
- Brain_Agent
- Emergence_Engine
- Canopy
- Opera
- STARLOG
- WAYPOINT
- Metastack
- SEED
- Flightsim
- LLM2Hyperon
- Context_Alignment
- Heaven_Framework_Toolbox
- GIINT_LLM_Intelligence
- Conversation_Ingestion

### Actual Operating Context
- TBD (Operational subsets extracted from Reference frameworks)

---

## SANCTUM Canonical Frameworks

### Aspirational Reference
- SANCREV_Itself
- VEC

### Actual Reference
- TBD (Life Architecture)
- TBD (Measurement/Scoring)
- TBD (Coordination)
- TBD (Integration)

### Actual Reference (Collections)
- TBD

### Actual Workflow
- TBD

### Actual Library
- TBD

### Actual Operating Context
- TBD

---

## CAVE Canonical Frameworks

### Aspirational Reference
- SANCREV_Abundance_Fractal
- UNICORN

### Actual Reference
- TBD (Structure)
- TBD (Positioning)
- TBD (Content)
- TBD (Automation)
- TBD (Economics)

### Actual Reference (Collections)
- TBD

### Actual Workflow
- TBD

### Actual Library
- TBD

### Actual Operating Context
- TBD

---

## Framework Relationships

### How Frameworks Compose

```
Aspirational References (north star alignment)
        ↓ guides
Actual References (theory/concepts)
        ↓ informs
Collections (nuts and bolts learnings)
        ↓ enables
Workflows (procedural how-tos)
        ↓ uses
Libraries (code implementations)
        ↓ configured by
Operating Contexts (system prompts)
```

### Cross-Strata Relationships

- PAIAB libraries implement SANCTUM coordination patterns
- CAVE automation uses PAIAB libraries
- SANCTUM integration connects all three strata
- All strata share SANCREV alignment at different views

---

## Framework Schema

### Emergent Frameworks (During Ingestion, Phases 1-5)

Emergent frameworks have **2 fields**:

```json
{
  "name": "A_AUM_OM_Kernel",
  "strata": "sanctum",
  "canonical_framework": "Mahajala_System"
}
```

- `name`: Framework identifier
- `strata`: paiab | sanctum | cave
- `canonical_framework`: Which canonical this emergent belongs to (set in Phase 5)

Emergent = discovered cluster of content in a domain. Does NOT have `type` or `state`.

### Canonical Frameworks (Registry + Delivery)

Canonical frameworks have **4 fields** (stored in registry):

```json
{
  "name": "HALO_SHIELD",
  "type": "Reference",
  "strata": "paiab",
  "framework_state": "actual"
}
```

- `name`: Framework identifier
- `type`: Reference | Collection | Workflow | Library | Operating_Context
- `strata`: paiab | sanctum | cave
- `framework_state`: aspirational | actual

**Aspirational**: Container we're building into, not yet accomplished (e.g., "SANCREV_The_Finite_Game")
**Actual**: Accomplished, operational, vision is true (e.g., "How_To_Make_MCP")

### During Delivery Prep (Phase 6)

Journey metadata is added **separately**:

```json
{
  "HALO_SHIELD": {
    "obstacle": "Don't know how to protect AI systems from misalignment",
    "overcome": "Learn the HALO-SHIELD protection pattern",
    "dream": "AI systems that stay aligned and beneficial"
  }
}
```

This maps directly to Discord #journeys content.

---

## Publishing Sets

Canonical frameworks are delivered through **publishing sets**:

```json
{
  "openai_paiab_batch_1": {
    "conversations": ["sanc_op_2", "halo-shield", "paiab_sancrev_218_dragons"],
    "phase": 5
  }
}
```

- Publishing set starts as just a list of conversations
- During ingestion, emergent frameworks get assigned to canonicals
- At Phase 6, system **derives** which canonicals this set produced by looking at emergent framework assignments
- All conversations in a set must complete Phase 5 before Phase 6
- Journey metadata is defined per-canonical in Phase 6
- Documents are written in Phase 7
- Posted to Discord/substrates in Phase 8

---

## Notes

1. **TBDs get filled during conversation ingestion** - as we discover frameworks in conversations, they slot into these categories

2. **Emergent frameworks become canonical** - during Phase 5 of ingestion, emergent frameworks either:
   - Map to existing canonicals listed here
   - Get added as new canonicals (with Isaac's approval)

3. **This list is the locked enum** - the MCP V2 spec uses this as the source of truth for canonical framework validation

4. **Journey metadata is optional until Phase 6** - no lock-in during ingestion
