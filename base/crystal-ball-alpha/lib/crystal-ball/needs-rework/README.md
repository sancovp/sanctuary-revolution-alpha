# needs-rework/

These demo files were moved here because they depend on `ReifyResult.signature`
and `ReifyResult.analysis` — properties that were removed when attributes were
eliminated from the DAG (Phase 1 of the homoiconic rewrite).

## What broke

`ReifyResult` (in `reify.ts`) used to have:
```ts
interface ReifyResult {
    kernel: KernelSpace;
    signature: FoundationSignature;  // ← REMOVED
    analysis: SpaceAnalysis;          // ← REMOVED
    slotSignature: SpaceSlotSignature;
    level: number;
}
```

Now it only has `kernel`, `slotSignature`, and `level`. The old `signature`
and `analysis` fields came from `kernel-function.ts` and were attribute-aware.

## Files

| File | Errors | What it tests |
|------|--------|---------------|
| `demo-attractor-tests.ts` | 19 | Attractor convergence via repeated reification. Accesses `result.signature` and `result.analysis` for convergence checking. |
| `demo-tower.ts` | 17 | Futamura tower (reify → reify → fixed point). Accesses `result.signature` for each tower level. |

## To fix

Replace `result.signature` / `result.analysis` references with
`result.slotSignature` equivalents. The `SpaceSlotSignature` from `kernel-v2.ts`
has per-slot orbit decomposition that serves the same purpose.

## Working examples that show the current architecture

All of these compile and run correctly after the homoiconic rewrite:

### Core regression suite
- **`test-regression.ts`** — 72/72 tests passing. Covers:
  - `parseCoordinate` (token stream parsing)
  - `scry` (basic + multi-level coordinate resolution)
  - `mine` / `computeMinePlane` (path enumeration, empty spaces, heat, drill)
  - `encodeDot` / `decodeDot` / `coordToReal` (round-trip encoding)
  - `mine()` / `declareMineSpace` / `projectKernel` (kernel plane projection)
  - Lock enforcement (≥2 children or terminal)

### Demo files (working)
- **`demo-foundation.ts`** — Foundation signature + symmetry breaking detection
- **`demo-kernel-hs.ts`** — RKHS kernel function on spaces with children-as-spectrum
- **`demo-kernel-v2.ts`** — Tensor product kernel (per-slot orbits, full space signature)
- **`demo-kernelspace.ts`** — KernelSpace architecture: create, lock, sub-kernels, full coordinates
- **`demo-futamura.ts`** — Futamura projection (grammar → parser → scry → encoder → locker → miner)
- **`demo-funnel-kernel.ts`** — Business funnel × tweet kernel with multi-kernel mine projection
- **`demo-tweet-kernel.ts`** — Deep tweet kernel: 7 slots × 3-4 subtypes × leaf variants → mine
- **`demo-mine-comprehensive.ts`** — 11-test exhaustive mine validation (empty, single, deep, wide, mixed, multi-kernel, idempotent, adjacent depth, round-trip, uniqueness, encoding markers)
- **`demo-fractran.ts`** — Fractran prime encoding (pre-existing minor type issue, unrelated)
- **`demo-superposition.ts`** — Superposition resolution

### Key architectural change
**Children ARE the spectrum.** No more `addAttribute()`. What used to be
`addAttribute(space, node.id, 'mood', ['casual', 'pro', 'sentimental'])` is now
just children: `addNode(space, node.id, 'Casual')`, `addNode(space, node.id, 'Professional')`, etc.

The homoiconic layer (`homoiconic.ts`) provides:
- `cbEval(coord)` → resolve coordinate against DAG (wraps `scry`)
- `cbQuote(node)` → inverse: node → coordinate
- `cbApply(a, b)` → compose coordinates
- `cbWalk()` → enumerate all valid coordinates

Engine commands: `eval <coord>` and `quote <nodeId>` expose these via MCP.
