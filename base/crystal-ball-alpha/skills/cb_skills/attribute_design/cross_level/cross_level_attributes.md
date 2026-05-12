# Cross-Level Attributes

> Designing attributes that make sense across fold boundaries

## When to use
You have a multi-fold hierarchy and want attributes that are meaningful at each level — e.g., "total_venues" means different things at restaurant vs. group vs. empire level.

## Process

1. **Same attribute name, different scale**:
   ```
   # Restaurant level
   add_attribute(HellsKitchenNYC, "seats", ["20", "50", "100", "200", "400"])

   # Group level
   add_attribute(RamsayUSGroup, "total_seats", ["100", "500", "1000", "5000"])

   # Empire level
   add_attribute(RamsayCulinaryEmpire, "global_seats", ["1000", "5000", "20000", "100000"])
   ```

2. **Aggregation attributes** — values at higher levels summarize lower levels:
   ```
   # Each restaurant: michelin_stars [0, 1, 2, 3]
   # Group level: total_stars [0, 1, 3, 5, 7]
   # Empire level: total_stars [0, 3, 7, 12, 20]
   ```

3. **Mode attributes** — qualitative across levels:
   ```
   # Restaurant: service_style [casual, fine_dining, tasting_menu]
   # Group: dominant_style [mixed, casual_focus, fine_dining_focus]
   # Empire: brand_positioning [casual, premium, luxury, ultra_luxury]
   ```

## Key insight
Attributes at higher fold levels are NOT the same as at lower levels — they're *about* the collection, not about individual items.
