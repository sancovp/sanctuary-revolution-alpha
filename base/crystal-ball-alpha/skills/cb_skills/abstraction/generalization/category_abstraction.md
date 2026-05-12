# Category Abstraction

> Generalize from a domain-specific solution space to the universal pattern of category dominance

## When to use
You have a solution space for one domain (restaurants) and want to abstract to the pattern that works for ANY category (tech, media, finance, etc).

## Process

1. **Create the CategoryKing space**:
   ```
   crystal_ball(cmd: "create_space", body: { name: "CategoryKing" })
   ```

2. **Add universal dominance pillars**:
   ```
   add_point → Category_Definition      ← What category are you king of?
   add_point → Moat_Architecture         ← What makes you defensible?
   add_point → Flywheel_Dynamics         ← What self-reinforcing loops exist?
   add_point → Network_Effects           ← Do more users = more value?
   add_point → Instance_Empires          ← Container for domain-specific empires
   ```

3. **Nest domain solution spaces under Instance_Empires**:
   ```
   add_point(parent: "Instance_Empires") → RestaurantEmpireSolutionSpace
   add_point(parent: "Instance_Empires") → TechEmpireSolutionSpace
   add_point(parent: "Instance_Empires") → MediaEmpireSolutionSpace
   ```

## The abstraction move
- RestaurantEmpire.Unit_Economics → CategoryKing.Flywheel_Dynamics
- RestaurantEmpire.Brand_Architecture → CategoryKing.Moat_Architecture
- RestaurantEmpire.Replication_Model → CategoryKing.Network_Effects

Same structure, different vocabulary. The pattern IS the same.
