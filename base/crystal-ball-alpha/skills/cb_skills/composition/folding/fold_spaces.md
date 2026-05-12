# Fold Spaces

> Compose multiple spaces into a higher-order space where each node IS a space

## When to use
You have N individual spaces that belong to a logical group. You want to create an Order N+1 space.

## Process

1. **Create the group space**:
   ```
   crystal_ball(cmd: "create_space", body: { name: "RamsayLondonGroup" })
   ```

2. **Add nodes whose labels match existing space names**:
   ```
   crystal_ball(cmd: "add_point", body: {
     space: "RamsayLondonGroup",
     parentId: "root",
     label: "GordonRamsayRestaurant"    ← same name as the space
   })
   crystal_ball(cmd: "add_point", body: {
     space: "RamsayLondonGroup",
     parentId: "root",
     label: "BreadStreetLondon"
   })
   ```

3. **The fold**: Each node in the group space *represents* an entire space.
   When you `bloom` into that node, you enter the referenced space.

## Key facts
- The label matching is the link — if a node label matches a space name, it's a fold point
- You can fold N times: spaces → groups → empire → meta-empire → governance
- Each fold adds +1 to the total Order
- You can mix fold-nodes with regular nodes (e.g., Television_Division alongside RamsayLondonGroup)

## The hierarchy pattern
```
Order 1: Individual spaces (GordonRamsayRestaurant)
Order 2: Groups of spaces (RamsayLondonGroup)  ← FOLD 1
Order 3: Groups of groups (RamsayCulinaryEmpire)  ← FOLD 2
Order 4: Pattern of empires (CategoryKing)  ← FOLD 3
Order N: Keep going...
```
