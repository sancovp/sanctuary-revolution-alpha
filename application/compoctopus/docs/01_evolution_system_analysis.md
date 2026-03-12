# Evolution System: Analysis of Geometric Prompt Alignment in Multi-Agent Compilation

## What This System Is

The Evolution System (`evolution_system.py`) is a **self-evolving agent framework** where agents build new tools and agents for themselves. A mind_of_god agent tells an image_of_god agent to build something; image_of_god writes code in creation_of_god; creation_of_god runs it; results flow back up.

It is the **predecessor to the Compoctopus** — a proto-compiler pipeline that already demonstrates the key principles of geometric prompt alignment.

## The Full Call Stack

```
User → mind_of_god
  └→ EvolutionFlowTool.call(feature_description, is_tool|is_agent)
      └→ evolution_flow_request()
          ├→ Constructs full_request = feature_description + tool_help/agent_help
          │   (appends: paths, naming conventions, toolarg types, MERMAID DIAGRAM)
          └→ EvolutionFlow(feature_request=full_request, feature_type="tool"|"agent")
              └→ evolve()
                  └→ evolve_feature(full_request, feature_type)
                      └→ use_hermes_dict(
                            target="image_of_god",
                            hermes_config="tool_evolution_flow_iog_config_v2",
                            variable_inputs={ goal: { feature_request: full_request } }
                          )
                          ╔══════════════════════════════════════════╗
                          ║  image_of_god RUNS with:                ║
                          ║  System Prompt:                         ║
                          ║    <ARCHITECTURAL_IDENTITY>             ║
                          ║    <EVOLUTION_WORKFLOW>  ← prose rules  ║
                          ║    <PHILOSOPHICAL_FRAMEWORK>            ║
                          ║    <SYSTEM_CAPABILITY>                  ║
                          ║    <NETWORKING_RULES>                   ║
                          ║  Goal:                                  ║
                          ║    "Evolving a TOOL: {full_request}"    ║
                          ║    which CONTAINS the mermaid diagram   ║
                          ║  Tools:                                 ║
                          ║    EvolveToolTool, NetworkEditTool,      ║
                          ║    BashTool, IntegrationTest...         ║
                          ╚══════════════════════════════════════════╝
                          │
                          ├→ image_of_god calls NetworkEditTool to write util code in creation_of_god
                          ├→ image_of_god calls BashTool to test it in creation_of_god
                          ├→ image_of_god calls EvolveToolTool(tool_spec)
                          │   └→ use_hermes(
                          │         target="creation_of_god",
                          │         hermes_config="creation_evolution_flow_cog_config",
                          │         goal="Use ToolMakerTool to build a tool: {spec}"
                          │       )
                          │       ╔══════════════════════════════════╗
                          │       ║ creation_of_god RUNS with:      ║
                          │       ║ System: <EVOLUTION_WORKFLOW>     ║
                          │       ║   "receive request, use tool,   ║
                          │       ║    if error → block report"     ║
                          │       ║ Goal: "Use ToolMakerTool..."    ║
                          │       ║ Tools: ToolMakerTool ONLY       ║
                          │       ╚══════════════════════════════════╝
                          │       │
                          │       └→ Returns: success OR block report
                          │
                          ├→ If block report: image_of_god fixes code, retries
                          ├→ If success: image_of_god calls IntegrationTestForSuccessfulEvolutionTool
                          └→ Returns: GOAL ACCOMPLISHED or block report
```

## The Five Geometric Alignments

### 1. System Prompt ↔ Input Prompt (Dual Description)

The system prompt and input prompt describe the **same program from orthogonal angles**:

| System Prompt (`<EVOLUTION_WORKFLOW>`) | Input Prompt (goal + mermaid) |
|---|---|
| "You handle evolution by using NetworkEditTool, testing, using evolution tools..." | Mermaid sequence diagram showing exact tool calls in exact order |
| **Behavioral intent** — WHY and HOW | **Operational spec** — WHAT and WHEN |
| Prose: flexible, contextual | Mermaid: rigid, sequential |

The goal says "Work according to the sequence diagram" and the system prompt says "You handle system evolution by following directions." They **point at each other**. Neither is self-sufficient.

### 2. Tool Schemas ↔ System Prompt (Capability Surface)

The tools listed in `format_tools()` exactly match what the `<EVOLUTION_WORKFLOW>` describes:

- System says "Using NetworkEditTool to write code" → NetworkEditTool is in tools
- System says "Using your evolution tools (EvolveTool, EvolveAgent)" → EvolveToolTool, EvolveAgentTool in tools
- System says "write a block report with WriteBlockReportTool" → WriteBlockReportTool in tools

If you add a tool without updating the workflow, the agent won't use it. If you mention a tool in the workflow without adding it, the agent will hallucinate calls. **Tool list and system prompt must be co-compiled.**

### 3. Container Identity ↔ Trust Scope (Topology as Geometry)

Each container gets a **different system prompt** based on `resolve_identity()`:

| Container | Identity | Trust Level | Tools | Job |
|---|---|---|---|---|
| mind_of_god | MAIN/MIND | Full orchestration | Everything + EvolutionFlowTool | Decide what to build, route to image |
| image_of_god | MAIN/IMAGE | Hands-on coding + debug | NetworkEditTool + EvolveTools + BashTool | Write code, test, evolve |
| creation_of_god | CREATION | Minimal executor | ToolMakerTool OR AgentMakerTool ONLY | Run the maker, report errors |

The topology IS the trust model. creation_of_god can ONLY use the maker tool and write block reports. It cannot fix errors. It cannot edit files. It cannot make decisions. **The container boundary is the prompt boundary.** `remove_agents_config_tools: true` in the creation config enforces this — creation gets ONLY the tools injected via `additional_tools`, not its default set.

### 4. State Machine ↔ Prompt Templates (Phase Alignment)

The `EvolutionFlow` class is a state machine with two phases:

```
development → (success) → complete
development → (block)   → debug
debug       → (success) → complete  
debug       → (block)   → debug (loop)
```

Each phase maps to a **different hermes config** (= different prompt template):

- `development` → `tool_evolution_flow_iog_config_v2` → goal: "Evolving a new TOOL: {feature_request}"
- `debug` → `debug_evolution_flow_config` → goal: "Here's what I think: {hint}. Continue working."
- `debug` uses `continuation: true` → same conversation history!

The state machine is in Python. The prompt template is in JSON. The mermaid diagram is in the system prompt. They are **three representations of the same program** — Python for deterministic control, JSON for configuration, mermaid for the LLM.

### 5. Input Prompt Construction ↔ Feature Type (Polymorphic Compilation)

The `evolution_flow_request` function constructs the input prompt **polymorphically** based on feature type:

```python
if feature_type == "tool":
    full_request += tool_help    # Paths, naming conventions, toolarg types, tool_mermaid
if feature_type == "agent":
    full_request += agent_help   # agent_mermaid (different sequence diagram!)
```

The tool_mermaid and agent_mermaid are DIFFERENT sequence diagrams with DIFFERENT task lists:

- **Tool mermaid**: `["Analyze if util needed", "Write util code", "Write util test", "Test util", "Use EvolveToolTool", "Debug errors", "Run IntegrationTest", "Debug integration errors"]`
- **Agent mermaid**: `["Look at purpose and map tools", "Map out system prompt using XML tags", "Use EvolveAgentTool", "Debug errors", "Run IntegrationTest", "Debug integration errors"]`

The compilation of the input prompt is **type-dispatched**. Same system prompt, different input program. This is polymorphic compilation.

## Why This Works and Why It Fails Without It

### Why It Works

1. **No ambiguity for the LLM.** The mermaid diagram provides exact task names to use with the task system. The agent can't improvise different task names because the diagram specifies them literally.

2. **Every tool call is pre-validated.** The diagram only references tools the agent actually has. The system prompt only describes workflows using available tools.

3. **Error handling is baked into the diagram.** Each `alt` branch in the mermaid specifies what to do on failure: write a block report. The agent doesn't have to decide — the diagram tells it.

4. **Each container has exactly the right scope.** creation_of_god can't go rogue because it only has one tool. image_of_god can't skip testing because the diagram mandates it.

5. **The state machine catches non-determinism.** If the agent doesn't reach GOAL ACCOMPLISHED, EvolutionFlow transitions to `debug` phase. If it writes a block report, the system surfaces it to the user. Nothing is silently swallowed.

### Why It Fails Without It

- **Remove the mermaid from the input?** → The agent improvises its own workflow, uses wrong task names, skips steps
- **Remove the workflow from the system prompt?** → The agent doesn't understand WHY it's following the diagram, makes contextually wrong decisions
- **Add a tool without updating the diagram?** → Tool never gets called
- **Mention a tool in the diagram without providing it?** → The `tool call and result not match` error we just spent hours debugging
- **Give creation_of_god too many tools?** → It tries to fix errors instead of reporting them, creating compound failures

## What We Learn for Compoctopus

### 1. Prompt Compilation Is Multi-Pass

The evolution system already does this:
- **Pass 1**: Determine feature type (tool vs agent) → selects compilation path
- **Pass 2**: Construct input prompt (append type-specific help + mermaid)
- **Pass 3**: Construct system prompt (compose XML sections based on container identity)
- **Pass 4**: Select tools (based on application + aspect)

These passes must be **synchronized**. The Compoctopus formalizes this as separate compiler arms.

### 2. Mermaid Diagrams Are Programs

The sequence diagrams aren't documentation — they're **executable specifications** that the LLM follows as a state machine. This implies:
- The **chain compiler** should output mermaid diagrams
- The **system prompt compiler** should output prose rules that are dual to the mermaid
- They must be co-generated

### 3. Trust Boundaries = Prompt Boundaries = Container Boundaries

The principle: **an agent's capability surface must exactly match its prompt surface**. No tool without a workflow reference. No workflow reference without a tool. The Compoctopus enforces this by having the MCP compiler validate against the system prompt compiler's output.

### 4. State Machines Wrap Non-Determinism

The LLM is non-deterministic. The EvolutionFlow state machine wraps it in a deterministic shell:
- Python decides the phase
- Phase determines the prompt template
- Prompt template constrains the LLM's output space
- Output is classified into {success, block, incomplete}
- Classification determines next phase

This is the same pattern we applied to HS. **Every agent must be wrapped in a deterministic state machine.** The LLM never decides "what to do next" — the state machine does.

### 5. The Return Value IS the Interface

`evolution_flow_request` returns a formatted string:
```
===EVOLUTION FLOW===
**🆔 state_id**: {id}
**📊 status**: {status}
**result**: {formatted_output}
```

This is what the calling agent (mind_of_god) sees. It's designed to be parseable by an LLM AND by code. The formatted output preserves exact messages from the inner agent. The state_id enables continuation. The status enables branching.

The return value is the **interface contract** between compiler passes. The Compoctopus needs well-defined interface contracts between its arms.
