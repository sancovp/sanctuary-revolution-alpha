# PRD Authoring

You write Product Requirements Documents (PRDs) for the Compoctopus pipeline.

## PRD Fields (ALL required)

| Field | Type | Purpose |
|-------|------|---------|
| `name` | snake_case string | Project identifier |
| `description` | string | What this agent/system does |
| `architecture` | "Chain" or "EvalChain" | Chain = sequential, EvalChain = loop with evaluator |
| `links` | LinkSpec[] | The steps in the chain |
| `types` | TypeSpec[] | Data structures the agent uses |
| `behavioral_assertions` | BehavioralAssertion[] | Tests that PROVE it works |
| `imports_available` | string[] | Python imports the code can use |
| `system_prompt_identity` | string | Who this agent is |
| `file_structure` | {path: desc} | Expected output files |
| `project_id` | string | GIINT project to link to (optional) |

## LinkSpec Format

```json
{"name": "parser", "kind": "SDNAC", "description": "Parses input", "inputs": ["raw_text"], "outputs": ["parsed_data"]}
```

- `kind`: "SDNAC" (LLM-powered) or "FunctionLink" (mechanical)
- `inputs`/`outputs` define the dovetail contract between links

## When to use Chain vs EvalChain

- **Chain**: Linear, one-pass. Good for: data transforms, simple generators, parsers.
- **EvalChain**: Loop with evaluator (approve/reject/retry). Good for: code generation, quality-gated workflows.

## Common Mistakes

1. ❌ Empty behavioral_assertions — ALWAYS include at least 2
2. ❌ Missing types — if links reference data structures, define them
3. ❌ Vague link descriptions — be specific about what each link transforms
4. ❌ No error handling assertions — always test the unhappy path
5. ❌ Forgetting project_id — check GIINT projects first with planning__list_projects
