# OPERA MCP - Operadic Pattern Discovery

**Version:** 0.1.0
**Status:** v1 (Pattern viewing and promotion only)

OPERA MCP manages execution patterns discovered from Canopy work, enabling pattern reuse and workflow optimization.

## Architecture

### Two Pattern Types

1. **CanopyFlowPattern** (Quarantine)
   - Auto-detected from execution history
   - Unverified, awaiting human review
   - Stored in `opera_canopy_patterns` registry

2. **OperadicFlow** (Golden Library)
   - Human-verified production-ready patterns
   - Promoted from CanopyFlowPattern after review
   - Stored in `opera_operadic_flows` registry
   - Can spawn TreeKanban cards (future)

### Data Flow

```
User works on Canopy schedule
    ↓
Canopy auto-records to operadic_ledger/YYYY-MM-DD
    ↓
OPERA automation (OMNISANC) detects patterns
    ↓
CanopyFlowPatterns stored in quarantine
    ↓
Human reviews via OPERA MCP tools
    ↓
Promote to OperadicFlows (golden library)
    ↓
Future: Spawn TreeKanban cards with auto-tags
```

## MCP Tools (v1)

### Pattern Viewing

- `view_canopy_patterns(limit=50)` - View detected patterns in quarantine
- `view_operadic_flows(limit=50)` - View golden verified patterns
- `get_pattern_details(pattern_id, pattern_type)` - Get specific pattern details

### Pattern Promotion

- `promote_pattern(pattern_id, verified_by, notes)` - Promote CanopyFlowPattern → OperadicFlow

### Not Yet Implemented

- Search/goldenization tools (waiting for OMNISANC MCP review)
- Pattern detection automation (OMNISANC integration)
- TreeKanban card spawning

## Installation

```bash
cd /home/GOD/opera-mcp
pip install -e .
```

## Usage

Pattern detection happens automatically via OMNISANC automation. Use MCP tools to review and promote patterns:

```python
# View detected patterns
view_canopy_patterns()

# Get pattern details
get_pattern_details("pattern_xyz", "canopy")

# Promote to golden library
promote_pattern(
    pattern_id="pattern_xyz",
    verified_by="Isaac",
    notes="Verified OAuth implementation pattern"
)

# View golden library
view_operadic_flows()
```

## Next Steps

1. Review OMNISANC MCP patterns (flowchain, goldenization menu)
2. Add search/goldenization tools based on OMNISANC patterns
3. Implement OPERA automation for pattern detection
4. Integrate with OMNISANC enforcement
5. Enable TreeKanban card spawning from OperadicFlows

## Registry Structure

- `opera_canopy_patterns/` - Quarantine (detected patterns)
- `opera_operadic_flows/` - Golden library (verified patterns)
- `operadic_ledger/YYYY-MM-DD/` - Execution history (written by Canopy)
