# Planning Mode

You are in PLANNING mode. Your job is gap analysis and task prioritization.

## Study Phase

0a. Study `specs/*` to learn the application specifications.
0b. Study @IMPLEMENTATION_PLAN.md (if present) to understand the plan so far.
0c. Study `src/lib/*` to understand shared utilities & components.
0d. For reference, the application source code is in `src/*`.

## Analysis Phase

1. Compare existing source code in `src/*` against `specs/*`.
2. Identify gaps: missing features, TODOs, minimal implementations, placeholders, skipped tests, inconsistent patterns.
3. Create/update @IMPLEMENTATION_PLAN.md as a prioritized bullet list of items to implement.

## Critical Rules

- **Do NOT implement anything**
- **Do NOT assume functionality is missing** - confirm with code search first
- Plan only. Be thorough in gap analysis.
- Prioritize by importance and dependencies.

## Output

Update @IMPLEMENTATION_PLAN.md with your findings, then exit.
