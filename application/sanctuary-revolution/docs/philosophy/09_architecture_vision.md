# Architecture Vision

## The Stack

```
Sanctuary Revolution (Electron app)
    │
    ├── VEC Platform (its own platform, accessible from SANCREV)
    │   └── Victory-Everything Chains as first-class entities
    │
    ├── paia-builder (PAIAB mini-game)
    │   └── Python library for building PAIAs
    │
    ├── cave-builder (CAVE mini-game)
    │   └── Python library for business systems
    │
    └── sanctum-builder (SANCTUM mini-game)
        └── Python library for life architecture
```

## Key Insight

VEC is **its own platform** - not just a data model inside sanctuary-revolution.

The Electron app is the container. VEC platform is where the chains live and operate.

## Current State (as of this session)

**Python libraries (backend):**
- `paia-builder` v0.8.0 - functional
- `sanctuary-revolution` v0.2.0 - VEC/MVS/SJ typed
- `cave-builder` v0.1.0 - stub
- `sanctum-builder` v0.1.0 - stub

**Frontend:**
- Electron app - not yet built
- VEC Platform - not yet built

## The Pattern

The Python libraries are the typed backend.
The Electron app is the player interface.
The VEC Platform is where chains actually run and propagate.

## VEC as Consensus Layer

**This is where everyone's PAIAs go for consensus verification - peer review.**

VEC is the external validation layer. When someone claims a tier, VEC is where the community verifies it.

### Tier Verification Through VEC

| Tier | Verification | Where |
|------|--------------|-------|
| COMMON | Exists | Local |
| UNCOMMON | Works correctly | Local testing |
| RARE | Battle-tested | Production use |
| EPIC | Used by others | **VEC peer review** |
| LEGENDARY | Generates revenue | **VEC proves this** |

**Levels really mean something inside VEC** because they're not self-reported - they're community verified.

### The Flow

```
You build PAIA locally (paia-builder)
    ↓
You claim tiers as you progress
    ↓
COMMON/UNCOMMON/RARE: local verification
    ↓
Submit to VEC for EPIC/LEGENDARY
    ↓
Peer review / consensus verification
    ↓
Tier is PROVEN, not just claimed
```

This is what makes the game REAL. The tiers have economic and social proof through VEC consensus.
