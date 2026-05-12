# Add Pillars

> Define the 4-7 top-level structural categories of a space

## When to use
You have a fresh space and need to decompose it into its natural dimensions.

## Process

1. **Identify pillars** — Ask: "What are the 4-7 irreducible aspects of this domain?"
   - Restaurant: Kitchen, Experience, Brand, Team, Finance, Ambiance
   - Company: Product, Engineering, Sales, Operations, Culture
   - Concept: Definition, Properties, Relationships, Applications

2. **Add them as children of root**:
   ```
   crystal_ball(cmd: "add_point", body: { space: "MySpace", parentId: "root", label: "Kitchen" })
   crystal_ball(cmd: "add_point", body: { space: "MySpace", parentId: "root", label: "Experience" })
   crystal_ball(cmd: "add_point", body: { space: "MySpace", parentId: "root", label: "Brand" })
   ```

3. **Result**: Nodes at `root.0`, `root.1`, `root.2`, etc.

## Key facts
- Pillars are Order 1 nodes (depth 1 from root)
- 4-7 pillars is the sweet spot — fewer means under-decomposed, more means overlapping
- Pillar labels should be PascalCase or Snake_Case
- The coordinate digit for pillar N (0-indexed) is N+1

## Anti-patterns
- ❌ Too few pillars (< 3): You're not decomposing enough
- ❌ Too many pillars (> 8): Some are probably sub-nodes of others
- ❌ Overlapping pillars: "Menu" and "Food" — pick one, nest the other
