# Evolution System Mermaid Rules

> Extracted from `evolution_system.py` in mind_of_god
> These are the rules for building "executable mermaid" sequence diagrams
> that an LLM follows as a program during agent mode.

## Structure Rules

1. **Always `sequenceDiagram`** — never state diagrams, flowcharts, etc.
   The LLM follows a sequence of interactions, not a graph of states.

2. **Participants are the execution boundary**
   - `User` — Heaven's iteration loop (sends "Next task" prompts)
   - `Agent` (named) — the LLM itself (Planner, IoG, etc.)
   - `Tools` — the tool surface (collapsed into one participant)
   - Optional: other containers (CoG, MoG) when cross-container

3. **First message: User gives the task description**
   ```
   User->>Agent: Evolve a tool
   ```

4. **Agent's first response: declare task list**
   ```
   Agent->>User: ```update_task_list=["task1", "task2", ...]```
   ```
   This maps directly to Heaven's TaskSystemTool `update_tasks` operation.
   The task list IS the execution plan.

5. **Each task follows the pattern:**
   ```
   User->>Agent: Next task
   Agent->>Tools: <exact tool call with params>
   Tools->>Agent: <expected response shape>
   Agent->>User: ```complete_task=<task name>```
   ```
   The `User->>Agent: Next task` corresponds to Heaven's iteration boundary.

6. **Alt/else blocks for branching:**
   ```
   alt Error case
       Tools->>Agent: <error details>
       Agent->>Tools: <fix action>
   else Success case
       Tools->>Agent: <success message>
       Agent->>User: ```complete_task=...```
   end
   ```

7. **Terminal: GOAL ACCOMPLISHED**
   ```
   Agent->>User: ```GOAL ACCOMPLISHED```
   ```
   This triggers Heaven's goal_accomplished check and ends the execution.

## Content Rules

8. **Tool calls start with the tool name** — natural language, not Python syntax:
   ```
   Agent->>Tools: EvolveToolTool: <Tool configuration>
   Agent->>Tools: BashTool: <Run test command in creation_of_god>
   Agent->>Tools: NetworkEditTool with target `creation_of_god` and path `/home/...`
   Agent->>Tools: EditTool: create a file at path `/tmp/<name>.py` with file_text `<code>`
   ```
   NOT: `Agent->>Tools: use the tool to do something`

9. **Response shapes show what comes back:**
   ```
   Tools->>Agent: {success, project}
   ```

10. **Notes for repetition/emphasis:**
    ```
    Note over Agent: Repeat for each feature identified in analysis
    Note over Agent: CRITICAL - descriptions must be specific
    ```

11. **Skippable tasks chain complete_task calls:**
    ```
    else No Util Needed
        Agent->>User: ```complete_task=Write util code if needed```
        Agent->>User: ```complete_task=Write util test if needed```
    ```

12. **WriteBlockReportTool for unresolvable errors:**
    ```
    alt Cannot Fix
        Agent->>Tools: WriteBlockReportTool: <block report>
        Tools->>Agent: <block report response>
    end
    ```

## Anti-patterns

- ❌ State diagrams (stateDiagram-v2) — the mermaid is a SEQUENCE, not a graph
- ❌ Vague tool names — "use the tool" vs exact `EvolveToolTool: <config>`
- ❌ Missing task lifecycle — every task must have update_task_list, complete_task, GOAL ACCOMPLISHED
- ❌ Missing alt/else — error paths are NOT optional, they're how the agent handles failures
- ❌ Missing `User->>Agent: Next task` — this is the iteration boundary, it's structural

## Relationship to Components

- **System prompt**: prose rules + identity (WHO/HOW/WHY)
- **Goal**: contains the mermaid (WHAT/WHEN) + request context
- **Interlock**: goal says "follow the sequence diagram in your system prompt"
  and the system prompt references the diagram

The mermaid and system prompt are **co-compiled** — they describe the same
program from orthogonal angles (Geometric Invariant #1: Dual Description).
