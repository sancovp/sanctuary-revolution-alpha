# Bandit Spec — CompoctopusAgent Configuration

## Name
bandit

## Description
The Bandit is the head of the Compoctopus. It implements the Select/Construct
decision: given a task, either reuse a known-good "golden chain" (Select) or
build a new pipeline via the OctoCoder (Construct).

## Type
CompoctopusAgent — same base as OctoCoder. Uses KeywordBasedStateMachine
from heaven_base.state_machine.

## State Machine
    LOOKUP → SELECT|CONSTRUCT → RECORD → DONE

- LOOKUP: Check golden_chains dict for a matching config
- SELECT: Match found — load and return the golden chain
- CONSTRUCT: No match — invoke construction pipeline
- RECORD: Store the outcome (success/fail, config used)
- DONE: Return result

## Transitions
    LOOKUP → SELECT     (match found)
    LOOKUP → CONSTRUCT  (no match)
    SELECT → RECORD     (chain loaded)
    CONSTRUCT → RECORD  (pipeline complete)
    RECORD → DONE       (outcome stored)

## Class: Bandit

### Fields
- golden_chains: Dict[str, GoldenChain] — cached success configs
- outcomes: List[BanditOutcome] — recorded execution history

### Dataclass: GoldenChain
- name: str
- task_pattern: str — regex or keyword pattern matching task descriptions
- config: Dict[str, Any] — the agent config that worked
- success_count: int — times this chain succeeded
- last_used: Optional[str] — ISO timestamp

### Dataclass: BanditOutcome
- task_description: str
- strategy: str — "select" or "construct"
- config_used: Dict[str, Any]
- success: bool
- timestamp: str

### Methods
- lookup(task_description: str) -> Optional[GoldenChain]
    Search golden_chains for a match. Return the best match or None.
    Match by checking if task_pattern appears in task_description.

- select(chain: GoldenChain) -> Dict[str, Any]
    Return the chain's config for execution.
    Increment success_count and update last_used.

- construct(task_description: str) -> Dict[str, Any]
    No match — return a default construction config.
    The actual pipeline invocation happens externally.

- record(task_description: str, strategy: str, config: Dict[str, Any], success: bool) -> BanditOutcome
    Record the outcome. If success and strategy was "construct",
    graduate the config to a golden chain.

- graduate(task_description: str, config: Dict[str, Any]) -> GoldenChain
    Create a new GoldenChain from a successful construction.
    Derive task_pattern from the task_description keywords.

## Factory Function
make_bandit() -> CompoctopusAgent

Creates the Bandit with:
- KeywordBasedStateMachine with the states/transitions above
- StateConfig goals for each state
- System prompt describing the select/construct decision
