# Bloom Navigation

> Enter the interior space of a node to navigate its sub-structure

## When to use
You're looking at a node that represents a deeper structure (either sub-nodes or a folded space) and want to go inside.

## Process

1. **Bloom into a node**:
   ```
   crystal_ball(cmd: "bloom", body: {
     space: "RamsayCulinaryEmpire",
     coordinate: "root.0"              ← RamsayLondonGroup node
   })
   ```

2. **Result**: You're now "inside" that node. If it maps to a space name, you enter that space.

3. **Navigate deeper** — bloom again to go another level:
   ```
   # Now inside RamsayLondonGroup, bloom into GordonRamsayRestaurant
   crystal_ball(cmd: "bloom", body: {
     space: "RamsayLondonGroup",
     coordinate: "root.0"
   })
   ```

## Key facts
- Bloom = zooming in to a node's interior
- If the node label matches a space name, bloom transitions to that space
- You can chain blooms: Empire → Group → Restaurant → Kitchen → Grill_Station
- This is how you traverse the fold hierarchy
