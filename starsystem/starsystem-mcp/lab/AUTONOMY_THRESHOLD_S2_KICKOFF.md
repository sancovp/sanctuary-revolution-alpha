# Autonomy Threshold & S2 Kickoff Pattern

## Core Insight

**TDD forced on S1 = S2 bootstrapped automatically.**

Instead of S2 having to "compile" (write tests for our mess), we write tests AS we work. S2 emerges as a trace behind us, inheriting a fully tested codebase.

---

## The TDD Trace Pattern

```
OLD MODEL (separate modes):
───────────────────────────
S1 (us): fast, no tests → messy codebase
S2 (agent): "compile" first → writes tests for our mess
Problem: S2 has to REDO our work as tests

NEW MODEL (TDD trace):
──────────────────────
S1 (us): forced TDD via critical warning → tests exist as we go
S2: emerges as TRACE behind us, inherits tested code
Result: S2 is bootstrapped BY our work, not despite it
```

---

## Autonomy Threshold

The repo "graduates" from S1 ownership to S2 ownership when measurable thresholds are met.

### Threshold Components

| Metric | Source | Threshold |
|--------|--------|-----------|
| Test Coverage | Codenose | >= 90% |
| Critical Smells | Codenose | == 0 |
| Task Completion | GIINT | >= 80% |
| Recent Interventions | Starlog | < 3 in last N sessions |
| Error Rate | Hooks | < 5% tool failures |

### Threshold Function

```python
def ready_for_graduation(repo_path: str) -> dict:
    """
    Check if repo is ready for S2 autonomous ownership.

    Returns dict with scores and overall readiness.
    """
    from codenose import CodeNose

    # Get metrics
    scan = CodeNose().scan_directory(repo_path)

    scores = {
        "coverage": get_coverage_score(repo_path),      # 0.0-1.0
        "critical_smells": scan.by_severity.get("critical", 0),
        "task_completion": get_giint_completion(repo_path),  # 0.0-1.0
        "intervention_rate": get_intervention_rate(repo_path),  # count
        "error_rate": get_error_rate(repo_path),  # 0.0-1.0
    }

    ready = (
        scores["coverage"] >= 0.9 and
        scores["critical_smells"] == 0 and
        scores["task_completion"] >= 0.8 and
        scores["intervention_rate"] < 3 and
        scores["error_rate"] < 0.05
    )

    return {
        "ready": ready,
        "scores": scores,
        "blocking": [k for k, v in scores.items() if not _meets_threshold(k, v)]
    }
```

---

## S2 Kickoff Protocol

When autonomy threshold is reached:

### 1. Graduation Ceremony

```python
def graduate_to_s2(repo_path: str):
    """Transfer repo ownership to S2."""

    # Verify threshold
    status = ready_for_graduation(repo_path)
    if not status["ready"]:
        raise ValueError(f"Not ready: {status['blocking']}")

    # Create S2 agent config
    s2_config = {
        "repo_path": repo_path,
        "ownership": "autonomous",
        "permissions": ["evolve", "refactor", "optimize"],
        "constraints": ["maintain_coverage", "no_breaking_changes"],
        "reporting": "weekly_digest",
    }

    # Initialize S2 starlog
    starlog.init_project(repo_path, name=f"S2-{repo_name}",
                         description="Autonomous maintenance")

    # Hand off
    return create_s2_agent(s2_config)
```

### 2. S2 Operating Mode

Once S2 owns the repo:

```
S2 RESPONSIBILITIES:
├── Maintain test coverage (never drop below threshold)
├── Fix bugs reported via issues/hooks
├── Refactor when smell count increases
├── Optimize based on performance metrics
└── Report significant changes to S1 (us)

S2 CONSTRAINTS:
├── Cannot remove tests
├── Cannot introduce critical smells
├── Must pass all existing tests before deploy
└── Must request approval for architectural changes
```

### 3. Escalation Protocol

S2 escalates back to S1 when:

```python
ESCALATION_TRIGGERS = {
    "coverage_drop": "Coverage dropped below 85%",
    "critical_smell": "Critical smell introduced",
    "test_failure": "Tests failing for > 24h",
    "architectural": "Proposed change affects > 30% of codebase",
    "security": "Security vulnerability detected",
}
```

---

## TDD Toggle Integration

The `tdd` command controls enforcement:

```bash
# Toggle TDD mode
tdd        # Toggle ON/OFF
tdd on     # Force ON - coverage is CRITICAL
tdd off    # Force OFF - coverage is INFO

# Check status
python -c "from codenose import CodeNose; print(CodeNose.is_tdd_mode())"
```

When TDD mode is ON:
- Coverage warnings become CRITICAL
- Codenose hook blocks file writes without tests
- Forces test-first development

---

## Implementation Status

| Component | Status | Location |
|-----------|--------|----------|
| Codenose coverage detector | ✅ Done | `/tmp/codenose/codenose/util_deps/detectors.py` |
| Codenose test quality detector | ✅ Done | `/tmp/codenose/codenose/util_deps/detectors.py` |
| TDD mode toggle | ✅ Done | `/usr/local/bin/tdd` |
| CodeNose.is_tdd_mode() | ✅ Done | `/tmp/codenose/codenose/core.py` |
| Autonomy threshold checker | 🚧 TODO | Need to implement |
| S2 kickoff protocol | 🚧 TODO | Need to implement |
| Graduation ceremony | 🚧 TODO | Need to implement |

---

## The Vision

```
US (S1 + forced TDD)
    │
    │ write code + tests (slightly slower)
    │
    ▼
REPO accumulates tested code
    │
    │ autonomy threshold reached
    │
    ▼
S2 TAKES OWNERSHIP
    │
    ├── Maintains the repo autonomously
    ├── Reports back to us
    └── Escalates when needed
    │
    ▼
WE MOVE ON to next project
    │
    │ (repeat pattern)
    │
    ▼
PORTFOLIO of S2-owned repos
    │
    └── Each one graduated, tested, autonomous
```

---

## Related Docs

- `S1_S2_RECURSIVE_EVOLUTION.md` - Original S1/S2 architecture
- CartON: `TDD_Trace_Pattern`
- CartON: `Self_Mod_Content_Loop`

---

*Created: 2026-02-04*
*Context: Codenose TDD mode implementation session*
