# Omnisanc TODO

Future enhancements to the Omnisanc state machine as we discover them.

## DAY/NIGHT Mode Enforcement

**Concept**: Two fundamental modes of operation:
- **DAY mode**: Live generative work. Conversations that create content, build things, observe. Optionally flag conversations for later ingestion.
- **NIGHT mode**: Extractive work. Processing flagged conversations to harvest frameworks via conversation-ingestion MCP.

**Current state**: Conceptual only - not yet enforced in state machine.

**To implement**:
- Add `mode: day | night` to course state
- NIGHT mode restricts to ingestion-related tools
- DAY mode restricts conversation-ingestion MCP (except `flag_conversation`)
- Mode switch requires explicit transition (part of plot_course?)

---

## Slash Command Integration

**Concept**: When slash commands exist, decision tree may need step 0: "check if user should invoke a slash command"

**Current state**: No slash commands implemented yet. Decision tree is: skill trigger check → tool use → cycle.

**To implement**: TBD when slash commands are built

---

## Other TODOs

(Add as discovered)
