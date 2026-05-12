# Crystal Ball — Bug Tracker

> Last updated: 2026-02-22
> Status: CRITICAL — foundational architecture broken

---

## ROOT CAUSE ANALYSIS — The Flattening Cascade

The V2 rewrite of `index.ts` changed the base data model without updating the layers above it. This triggered a cascade where each layer was silently abandoned or worked around, accumulating compensatory complexity in the wrong places.

### The Chain of Failure

```
1. V2 rewrites index.ts (base)
   - subspace: Space object → producedSpace: string
   - Character-by-character coordinate parser → parseInt on whole segments
   - 8/88/9 token mechanics DELETED
   ↓
2. homoiconic.ts (meta layer) BREAKS
   - All subspace references now type-error (string ≠ Space)
   - evalSpace, quote, apply — all broken
   - Nobody notices because nothing calls it
   ↓
3. engine.ts written to call index.ts DIRECTLY
   - Bypasses homoiconic entirely
   - Ad-hoc string parsing in cb() becomes the de facto interpreter
   - No meta-circular evaluation, no quote/eval semantics
   ↓
4. MCP compensates for missing interpreter
   - Builds thick switchboard to translate commands
   - MCP becomes an interpreter layer (wrong place for that)
   - Parameter name mismatches accumulate (BUG-001 through BUG-006, now stale)
   ↓
5. mine.ts built on broken foundation
   - Reads from attributes Map (should not exist)
   - Does Cartesian product of attribute values
   - Has no relationship to coordinate mechanics
   ↓
6. Frontend visualizes the WRONG data model
   - Shows raw CBNode objects, not homoiconic Spaces
   - No coordinate token visualization (8/88/9 don't exist in the data)
   ↓
7. Last session: MCP switchboard removed (correct instinct)
   - Made MCP a "dumb pipe" — right idea
   - But the real interpreter (homoiconic) is still dead
   - Treated the symptom, not the disease
```

---

## ACTIVE BUGS

### BUG-A: engine.ts bypasses homoiconic.ts

**Severity:** 🔴 CRITICAL — Architectural violation
**Status:** Open

The engine calls `index.ts` directly instead of going through `homoiconic.ts`. This means:
- No `evalSpace`, `quote`, `apply` — the core homoiconic primitives
- No meta-circular evaluation
- The engine is a flat interpreter, not a space-aware one
- Every value flowing through the system is raw CBNode data, not Spaces

**Correct architecture:**
```
engine.ts → homoiconic.ts → index.ts
```

**Current (broken) architecture:**
```
engine.ts → index.ts  (homoiconic.ts is dead code)
```

---

### BUG-B: `attributes` Map on CBNode duplicates children

**Severity:** 🔴 CRITICAL — Ontological error
**Status:** Open

`CBNode` has both `children: NodeId[]` and `attributes: Map<string, Attribute>`. These are the same concept — children ARE the spectrum values / attributes of the parent node. The separate `attributes` Map:
- Is invisible to coordinate resolution
- Creates a parallel unaddressable data structure
- Is what `instantiate()` and `mine.ts` read from (wrong)

**Fix:** Remove `attributes` Map. Children are the spectrum.

---

### BUG-C: `scry` does not use token-based coordinate parsing

**Severity:** 🔴 CRITICAL
**Status:** Partially fixed

`parseCoordinate` now correctly produces tokens (select, superposition, drill, close_drill) via character-by-character parsing with 0/1-7/8/88/9 mechanics.

BUT `scry()` still reads `parsed.segments` (the backward-compat flat array) instead of `parsed.levels` (the token stream). This means:
- 8 (drill into subspace) is ignored
- 88 (close drill) is ignored
- 9 (wrap/+7) works only because the backward-compat `segments` array resolves wrap to the final value
- Multi-token-per-level coordinates are flattened to a single primary selection

**Fix:** Rewrite `scry.traverse()` to walk the token stream in `parsed.levels`.

---

### BUG-D: `instantiate()` reads from broken `attributes` Map

**Severity:** 🟠 High
**Status:** Open

`instantiate()` collects `SpectrumSlot` objects from `resolved.attributes` — the broken parallel data structure. It should traverse the child tree and understand each child as a spectrum value.

**Fix:** Depends on BUG-B (remove attributes Map first).

---

### BUG-E: `mine.ts` does Cartesian product instead of coordinate path enumeration

**Severity:** 🟠 High
**Status:** Open

`computeMinePlane` calls `instantiate()` which reads from `attributes` Map and computes a Cartesian product of string values. This has no relationship to the coordinate mechanics.

Mine should enumerate **valid coordinate paths** — sequences of digits that form legal traversals through the space given the 8/88/9 notation. The "configuration space" is the set of valid coordinates, not attribute value combinations.

**Fix:** Complete rewrite after BUG-B and BUG-C are resolved.

---

### BUG-F: `homoiconic.ts` has 9 type errors

**Severity:** 🔴 CRITICAL
**Status:** Open

All 9 errors are the same root cause: `producedSpace` is a `string` (space name for registry lookup) but `homoiconic.ts` was written when `subspace` was an inline `Space` object. Every reference to `.producedSpace.name`, `.producedSpace.nodes`, or passing `producedSpace` as a `Space` argument fails.

**Fix:** Either revert `producedSpace` to an inline Space object (restoring V1 semantics) or update homoiconic.ts to accept a Registry and resolve names. The former is simpler and preserves layering.

---

### BUG-G: `producedSpace: string` breaks layering

**Severity:** 🟠 High
**Status:** Open

In V1, `subspace` was an inline `CrystalBall` object — a Space CONTAINING the subspace data. In V2, `producedSpace` is a string name that requires a `Registry` to resolve. This means:
- Every function that touches subspaces needs a `Registry` parameter
- The homoiconic layer can't follow subspace references without a registry
- The base layer is no longer self-contained — it depends on an external lookup

**Fix:** Revert to inline subspace objects or make Registry a first-class part of the base types.

---

### ~~BUG-H: Bloom ID collisions (from BUG-007)~~

**Severity:** N/A
**Status:** ✅ Already fixed in V2

V2 bloom creates Spaces (not child nodes). `addNode` uses `parent.children.length` for IDs. No collision possible.

---

### BUG-I: Dashboard activity page type error

**Severity:** 🟢 Low
**Status:** Open

`app/(dashboard)/dashboard/activity/page.tsx` — `Record<ActivityType, LucideIcon>` is missing keys: `CREATE_API_KEY`, `REVOKE_API_KEY`, `CREATE_SPACE`, `DELETE_SPACE`, `SCRY_SPACE`. This is a SaaS-layer issue, not engine.

---

## STALE BUGS (from old architecture)

The following bugs referenced `web/server.ts` which no longer exists. The MCP is now a dumb pipe to `cb()` via `POST /api/cb`. These are preserved for historical record only.

- ~~BUG-001: add_point ignores parent_coordinate~~ (stale — old parameter routing)
- ~~BUG-002: bloom label → slotLabel mismatch~~ (stale)
- ~~BUG-003: add_attribute coordinate → nodeId mismatch~~ (stale)
- ~~BUG-004: resolve returns 404~~ (stale)
- ~~BUG-005: add_attribute default not stored~~ (stale)
- ~~BUG-006: scry included → includeNodeIds mismatch~~ (stale)
- ~~BUG-008: bloom design issue~~ (retracted — was a misunderstanding)
