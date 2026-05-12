# Cross-Space Scry

> Query across fold boundaries to get composed coordinates spanning multiple spaces

## When to use
You want a single coordinate that addresses structure across the fold hierarchy — e.g., querying a specific kitchen station inside a restaurant inside a group inside an empire.

## Process

1. **Scry the empire level**:
   ```
   scry(RamsayCulinaryEmpire, root, [root.0])  → "1" (London Group)
   ```

2. **Scry the group level**:
   ```
   scry(RamsayLondonGroup, root, [root.0])  → "1" (GordonRamsayRestaurant)
   ```

3. **Scry the restaurant level**:
   ```
   scry(GordonRamsayRestaurant, root, [root.0, root.0.0])  → "1.1" (Kitchen → Grill)
   ```

4. **The full cross-space address**: `Empire.Group.Restaurant.Kitchen.Grill`
   = `1.1.1.1` across 4 fold boundaries

## Key facts
- Cross-space scry = chaining scries across bloom boundaries
- The full address is the concatenation of per-space coordinates separated by fold-dots
- This is fractal addressing — each dot is a fold boundary
- An agent can address ANY node in the entire hierarchy with one coordinate string
