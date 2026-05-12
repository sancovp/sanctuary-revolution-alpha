# Create a Space

> Initialize a new ontological space from a domain seed

## When to use
You have a domain (restaurant, company, product, concept) and want to model it as a navigable space.

## Process

1. **Name it** — PascalCase, descriptive. The name IS the root node label.
   ```
   crystal_ball(cmd: "create_space", body: { name: "GordonRamsayRestaurant" })
   ```

2. **Verify** — Check it exists:
   ```
   crystal_ball(cmd: "list_spaces")
   ```

## Key facts
- The root node is created automatically with `id: "root"`
- The root label matches the space name
- Spaces are independent — no cross-space relationships by default
- Space names must be unique across the system

## Output
A space with a single root node, ready for pillars.
