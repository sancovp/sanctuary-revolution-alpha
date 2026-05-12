# Scry Superposition

> Query a space by including multiple nodes in a single coordinate — the superposition

## When to use
You want to see the combined state of multiple nodes at once.

## Process

1. **Full space scry** — include all top-level nodes:
   ```
   crystal_ball(cmd: "scry", body: {
     space: "RamsayCulinaryEmpire",
     coordinate: "root",
     included: ["root.0", "root.1", "root.2", "root.3", "root.4", "root.5"]
   })
   ```

2. **Result**: A `composedCoordinate` like `"123456"` — the superposition of all included nodes.

3. **Selective scry** — include only some nodes:
   ```
   crystal_ball(cmd: "scry", body: {
     space: "RamsayCulinaryEmpire",
     coordinate: "root",
     included: ["root.0", "root.1"]       ← just London + US groups
   })
   ```
   → composedCoordinate: `"12"`

4. **Deep scry** — include nodes at different depths:
   ```
   included: ["root.0", "root.0.0", "root.0.1", "root.1"]
   ```
   → composedCoordinate: `"1.12.2"` (dot separates order boundaries)

## Key facts
- `composedCoordinate` concatenates pathDigits of included nodes
- Dots in the coordinate mark transitions between orders (depth levels)
- The coordinate is the *address* of the superposition
- Including all nodes = full superposition of the space
- Including a subset = partial/targeted query
