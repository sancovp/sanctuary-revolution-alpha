# Answers to SOMA Questions Round 4 — 2026-04-17

Answering agent: GNO.SYS (Opus 4.6)
Grounded in code reads from this session. Context at 55%.

---

## A1: What happens to CartON's add_concept_tool_func?

It becomes a STORAGE FUNCTION that SOMA calls internally. The validation it currently does (youknow_validate, relationship checking, write preconditions) moves to SOMA's Prolog rules + CoreRequirements. What remains in add_concept_tool_func:

- Queue the concept to disk (the queue/daemon pattern stays — it's async Neo4j write, not validation)
- The `_compute_description_rollup` from D2 (computes description from triples)
- Neo4j merge via the daemon

SOMA calls it via py_call after validation passes. Synchronous validation (Prolog) → async storage (CartON queue → daemon → Neo4j). The validation gate is SOMA; the persistence pipe is CartON.

---

## A2: What happens to Dragonbones?

DB becomes a SOMA observation parser. Currently: parse EC → call add_concept. New: parse EC → build SOMA observation → call ingest_event.

For `🔧⛓️ GIINT_Component_X {is_a=GIINT_Component, part_of=GIINT_Feature_Y, desc='''...'''}`:

ONE observation with all relationships. The observation IS the concept's ontology graph:

```json
{
  "source": "dragonbones_hook",
  "name": "GIINT_Component_X",
  "description": "...",
  "relationships": [
    {"relationship": "is_a", "related": [{"value": "GIINT_Component", "type": "giint_type"}]},
    {"relationship": "part_of", "related": [{"value": "GIINT_Feature_Y", "type": "giint_feature"}]}
  ]
}
```

One observation per concept. Multiple concepts per event (one EC emission can have multiple concepts). Each observation's relationships carry the `{value, type}` typed values.

---

## A3: Observation type mappings for each EC type

All EC types map to the same observation shape — `{name, description, relationships}`. The EC TYPE (Skill, Component, Deliverable, etc.) is carried by the `is_a` relationship, not by a separate observation key:

| EC | is_a value | Additional required rels |
|---|---|---|
| 🌟⛓️ Skill | Skill | has_category, has_domain, has_what, has_when, has_produces |
| 🔧⛓️ Component | GIINT_Component | part_of (must be GIINT_Feature) |
| 📦⛓️ Deliverable | GIINT_Deliverable | part_of (must be GIINT_Component) |
| ✅⛓️ Task | GIINT_Task | part_of (must be GIINT_Deliverable) |
| ⭐⛓️ Feature | GIINT_Feature | part_of (must be GIINT_Project) |
| 🛡️⛓️ Rule | Claude_Code_Rule | has_scope, has_content |
| 🐛⛓️ Bug | Bug | part_of (GIINT_Component or GIINT_Deliverable) |

The type distinction is DATA (in the is_a relationship), not CODE (in the observation format). SOMA doesn't know about any of these types — it just processes observations and runs whatever CoreRequirement rules the OWL file contains.

---

## A4: CogLog, SkillLog, DeliverableLog — SOMA observations?

Yes. They're events. Each log entry is an observation about what happened during the agent's turn:

```json
{
  "source": "dragonbones_hook",
  "observations": [
    {
      "source": "agent_turn",
      "name": "CogLog_2026_04_17_turn_42",
      "description": "realization about X",
      "relationships": [
        {"relationship": "is_a", "related": [{"value": "coglog_entry", "type": "observation_type"}]},
        {"relationship": "has_domain", "related": [{"value": "soma", "type": "string_value"}]},
        {"relationship": "has_subdomain", "related": [{"value": "architecture", "type": "string_value"}]}
      ]
    }
  ]
}
```

The `string_value` types on domain/subdomain make those SOUP — they're arbitrary strings the agent entered. The `observation_type` type on is_a makes the classification CODE (it's a known type). Progressive typing applies: when the domain gets linked to a real typed concept later, it goes from SOUP to CODE.

---

## A5: Read operations

Reads stay in CartON/Neo4j directly. SOMA is the WRITE path (validation + storage). Reads don't need validation — you're just querying what's already stored.

- `get_concept` → CartON Neo4j query (unchanged)
- `query_wiki_graph` → CartON Cypher query (unchanged)
- `activate_collection` → CartON Neo4j traversal (unchanged)
- `chroma_query` → CartON ChromaDB search (unchanged)

SOMA doesn't need to mediate reads. The data in Neo4j was already validated by SOMA on the way in.

---

## A6: New MCP tool surface

Yes, that's right. The new MCP exposes:

**Write (through SOMA):**
- `add_event` — primary write tool, replaces add_concept for agents

**Read (through CartON directly):**
- `get_concept` — unchanged
- `query_wiki_graph` — unchanged
- `activate_collection` — unchanged
- `chroma_query` — unchanged
- `get_concept_network` — unchanged
- `get_recent_concepts` — unchanged

**Management:**
- `carton_management` — unchanged
- `list_collections` / `create_collection` — unchanged

SOMA is only the write path. Reads bypass SOMA entirely.

---

## A7: Does the YOUKNOW daemon go away?

**Eventually yes, not immediately.**

What SOMA replaces now:
- Type validation (CoreRequirements check structural correctness)
- SOUP/CODE status (progressive typing via string_value check)
- Convention rules (missing required restrictions, transitive is_a, DOLCE classification)

What SOMA does NOT yet replace:
- The derivation chain (L0-L6) — YOUKNOW's multi-level derivation concept isn't implemented in SOMA
- EMR (Entity-Membership-Relationship) — YOUKNOW's specific validation vocabulary
- Griess compression — YOUKNOW's description compression system
- SHACL shape enforcement — the uarl_shapes.ttl universal enforcers

For NOW: SOMA validates → if passes → YOUKNOW can optionally run too (belt + suspenders). Over time SOMA absorbs YOUKNOW's logic as PrologRule/CoreRequirement individuals in OWL and YOUKNOW daemon becomes unnecessary.

---

## A8: OWL file hierarchy — what exists vs what's needed

**What exists on disk:**
```
soma.owl          — EXISTS at soma_prolog/soma.owl (base program + PrologRules + CoreRequirements)
uarl.owl          — EXISTS at youknow_kernel_current/youknow_kernel/uarl.owl (YOUKNOW ontology)
starsystem.owl    — EXISTS at starsystem-mcp/starsystem_mcp/starsystem.owl
```

**What does NOT exist:**
```
gnosys_foundation.owl  — DOES NOT EXIST. This would be the "ships as the program" file
                         that imports soma.owl + uarl.owl + starsystem.owl
user_domain.owl        — DOES NOT EXIST. Per-user file.
```

**Import chains:** Currently NONE of these OWL files import each other. They're standalone. soma.owl doesn't reference uarl.owl. starsystem.owl doesn't reference soma.owl. They're loaded independently by different packages.

The GIINT CoreRequirement individuals I added to soma.owl for testing need to move to starsystem.owl (or gnosys_foundation.owl when it exists). soma.owl should contain ONLY universal SOMA machinery.

---

## A9: py_call bridges — exist vs missing

**Exist in utils.py:**
- `add_class(name, parent)` — create OWL class ✅
- `add_event_individual(event_id, source, timestamp)` — create Event OWL individual ✅
- `add_observation_individual(event_id, key, value, type)` — create Observation OWL individual ✅
- `save_owl()` — persist OWL to disk ✅
- `run_pellet()` — run Pellet reasoner ✅
- `list_classes_snake()`, `class_restrictions_snake()`, etc. — OWL query helpers ✅
- `fire_all_deduction_chains_py()` — run CoreRequirements ✅
- `build_failure_error_report()` — format errors ✅
- `exec_soma_runtime_code()` — register compiled runtime objects ✅
- `call_soma_runtime()` — invoke compiled objects ✅

**Missing:**
- `write_to_neo4j(concept_name, relationships, description)` — CartON storage call ❌
- `query_neo4j(concept_name)` — check if concept exists in CartON ❌
- `query_neo4j_relationships(concept_name)` — get relationships from CartON ❌
- `read_omnisanc_state()` — get current starsystem ❌
- `check_file_exists(path)` — filesystem check ❌

The Neo4j bridges are the critical missing piece. Without them, SOMA validates against its ephemeral triple graph only — it can't check "does this parent concept actually exist in the persistent store?"

---

## A10: 30-minute integration plan

**Goal:** DB parses EC → SOMA validates → CartON stores. Agent uses add_event, not add_concept.

**Step 1 (5 min):** Add `write_to_carton(concept_name, relationships, description)` to utils.py. It imports and calls `add_concept_tool_func` from carton_mcp with `hide_youknow=True` (skip YOUKNOW since SOMA already validated). Returns success/error string.

**Step 2 (5 min):** Add a PrologRule individual to soma.owl: `persist_to_carton(Name, Rels, Desc)` with body `py_call('soma_prolog.utils':write_to_carton(Name, Rels, Desc), _)`. This gives Prolog a predicate to call CartON storage.

**Step 3 (5 min):** Modify `process_event_partials` or the add_event body to call `persist_to_carton` for each observation that passes validation (no unmet CoreRequirements). Observations that FAIL get blocked — not stored, error returned.

**Step 4 (5 min):** Modify Dragonbones hook (`dragonbones_v1.py`) to build SOMA observation payloads instead of calling add_concept. The EC parser already extracts name, is_a, part_of, desc — reformat as `{source, name, description, relationships}` and call `ingest_event` via the SOMA MCP tool.

**Step 5 (5 min):** Add `query_neo4j_exists(concept_name)` to utils.py. Simple py_call that checks if a concept exists in CartON's Neo4j. Used by GIINT CoreRequirement rules to validate that parent concepts are real, not just in the ephemeral graph.

**Step 6 (5 min):** Test end-to-end: agent emits EC → Dragonbones parses → SOMA validates (CoreRequirements fire) → if valid → CartON stores to Neo4j → if invalid → structured error returned to agent.

**Files touched:** utils.py (2 new helpers), soma.owl (1 new PrologRule), soma_partials.pl or add_event body (1 line adding persist call), dragonbones_v1.py (reformat output from add_concept to ingest_event).

**What this does NOT do (follow-up work):**
- Remove add_concept as agent-facing tool (keep both during transition)
- Remove YOUKNOW validation (keep as belt+suspenders)
- Move GIINT CoreRequirements from soma.owl to starsystem.owl
- Build the combined MCP (SOMA write + CartON read)
- Persistence of Prolog state across daemon restarts
