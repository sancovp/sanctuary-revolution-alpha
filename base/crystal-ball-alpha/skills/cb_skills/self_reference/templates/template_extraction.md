# Template Extraction

> Extract the abstract template from a concrete trajectory through the abstraction ladder

## When to use
You've completed a full trajectory (concrete → abstract → governance) and want to capture the SHAPE of that trajectory as a reusable template.

## Process

1. **Create the template space**:
   ```
   crystal_ball(cmd: "create_space", body: { name: "TrajectoryTemplate" })
   ```

2. **Add one node per step in the trajectory** — in order:
   ```
   add_point → Concrete_Instance            ← Step 1: Start with a thing
   add_point → Composition_Into_Groups      ← Step 2: Group instances
   add_point → Folding_Into_Empire          ← Step 3: Fold groups
   add_point → Solution_Space_Extraction    ← Step 4: Extract the pattern
   add_point → Category_Abstraction         ← Step 5: Generalize domain
   add_point → Meta_Composition             ← Step 6: Pattern of patterns
   add_point → Governance_Layer             ← Step 7: Oversight
   add_point → Self_Application             ← Step 8: Apply to itself ← 🔁
   ```

3. **Scry the template**:
   ```
   scry → composedCoordinate: "12345678"
   ```
   8 steps, one coordinate, the full trajectory in a single string.

## Key insight
The template IS the recipe for doing what you just did.
Any domain can instantiate this template:
- Healthcare: Hospital → Hospital_Group → HealthCorp → CategoryKing → ...
- Software: Module → Service → Platform → CategoryKing → ...
- Education: Course → Department → University → CategoryKing → ...

The template is domain-independent. The instances are domain-specific.
