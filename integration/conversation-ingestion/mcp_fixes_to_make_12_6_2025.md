# Conversation Ingestion MCP - Fix Plan

## What Happened

The MCP was built wrong. It just moves strings around in JSON with no enforcement.

- `tag_pair()` appends strings to lists
- No slots, no types, no ratcheting
- `tag_enum` validation is backwards/useless
- `get_violations()` only checks definition pairs, not the real rules

Result: 2600 "frameworks" created when there should be ~50 canonicals. Every concept became its own framework. Data is polluted.

## The Actual Intent

The pipeline should go: **Raw conversations → Complete set of all frameworks**

Each pair gets tagged with:
1. **Strata**: paiab | sanctum | cave (always required)
2. **State**: evolving | definition
3. **For definitions**:
   - EITHER: canonical framework (from Master Framework List)
   - OR: `emergent_framework_{{name}}` with TYPE and STRATA

Emergent frameworks are just: `emergent_framework_{{name}} which is a {{type}} framework in {{strata}}`

Three fields:
- Name
- Type (Reference | Operating_Context | Workflow | Library)
- Strata (paiab | sanctum | cave)

## The Ontology That Needs to Exist

**Canonical frameworks**: Locked list from Master Framework List. ~50. WHERE content gets delivered.

**Concept tags**: Free-form. WHAT content is about. The 2600 things should be these.

**Emergent frameworks**: New frameworks discovered during reading. Have name + type + strata. Later become canonicals or merge into existing ones.

These are DIFFERENT CATEGORIES. The current code treats them as the same (flat tag_enum list).

## Ratcheting Rules

- `evolving`: always allowed
- `strata` (paiab/sanctum/cave): always allowed
- `definition`: only if strata already present
- `canonical framework` or `emergent_framework_X`: only if definition already present

Tool must BLOCK invalid operations, not just detect them after.

## Phases vs Passes

**PHASES** (distinct operations):
1. Read, find definitions, tag what is being defined
2. Relate definitions to CANONICAL frameworks
3. Relate remaining definitions to EMERGENT frameworks → then Isaac decides: make canonical or subsume

**PASSES** (iterations):
- Each pass = one full read of the conversation
- Each pass = separate context window, Claude doesn't remember between
- A phase might require multiple passes to complete

The system prompt conflated these. They are different.

## Starlog Structure

Each conversation = its own starlog project.

- `/tmp/conversation_ingestion_openai_paiab/claude_reviewing_earlier_conversation_notes/` → starlog project
- `/tmp/conversation_ingestion_openai_paiab/sanc_op_2/` → starlog project
- etc.

Each pass through a conversation = debug diary entry in that conversation's starlog. The diary IS the memory between passes.

## What Needs to Happen

1. **Diagram the ontology**: What are the canonical frameworks? What are the tag types? How should we model this?

2. **Fork and fix the code**:
   - Separate canonical frameworks (locked list) from concept tags (free-form)
   - Add proper type tracking for emergent frameworks
   - Implement ratcheting enforcement
   - Fix data structure (slots not just flat lists)

3. **Set up starlog projects** for each conversation

4. **Rerun the 11 conversations** with the fixed MCP, using debug diary for pass memory

## Key Files

- `/tmp/conversation_ingestion_mcp/conversation_ingestion_mcp/core.py` - main logic (broken)
- `/tmp/conversation_ingestion_mcp/conversation_ingestion_mcp/utils.py` - data loading/saving
- `/tmp/conversation_ingestion_openai_paiab/state.json` - current polluted state
- `/tmp/conversation_ingestion_openai_paiab/emergent_frameworks.json` - 2600 wrong frameworks

## The Simple Thing We Want

When reading a pair with a definition:

1. Is it about an existing canonical? → tag with that canonical
2. Is it something new? → `emergent_framework_{{name}}` + type + strata

That's it. Three fields for emergent. Map to canonical if known.

End state: Every concept either mapped to canonical OR marked as emergent with strata + type.
