---
description: How to test Crystal Ball features
---

# Testing Crystal Ball Features

## Two test systems

### 1. Core Regression Suite (unit tests)
Run the regression test suite directly:

// turbo
```bash
npx tsx lib/crystal-ball/test-regression.ts
```

This tests:
- parseCoordinate (token streams, wrap, drill)
- scry (basic, multi-level, out-of-range)
- mine (paths, empty, heat, drill, no-strata)
- dot encoding (encode/decode roundtrip, coordToReal, fullCoordinate)
- mine() plane (declare, project kernel, identity on diagonal)
- multi-kernel projection (persistent plane, two kernels)

Expected: **72 passed, 0 failed**

### 2. MCP Integration Tests (FLOW pipeline)

**RULE: ALL interactive testing goes through the MCP tool.**
**NEVER use curl, python, or direct HTTP.**

Use `mcp_crystal-ball_crystal_ball` with a single string input:

#### FLOW Pipeline Test

```
# 1. List spaces
list

# 2. Create a new space → enters BLOOM phase
create MySpace

# 3. Add children (spectrum expansion) — still in BLOOM
Hook
Claim
Evidence
CTA

# 4. Finish bloom → transitions to FILL phase
done

# 5. Navigate to a slot in FILL phase
MySpace 1

# 6. Add sub-spectrum to slot
Question
Statistic
Provocative

# 7. Lock a node
lock

# 8. Mine the space
MySpace mine

# 9. View mineSpace
MySpace mine view
```

#### Phase Tracking Verification
Each response should include:
- `phase` field: one of `idle`, `create`, `bloom`, `fill`, `lock`, `mine`, `compose`
- `[FLOW PHASE]` prompt in the view text
- Phase-appropriate guidance

Expected transitions:
```
idle → create → bloom → fill → lock/mine → compose → bloom → ...
                  ↑ "done"    ↑ "lock"     ↑ "done"
```

#### Quick Smoke Test (copy-paste sequence)
```
create SmokeTest
Alpha
Beta
done
SmokeTest 1
Sub1
Sub2
lock
SmokeTest mine
```

### 3. Frontend Verification
Use Playwright MCP's `browser_snapshot` to verify the viz reflects changes.
Do NOT launch new browser windows — use the existing Antigravity browser tab.

## Key Commands Reference

| Command | What it does |
|---------|-------------|
| `list` | Show all spaces |
| `create Name` | Create new space → bloom phase |
| `Label` | Add child node (in bloom/fill) |
| `SpaceName N` | Navigate to coordinate N |
| `done` | Transition bloom→fill or mine→idle |
| `lock` | Lock current node |
| `freeze` | Freeze current node (immutable) |
| `SpaceName mine` | Mine the space |
| `SpaceName mine view` | View persisted mineSpace |
| `exit` / `..` | Go up / exit current space |
| `@nodeId` | Navigate to node by ID |
