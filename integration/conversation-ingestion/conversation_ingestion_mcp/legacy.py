"""
Legacy/deprecated V1 tools for backward compatibility.

These tools are deprecated but kept for migration purposes.
Most return deprecation notices pointing to V2 equivalents.
"""

import json
import os
from typing import Optional, List
from datetime import datetime

from . import utils


# Meta-tag definitions (V1)
META_TAGS = {
    'paiab', 'sanctum', 'cave',
    'evolving', 'definition',
    '218_background'
}


def get_meta_tags() -> str:
    """DEPRECATED: Use registry tools for strata, state tags are fixed."""
    return (
        "DEPRECATED: get_meta_tags is deprecated in V2.\n"
        "→ Strata: Use list_canonical_frameworks() to see registry strata\n"
        "→ State tags: Fixed as 'evolving' and 'definition'\n"
        "→ Source tags: No longer used"
    )


def get_framework_tags() -> str:
    """DEPRECATED: Use list_tags() for organized tag view."""
    return (
        "DEPRECATED: get_framework_tags is deprecated in V2.\n"
        "→ Use list_tags() for organized view of all tag types"
    )


def verify_orphaned_pairs(conversation_name: Optional[str] = None) -> str:
    """DEPRECATED: Use get_phase_status() for phase-based validation."""
    return (
        "DEPRECATED: verify_orphaned_pairs is deprecated in V2.\n"
        "→ Use get_phase_status(conversation) to see pair states\n"
        "→ Ratcheting prevents orphaned pairs from existing"
    )


def get_violations(conversation_name: Optional[str] = None) -> str:
    """DEPRECATED: Ratcheting prevents violations from existing."""
    return json.dumps({
        "deprecated": True,
        "message": "V2 ratcheting prevents violations. Use get_phase_status()."
    })


def inject_pair(index: int) -> str:
    """DEPRECATED: Phase tracking replaces injection."""
    return (
        "DEPRECATED: inject_pair is deprecated in V2.\n"
        "→ Phase tracking replaces manual injection\n"
        "→ Pairs advance through phases via tagging"
    )


def remove_tag(index: int, tag: str) -> str:
    """DEPRECATED: V2 is append-only during ingestion."""
    return (
        "DEPRECATED: remove_tag is deprecated in V2.\n"
        "→ Ingestion is append-only to maintain audit trail\n"
        "→ If needed, manually edit state.json"
    )


def remove_tag_range(start: int, end: int, tag: str) -> str:
    """DEPRECATED: V2 is append-only during ingestion."""
    return (
        "DEPRECATED: remove_tag_range is deprecated in V2.\n"
        "→ Ingestion is append-only to maintain audit trail"
    )


def report_pass(
    conversation: str,
    phase: int,
    pass_num: int,
    notes: str,
    converged: bool = False
) -> str:
    """DEPRECATED: V2 tracks phases, not passes."""
    return (
        "DEPRECATED: report_pass is deprecated in V2.\n"
        "→ V2 tracks phases via state machine, not passes\n"
        "→ Use get_phase_status() to check phase progress"
    )


def get_pass_status(conversation: Optional[str] = None) -> str:
    """DEPRECATED: V2 tracks phases, not passes."""
    return (
        "DEPRECATED: get_pass_status is deprecated in V2.\n"
        "→ Use get_phase_status(conversation) for phase info"
    )


def read_current_framework_def(framework: Optional[str] = None, all: bool = False) -> str:
    """DEPRECATED: Emergent frameworks stored in state, not separate file."""
    state = utils.load_state()

    if utils.is_v2_state(state):
        emergents = state.get("emergent_frameworks", {})
        if not emergents:
            return "No emergent frameworks in V2 state."

        if framework:
            ef = emergents.get(framework)
            if not ef:
                return f"Emergent framework '{framework}' not found."
            return (
                f"Emergent Framework: {framework}\n"
                f"  Strata: {ef.get('strata')}\n"
                f"  Canonical: {ef.get('canonical_framework') or 'unassigned'}"
            )

        if all:
            output = [f"Emergent Frameworks ({len(emergents)}):"]
            for name, ef in emergents.items():
                canonical = ef.get('canonical_framework') or 'unassigned'
                output.append(f"  - {name} [{ef.get('strata')}] → {canonical}")
            return "\n".join(output)

    # V1 fallback
    frameworks_path = os.path.join(utils.CONV_DIR, 'emergent_frameworks.json')
    if not os.path.exists(frameworks_path):
        return "No emergent_frameworks.json found."

    with open(frameworks_path, 'r') as f:
        frameworks = json.load(f)

    if framework:
        if framework not in frameworks:
            return f"Framework '{framework}' not found."
        return json.dumps(frameworks[framework], indent=2)

    if all:
        return f"V1 Emergent Frameworks ({len(frameworks)}):\n" + "\n".join(
            f"  - {name}" for name in frameworks.keys()
        )

    return "Specify framework name or use all=True"


def get_framework_tree(layer: Optional[str] = None) -> str:
    """DEPRECATED: Use list_canonical_frameworks() for registry view."""
    return (
        "DEPRECATED: get_framework_tree is deprecated in V2.\n"
        "→ Use list_canonical_frameworks() for canonical registry\n"
        "→ Use read_current_framework_def(all=True) for emergent list"
    )


def get_instructions() -> str:
    """Return V2 workflow instructions pointing to flight configs."""
    return """# Conversation Ingestion V2 - Flight Config Guided Workflow

## Quick Start
Use STARSHIP flight configs to guide you through the 8-phase pipeline.

### Check Status First
```
status()
```

### Then Start the Appropriate Flight
Use `starship.fly(path, category="night")` to see available flights.

## Available Flight Configs (category: night)

| Flight Config | Phases | Description |
|--------------|--------|-------------|
| `ingestion_setup_flight_config` | 1-2 | Check status, create/activate publishing set, select conversation |
| `ingestion_tagging_flight_config` | 3 | Read batch → Tag batch → Next batch (with semantic guidance) |
| `ingestion_emergent_flight_config` | 4-5 | Create emergent framework documents from tagged pairs |
| `ingestion_publishing_flight_config` | 6-8 | Journey metadata, canonical documents, Discord delivery |

## How to Use Flights
```
waypoint.start_waypoint_journey(
    config_path="ingestion_setup_flight_config",
    starlog_path="/your/project"
)
```

Then navigate with:
```
waypoint.navigate_to_next_waypoint(starlog_path="/your/project")
```

## Phase Overview

### Per-Pair Ratcheting (within Phase 3)
strata → evolving → definition → concept → emergent_framework

### Per-Conversation Phases
- Phase 3: Tagging (default)
- Phase 4: Emergent framework assignment
- Phase 5: Conversation complete

### Per-Publishing-Set Phases
- Phase 5→6: Journey metadata unlocked
- Phase 6→7: Canonical document writing
- Phase 7→8: Delivery complete

## Key Semantic Rules

1. **Read batch → Tag batch → Next batch** (NEVER read entire conversation first)
2. **Concept tags = retrieval granularity** (tag ALL distinct ideas)
3. **Emergent frameworks = synthesis buckets** (which document will this contribute to)
4. **Create SEPARATE emergents for distinct concepts** (not one mega-framework with terms)

## Tool Reference

### Navigation
- status() - Current status with phase info
- set_publishing_set(name) - Activate publishing set
- set_conversation(name) - Select conversation
- show_pairs(start, end) - View pairs in batches

### Tagging
- batch_tag_operations([...]) - Tag with coherence checking
- tag_pair(index, tag_type, value) - Single pair
- tag_range(start, end, tag_type, value) - Range of pairs

### Phase Advancement
- authorize_next_phase(conv) - Advance conversation phase (3→4→5)
- authorize_publishing_set_phase(name) - Advance publishing set (5→6→7→8)

### Documents
- set_emergent_document(name) - Create emergent JSON skeleton
- preview_emergent(name, path) - Render to markdown
- set_canonical_document(name, emergents) - Create canonical JSON
- preview_canonical(name, path) - Render full canonical

### Scoring (Phase 5/6 Quality Gate)
- get_scores_registry() - View current scores + path to JSON
- After scoring: Edit the scores_registry.json with the result

### Metadata
- set_journey_metadata(canonical, obstacle, overcome, dream) - Discord journey post

## Scoring Workflow (REQUIRED Before Phase 6→7)

Every emergent framework MUST score 6/6 on the mimetic desire chain before advancing.

### The Scoring Loop
```
1. get_scores_registry()              → see current scores
2. preview_emergent(name, "/tmp/preview.md")  → render MD
3. Run framework-scorer agent on the MD       → get X/6 score
4. Edit /tmp/heaven_data/frameworks/scores_registry.json  → record score
5. If < 6/6: Edit the emergent JSON proof section, go to step 2
6. If 6/6: Move to next framework
```

### What framework-scorer Checks (6 Links)
1. **Link 1 - Author Had My Exact Pain**: Starts with visceral pain, not discovery
2. **Link 2 - How It Solved Their Version**: Shows the mechanism, not just "it worked"
3. **Link 3 - Translation To My Version**: Addresses variations for different contexts
4. **Link 4 - Jealousy**: Makes reader WANT what author has
5. **Link 5 - Identity Desire**: Reader wants to BE the author, not just learn
6. **Link 6 - Accessible Path**: Clear steps from "me now" to "me transformed"

### Common Failure: Link 1 Breaks
Most frameworks break at Link 1 because they start with:
- "We were having a conversation and discovered..." (expert perspective)
- "The naming journey..." (starting at the end)
- "I realized that..." (intellectual discovery, no pain)

Instead, start with: "I was drowning in X. Here's what that looked like. I opened Y, stared, felt Z..."

### Phase Gate
- Cannot advance publishing set 6→7 until ALL emergents score 6/6
- Check with: `get_scores_registry()`

## Re-Running Phases (Fixing Mistakes)

**Tags are mutable.** You can always re-tag pairs without resetting anything.

### Re-tag a conversation
1. `set_publishing_set(name)` - activate the publishing set
2. `set_conversation(name)` - select the conversation
3. `show_pairs(start, end)` - view pairs
4. `batch_tag_operations([...])` - re-tag with new values

The new tags simply overwrite the old ones. No reset needed.

### Re-assign to a different publishing set
If a conversation is already in a publishing set but you want to move it:
```
create_publishing_set("new_set", ["conversation_name"], force=True)
```
The `force=True` parameter reassigns conversations from their current set.

### Re-do emergent framework documents
1. Delete existing JSON: `rm /tmp/heaven_data/frameworks/emergent_<name>.json`
2. Call `set_emergent_document(name)` again to get fresh skeleton
3. Fill in with proper content

### Re-do synthesis (not happy with quality)
Just edit the JSON directly. The files are at:
- `/tmp/heaven_data/frameworks/emergent_<name>.json`
- `/tmp/heaven_data/frameworks/canonical_<name>.json`

Use `preview_emergent(name, path)` or `preview_canonical(name, path)` to check rendering.

### Phase gates are for advancement, not prevention
Phase gates only block ADVANCEMENT to the next phase. You can always go back and fix things in earlier phases without resetting phase counters.
"""
