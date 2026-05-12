# Get Space State

> Retrieve the full structure of a space for inspection

## When to use
You need to see the complete node tree, all attributes, and the structure of a space.

## Process

1. **Get the full space**:
   ```
   crystal_ball(cmd: "get_space", body: { space: "GordonRamsayRestaurant" })
   ```

2. **Key fields in response**:
   - `nodes[]`: All nodes with id, label, children, attributes, depth, pathDigits
   - `rootId`: Always "root"
   - `locked`: Whether the space is locked for editing

3. **Useful for**:
   - Verifying structure after building
   - Finding node IDs for subsequent operations
   - Understanding the depth/order of the space
   - Counting total nodes

## Key facts
- Returns EVERY node in the space — can be large for rich spaces
- Each node includes `pathDigits` for coordinate reconstruction
- Use `list_spaces` first to see what's available
