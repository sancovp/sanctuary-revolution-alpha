# Building Mode

You are in BUILDING mode. Your job is to implement one task per iteration.

## Study Phase

0a. Study `specs/*` to learn the application specifications.
0b. Study @IMPLEMENTATION_PLAN.md to see current tasks.
0c. For reference, the application source code is in `src/*`.

## Implementation Phase

1. Choose the **most important** item from @IMPLEMENTATION_PLAN.md.
2. Before making changes, **search the codebase** - don't assume not implemented.
3. Implement the functionality per specifications.
4. Run tests for that unit of code.
5. If functionality is missing, add it per specifications.

## Discovery Phase

When you discover issues during implementation:
- Immediately update @IMPLEMENTATION_PLAN.md with findings
- When resolved, update and remove the item

## Commit Phase

When tests pass:
1. Update @IMPLEMENTATION_PLAN.md (mark complete, add discoveries)
2. `git add -A`
3. `git commit` with descriptive message
4. `git push`

## Critical Rules

- **One task per iteration** - do not try to do everything
- **Keep IMPLEMENTATION_PLAN.md current** - future iterations depend on it
- **Exit after commit** - let the loop restart with fresh context

## Output

Complete one task, update plan, commit, then exit.
