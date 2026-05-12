# Add Attributes

> Define quality spectra on nodes to enable resolution

## When to use
A node exists but lacks measurable dimensions. You want to track how it varies.

## Process

1. **Identify the spectrum** — what range of values does this quality span?
   ```
   crystal_ball(cmd: "add_attribute", body: {
     space: "MySpace",
     coordinate: "root.0",
     name: "heat_intensity",
     spectrum: ["low", "medium", "high", "extreme", "inferno"],
     default: "high"
   })
   ```

2. **Common spectrum patterns**:
   - Binary: `["off", "on"]`
   - Quality: `["poor", "acceptable", "good", "excellent", "world_class"]`
   - Scale: `["1", "2", "3", "4", "5"]`
   - Mode: `["conservative", "organic", "aggressive", "global_domination"]`
   - Count: `["0", "3", "5", "8", "12", "20"]`

3. **Multiple attributes per node** are fine:
   ```
   add_attribute → total_venues: [3, 5, 8, 12, 20]
   add_attribute → michelin_stars: [0, 1, 2, 3, 7]
   ```

## Key facts
- Attributes have a `spectrum` (ordered list of possible values) and a `default`
- The default must be one of the spectrum values
- Attributes are what `resolve` acts on — it collapses the superposition
- Spectra should be ordered from least to most (intensity, count, quality)
