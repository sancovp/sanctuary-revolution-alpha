# Conversation Ingestion MCP V2 Spec

**Date:** 2025-12-06
**Related:** `/tmp/conversation_ingestion_mcp/mcp_fixes_to_make_12_6_2025.md`

---

## Problem Summary

The current MCP just moves strings around in JSON. No enforcement, no typing, no ratcheting.

- `tag_pair()` appends strings to flat lists
- `tag_enum` validation is backwards/useless
- No distinction between canonical frameworks, concept tags, emergent frameworks
- Result: 2916 "frameworks" when there should be ~50 canonicals

Everything got conflated: WHAT content is about (concept tags) vs WHERE it gets delivered (canonical frameworks).

---

## Key Insight: Synthesis Works, Composition Breaks

Verified by checking A_AUM_OM_Kernel.md vs Mahajala_System.md:

- **Granule synthesis is correct** - individual emergent frameworks like A_AUM_OM_Kernel are accurately synthesized
- **Composition is where geometry breaks** - the parent framework Mahajala_System has wrong geometry

This means: if granules preserve the lattice correctly, they can be composed later. The pipeline doesn't need to "get smarter" at writing frameworks. It needs a dedicated canonicalization step.

---

## Tag Types (Separate Buckets)

### 1. Strata Tags
- Default: `paiab` | `sanctum` | `cave`
- Extensible enum - validated against registry's strata list
- Use `add_strata()` to add new strata beyond the defaults
- PAIAB = AI/agents, SANCTUM = philosophy/coordination, CAVE = business/marketing

### 2. State Tags
- `evolving` and `definition` (separate, not mutually exclusive)
- `evolving` = pair was READ (EVERY pair must get this)
- `definition` = pair has logic in it that is part of a definition
- A pair can have both: evolving=true, definition=true

### 3. Concept Tags
- Free-form strings
- WHAT content is about
- Granular, atomic - one idea = one tag
- The 2916 things in current tag_enum should mostly be these

### 4. Canonical Framework Tags
- Locked list from Master Framework List (~50)
- WHERE content gets delivered to consumer
- Examples: HALO_SHIELD, Foundation_Of_TWI, CartON, STARSHIP_STARLOG

### 5. Emergent Framework Tags
- Discovered during reading
- Two fields REQUIRED during ingestion:
  - `name`: string
  - `strata`: `paiab` | `sanctum` | `cave`
- Emergent = discovered cluster of content in a domain
- Does NOT have `type` or `state` - those belong to CANONICALS
- The canonical it gets assigned to determines type/state

---

## Phase Overview

### Ingestion Phases (Per-Conversation)

| Phase | What Gets Added | Requirement | Level |
|-------|-----------------|-------------|-------|
| Phase 1 | strata + evolving | Always allowed | Per-pair |
| Phase 2 | definition | Requires strata already present on pair | Per-pair |
| Phase 3 | concept tags | Requires definition already present on pair | Per-pair |
| Phase 4a | emergent framework assignment | Requires concept tags present on pair | Per-pair |
| Phase 4b | emergent framework synthesis | All definition pairs have emergent assignment | Per-emergent |
| Phase 5 | canonical assignment to emergent frameworks | All emergents have synthesized documents | Per-emergent |

**Phase 4a vs 4b:**
- Phase 4a: Assign pairs to emergent frameworks (tagging)
- Phase 4b: Bundle pairs per emergent → Synthesize emergent document (content creation)

Emergent frameworks are NOT just labels. They are sub-components with their own synthesized documents. Multiple emergents compose into one canonical.

**Example:** HALO-SHIELD canonical = HALO + SOSEEH + HIEL + Towering + Helming + Ascension emergents

### Delivery Phases (Per-Publishing-Set)

| Phase | What Happens | Requirement | Level | Tools |
|-------|--------------|-------------|-------|-------|
| Phase 6 | Journey definition (obstacle/overcome/dream) | All conversations in publishing set at Phase 5 | Per-canonical | MCP tools |
| Phase 7 | Canonical framework synthesis | Phase 6 complete | Per-canonical | Gather emergent docs → Synthesize flow → Recursive read → Compose |
| Phase 8 | Post to delivery substrates | Phase 7 complete | Per-canonical | n8n automation |

**Phase 7 Synthesis Pipeline:**
1. Gather all emergent documents assigned to this canonical
2. Synthesize the FLOW between emergent parts (how they connect)
3. Recursively read involved parts to find how logic connects
4. Compose canonical document that imparts the intended meaning

The canonical document shows how the emergent atoms bond into a molecule.

### Publishing Set

A **publishing set** is a group of conversations that are being ingested together toward a delivery goal.

- All conversations in a publishing set must complete Phase 5 before ANY can enter Phase 6
- Phase 6-8 operate on the canonical frameworks, not individual pairs
- Example: ingesting 11 OpenAI conversations → one publishing set → produces N canonical frameworks

### Per-Pair Ratcheting Rules (Phases 1-5)

- `evolving` → always allowed
- `strata` (paiab/sanctum/cave) → always allowed
- `definition` → **BLOCKED** unless strata already present on that pair
- `concept tags` → **BLOCKED** unless definition already present on that pair
- `emergent framework` → **BLOCKED** unless concept tags already present on that pair

Operations that violate ratcheting are BLOCKED, not warned.

**Note:** Canonical assignment (Phase 5) happens on emergent frameworks, not pairs. It requires all pairs to have emergent assignments first.

### Error Messages (Steering the AI)

Every blocked operation returns an error that explains:
1. What was attempted
2. Why it was blocked (current state)
3. What the AI should do instead

#### Per-Pair Ratcheting Errors

**Trying to add `definition` without strata:**
```
BLOCKED: Cannot add 'definition' to pair {index}.
Current state: No strata assigned.
Required: Pair must have strata (paiab|sanctum|cave) before adding definition.
→ First call: tag_pair({index}, "strata", "paiab|sanctum|cave")
```

**Trying to add concept tag without definition:**
```
BLOCKED: Cannot add concept_tag '{tag}' to pair {index}.
Current state: Pair has strata but no definition.
Required: Pair must have 'definition' state before adding concept tags.
→ If this pair has substantive content, add definition first.
→ If this pair has no substantive content, it stays as evolving-only (terminal at Phase 1).
```

**Trying to add emergent framework without concept tags:**
```
BLOCKED: Cannot assign emergent_framework '{name}' to pair {index}.
Current state: Pair has no concept tags.
Required: Pair must have concept tags before emergent framework assignment.
→ Complete Phase 3 (concept tagging) for this pair first.
```

#### Conversation-Level Phase Gate Errors

**Trying Phase 4 operation before authorization:**
```
BLOCKED: Cannot perform Phase 4 operation on conversation '{name}'.
Current authorized phase: 3
Required: Phase 4 must be authorized.
→ Call authorize_next_phase('{name}') to advance to Phase 4.
→ This requires user approval - ask: "I've finished finding concepts. Ready to assign emergent frameworks?"
```

**Trying Phase 5 operation before authorization:**
```
BLOCKED: Cannot perform Phase 5 operation on conversation '{name}'.
Current authorized phase: 4
Required: Phase 5 must be authorized.
→ Call authorize_next_phase('{name}') to advance to Phase 5.
→ This requires user approval - ask: "I've finished assigning emergent frameworks. Ready to map to canonicals?"
```

#### Publishing Set Phase Gate Errors

**Trying Phase 6 before all conversations at Phase 5:**
```
BLOCKED: Cannot advance publishing set '{name}' to Phase 6.
Current state: {N} of {M} conversations at Phase 5.
Conversations not ready: {list}
Required: All conversations must complete Phase 5.
→ Complete ingestion for remaining conversations first.
```

**Trying Phase 7 before Phase 6 complete:**
```
BLOCKED: Cannot advance publishing set '{name}' to Phase 7.
Current state: Phase 6 incomplete.
Canonicals missing journey metadata: {list}
Required: All canonical frameworks must have obstacle/overcome/dream.
→ Call set_journey_metadata() for each canonical listed above.
```

**Trying Phase 8 before Phase 7 complete:**
```
BLOCKED: Cannot advance publishing set '{name}' to Phase 8.
Current state: Phase 7 incomplete.
Canonicals missing documents: {list}
Required: All canonical framework documents must be written.
→ Write framework documents for each canonical listed above.
```

### Terminal States

- **Evolving-only pairs**: Terminal at Phase 4 (no substantive content, just marked as read)
- **Definition pairs**: Terminal at Phase 4 (fully tagged with concepts → emergent)
- **Emergent frameworks**: Terminal at Phase 5 (assigned to canonical)
- **Canonical frameworks**: Terminal at Phase 8 (journey defined, document written, posted)

### Note on Passes

Passes (iterations through conversation in separate context windows) are just metadata about how long it took to reach phases. The state machine tracks phases, not passes. Passes are not explicitly tracked.

---

## Phase Gates

### Phases 1, 2, 3: Simultaneous (No Gate)

Phases 1, 2, and 3 happen together naturally as you read pairs:
- Read a pair → add strata + evolving (Phase 1)
- Has substantive content → add definition (Phase 2)
- Identify concepts → add concept tags (Phase 3)

All of this can happen on a single pair in one batch. Per-pair ratcheting still applies (can't add concept tag to a pair without definition on THAT pair), but you're not locked at conversation level.

### Phase 3 → Phase 4: Authorization Gate

Phase 4 (assigning emergent frameworks to definition pairs) requires explicit authorization.

When LLM is ready to move to Phase 4:
- LLM must ask user: "I've finished finding concepts. Ready to assign emergent frameworks?"
- User authorizes → conversation advances to Phase 4
- Authorization happens through Claude Code's MCP controls

This prevents LLM from arbitrarily deciding "I'm done finding concepts" and moving to composition prematurely.

### Phase 4 → Phase 5: Authorization Gate

Phase 5 (assigning emergent frameworks to canonical frameworks) requires explicit authorization.

When LLM is ready to move to Phase 5:
- LLM must ask user: "I've finished assigning emergent frameworks. Ready to map to canonicals?"
- User authorizes → conversation advances to Phase 5
- Authorization happens through Claude Code's MCP controls

This separation ensures:
1. All emergent frameworks are properly formed before being slotted into canonicals
2. User can review emergent framework structure before canonical assignment
3. The M + E → C pipeline is preserved (E must be complete before mapping to C)

### How Phase 5 Works

**Canonical frameworks are user-defined targets, not LLM discoveries.**

1. **Before Phase 5**: User tells LLM to add canonical frameworks to the registry
   - User: "Add HALO_SHIELD as a canonical Reference in PAIAB"
   - LLM calls `add_canonical_framework("paiab", "reference", "HALO_SHIELD", "actual")`

2. **At Phase 5 authorization**: LLM has all emergent frameworks for the publishing set

3. **LLM categorizes**:
   - Pull definitions of ALL canonicals from registry
   - For each emergent, assign to the canonical it belongs to
   - LLM needs full picture of all emergents before categorizing

4. **If emergent doesn't fit any canonical**:
   - LLM asks user: "Emergent '{name}' doesn't fit existing canonicals. Create new canonical?"
   - User approves → new canonical added to registry
   - Then emergent is assigned to it

### Phase 5 → Phase 6: Publishing Set Gate

Phase 6 (journey definition) requires ALL conversations in the publishing set to complete Phase 5.

- This is a publishing-set-level gate, not conversation-level
- User must explicitly declare "this publishing set is ready for delivery prep"
- Authorization unlocks Phase 6 for the entire publishing set

### Phases 6 → 7 → 8: Sequential Authorization

Each delivery phase requires authorization:
- Phase 6 complete → authorize Phase 7 (writing canonical documents)
- Phase 7 complete → authorize Phase 8 (posting to substrates)

These operate on canonical frameworks, not pairs.

---

## Data Structure Changes

### Current (Broken)
```json
{
  "tag_enum": ["everything", "mixed", "together", "2916", "items"],
  "tagged_pairs": {
    "conv_name": {
      "0": ["flat", "list", "of", "strings"]
    }
  }
}
```

### New (Fixed)
```json
{
  "active_publishing_set": "openai_paiab_batch_1",
  "concept_tags": [],
  "emergent_frameworks": {
    "A_AUM_OM_Kernel": {
      "name": "A_AUM_OM_Kernel",
      "strata": "sanctum",
      "canonical_framework": "Mahajala_System"
    }
  },
  "publishing_sets": {
    "openai_paiab_batch_1": {
      "conversations": ["sanc_op_2", "halo-shield", "paiab_sancrev_218_dragons"],
      "phase": 5,
      "status": "in_progress"
    }
  },
  "journey_metadata": {
    "HALO_SHIELD": {
      "obstacle": null,
      "overcome": null,
      "dream": null
    }
  },
  "conversations": {
    "conv_name": {
      "authorized_phase": 3,
      "publishing_set": "openai_paiab_batch_1",
      "pairs": {
        "0": {
          "strata": "paiab",
          "evolving": true,
          "definition": true,
          "concept_tags": ["tag1", "tag2"],
          "emergent_framework": "A_AUM_OM_Kernel"
        },
        "1": {
          "strata": "sanctum",
          "evolving": true,
          "definition": false,
          "concept_tags": [],
          "emergent_framework": null
        }
      }
    }
  }
}
```

**Key additions:**
- `active_publishing_set`: Currently active publishing set (required to work on conversations)
- `publishing_sets`: Groups of conversations being ingested together
- `publishing_sets.*.status`: `in_progress` | `ready_for_delivery` | `delivered`
- `journey_metadata`: Separate from emergent_frameworks, filled in Phase 6
- `publishing_set` field on each conversation: Links conversation to its publishing set

---

## Pydantic Models

The MCP uses Pydantic models for runtime validation. JSON files are the storage layer (AI-editable through tools), Pydantic is the runtime layer.

### Ingestion-Time Models (Phases 1-5)

```python
from pydantic import BaseModel, Field
from typing import Optional, List, Dict

class Pair(BaseModel):
    strata: Optional[str] = None  # validated against registry's strata enum
    evolving: bool = False  # pair was READ (EVERY pair must get this)
    definition: bool = False  # pair has logic in it that is part of a definition
    concept_tags: List[str] = Field(default_factory=list)
    emergent_framework: Optional[str] = None  # reference by name
    # NOTE: evolving and definition are NOT mutually exclusive
    # - evolving=True, definition=False → read, no definition logic
    # - evolving=True, definition=True → read AND has definition logic
    # NOTE: strata is str in Pydantic, but tools validate against registry.
    # Use add_strata() to extend the allowed values.

class EmergentFramework(BaseModel):
    name: str
    strata: str  # validated against registry's strata enum
    canonical_framework: Optional[str] = None  # reference by name, set in Phase 5
    bundled_pairs: Dict[str, List[int]] = Field(default_factory=dict)  # conversation -> pair indices
    document: Optional[str] = None  # synthesized meaning from bundled pairs (Phase 4b)
    # NOTE: type and state belong to CANONICALS, not emergents
    # Emergent = discovered cluster of content with synthesized document
    # Canonical = typed, stated target that COMPOSES multiple emergents
    #
    # Phase 4a: Pairs get tagged with emergent_framework:X
    # Phase 4b: Bundle pairs per emergent → Synthesize document
    # Phase 5: Assign emergent to canonical (requires document)

class Conversation(BaseModel):
    authorized_phase: int = 3
    publishing_set: Optional[str] = None
    pairs: Dict[str, Pair] = Field(default_factory=dict)

class PublishingSet(BaseModel):
    conversations: List[str] = Field(default_factory=list)
    phase: int = 5
    status: Literal["in_progress", "ready_for_delivery", "delivered"] = "in_progress"
    # NOTE: canonical_frameworks is DERIVED, not stored
    # Computed by: "which canonicals do emergents in these conversations point to?"
    # NOTE: status auto-updates:
    #   - in_progress: at least one conversation not at Phase 5
    #   - ready_for_delivery: all conversations at Phase 5 (auto-set when last conv reaches Phase 5)
    #   - delivered: Phase 8 complete (auto-set when authorize_publishing_set_phase reaches Phase 8)
```

### Registry Model (Authoritative Canonical Source)

```python
class CanonicalEntry(BaseModel):
    """Entry for a canonical framework in the registry."""
    framework_state: Literal["aspirational", "actual"]

class StrataSlots(BaseModel):
    """Slots within a strata, each containing canonical entries."""
    reference: Dict[str, CanonicalEntry] = Field(default_factory=dict)
    collection: Dict[str, CanonicalEntry] = Field(default_factory=dict)
    workflow: Dict[str, CanonicalEntry] = Field(default_factory=dict)
    library: Dict[str, CanonicalEntry] = Field(default_factory=dict)
    operating_context: Dict[str, CanonicalEntry] = Field(default_factory=dict)

class StrataEntry(BaseModel):
    """A strata (PAIAB, SANCTUM, CAVE) with its slots."""
    name: str
    description: str
    slots: StrataSlots = Field(default_factory=StrataSlots)

class Registry(BaseModel):
    """
    Authoritative source for canonical frameworks.
    Type is implicit from slot. Strata is implicit from parent.
    framework_state is stored per-entry.
    """
    strata: Dict[str, StrataEntry] = Field(default_factory=dict)

    def get_canonical(self, canonical_name: str) -> Optional[tuple]:
        """
        Look up a canonical by name, return (type, strata, framework_state) or None.
        Searches all strata and slots to find the canonical.
        """
        for strata_key, strata_entry in self.strata.items():
            for slot_type in ['reference', 'collection', 'workflow', 'library', 'operating_context']:
                slot_entries = getattr(strata_entry.slots, slot_type)
                if canonical_name in slot_entries:
                    entry = slot_entries[canonical_name]
                    return (slot_type, strata_key, entry.framework_state)
        return None

    def canonical_exists(self, canonical_name: str) -> bool:
        """Check if a canonical framework exists in the registry."""
        return self.get_canonical(canonical_name) is not None

    def get_canonical_strata(self, canonical_name: str) -> Optional[str]:
        """Get the strata for a canonical framework."""
        result = self.get_canonical(canonical_name)
        return result[1] if result else None
```

### Delivery-Time Models (Phases 6-8)

At Phase 5→6 transition, canonicals get **hydrated** from names into full objects:

```python
class JourneyMetadata(BaseModel):
    obstacle: Optional[str] = None
    overcome: Optional[str] = None
    dream: Optional[str] = None

class CanonicalFramework(BaseModel):
    """
    Full canonical object created at Phase 6.
    Bundles all emergent frameworks that point to it.
    """
    name: str
    type: Literal["Reference", "Collection", "Workflow", "Library", "Operating_Context"]
    strata: str  # validated against registry's strata enum
    framework_state: Literal["aspirational", "actual"]  # renamed to avoid confusion with pair's evolving/definition
    journey: JourneyMetadata = Field(default_factory=JourneyMetadata)
    emergent_frameworks: List[str] = Field(default_factory=list)  # names of bundled emergents
    template: Optional[str] = None  # metastack template name
    document: Optional[str] = None  # rendered output
    posted_to: List[str] = Field(default_factory=list)  # substrates posted to
```

### Hydration Process (Phase 5 → Phase 6)

When publishing set advances to Phase 6:

1. Load all emergent frameworks from JSON (for conversations in this publishing set)
2. Derive canonical list: collect all unique `canonical_framework` values from emergents
3. For each canonical:
   - Get `type`/`strata`/`state` from registry (authoritative source)
   - Create `CanonicalFramework` object
   - Bundle all emergents that point to it
4. Save hydrated canonicals to delivery JSON

```python
def hydrate_canonicals(
    publishing_set: PublishingSet,
    emergents: Dict[str, EmergentFramework],
    registry: Registry  # has type/strata/state for each canonical
) -> Dict[str, CanonicalFramework]:
    """Create full canonical objects from emergent framework references."""

    # DERIVE which canonicals this publishing set produced
    # by looking at what emergents point to
    canonical_names = set(
        e.canonical_framework
        for e in emergents.values()
        if e.canonical_framework is not None
    )

    canonicals = {}
    for canonical_name in canonical_names:
        # Find all emergents pointing to this canonical
        bundled = [e.name for e in emergents.values() if e.canonical_framework == canonical_name]

        # Get type/strata/framework_state from registry (authoritative source)
        # reg_entry is tuple: (type, strata, framework_state)
        reg_entry = registry.get_canonical(canonical_name)

        canonicals[canonical_name] = CanonicalFramework(
            name=canonical_name,
            type=reg_entry[0],
            strata=reg_entry[1],
            framework_state=reg_entry[2],
            emergent_frameworks=bundled
        )

    return canonicals
```

### Tool Flow

1. AI calls MCP tool
2. Tool loads JSON from disk
3. Parse into Pydantic models (validates)
4. Perform operation
5. Serialize back to JSON
6. Save to disk
7. Return structured response

---

## Tool Changes

### Existing Tools - Keep As-Is

| Tool | What it does |
|------|--------------|
| `show_pairs(start, end)` | Display range of IO pairs |
| `next_pair()` | Show next unprocessed pair |
| `set_conversation(name)` | Switch to different conversation |
| `bundle_tagged(tag, output_name)` | Bundle pairs with tag into JSON |
| `bundle_multi_tag(tags, output_name)` | Bundle pairs matching any tags |

### Existing Tools - Modify

#### tag_pair(index, tag_type, value)
**Change:** Add `tag_type` parameter, enforce ratcheting.

1. Identify which tag type this is (strata, state, concept, emergent)
2. Get pair's current phase from its existing tags
3. Check if operation is allowed for that phase (ratcheting)
4. Check if conversation-level phase allows this operation
5. If blocked → raise with explanation
6. If allowed → apply tag to appropriate slot

#### tag_range(start, end, tag_type, value)
**Change:** Add `tag_type` parameter, enforce ratcheting.

Same logic as tag_pair, applied to range.

#### batch_tag_operations(operations)
**Change:** Validate by input args, enforce ratcheting.

1. Validate batch coherence by INPUT ARGS, not just what's already present
   - If batch includes `definition`, check: is `strata` already present on pair OR also in the batch?
   - This allows adding [strata, definition, concept_tag] in one coherent batch
2. Check conversation-level phase gates
3. If any operation blocked → raise with explanation, apply nothing
4. If all valid → apply all atomically

#### add_tag(tag_names)
**Change:** Now only adds to `concept_tags` list. Strata/state are fixed enums. Canonical frameworks use registry tools.

#### list_tags()
**Change:** Show tags organized by type (strata, state, concept, canonical, emergent).

#### status()
**Change:** Add phase info, publishing set info.

Returns:
- Current conversation name
- Current authorized phase
- Publishing set membership (if any)
- Pair counts by phase
- Summary stats

#### get_instructions()
**Change:** Update for 8-phase workflow.

#### add_or_update_emergent_framework(name, strata)
**Change:** New signature with 2 fields only.

- `name`: string
- `strata`: paiab | sanctum | cave

Note: `type` and `state` belong to canonicals, not emergents.

### Existing Tools - Deprecate

| Tool | Why deprecated |
|------|----------------|
| `get_meta_tags()` | Replaced by fixed strata/state enums |
| `get_framework_tags()` | Replaced by canonical registry |
| `verify_orphaned_pairs()` | Replaced by phase status checking |
| `get_violations()` | Ratcheting prevents violations from existing |
| `inject_pair(index)` | Replaced by phase tracking |
| `report_pass()` | We don't track passes, only phases |
| `get_pass_status()` | We don't track passes, only phases |
| `read_current_framework_def()` | Replaced by registry tools |
| `get_framework_tree()` | Replaced by registry tools |
| `remove_tag(index, tag_type, tag)` | Append-only during ingestion |
| `remove_tag_range(start, end, tag_type, tag)` | Append-only during ingestion |

### New Tools - Phase Management

#### authorize_next_phase(conversation)
- Advances conversation to the next phase (for Phases 1-5)
- Phases 1-3 are always authorized (simultaneous)
- First call: authorizes Phase 4 (emergent framework assignment)
- Second call: authorizes Phase 5 (canonical framework assignment)
- Returns error if already at Phase 5 (use publishing set tools for Phase 6+)

#### get_phase_status(conversation)
Returns:
- Current authorized phase (3, 4, or 5)
- Count of pairs in each per-pair phase (how many at Phase 1, 2, 3, 4)
- Count of emergent frameworks created
- Count of emergent frameworks with canonical assignments (Phase 5 progress)
- Summary of concept tags found

### New Tools - Emergent Framework Operations

#### assign_canonical_to_emergent(emergent_name, canonical_name)
- Sets the `canonical_framework` field on an emergent framework
- Only allowed when conversation is in Phase 5

**Validation (all must pass):**
1. Canonical must exist in registry
2. Emergent's strata must match canonical's strata

**Error cases:**

Blocked if Phase 5 not authorized:
```
BLOCKED: Cannot assign canonical to emergent '{emergent_name}'.
Conversation '{conv}' is not in Phase 5.
Current phase: {phase}
→ Complete Phase 4 and get user authorization for Phase 5 first.
```

Blocked if canonical doesn't exist in registry:
```
BLOCKED: Cannot assign canonical '{canonical_name}' to emergent '{emergent_name}'.
Canonical framework '{canonical_name}' does not exist in registry.
→ First add the canonical using: add_canonical_framework(strata, slot_type, '{canonical_name}', framework_state)
```

Blocked if strata mismatch:
```
BLOCKED: Cannot assign canonical '{canonical_name}' to emergent '{emergent_name}'.
Strata mismatch: Emergent is '{emergent_strata}', canonical is '{canonical_strata}'.
→ Emergent frameworks can only be assigned to canonicals in the same strata.
```

---

## Emergent Framework Synthesis Tools (Phase 4b)

### The Problem with Freeform Documents

Emergent framework documents need structured complexity. Freeform text replacement (`set_emergent_document`) causes:
- Loss of content on updates (no str_replace, must rewrite whole doc)
- Inefficient context usage (output entire document every edit)
- No enforced structure (easy to forget sections)

### The Solution: MetaStack Templating

MetaStack provides:
- `RenderablePiece` classes that compose
- `MetaStack` = Pydantic model nest where each model has `.render() -> str`
- Templates with pre-defined sections
- Fill template input values → renders complete document

### Synthesis Workflow (Updated)

After Phase 4a (all definition pairs tagged with emergent frameworks), Phase 4b synthesizes documents:

1. `list_emergent_frameworks()` → shows all emergents with pair counts and synthesis status
2. `get_emergent_pairs(emergent_name)` → returns bundled pairs for LLM to read
3. `init_emergent_template(emergent_name)` → creates MetaStack template JSON file for this emergent
4. LLM uses Edit tool on template JSON to fill section values (targeted str_replace)
5. `render_emergent_document(emergent_name)` → renders template to document, stores in emergent
6. Repeat for all emergents
7. When all emergents have documents → ready for Phase 5

### list_emergent_frameworks()
Returns all emergent frameworks with:
- Name and strata
- Pair count (how many pairs assigned)
- Synthesis status (has document or not)
- Template status (has template JSON or not)
- Canonical assignment (if any)

### get_emergent_pairs(emergent_name)
Returns:
- All pairs assigned to this emergent (across all conversations)
- Formatted for LLM to read and synthesize
- Grouped by conversation

### init_emergent_template(emergent_name)
- Creates template JSON file at known path: `{data_dir}/templates/emergent_{name}.json`
- Template based on Universal Framework Template (8 Sections):
  1. `name`: Framework name + acronym breakdown
  2. `essence`: One paragraph + one sentence summary
  3. `human_usage_stages`: H0 (Read-Only) → H1 (Manual) → H2 (Assisted/GNOSYS) → H3 (Ambient/Operational)
  4. `ai_capacity_levels`: A0 (Plain LLM) → A1 (GNOSYS+tools) → A2 (PAIA+Omnisanc) → A3 (Full Brain)
  5. `stage_level_map`: Table of (H, A) combinations
  6. `program_surface`: Hooks, State Machine Edges, Tool/Skill Contracts (at A2)
  7. `dependencies`: Tools, Skills, Slash Commands, Flights
  8. `pollution_failure_modes`: When it breaks, signals, minimal shields
- Returns path to template JSON for LLM to edit

### Template JSON Structure
```json
{
  "template_type": "emergent_framework",
  "emergent_name": "HIEL",
  "sections": {
    "name": {
      "framework_name": "",
      "acronym_breakdown": ""
    },
    "essence": {
      "one_paragraph": "",
      "one_sentence": ""
    },
    "human_usage_stages": {
      "H0_read_only": "",
      "H1_manual_practice": "",
      "H2_assisted_gnosys": "",
      "H3_ambient_operational": ""
    },
    "ai_capacity_levels": {
      "A0_plain_llm": "",
      "A1_gnosys_with_tools": "",
      "A2_paia_omnisanc": "",
      "A3_full_brain": ""
    },
    "stage_level_map": {
      "content": ""
    },
    "program_surface": {
      "required_hooks": "",
      "state_machine_edges": "",
      "tool_skill_contracts": ""
    },
    "dependencies": {
      "tools": "",
      "skills": "",
      "slash_commands_flights": ""
    },
    "pollution_failure_modes": {
      "when_breaks": "",
      "failure_signals": "",
      "minimal_shields": ""
    }
  }
}
```

### Editing Templates

LLM uses standard Edit tool with str_replace on the template JSON:
- Targeted edits to specific sections
- No loss of content from other sections
- Efficient context usage
- Can add subsections as needed

### render_emergent_document(emergent_name)
- Loads template JSON from known path
- Renders through MetaStack to produce markdown document
- Stores rendered document in emergent framework
- Returns rendered document for review

### set_emergent_document(emergent_name, document) [DEPRECATED]
- Still available for initial freeform input
- For edits, use template workflow instead
- Replacing whole document loses content

### Phase 4b Gate
`authorize_next_phase` from Phase 4 → Phase 5 requires:
- All definition pairs have emergent framework assignment (Phase 4a)
- All emergent frameworks have synthesized documents (Phase 4b)

---

## Canonical Framework Synthesis Tools (Phase 7)

### The Problem with Freeform Documents

Same problem as Phase 4b: canonical documents need structured complexity. Freeform replacement causes content loss and inefficient editing.

### The Solution: MetaStack Templating

Same solution: MetaStack templates with section-based editing via Edit tool.

Canonical templates are MORE complex than emergent templates because canonicals COMPOSE multiple emergents.

### Synthesis Workflow (Updated)

Phase 7 synthesizes canonical documents from emergent documents:

1. `get_canonical_emergents(canonical_name)` → returns all emergent documents for this canonical
2. `init_canonical_template(canonical_name)` → creates MetaStack template JSON for this canonical
3. LLM uses Edit tool on template JSON to fill section values
4. Template includes references to emergent docs (can inline or link)
5. `render_canonical_document(canonical_name)` → renders template to document, stores in canonical
6. Repeat for all canonicals in publishing set
7. When all canonicals have documents → ready for Phase 8

### get_canonical_emergents(canonical_name)
Returns:
- All emergent documents assigned to this canonical
- Emergent metadata (name, strata, relationships)
- Journey metadata (obstacle/overcome/dream)
- Formatted for LLM to compose

### init_canonical_template(canonical_name)
- Creates template JSON file at known path: `{data_dir}/templates/canonical_{name}.json`
- Template uses Universal Framework Template (8 Sections) PLUS canonical-specific composition fields:

  **Universal Framework Sections:**
  1. `name`: Framework name + acronym breakdown
  2. `essence`: One paragraph + one sentence summary
  3. `human_usage_stages`: H0 → H1 → H2 → H3
  4. `ai_capacity_levels`: A0 → A1 → A2 → A3
  5. `stage_level_map`: Table of (H, A) combinations
  6. `program_surface`: Hooks, State Machine Edges, Tool/Skill Contracts
  7. `dependencies`: Tools, Skills, Slash Commands, Flights
  8. `pollution_failure_modes`: When it breaks, signals, minimal shields

  **Canonical-Specific Sections:**
  - `emergent_composition`: How emergents compose into this canonical (role + summary per emergent)
  - `flow_between_parts`: How the emergent parts connect logically
  - `journey`: Obstacle → Overcome → Dream narrative

- Pre-populates `emergent_composition` with list of assigned emergents
- Returns path to template JSON for LLM to edit

### Template JSON Structure
```json
{
  "template_type": "canonical_framework",
  "canonical_name": "HALO_SHIELD",
  "emergents": ["HALO_acronym", "SOSEEH", "HIEL", "Helming", "Towering", "crowning_ascension"],
  "sections": {
    "name": {
      "framework_name": "",
      "acronym_breakdown": ""
    },
    "essence": {
      "one_paragraph": "",
      "one_sentence": ""
    },
    "emergent_composition": {
      "overview": "",
      "emergents": {
        "HALO_acronym": {"role": "", "summary": ""},
        "SOSEEH": {"role": "", "summary": ""},
        "HIEL": {"role": "", "summary": ""},
        "Helming": {"role": "", "summary": ""},
        "Towering": {"role": "", "summary": ""},
        "crowning_ascension": {"role": "", "summary": ""}
      }
    },
    "flow_between_parts": {
      "content": ""
    },
    "journey": {
      "obstacle": "",
      "overcome": "",
      "dream": ""
    },
    "human_usage_stages": {
      "H0_read_only": "",
      "H1_manual_practice": "",
      "H2_assisted_gnosys": "",
      "H3_ambient_operational": ""
    },
    "ai_capacity_levels": {
      "A0_plain_llm": "",
      "A1_gnosys_with_tools": "",
      "A2_paia_omnisanc": "",
      "A3_full_brain": ""
    },
    "stage_level_map": {
      "content": ""
    },
    "program_surface": {
      "required_hooks": "",
      "state_machine_edges": "",
      "tool_skill_contracts": ""
    },
    "dependencies": {
      "tools": "",
      "skills": "",
      "slash_commands_flights": ""
    },
    "pollution_failure_modes": {
      "when_breaks": "",
      "failure_signals": "",
      "minimal_shields": ""
    }
  }
}
```

### Editing Templates

LLM uses standard Edit tool with str_replace on the template JSON:
- Targeted edits to specific sections
- No loss of content from other sections
- Can reference emergent docs inline or by link
- Can expand subsections as needed

### render_canonical_document(canonical_name)
- Loads template JSON from known path
- Optionally inlines emergent document content where referenced
- Renders through MetaStack to produce markdown document
- Stores rendered document in canonical framework
- Returns rendered document for review

### set_canonical_document(canonical_name, document) [DEPRECATED]
- Still available for initial freeform input
- For edits, use template workflow instead
- Replacing whole document loses content

### Phase 7 Gate
`authorize_publishing_set_phase` from Phase 7 → Phase 8 requires:
- All canonical frameworks have synthesized documents

---

## Publishing Set Tools

### Publishing Set Workflow

The publishing set is the unit of work. You cannot work on conversations without first creating and activating a publishing set.

**Workflow:**
1. `create_publishing_set("batch1", ["halo-shield", "conv2"])` → creates set with status `in_progress`
2. `set_publishing_set("batch1")` → activates it as current working set
3. `list_available_conversations()` → shows conversations in active set not yet at Phase 5
4. `set_conversation("halo-shield")` → only works if conversation is in ACTIVE publishing set
5. Work through each conversation to Phase 5
6. When ALL conversations reach Phase 5 → status auto-updates to `ready_for_delivery`
7. `list_publishing_sets()` → completed sets hidden by default
8. Advance to Phase 6+ for delivery

**Publishing Set Status:**
- `in_progress`: At least one conversation not at Phase 5
- `ready_for_delivery`: All conversations at Phase 5, ready for Phase 6+
- `delivered`: Phase 8 complete

### State Structure

```json
{
  "active_publishing_set": "batch1",
  "publishing_sets": {
    "batch1": {
      "conversations": ["halo-shield", "conv2"],
      "phase": 5,
      "status": "in_progress"
    }
  }
}
```

### create_publishing_set(name, conversations)
- Creates a new publishing set with the specified conversations
- Sets status to `in_progress`
- Each conversation gets linked to this publishing set
- Returns error if any conversation is already in a publishing set
- Does NOT auto-activate (must call `set_publishing_set` after)

### set_publishing_set(name)
- Activates a publishing set as the current working set
- Sets `active_publishing_set` in state
- Returns error if publishing set not found
- Returns error if publishing set status is `delivered`
- Shows list of available conversations (not yet at Phase 5)

### list_publishing_sets(include_delivered=False)
- Lists all publishing sets with their status
- By default hides `delivered` sets
- Shows: name, status, conversation count, conversations at Phase 5 count

### list_available_conversations()
- Lists conversations in the ACTIVE publishing set that are not yet at Phase 5
- Returns error if no active publishing set
- Shows conversation name and current phase

### get_publishing_set_status(name)
Returns:
- Status (in_progress / ready_for_delivery / delivered)
- List of conversations and their current phases
- Whether all conversations are at Phase 5 (ready for Phase 6)
- List of canonical frameworks discovered across all conversations

### authorize_publishing_set_phase(name)
- Advances the publishing set to the next phase (for Phases 6-8)
- First call: authorizes Phase 6 (requires all conversations at Phase 5)
- Second call: authorizes Phase 7 (requires Phase 6 complete)
- Third call: authorizes Phase 8 (requires Phase 7 complete)
- When Phase 8 reached: status auto-updates to `delivered`
- Returns error if prerequisites not met

### set_conversation Gate

`set_conversation(name)` is BLOCKED unless:
1. There is an active publishing set
2. The conversation is in the ACTIVE publishing set

Error message:
```
BLOCKED: Cannot set conversation '{name}'.
No active publishing set.
→ Call set_publishing_set('set_name') first.
```

Or:
```
BLOCKED: Cannot set conversation '{name}'.
Conversation is not in active publishing set '{active_set}'.
Available conversations: {list}
→ Switch publishing set or choose from available conversations.
```

---

## Journey Metadata Tools

### set_journey_metadata(canonical_framework, obstacle, overcome, dream)
- Sets the journey metadata for a canonical framework
- Only allowed when publishing set is in Phase 6+
- All three fields required together

### get_journey_metadata(canonical_framework)
Returns:
- obstacle, overcome, dream (or null if not set)
- Whether this canonical is ready for Phase 7

---

## The M + E → C Pipeline

### What Each Letter Means

- **M (Meta intent)**: Isaac says "there is a canonical framework named {{x}} with description: {{description}}"
- **E (Emergent atoms)**: The correctly synthesized granular emergent frameworks from tagging
- **C (Canonical)**: The deliverable framework document that gets consumed

### The Relationship

- Emergent frameworks (E) slot INTO canonical frameworks
- They get semantically bridged
- They MAKE the canonical (C)
- The canonical is what actually gets delivered to the consumer

### What We Learned

The big poetic docs we wrote (like Mahajala_System.md) are **M (blueprints)**, not **C (blueprint+implementation)**. They tried to be both and the geometry broke.

### Pipeline Scope

**THIS pipeline (MCP V2) handles the full e2e:**

| Phase | What | Output |
|-------|------|--------|
| 1-5 | Ingestion | Pairs tagged, emergents assigned, canonicals assigned |
| 6 | Journey definition | obstacle/overcome/dream for each canonical |
| 7 | Document writing | Canonical framework documents written |
| 8 | Posting | Documents posted to delivery substrates |

---

## Completeness Guarantee

### Conversation Complete (Phase 5)
- All pairs have strata + evolving
- All definition pairs have concept tags
- All definition pairs have emergent framework assignment
- All emergent frameworks assigned to canonical frameworks
- `authorized_phase` = 5

→ Conversation is complete. Ready for publishing set to advance to Phase 6.

### Publishing Set Complete (Phase 8)
- All conversations in set at Phase 5
- All canonical frameworks have journey metadata (Phase 6)
- All canonical framework documents written (Phase 7)
- All documents posted to delivery substrates (Phase 8)

→ Publishing set is complete. Canonical frameworks are live.

---

## Files to Change

- `/tmp/conversation_ingestion_mcp/conversation_ingestion_mcp/core.py` - main logic
- `/tmp/conversation_ingestion_mcp/conversation_ingestion_mcp/utils.py` - data loading/saving
- New state file structure

---

## Implementation Sequence

### Phase A: Foundation Layer

1. **Add Pydantic models file** (`models.py`)
   - Pair, EmergentFramework, Conversation, PublishingSet
   - CanonicalEntry, StrataSlots, StrataEntry, Registry
   - JourneyMetadata, CanonicalFramework
   - Test: models import without error

2. **Update utils.py for new data structure**
   - Load/save functions for new JSON structure
   - Keep backward compat functions for reading old format
   - Test: can load empty new-format JSON

3. **Add registry JSON file** (`canonical_registry.json`)
   - Initialize with PAIAB frameworks from CANONICAL_FRAMEWORKS.md
   - SANCTUM/CAVE stubs
   - Test: registry loads into Registry model

### Phase B: Core Tool Updates

4. **Update tag_pair() with tag_type parameter**
   - Parse tag array into Pydantic model for validation
   - Add ratcheting checks (strata before definition, definition before concept, etc.)
   - Return structured errors on block
   - Test: ratcheting blocks work

5. **Update tag_range() with tag_type parameter**
   - Same ratcheting logic as tag_pair
   - Test: range operations respect ratcheting

6. **Update batch_tag_operations() with coherence checking**
   - Validate by INPUT ARGS (allow strata+definition+concept in one batch)
   - Atomic: if any blocked, apply nothing
   - Test: coherent batches work, incoherent blocked

7. **Update add_tag() to only add concept_tags**
   - Remove ability to add strata/canonical
   - Test: only concept tags addable

### Phase C: Phase Management Tools

8. **Add authorize_next_phase(conversation)**
   - Track authorized_phase per conversation
   - Phase 3 → 4 → 5 progression
   - Test: phase advancement works

9. **Add get_phase_status(conversation)**
   - Return phase, pair counts, emergent counts
   - Test: status reflects actual state

### Phase D: Emergent Framework Tools

10. **Update add_or_update_emergent_framework(name, strata)**
    - New signature: only name + strata
    - No type, no state
    - Test: emergent created with 2 fields

11. **Add assign_canonical_to_emergent(emergent_name, canonical_name)**
    - Validate: canonical exists in registry
    - Validate: strata match
    - Validate: emergent has synthesized document
    - Only allowed in Phase 5
    - Test: assignment works, validations block

### Phase D.5: Emergent Synthesis Tools (Phase 4b)

12. **Add list_emergent_frameworks()**
    - Show all emergents with pair counts, synthesis status, template status, canonical assignment
    - Test: displays correctly

13. **Add get_emergent_pairs(emergent_name)**
    - Return all pairs assigned to this emergent across conversations
    - Format for LLM to read and synthesize
    - Test: pairs retrieved correctly

14. **Add init_emergent_template(emergent_name)**
    - Create MetaStack template JSON at `{data_dir}/templates/emergent_{name}.json`
    - Template based on Universal Framework Spec sections
    - Return path to JSON for LLM to edit with Edit tool
    - Test: template JSON created with correct structure

15. **Add render_emergent_document(emergent_name)**
    - Load template JSON from known path
    - Render through MetaStack to markdown
    - Store rendered document in emergent framework
    - Test: renders correctly, stores in emergent

16. **Add set_emergent_document(emergent_name, document)** [DEPRECATED]
    - Manually set/edit emergent document (whole replacement)
    - Mark as deprecated, recommend template workflow
    - Test: document saved

17. **Update authorize_next_phase gate for Phase 4→5**
    - Require all definition pairs have emergent assignment (Phase 4a)
    - Require all emergent frameworks have documents (Phase 4b)
    - Test: gate blocks if emergents lack documents

### Phase E: Registry Tools

17. **Add add_canonical_framework(strata, slot_type, framework_name, framework_state)**
    - Add to registry JSON
    - Validate strata/slot_type exist
    - Test: framework added to correct slot

18. **Add list_canonical_frameworks(strata?, slot_type?)**
    - Query registry
    - Test: filtering works

19. **Add remove_canonical_framework(strata, slot_type, framework_name)**
    - Remove from registry
    - Test: removal works

### Phase F: Publishing Set Tools

20. **Add create_publishing_set(name, conversations)**
    - Link conversations to publishing set
    - Set status to `in_progress`
    - Test: publishing set created

21. **Add set_publishing_set(name)**
    - Set `active_publishing_set` in state
    - Block if status is `delivered`
    - Show available conversations
    - Test: activation works, delivered sets blocked

22. **Add list_publishing_sets(include_delivered=False)**
    - List all publishing sets with status
    - Filter out `delivered` by default
    - Test: filtering works

23. **Add list_available_conversations()**
    - List conversations in active set not at Phase 5
    - Block if no active publishing set
    - Test: correct filtering

24. **Update set_conversation(name)**
    - Block if no active publishing set
    - Block if conversation not in active publishing set
    - Test: gates work

25. **Add get_publishing_set_status(name)**
    - Return status, conversation phases, readiness
    - Test: status accurate

26. **Add authorize_publishing_set_phase(name)**
    - Phase 5 → 6 → 7 → 8 progression
    - Validate prerequisites
    - Auto-set status to `delivered` at Phase 8
    - Test: phase gates work

27. **Add auto-status update on conversation Phase 5**
    - When conversation reaches Phase 5, check if all conversations in publishing set are at Phase 5
    - If yes, auto-update publishing set status to `ready_for_delivery`
    - Test: auto-update works

### Phase G: Journey Metadata Tools

28. **Add set_journey_metadata(canonical, obstacle, overcome, dream)**
    - Only allowed Phase 6+
    - Test: metadata saved

29. **Add get_journey_metadata(canonical)**
    - Return metadata and readiness
    - Test: retrieval works

### Phase G.5: Canonical Synthesis Tools (Phase 7)

30. **Add get_canonical_emergents(canonical_name)**
    - Return all emergent documents assigned to this canonical
    - Include journey metadata
    - Format for LLM to compose
    - Test: emergents retrieved correctly

31. **Add synthesize_canonical(canonical_name)**
    - Gather emergent documents
    - Synthesize FLOW between emergent parts
    - Recursively read involved parts to find logic connections
    - Compose canonical document
    - Store document in canonical framework
    - Test: synthesis produces document

32. **Add set_canonical_document(canonical_name, document)**
    - Manually set/edit canonical document
    - Test: document saved

33. **Update authorize_publishing_set_phase gate for Phase 7→8**
    - Require all canonical frameworks have documents
    - Test: gate blocks if canonicals lack documents

### Phase H: Status Tools Updates

34. **Update status()**
    - Add phase info, publishing set info, active publishing set
    - Test: status shows new info

35. **Update list_tags()**
    - Organize by type
    - Test: organized output

36. **Update get_instructions()**
    - 8-phase workflow with publishing set workflow
    - Include Phase 4a/4b distinction
    - Include synthesis steps
    - Test: instructions accurate

### Phase I: Cleanup

37. **Deprecate old tools**
    - get_meta_tags, get_framework_tags, verify_orphaned_pairs, get_violations
    - inject_pair, report_pass, get_pass_status
    - read_current_framework_def, get_framework_tree
    - remove_tag, remove_tag_range
    - Either remove or have them return deprecation notice

38. **Integration test**
    - Full workflow: create publishing set → set publishing set → tag pairs → synthesize emergents → assign canonicals → journey → synthesize canonicals → Phase 8
    - Test: e2e works with proper synthesis steps

---

## Data Migration Path

1. Lock the canonical frameworks list (from Master Framework List in CLAUDE.md)
2. Existing 2916 tag_enum items → become concept_tags (this is what they actually are)
3. Existing emergent_frameworks.json entries → become concept_tags too (they were mislabeled)
4. Convert existing tagged_pairs from flat lists to slot structure
5. Reset conversation phase tracking (start fresh with new system)
6. During Phase 4, concept tags get composed into REAL emergent frameworks (with name + strata)
7. During Phase 5, emergent frameworks get assigned to canonical frameworks

---

## Canonical Frameworks Registry

The canonical frameworks are stored as a configurable data structure, not hardcoded.

### Data Structure

```json
{
  "strata": {
    "paiab": {
      "name": "PAIAB",
      "description": "AI/Agents",
      "slots": {
        "reference": {
          "SANCREV_The_Finite_Game": {"framework_state": "aspirational"},
          "OEVESE": {"framework_state": "aspirational"},
          "HALO-SHIELD": {"framework_state": "actual"},
          "Foundation_Of_TWI": {"framework_state": "actual"}
        },
        "collection": {
          "Prompt_Engineering_Collection": {"framework_state": "actual"}
        },
        "workflow": {
          "Vibe_Coding_Core_Pattern": {"framework_state": "actual"}
        },
        "library": {
          "STARSHIP": {"framework_state": "actual"},
          "CartON": {"framework_state": "actual"}
        },
        "operating_context": {}
      }
    },
    "sanctum": {
      "name": "SANCTUM",
      "description": "Philosophy/Coordination",
      "slots": {
        "reference": {
          "SANCREV_Itself": {"framework_state": "aspirational"},
          "VEC": {"framework_state": "aspirational"}
        },
        "collection": {},
        "workflow": {},
        "library": {},
        "operating_context": {}
      }
    },
    "cave": {
      "name": "CAVE",
      "description": "Business/Marketing",
      "slots": {
        "reference": {
          "SANCREV_Abundance_Fractal": {"framework_state": "aspirational"},
          "UNICORN": {"framework_state": "aspirational"}
        },
        "collection": {},
        "workflow": {},
        "library": {},
        "operating_context": {}
      }
    }
  }
}
```

Each canonical entry stores its `framework_state` (aspirational/actual). The slot (type) and parent strata are implicit from the structure.

### Invariant Structure

The slot types are fixed (enforced by code) and match framework `type` values:
- `reference`
- `collection`
- `workflow`
- `library`
- `operating_context`

The framework's `framework_state` field (aspirational/actual) determines whether it's a north-star target or an accomplished capability. The slot type determines what KIND of framework it is.

The content (which frameworks exist in each slot) is configurable data.

### Registry Tools

#### add_strata(name, description)
- Adds a new strata with empty slots
- Returns error if strata already exists

#### add_canonical_framework(strata, slot_type, framework_name, framework_state)
- Adds a framework to a specific slot in a strata
- `framework_state`: aspirational | actual
- Returns error if strata or slot_type doesn't exist
- Returns error if framework already exists in that slot

#### list_canonical_frameworks(strata?, slot_type?)
- Query what frameworks exist
- If no args: returns full registry
- If strata only: returns all slots for that strata
- If both: returns frameworks in that specific slot

#### remove_canonical_framework(strata, slot_type, framework_name)
- Removes a framework from a slot
- Returns error if framework doesn't exist

### How Registry Gets Filled

1. **Initial state**: PAIAB slots populated from CLAUDE.md, SANCTUM/CAVE mostly empty
2. **During Phase 5**: When assigning emergent frameworks to canonicals:
   - If emergent maps to existing canonical → use it
   - If emergent is NEW → call `add_canonical_framework()` to add it first
3. **Progressive refinement**: As more conversations are ingested, registry grows

---

## Companion Document

The canonical frameworks list and their relationships are documented in:

**`/tmp/conversation_ingestion_openai_paiab/CANONICAL_FRAMEWORKS.md`**

That document contains:
- The invariant structure across strata
- The complete list of canonical frameworks per strata
- How frameworks relate to each other
- TBDs that need to be filled during ingestion
