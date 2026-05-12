# Spectrum Design Patterns

> Common patterns for designing attribute spectra

## When to use
You need to add attributes to nodes and want well-designed spectra.

## Common patterns

### Binary Toggle
```json
{ "name": "active", "spectrum": ["off", "on"], "default": "on" }
```

### Quality Scale
```json
{ "name": "quality", "spectrum": ["poor", "acceptable", "good", "excellent", "world_class"], "default": "good" }
```

### Intensity
```json
{ "name": "heat_intensity", "spectrum": ["mild", "medium", "hot", "fiery", "inferno"], "default": "medium" }
```

### Growth Mode
```json
{ "name": "expansion_mode", "spectrum": ["conservative", "organic", "franchise", "aggressive", "global_domination"], "default": "organic" }
```

### Count Scale (non-linear)
```json
{ "name": "total_venues", "spectrum": ["1", "3", "5", "12", "50", "200"], "default": "3" }
```

### Maturity
```json
{ "name": "maturity", "spectrum": ["concept", "prototype", "mvp", "growth", "mature", "legacy"], "default": "concept" }
```

## Design rules
1. **Ordered**: Spectra should go from least to most (small→big, bad→good, few→many)
2. **5-7 values**: Enough granularity without being unwieldy
3. **Meaningful defaults**: The default is the "ground state" — the most common/expected value
4. **Domain-appropriate vocabulary**: Use terms the domain actually uses
