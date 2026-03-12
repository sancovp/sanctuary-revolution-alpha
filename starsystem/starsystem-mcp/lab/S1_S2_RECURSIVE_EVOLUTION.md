# S1/S2 Recursive Evolution Architecture

## Core Insight

**Test coverage is the compilation step for autonomous code evolution.**

Without tests, autonomous agents cannot safely modify code. With tests, they can evolve infinitely with guarantees.

---

## The Problem

When WE (human + AI pair) develop code:
- We go fast, break things
- "oops that MCP broke" = acceptable
- We can restart, rollback, fix manually
- Tests are nice-to-have

When an AUTONOMOUS AGENT evolves code:
- No human in the loop
- Cannot "install and see if it breaks"
- Must VERIFY changes are correct
- Tests are **MANDATORY**

---

## System 1 / System 2 Model

Borrowed from Kahneman's cognitive model:

| Mode | Behavior | Test Requirement |
|------|----------|------------------|
| **System 1** | Fast, intuitive, error-prone | Optional |
| **System 2** | Slow, deliberate, verified | Mandatory 100% |

---

## The Recursive Architecture

```
LEVEL 0: US (Human + GNOSYS)
├── System 1: Go fast, break shit
│   └── "oops MCP broke lol" = acceptable
│   └── We can restart Claude, fix manually
│
└── System 2: AUTONOMOUS EVOLUTION AGENT
    └── CANNOT just "install and see"
    └── First task: "compile" = achieve 100% test coverage
    └── Write tests for ALL existing code
    └── THEN evolve code (tests = guardrails)
    └── Output: tested code + auto-generated test suite

                    ↓ we install it ↓

LEVEL 1: THAT CODE BECOMES LIVE AGENT
├── System 1: IT goes fast, breaks shit
│   └── In its own sandbox/context
│   └── Can experiment, fail fast
│
└── System 2: ITS OWN evolution agent
    └── Same rules: compile first, then evolve
    └── Maintains test coverage
    └── Outputs tested code

                    ↓ reports to us ↓

FEEDBACK LOOP: Its S2 becomes Our S1
└── It gives us observations, patterns, errors
└── WE act as ITS System 2
└── We review, approve, integrate major changes

                    ↓ cycle continues ↓
```

---

## Test Coverage as Compilation

Traditional view: "Tests are good practice"
Our view: "Tests are the compilation step"

```
SOURCE CODE (uncompiled)
    │
    ▼
SYSTEM 2 AGENT
    │
    ├── Step 1: Write tests for all functions/classes
    │   └── Use naming convention: foo() → test_foo()
    │   └── Must cover: unit tests + integration tests
    │
    ├── Step 2: Run tests (must pass)
    │   └── If fail → fix code OR fix tests
    │   └── Loop until 100% pass
    │
    └── Step 3: NOW can evolve code
        └── Make changes
        └── Run tests
        └── Tests pass = change is valid

COMPILED CODE (tested, safe to deploy)
```

Without this "compilation" step, the agent is just guessing.

---

## Codenose Integration

Codenose becomes the compiler that reports errors:

```
ERROR: Cannot compile for autonomous evolution.

  utils.py
    ├── process_data() - NO TEST
    ├── validate_input() - NO TEST
    └── transform_output() - NO TEST

  core.py
    ├── class DataProcessor - NO TEST
    └── initialize() - NO TEST

Coverage: 2/7 (28%)
Required: 7/7 (100%)

Write tests before evolving.
```

### Detection Protocol

For each source file, extract:
1. All public functions (`def foo():` without leading `_`)
2. All classes (`class Foo:`)
3. Optionally: public methods on classes

Look for corresponding tests:
- `foo()` → `test_foo*` in any test file
- `class Foo` → `TestFoo` class OR `test_foo_*` functions

Score = `covered / total`

### Scoring Levels

| Score | Meaning | S1 Status | S2 Status |
|-------|---------|-----------|-----------|
| 0% | No tests | OK (dev) | BLOCKED |
| 1-49% | Partial | OK (dev) | BLOCKED |
| 50-99% | Mostly | OK (dev) | BLOCKED |
| 100% | Complete | OK | **COMPILED** |

---

## Journey Phase Mapping

Test coverage maps to Hero's Journey phases:

| Coverage State | Journey Phase | Content Type |
|----------------|---------------|--------------|
| 0% - No tests | Ordinary World | - |
| Test file exists | Threshold Crossed | - |
| Unit tests written | Road of Trials | Behind-the-scenes |
| Integration tests | Ordeal | **Record this** |
| 100% + passing | Proof | Demo content |
| In production | New World | Marketing content |

The **integration testing phase** is where content happens because:
- Things break (ordeal)
- You fix them (resolution)
- The struggle is authentic
- The resolution is proof

---

## Content Generation Loop

```
System 1 work (recorded via OBS)
         ↓
Hierarchical Summarizer (phases conversation)
         ↓
Narrative System (maps to Hero's Journey)
         ↓
Three-Voice Script:
  - ISAAC (human): raw, emotional
  - AGENT (AI): professional, helpful
  - NARRATOR: meta-commentary
         ↓
Animator/Editor (matches script to footage)
         ↓
Video Output
         ↓
Framework Observers (find patterns)
         ↓
Queue more content → CYCLE
```

---

## Implementation Priority

1. **Codenose test coverage detection** - the foundation
   - Parse source AST for public names
   - Parse test files for test functions
   - Match by naming convention
   - Report coverage score

2. **S2 agent compilation gate** - the enforcement
   - Before any code evolution, check coverage
   - Block evolution if < 100%
   - Force test writing first

3. **OBS trigger on integration test** - the content capture
   - Detect when integration tests start
   - Start recording
   - Stop when tests complete

4. **Narrative pipeline** - the content generation
   - Connect hierarchical summarizer
   - Connect narrative system
   - Generate three-voice scripts

---

## Key Principles

1. **Self-mod true** - We are our own users. We ship, then use, then demo.

2. **Tests = compilation** - Not good practice. Prerequisite for autonomy.

3. **S1 fast, S2 verified** - Different modes, different requirements.

4. **Recursion** - Each agent level has its own S1/S2 pair.

5. **Content as byproduct** - Work IS content. Capture, don't create.

---

## Related Concepts

- `Self_Mod_Content_Loop` (CartON)
- `Test_Journey_Phase_Mapping` (CartON)
- `Automated_Content_Pipeline` (CartON)
- `Three_Voice_Format` (CartON)
- `CAVE_Content_Engine` (CartON)

---

*Created: 2026-02-04*
*Context: Codenose test coverage enhancement design session*
