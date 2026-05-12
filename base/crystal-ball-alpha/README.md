# Crystal Ball

A **homoiconic coordinate engine** where every valid path through a DAG maps to a unique real number in `[0, 1)`. Build structured solution spaces, lock them into kernels, and mine the configuration landscape.

## Core Concepts

**Spaces** are DAGs. Each node's children define its **spectrum** — the set of choices at that slot. A coordinate like `1.3.2` means: pick child 1, then child 3, then child 2.

**Children ARE the spectrum.** No separate attribute system — the tree structure itself encodes all configuration dimensions.

**Kernels** are lockable spaces. Once every non-terminal node has ≥2 children (a spectrum needs a high and a low), the kernel locks and becomes mineable.

**Mining** projects all valid coordinates onto a 2D plane where `x = coordToReal(coord)` and `y` is a kernel-level identity. Every point is a specific configuration you could generate from.

## Architecture

```
homoiconic.ts   ← The Crystal Ball Lisp (eval, quote, apply, walk)
    ↓
index.ts        ← Core: Space, CBNode, scry, lock, mine encoding
    ↓
engine.ts       ← MCP state machine (create → bloom → fill → lock → mine)
    ↓
mine.ts         ← MineSpace projection (multi-kernel planes)
```

### The Homoiconic Layer

Crystal Ball coordinates are S-expressions. The DAG is the data. Four primitives:

| Function | What it does |
|----------|-------------|
| `cbEval(coord)` | Resolve coordinate against DAG → node (wraps `scry`) |
| `cbQuote(node)` | Inverse: node → coordinate path |
| `cbApply(a, b)` | Compose two coordinates |
| `cbWalk()` | Enumerate all valid coordinates systematically |

### Encoding

Coordinates encode to reals via dot-replacement (`"."` → `"8988"`) and CB-encoded selections (`8–9` → `91`, `9–10` → `92`, etc.). This guarantees unique, collision-free real numbers for every path through the DAG.

## MCP Integration

The engine exposes Crystal Ball as an MCP tool (`crystal_ball`). The state machine flow:

```
list spaces → select space → bloom (add nodes) → fill slots → lock → mine
```

Commands: `eval <coord>`, `quote <nodeId>`, `lock`, `mine`, and the full space management suite.

## Running Tests

```bash
# Core regression suite (72 tests)
npx tsx lib/crystal-ball/test-regression.ts

# Comprehensive mine validation (11 tests)
npx tsx lib/crystal-ball/demo-mine-comprehensive.ts

# Type check
npx tsc --noEmit
```

## Demo Files

| File | What it demonstrates |
|------|---------------------|
| `demo-foundation.ts` | Foundation signature + symmetry breaking |
| `demo-kernel-hs.ts` | RKHS kernel function on spaces |
| `demo-kernel-v2.ts` | Tensor product kernel (per-slot orbits) |
| `demo-kernelspace.ts` | KernelSpace: create, lock, sub-kernels, full coordinates |
| `demo-futamura.ts` | Futamura projection chain |
| `demo-funnel-kernel.ts` | Business funnel × tweet kernel multi-projection |
| `demo-tweet-kernel.ts` | Deep 7-slot tweet kernel → mine |
| `demo-mine-comprehensive.ts` | Exhaustive mine + encoding validation |

See `needs-rework/` for demos awaiting ReifyResult interface update.

## Tech Stack

- **Runtime**: Next.js 15 + TypeScript
- **Database**: Postgres via Drizzle ORM
- **Frontend**: Three.js 3D visualization (separate `crystal-ball-viz` repo)
- **MCP**: Crystal Ball MCP server for LLM integration
- **Payments**: Stripe (SaaS scaffold)

## Dev Setup

```bash
npm install
npm run dev          # Next.js on :3000
```

The Crystal Ball MCP server runs alongside the Next.js app and is configured in your MCP client settings.
