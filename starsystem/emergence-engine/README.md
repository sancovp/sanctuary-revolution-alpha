![](https://raw.githubusercontent.com/sancovp/emergence-engine/refs/heads/master/ee_img.png)

[![Part of STARSYSTEM](https://img.shields.io/badge/Part%20of-STARSYSTEM-blue)](https://github.com/sancovp/starsystem-metarepo)

# Emergence Engine MCP

Track progress through the 3-pass systematic thinking methodology using the System Design DSL notation.

## Installation

```bash
pip install /tmp/core_libraries_to_publish/emergence_engine
```

## MCP Configuration

Add to your MCP server configuration:

```json
{
  "mcpServers": {
    "emergence-engine": {
      "command": "python3",
      "args": ["/path/to/emergence_engine/mcp_server.py"]
    }
  }
}
```

## Available Tools

### `core_run(domain, starlog_path)`
Sets up basic 3-pass session with minimal guidance.
- **domain**: The domain you're applying 3-pass thinking to (e.g., "Autobiography System")
- **starlog_path**: STARLOG project path as unique identifier

### `expanded_run(domain, starlog_path)`  
Full step-by-step guidance with detailed prompts for each phase.
- Provides comprehensive instructions, examples, and explanations
- Same parameters as core_run

### `get_next_phase(starlog_path)`
Advance to next phase and get appropriate prompt for current pass + phase.
- Returns contextual guidance like: "You're on Pass 2, Phase 3. Now focus on DSL for your generation system..."

### `get_status(starlog_path)`
Show overall progress and what's next.
- Shows: "Pass 2 of 3, Phase 4 of 7", what files should exist, what's next

### `reset_journey(starlog_path)`
Reset journey back to the beginning (L0P1W[0](0)).

## DSL Notation

The system uses formal System Design DSL notation:
- **L₀P₁W[0](3)** = Layer 0, Pass 1, Workflow Phase 3
- **Layers**: L₀, L₁, L₂... (recursive application)
- **Passes**: P₁ (Conceptualize), P₂ (Generally Reify), P₃ (Specifically Reify)  
- **Phases**: 0-6 (AbstractGoal → SystemsDesign → Architecture → DSL → Topology → EngineeredSystem → FeedbackLoop)

## Three-Pass Methodology

1. **Pass 1 (Conceptualize)**: What IS this domain? (Ontological understanding)
2. **Pass 2 (Generally Reify)**: How do we MAKE things in this domain? (System building)
3. **Pass 3 (Specifically Reify)**: How do we make THIS specific instance? (Concrete creation)

## Example Usage

```python
# Start a session
core_run("Autobiography System", "/my/starlog/project")

# Get guidance for current phase  
get_next_phase("/my/starlog/project")

# Check progress
get_status("/my/starlog/project")

# Continue advancing through phases
get_next_phase("/my/starlog/project")
```

## State Persistence

State is persisted to JSON files using starlog paths as identifiers:
- Default location: `/tmp/emergence_engine_states/`
- Files named based on sanitized starlog paths
- Includes timestamps, domain, and full position tracking

## Integration

Designed to integrate with:
- **STARLOG**: Uses starlog paths as unique identifiers
- **PayloadDiscovery**: Can serve as waypoint navigation system  
- **GIINT**: Compatible with respond() workflow for complex implementations
- **STARSHIP**: Flight configs can use these tools for 3-pass missions
