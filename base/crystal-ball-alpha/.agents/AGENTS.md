# Crystal Ball Project Rules

## COORDINATE MECHANICS — THE FOUNDATION OF CRYSTAL BALL

**This is how coordinates work. Every digit matters. There is no `parseInt`.**

Coordinates are parsed CHARACTER BY CHARACTER within each dot-separated level.

### Digit Semantics

| Digit | Meaning |
|-------|---------|
| **0** | **SUPERPOSITION.** The spectrum is NOT chosen. |
| **1-7** | **EXACT SELECTION** of the primacy of a childspace from a parent node. This IS the parent's property spectrum being selected. You CANNOT define a node with a composite attribute set unless you have defined a composite space of other spaces that would allow that. |
| **8** | **DRILL.** Opens the subspace of the currently selected slot at whatever primacy was selected. Chain 8s to drill deeper into nested subspaces. |
| **88** | **CLOSE DRILL.** Exits back out of the drilled subspace. 88 is invalid without a preceding 8 that opened a drill. 8→8 implies 8→0→8 (drill into superposition) which is invalid — you cannot drill a superposition. |
| **9** | **WRAP.** Adds 7 to the selection. Extends range beyond 7 children. |

### Examples

- `1.991` = At level 1 select child 1; at slot 1: 9(+7) + 9(+7) + 1 = **15th primacy option**
- `1.1238123...88` = Select children, DRILL (8) into subspace, work inside, CLOSE DRILL (88), continue at parent level
- `0` = Superposition — nothing selected, full spectrum open

### Symmetry Rule

**A node is a superposition. Its children are its attributes, denoted as a spectrum of selections forming a subspace relative to it via drilldown slots.**

- Adding a node IS adding a spectrum value from the parent's perspective
- `add_point` and `add_attribute` are THE SAME OPERATION — there is only `add`
- The `attributes` Map on CBNode is an IMPLEMENTATION BUG — it duplicates children
- See `SYMMETRY.md` for the full bra-ket duality explanation

## ENGINE LAYER ARCHITECTURE — FROZEN BELOW THE INTERPRETER

```
engine.ts       ← THE INTERPRETER. Only this changes for features.
    ↓ calls
homoiconic.ts   ← META-LAYER. Stable. NEVER modify without refactoring everything above.
    ↓ calls
index.ts        ← BASE TYPES & OPS. Stable. NEVER modify without refactoring everything above.
```

**index.ts and homoiconic.ts are FROZEN LAYERS.** If you need to change them, you MUST refactor every module that depends on them. Changing the base without updating all consumers DESTROYS THE APPLICATION.

The engine (engine.ts) is the ONLY file that should change for new features. It calls through homoiconic into base. It never calls base directly (that bypasses the meta layer).

## ABSOLUTE RULES

### 1. TEST THROUGH THE MCP, NOT CURL/PYTHON/DIRECT HTTP
- Use `mcp_crystal-ball_crystal_ball`. That is the interface.
- If a command doesn't exist in the MCP, the fallback pass-through handles it automatically.
- NEVER bypass the MCP with curl or direct API calls.

### 2. Architecture Data Flow
```
MCP → SaaS (POST /api/cb) → Engine → Frontend (SSE)
```
- MCP is a dumb pipe. It constructs text strings and POSTs them.
- The SaaS does everything internally.
- The frontend only displays. Data flows: MCP → SaaS → Frontend. Never MCP → Frontend.

### 3. DESIGN.md is the Single Canonical Design
- DESIGN.md is the user's words only. Do not add decisions without the user saying them.
- Mark aspirational features as `ASPIRATIONAL:`.
- Update DESIGN.md when architecture changes. No exceptions.

### 4. Do Not Add Complexity
- Ask before adding new protocols, servers, or connection types.

### 5. Do Not Start Extra Dev Servers
- Check if one is running first. Multiple Vite servers exhaust WebGL on macOS.

### 6. ENGINE MUST BE GREEN — ZERO TYPE ERRORS
- Run `npx tsc --noEmit` before starting ANY feature work.
- If the engine has errors, FIX THEM FIRST. No exceptions.
- Do not build features on top of a broken engine.
- After fixing, run again to confirm zero errors.

### 7. REGRESSION TESTS REQUIRED
- The engine must have test coverage for every coordinate mechanic (0, 1-7, 8, 88, 9).
- Tests must pass before any feature work is built on top.
- If a feature touches the engine, add tests for the changed behavior.

### 8. The MCP Commands (Flow-Level Only)
`list`, `scry`, `bloom`, `add`, `lock`, `freeze`, `mine`, `kernel`. Nothing else needs to exist.

### 9. READ BUGS.md BEFORE ANY WORK
- `CRYSTAL_BALL_BUGS.md` documents the current broken state and root cause chain.
- Do NOT build features until the active bugs are resolved.
- BUG-A (engine bypasses homoiconic) is the root issue — everything follows from it.

## ⚠️ KNOWN IMPLEMENTATION BUGS

See `CRYSTAL_BALL_BUGS.md` for full details. Summary:

1. **BUG-A:** `engine.ts` bypasses `homoiconic.ts` — calls `index.ts` directly (ROOT CAUSE)
2. **BUG-B:** `attributes` Map on CBNode duplicates children
3. **BUG-C:** `scry` doesn't use token-based coordinate parsing (8/88/9 ignored)
4. **BUG-D:** `instantiate()` reads from broken `attributes` Map
5. **BUG-E:** `mine.ts` does Cartesian product instead of coordinate path enumeration
6. **BUG-F:** `homoiconic.ts` has 9 type errors (producedSpace string ≠ Space object)
7. **BUG-G:** `producedSpace: string` breaks layering (was inline Space object in V1)
8. **BUG-H:** Bloom ID collisions (slotCount vs children.length)
