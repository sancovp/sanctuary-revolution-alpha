# Conversation Ingestion MCP

Semi-automated system for ingesting OpenAI conversation exports into structured documents.

## Features

- **Stateful Navigation**: Persistent state tracking across sessions
- **Tagging System**: Categorize IO pairs with extensible tag enum
- **Bundling**: Collect tagged pairs into JSON documents
- **Ratcheting**: Auto-increment index when processing pairs

## Installation

```bash
pip install -q .
```

## Usage

### As MCP Server

Add to your `.claude.json`:

```json
{
  "mcpServers": {
    "conversation-ingestion": {
      "command": "python",
      "args": ["-m", "conversation_ingestion_mcp.main"],
      "env": {}
    }
  }
}
```

### MCP Tools

**Navigation:**
- `set_conversation(name)` - Switch conversations
- `show_pairs(start, end)` - Display range
- `next_pair()` - Show next unprocessed
- `status()` - Current state

**Tagging:**
- `tag_pair(index, tag)` - Tag from enum
- `tag_range(start, end, tag)` - Tag range of pairs
- `batch_tag_operations(operations)` - Batch tag operations
- `add_tag(tag_name)` - Extend enum
- `list_tags()` - Show all tags

**Verification:**
- `get_meta_tags()` - Show authoritative meta-tags (layer/state/source)
- `get_framework_tags()` - Show framework/topic tags
- `verify_orphaned_pairs(conversation_name)` - Check for pairs with evolving/definition but no framework tags

**Processing:**
- `inject_pair(index)` - Mark processed, increment
- `bundle_tagged(tag, output_name)` - Bundle single tag
- `bundle_multi_tag(tags, output_name)` - Bundle multiple tags

**Framework Extraction:**
- `add_or_update_emergent_framework(...)` - Add/update framework definitions
- `read_current_framework_def(framework, all)` - Read framework definitions
- `get_instructions()` - Get complete workflow instructions

## Workflow

```
Conversations → IO Pairs → Tag + Bundle → Documents → CartON Concepts → Discord
```

## State Persistence

State file: `/tmp/conversation_ingestion_openai_paiab/state.json`

Tracks:
- Current conversation
- Current index
- Tag enum
- Tagged pairs
- Injected pairs
- Conversation priority

## License

GNOSYS Personal Builder License (GPBL) v1.0
