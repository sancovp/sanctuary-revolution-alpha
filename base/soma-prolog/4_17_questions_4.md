# Questions for SOMA Agent Round 4 — 2026-04-17

## Context

You proved CoreRequirements work in minutes. Now the integration question.

## The Architecture Isaac Is Describing

**SOMA becomes the primary tool. CartON becomes SOMA's storage backend.**

```
Agent speaks/works
  ↓
Dragonbones (stop hook) — parses EC syntax into typed SOMA observations
  ↓ auto-resolves arg mappings per observation type
SOMA MCP tool (add_event) — receives observations, Prolog validates, CoreRequirements fire
  ↓ if valid
CartON (internal) — writes to Neo4j (storage only, not agent-facing)
```

- **Dragonbones** = inline SOMA. It's a parser that converts EC types into SOMA observation types. The EC syntax maps to observation keys/values. DB auto-deduces the mapping. No agent calls add_concept directly anymore.
- **SOMA tool** = the agent's primary tool. Agent calls add_event. SOMA handles validation + storage.
- **CartON** = storage backend. SOMA calls CartON internally to write to Neo4j. CartON is no longer an agent-facing MCP.
- **New MCP** = shaved-down MCP that exposes SOMA + management queries (get_concept, query_wiki_graph, collections, etc.). Replaces CartON MCP.

## Questions

### Q1: What happens to CartON's add_concept_tool_func?
Right now it: validates relationships, calls youknow_validate, checks write preconditions, queues to disk, daemon processes to Neo4j. In the new architecture, SOMA does the validation. What remains? Is add_concept just "write to Neo4j" — a storage function SOMA calls via py_call? Does the queue/daemon pattern stay or does SOMA write synchronously?

### Q2: What happens to Dragonbones?
DB currently: parses ECs → calls add_concept_tool_func. In the new architecture, DB parses ECs → converts to SOMA observations → calls ingest_event. What does the observation format look like for an EC like `🔧⛓️ GIINT_Component_X {is_a=GIINT_Component, part_of=GIINT_Feature_Y, desc='''...'''}`? Is it one observation with structured data, or multiple observations (one per relationship)?

### Q3: What are the observation type mappings for each EC type?
ECs have types: EntityChain (🌟⛓️🔧⛓️📦⛓️ etc.), each with different semantics. How does each map to SOMA observations? Is it:
```
observation(key="entity_chain", value="GIINT_Component_X", type="dict_value")
observation(key="is_a", value="GIINT_Component", type="string_value")
observation(key="part_of", value="GIINT_Feature_Y", type="string_value")
```
Or something else? What format does process_event_partials expect?

### Q4: The CogLog, SkillLog, DeliverableLog — are these also SOMA observations?
DB currently persists these to CartON as concepts. In the new architecture, are they events submitted to SOMA? Like:
```
source: "agent_turn_42"
observations: [{key: "coglog", value: "realization about X", type: "string_value"}]
```

### Q5: What about CartON's read operations?
get_concept, query_wiki_graph, activate_collection, chroma_query — these are READ operations. SOMA is about event processing (WRITE). Do read operations stay in CartON/Neo4j directly? Or does SOMA also handle reads?

### Q6: The new MCP — what tools does it expose?
Thinking something like:
- `add_event` (SOMA — write path, replaces add_concept)
- `get_concept` (CartON — read path, unchanged)
- `query_wiki_graph` (CartON — read path, unchanged)
- `activate_collection` (CartON — read path, unchanged)
- `chroma_query` (CartON — read path, unchanged)
- Management tools (carton_management, etc.)
Is that right? Is SOMA only the write path?

### Q7: Does the YOUKNOW daemon go away?
Currently: CartON calls youknow_validate → HTTP to daemon:8102 → youknow() runs → returns OK/SOUP. In the new architecture, SOMA does the validation. Does YOUKNOW's logic need to run too, or does SOMA's CoreRequirement + convention system replace it entirely? What about the derivation chain (L0-L6), EMR, Griess — do those still matter?

### Q8: The OWL import hierarchy — what does it look like in files right now?
Isaac's vision:
```
soma.owl (base program)
  ↑
uarl.owl (YOUKNOW ontology)
  ↑
starsystem.owl (GIINT, Skills, Navy)
  ↑
gnosys_foundation.owl (ships as "the program")
  ↑
user_domain.owl (per-user)
```
What actually exists? Does gnosys_foundation.owl exist? What imports what? How far from this structure?

### Q9: What py_call bridges exist vs need building?
For SOMA to be the validation+storage layer, Prolog needs py_call to:
- Write to Neo4j (CartON's write functions)
- Query Neo4j (does concept exist? relationships?)
- Check filesystem (file exists? contains pattern?)
- Read OMNISANC state (current starsystem)
Which helpers exist in utils.py? Which are missing?

### Q10: Can you write the 30-minute integration plan for making SOMA the primary write path?
Same energy as "add CoreRequirement individuals" — stop overthinking, what are the actual steps? The goal: DB parses EC → SOMA validates → CartON stores. Agent uses SOMA tool, not add_concept.
