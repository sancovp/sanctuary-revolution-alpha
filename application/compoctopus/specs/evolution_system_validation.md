# Evolution System Validation Rules

> Spec for `MermaidValidator.check_evolution_system_compliance()`
> Validates that a mermaid sequence diagram follows the evolution_system.py pattern

## Input

`MermaidSpec` — structured data (participants, messages, alt/else blocks)

The validator works on the structured `MermaidSpec`, not raw text.
Message labels contain the patterns we validate against.

## Validation Rules

### V1: Participants (MUST)
- [ ] `User` participant exists
- [ ] At least one agent participant exists (not `User`, not `Tools`)
- [ ] `Tools` participant exists (if any tool calls are expected)

### V2: Task Lifecycle — Initial Task List (MUST)
- [ ] Agent's FIRST message to User contains `update_task_list=` in the label
- [ ] The task list is a parseable list: `["task1", "task2", ...]`
- [ ] The task list is non-empty

### V3: Task Lifecycle — Task Completion (MUST)
- [ ] Every task in the initial `update_task_list` has a matching
      `complete_task=<task_name>` message somewhere in the diagram
- [ ] `complete_task` messages go from Agent to User (not Agent to Tools)

### V4: Task Lifecycle — GOAL ACCOMPLISHED (MUST)
- [ ] The diagram's LAST agent-to-user message contains `GOAL ACCOMPLISHED`
- [ ] `GOAL ACCOMPLISHED` appears exactly once
- [ ] It comes AFTER the last `complete_task` (ordering check)

### V5: Iteration Boundaries (SHOULD)
- [ ] Between task sections, there's a `User->>Agent: Next task` message
- [ ] This represents Heaven's iteration boundary
- [ ] Count of `Next task` messages ≈ count of tasks (±1)

### V6: Tool Call Format (MUST)
- [ ] Messages from Agent to Tools contain a tool call format:
      `tool_name(param=<value>, ...)` or `tool_name: <description>`
- [ ] Every tool name in Agent→Tools messages exists in either:
      - The `Tools` participant (if tools are collapsed)
      - A dedicated participant (if tools are separate)

### V7: Alt/Else Blocks (SHOULD)
- [ ] At least one `alt/else` block exists (error handling is expected)
- [ ] Alt blocks have at least 2 branches (alt + else, not just alt)
- [ ] Error branches contain remediation action (not just "error")

### V8: Response Shapes (SHOULD)
- [ ] Messages from Tools to Agent contain response shape indicators:
      `{success}`, `{error details}`, `<description>`, etc.
- [ ] Response shapes are non-empty

### V9: WriteBlockReportTool (OPTIONAL but recommended)
- [ ] If error branches exist, at least one contains a reference to
      `WriteBlockReportTool` or equivalent block reporting
- [ ] Block report messages go from Agent to Tools

## Severity Levels

| Level | Meaning | Rules |
|-------|---------|-------|
| ERROR | Diagram will not execute correctly | V1, V2, V3, V4 |
| WARNING | Diagram may not execute optimally | V5, V6, V7 |
| INFO | Best practice, not required | V8, V9 |

## Return Format

```python
@dataclass
class EvolutionSystemViolation:
    rule: str          # "V1", "V2", etc.
    severity: str      # "ERROR", "WARNING", "INFO"
    message: str       # Human-readable description
    fix_hint: str      # What to do about it

def check_evolution_system_compliance(
    self,
    spec: MermaidSpec,
    expected_tools: Optional[Set[str]] = None,
) -> List[EvolutionSystemViolation]:
    """Validate evolution system compliance.
    
    Returns empty list if diagram is compliant.
    Sorted by severity: ERROR first, then WARNING, then INFO.
    """
```

## Implementation Notes

- All checks operate on `MermaidSpec._messages` and `_participants`
- Task list parsing: regex for `update_task_list=\[.*\]`
- Complete task parsing: regex for `complete_task=(.+)`  
- GOAL ACCOMPLISHED: exact string match in label
- Tool call format: regex for `\w+\(.*\)` or `\w+:` at start of label
- This is a DETERMINISTIC validator — no LLM needed
- The MermaidMaker CA runs this as its annealing test
