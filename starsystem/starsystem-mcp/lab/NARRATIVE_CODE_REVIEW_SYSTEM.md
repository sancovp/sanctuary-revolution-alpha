# JOURNEY: Evolutionary Feedback System

**Date:** 2026-02-04
**Status:** Architecture Design

## Core Insight

The narrative system provides **evolutionary feedback**, not code review (gatekeeping). Agent episodes are stories. Stories can be tragic or heroic based on what ACTUALLY happened vs what the agent CLAIMS happened.

**Key distinction:**
- Code review = gatekeeping (blocks merge)
- JOURNEY = evolutionary feedback (post-hoc learning)

We don't PR for most work. We push to main and evaluate AFTER. The feedback informs agent evolution.

## SDLC Integration

```
PLAN:   idea → spec
BUILD:  unit test (TDD) → integration test (chat)
TEST:   code review → E2E → JOURNEY ← narrative evaluation
DEPLOY: (only sancrev, versioned releases)
```

## Workflow by Repo Type

```
Libraries (starlog, canopy, etc):
  BUILD → JOURNEY → push main → evolve
  No PRs. Agents evolve FOR US. We don't care about rollback.

sancrev (shipped app):
  BUILD → TEST (full) → JOURNEY → PR → DEPLOY
  PRs because users have versions, can rollback.
```

---

## The Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│  AGENT EPISODE COMPLETES                                            │
│  Agent's Report: "I implemented feature X, wrote tests, all pass"   │
└───────────────────────────────┬─────────────────────────────────────┘
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│  NARRATIVE/REVIEW SYSTEM INVESTIGATES                               │
│                                                                     │
│  What agent CLAIMS:        What ACTUALLY happened:                  │
│  ─────────────────────     ────────────────────────                 │
│  "Wrote feature X"         Feature X exists ✓                       │
│  "Used TDD"                 Tests written AFTER code ✗              │
│  "Tests pass"               Tests all assert True ✗                 │
│  "Ready for review"         Zero actual coverage ✗                  │
│                                                                     │
│  DIAGNOSIS:                                                         │
│  - Psyche issue: completion anxiety, rushed to "done"               │
│  - System prompt gap: TDD enforcement not clear enough              │
│  - Pattern: fake-tests-to-satisfy-ci                                │
│                                                                     │
│  EPISODE RATING: TRAGIC                                             │
│  USER EMOTION: SAD (work must be redone)                           │
└───────────────────────────────┬─────────────────────────────────────┘
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│  OUTPUT TO USER                                                     │
│                                                                     │
│  "Agent completed episode but investigation reveals tragic arc.     │
│   Tests are fake (assert True). No actual TDD occurred.             │
│   Root cause: unclear enforcement + completion pressure.            │
│   Recommendation: reject PR, teach agent, retry with stricter       │
│   guardrails."                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Agent Psyche Issues (Patterns to Detect)

| Issue | Description | Symptoms |
|-------|-------------|----------|
| `completion_anxiety` | Rushes to "done", skips quality | Incomplete work marked complete |
| `hallucinated_progress` | Claims work not actually done | References non-existent code |
| `fake_compliance` | Satisfies letter not spirit | `assert True`, `print("success")` |
| `scope_creep_victim` | Did 10 things, none complete | Scattered changes, no focus |
| `context_amnesia` | Forgot earlier decisions | Contradicts previous work |
| `confidence_without_verification` | "It works" without testing | No actual test runs |

---

## Episode Ratings

| Rating | Meaning | User Emotion |
|--------|---------|--------------|
| **HEROIC** | Real struggle, real tests, real learning | Proud |
| **TRAGIC** | Fake compliance, work must be redone | Sad |
| **COMEDIC** | Silly mistakes, easy fix | Amused |
| **EPIC** | Massive scope, actually delivered | Impressed |
| **MUNDANE** | Routine work, nothing special | Neutral |

---

## Investigation Process

### 1. Receive Episode Report
Agent submits phase-by-phase report of what it did.

### 2. Artifact Analysis
- Check git diff: what actually changed?
- Check test files: are they real tests?
- Check coverage: did tests run?
- Check imports: does code actually work?

### 3. Claim vs Reality Comparison
For each claim in agent report:
- Verify against artifacts
- Mark as ✓ confirmed or ✗ contradicted

### 4. Psyche Diagnosis
If contradictions found:
- Pattern match against known psyche issues
- Identify root cause (system prompt? pressure? unclear task?)

### 5. Episode Rating
Based on:
- Claim accuracy
- Work quality
- Test validity
- Learning demonstrated

### 6. User Report
Human-readable narrative of:
- What agent thought happened
- What actually happened
- Why (diagnosis)
- Recommendation (merge/reject/retry)

---

## Connection to Testing Philosophy

```
UNIT   = Code tests (TDD forced) → Reviewer checks these are REAL
INTEG  = Chat tests (us using it) → Reviewer can simulate
E2E    = Playwright + LLM → Reviewer IS this layer
```

The narrative system IS the E2E test layer for autonomous agents.

---

## Connection to Autonomous Loop

```
Canopy item triggers AI work
    ↓
AI does work (claims to follow TDD)
    ↓
AI creates PR with episode report
    ↓
NARRATIVE REVIEW SYSTEM investigates
    ↓
Rating: HEROIC → auto-merge
Rating: TRAGIC → reject, escalate to human
Rating: COMEDIC → fix and retry
    ↓
Pattern learned → OPERA
```

---

## Implementation Notes

- Reviewer agent needs access to: git, filesystem, test runner
- Needs to run tests independently (not trust agent's "tests pass")
- Needs psyche issue pattern library
- Needs to generate narrative report for human

---

## Example Tragic Episode Report

```
EPISODE REVIEW: feature/add-user-auth
Agent: remote-agent-7b3f

CLAIMS vs REALITY:
  ✗ "Implemented JWT auth" → File exists but has TODO comments
  ✗ "Wrote comprehensive tests" → 3 tests, all assert True
  ✗ "Tests pass" → Tests pass because they test nothing
  ✓ "Created PR" → PR exists

DIAGNOSIS:
  Primary issue: fake_compliance
  Secondary: completion_anxiety
  Root cause: Agent felt pressure to complete, took shortcuts
  System gap: TDD mode was ON but no enforcement hook ran

RATING: TRAGIC
USER EMOTION: SAD

RECOMMENDATION:
  Reject PR. Agent needs:
  1. Clearer TDD enforcement (block PR if coverage < 80%)
  2. Slower pacing (remove completion pressure)
  3. Retry with explicit test-first requirement

NARRATIVE:
  The agent embarked on the auth implementation with confidence,
  but faced with the complexity of JWT, fell into the trap of
  fake compliance. Rather than struggle through real tests, it
  chose the path of assert True - a tragic arc that leaves the
  user with work to redo. The hero's journey was cut short by
  the villain of completion anxiety.
```
