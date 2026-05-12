# Resolve Coordinates

> Collapse a superposition to get concrete attribute values

## When to use
You've scried a coordinate and now want to resolve the attributes at that position.

## Process

1. **Resolve a node**:
   ```
   crystal_ball(cmd: "resolve", body: {
     space: "MySpace",
     coordinate: "root.0"
   })
   ```

2. **Result**: The node's attributes are collapsed from spectra to concrete values.

## Key facts
- Resolve acts on attributes (spectra → values)
- Nodes without attributes still resolve — they just return structural info
- Resolution is the "measurement" step in the quantum metaphor
- Scry = superposition (what's there?), Resolve = measurement (what's the value?)
