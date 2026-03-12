# Behavioral Assertions

You write behavioral assertions — tests that PROVE an agent works by running it.

## What Makes a Behavioral Assertion

A behavioral assertion calls `execute()` with real inputs and verifies real outputs.
It is NOT a unit test of internal functions. It is a test of the WHOLE agent.

## Format

```json
{
  "description": "Responds with greeting containing the user's name",
  "setup": "agent = make_greeter()\ninput_data = {'name': 'Alice'}",
  "call": "result = await agent.execute(input_data)",
  "assertions": [
    "result.status == LinkStatus.SUCCESS",
    "'Alice' in result.context['greeting']"
  ]
}
```

## Rules

1. **Real LLM calls** — assertions MUST make real API calls. A test that passes in <5 seconds is fake.
2. **At least 2 per PRD** — one happy path, one error/edge case.
3. **Verify outputs, not internals** — check what `execute()` produces, not how.
4. **Include error cases** — empty input, invalid types, missing fields.
5. **Be specific** — "result contains greeting" is too vague. "'Alice' in result.context['greeting']" is correct.

## Common Assertion Patterns

### Happy path
```json
{"description": "Processes valid input correctly", "assertions": ["result.status == LinkStatus.SUCCESS", "len(result.context['output']) > 0"]}
```

### Error handling
```json
{"description": "Handles empty input gracefully", "assertions": ["result.status == LinkStatus.SUCCESS", "'error' in result.context or 'default' in result.context['output']"]}
```

### Multi-step chain
```json
{"description": "All chain links execute in order", "assertions": ["result.status == LinkStatus.SUCCESS", "result.context.get('step_count') == 3"]}
```

## Anti-Patterns

- ❌ `assert True` — proves nothing
- ❌ Mocking the LLM — defeats the purpose of behavioral testing
- ❌ Testing only the happy path — errors WILL happen
- ❌ Checking string equality on LLM output — LLM output varies, check for containment
