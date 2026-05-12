# Extract Solution Space

> Abstract from a concrete instance to the pattern that makes it work

## When to use
You have a working concrete space (e.g., GordonRamsayRestaurant) and want to extract the abstract pattern — the "solution space" that any similar instance would follow.

## Process

1. **Study the concrete instance** — identify what's structural vs. specific:
   - Structural: Kitchen, Experience, Brand, Team (these generalize)
   - Specific: Gordon_Ramsay_Name, Chelsea_Location (these don't)

2. **Create the solution space**:
   ```
   crystal_ball(cmd: "create_space", body: { name: "RestaurantEmpireSolutionSpace" })
   ```

3. **Add the abstract pillars** — the pattern, not the instance:
   ```
   add_point → Unit_Economics          (not "£2M_Revenue")
   add_point → Replication_Model       (not "3_Locations")
   add_point → Brand_Architecture      (not "Gordon_Ramsay_Brand")
   add_point → Talent_Pipeline         (not "Chef_Training_Program")
   add_point → Geographic_Strategy     (not "London_NYC_Dubai")
   ```

4. **Add an Instance_Spaces node** — this is where concrete instances live:
   ```
   add_point → Instance_Spaces
   ```

## The key move
Replace **nouns** (specific things) with **functions** (what they do).
- "Gordon Ramsay" → Brand_Architecture
- "Hell's Kitchen NYC" → Geographic_Strategy.US_Market
- "Michelin stars" → Quality_Signal_Mechanism
