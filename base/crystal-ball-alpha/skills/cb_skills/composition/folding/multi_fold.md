# Multi-Fold Composition

> Create Order 3+ systems by folding spaces that already contain folded spaces

## When to use
You have group-level spaces and want to compose them into an empire or meta-structure.

## Process

1. **Verify your fold-1 spaces exist** (groups containing instance spaces):
   ```
   crystal_ball(cmd: "list_spaces")
   ```

2. **Create the empire space**:
   ```
   crystal_ball(cmd: "create_space", body: { name: "RamsayCulinaryEmpire" })
   ```

3. **Add group-spaces as nodes** (plus any non-fold strategic nodes):
   ```
   add_point → RamsayLondonGroup       ← Fold 1 space
   add_point → RamsayUSGroup           ← Fold 1 space
   add_point → RamsayMiddleEastGroup   ← Fold 1 space
   add_point → Television_Division     ← Regular node
   add_point → Product_Lines           ← Regular node
   add_point → Global_Strategy         ← Regular node
   ```

4. **Add empire-level attributes**:
   ```
   add_attribute → total_venues: [3, 5, 8, 12, 20]
   add_attribute → expansion_mode: [conservative, organic, franchise, aggressive]
   ```

## The resulting structure
```
Empire (Order 3)
├── Group A (Order 2) → [Space1 (O1), Space2 (O1), Space3 (O1)]
├── Group B (Order 2) → [Space4 (O1), Space5 (O1)]
├── Group C (Order 2) → [Space6 (O1)]
├── Strategic_Node_1
└── Strategic_Node_2
```

Total reachable nodes: all nodes in all spaces at all levels.
