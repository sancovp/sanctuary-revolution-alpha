# Conversation Ingestion MCP V2 - Integration Test Plan

## Pre-Test Setup
```bash
# Reset state to fresh V2
python3 -c "
import sys
sys.path.insert(0, '/tmp/conversation_ingestion_mcp_v2')
from conversation_ingestion_mcp import utils
state = utils.get_empty_state_v2()
utils.save_state(state)
print('Reset to fresh V2 state')
"
```

## Test Sequence (Using MCP Tools)

### 1. Set Conversation
```
mcp__conversation-ingestion__set_conversation("halo-shield")
mcp__conversation-ingestion__show_pairs(0, 5)
```
Expected: Shows 5 pairs from halo-shield conversation

### 2. Phase 1-3: Tagging Chain
```
# Add concept tags
mcp__conversation-ingestion__add_tag(["halo_concept", "protection"])

# Tag pair 0 with full chain using batch
mcp__conversation-ingestion__batch_tag_operations([
  {"action": "tag_pair", "index": 0, "tag_type": "strata", "value": "paiab"},
  {"action": "tag_pair", "index": 0, "tag_type": "evolving", "value": ""},
  {"action": "tag_pair", "index": 0, "tag_type": "definition", "value": ""},
  {"action": "tag_pair", "index": 0, "tag_type": "concept", "value": "halo_concept"}
])

# Check status
mcp__conversation-ingestion__status()
```
Expected: Pair 0 at Phase 3 (has concepts)

### 3. Test Ratcheting Block
```
# Try emergent WITHOUT Phase 4 authorization
mcp__conversation-ingestion__tag_pair(0, "emergent_framework", "Test_Emergent")
```
Expected: BLOCKED message about Phase 4 authorization required

### 4. Phase 4: Emergent Framework Assignment
```
# Create emergent framework
mcp__conversation-ingestion__add_or_update_emergent_framework("HALO_Emergent", "paiab")

# Authorize Phase 4
mcp__conversation-ingestion__authorize_next_phase("halo-shield")

# Now assign emergent
mcp__conversation-ingestion__tag_pair(0, "emergent_framework", "HALO_Emergent")

# Check phase status
mcp__conversation-ingestion__get_phase_status("halo-shield")
```
Expected: Phase 4 authorized, pair 0 has emergent assignment

### 5. Test Phase 5 Gate
```
# Try canonical assignment WITHOUT Phase 5 authorization
mcp__conversation-ingestion__assign_canonical_to_emergent("HALO_Emergent", "HALO_SHIELD")
```
Expected: BLOCKED message about Phase 5 authorization required

### 6. Phase 5: Canonical Assignment
```
# Add canonical to registry (if not exists)
mcp__conversation-ingestion__add_canonical_framework("paiab", "reference", "HALO_SHIELD", "actual")

# Authorize Phase 5
mcp__conversation-ingestion__authorize_next_phase("halo-shield")

# Assign canonical
mcp__conversation-ingestion__assign_canonical_to_emergent("HALO_Emergent", "HALO_SHIELD")

# List canonicals
mcp__conversation-ingestion__list_canonical_frameworks()
```
Expected: Emergent assigned to canonical

### 7. Phase 6: Publishing Set + Journey
```
# Create publishing set
mcp__conversation-ingestion__create_publishing_set("halo_batch", ["halo-shield"])

# Check status
mcp__conversation-ingestion__get_publishing_set_status("halo_batch")

# Authorize Phase 6
mcp__conversation-ingestion__authorize_publishing_set_phase("halo_batch")

# Set journey metadata
mcp__conversation-ingestion__set_journey_metadata(
  "HALO_SHIELD",
  "AI lacks protective boundaries",
  "Layered defense architecture",
  "Safe aligned AI"
)

# Verify
mcp__conversation-ingestion__get_journey_metadata("HALO_SHIELD")
```
Expected: Journey metadata set, ready for Phase 7

## Success Criteria
- [ ] All phase gates block correctly
- [ ] Ratcheting prevents skipping steps
- [ ] State persists between calls
- [ ] Real conversation file loads properly
- [ ] Full Phase 1-6 flow completes

## Notes
- Phases 7-8 not implemented (document writing, posting)
- Test with real `halo-shield` conversation file
- MCP config: `"command": "conversation-ingestion-server"`
