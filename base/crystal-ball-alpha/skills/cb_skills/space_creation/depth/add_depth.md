# Add Depth

> Recursively decompose pillars into sub-nodes to create Order 2+ structure

## When to use
Your pillars exist but they're flat. You need internal structure.

## Process

1. **For each pillar**, ask: "What are the 2-5 components of this?"
   ```
   # Kitchen (root.0) → stations
   crystal_ball(cmd: "add_point", body: { space: "MySpace", parentId: "root.0", label: "Grill_Station" })
   crystal_ball(cmd: "add_point", body: { space: "MySpace", parentId: "root.0", label: "Prep_Line" })
   crystal_ball(cmd: "add_point", body: { space: "MySpace", parentId: "root.0", label: "Pastry_Section" })
   ```

2. **Go deeper if needed** — Order 3:
   ```
   # Grill_Station (root.0.0) → equipment
   crystal_ball(cmd: "add_point", body: { space: "MySpace", parentId: "root.0.0", label: "Charcoal_Grill" })
   ```

3. **Result**: Multi-order tree. Coordinates like `root.0.0.0`

## Key facts
- Each level of depth = +1 Order
- The `pathDigits` array shows the coordinate: `[1, 2, 3]` = pillar 1, child 2, grandchild 3
- Composed coordinate string concatenates: `123`
- Stop adding depth when nodes become atomic/leaf concepts

## Heuristic
- Order 1: Categories (Kitchen, Experience)
- Order 2: Components (Grill_Station, Cocktail_Bar)
- Order 3: Elements (Charcoal_Grill, Martini_Menu)
- Order 4+: Rare, but valid for deep domains
