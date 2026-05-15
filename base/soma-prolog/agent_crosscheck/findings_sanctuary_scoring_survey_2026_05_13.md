# Findings: Sanctuary Scoring Rule Survey (2026-05-13)

## Survey scope

### Paths searched

Primary targets:
- `/home/GOD/gnosys-plugin-v2/starsystem/reward-system/starsystem_reward_system/scoring.py`
- `/home/GOD/gnosys-plugin-v2/starsystem/starsystem-mcp/starsystem/reward_system.py`
- `/home/GOD/gnosys-plugin-v2/application/sanctum-builder/sanctum_builder/core.py`
- `/home/GOD/gnosys-plugin-v2/application/sanctum-builder/sanctum_builder/models.py`
- `/home/GOD/gnosys-plugin-v2/application/cave/cave/core/sanctuary_degree_calculator.py`
- `/home/GOD/gnosys-plugin-v2/starsystem/starlog-mcp/starlog_mcp/score_compiler.py`
- `/home/GOD/gnosys-plugin-v2/starsystem/starlog-mcp/starlog_mcp/starlog_mcp.py`
- `/home/GOD/gnosys-plugin-v2/application/seed-mcp/src/seed_mcp/scoring_display.py`
- `/home/GOD/gnosys-plugin-v2/application/paia-builder/paia_builder/util_deps/gear_ops.py`
- `/home/GOD/gnosys-plugin-v2/starsystem/starsystem-mcp/lab/starsystem_calculator.py`
- `/home/GOD/gnosys-plugin-v2/knowledge/carton-mcp/ontology_graphs.py`
- `/home/GOD/gnosys-plugin-v2/base/sanctuary-system/sanctuary_system/models.py`

Grep scope: `grep -rn "def.*score|def.*scoring|def.*reward|def.*fitness|def.*emanation_score|def.*kardashev|def.*sanctuary_degree|def.*codenose" /home/GOD/gnosys-plugin-v2/ --include="*.py"` — 35 files matched. All with actual scoring rules were read in full.

### Files excluded from catalog (display/wrappers only, no scoring logic)

- `scoring_display.py` — pure display wrappers calling `compute_fitness()`, no scoring logic of their own.
- `scores_tools.py` — mimetic desire chain scores, just a JSON registry tool, no computation.
- `score_compiler.py` — orchestrator that calls other scoring functions and caches results, no scoring logic of its own.

---

## Scoring rules catalog

### CATEGORY A: Event-based reward scoring (DEPRECATED)

These exist in two identical copies: `starsystem_reward_system/scoring.py` and `starsystem/reward_system.py`. Both marked DEPRECATED in favor of state-based scoring. The `starsystem_reward_system` package is the public API (exported from `__init__.py`); `reward_system.py` duplicates it for backward compat.

---

#### A1. `compute_event_reward(event: Dict) -> float`

- **File:line**: `reward_system.py:1615` (also `scoring.py:202`)
- **Signature**: `compute_event_reward(event: Dict) -> float`
- **Computes**: Looks up `event["tool_name"]` suffix in `EVENT_REWARDS` dict (14 entries, values range -200 to +500). Falls back to error penalty checks (`omnisanc_error` in reason, `allowed=False`). Default 0.0.
- **Dependencies**: `EVENT_REWARDS` constant dict (same file). Reads `event["tool_name"]`, `event["allowed"]`, `event["reason"]`.
- **Flat/Recursive**: **FLAT**. Pure dict lookup + two conditionals. No recursion, no sub-calls.
- **Shape**: Pure Python expression over a single dict input.
- **Arity**: 1 (one event dict).

---

#### A2. `compute_session_reward(session_events: List[Dict]) -> float`

- **File:line**: `reward_system.py:1645` (also `scoring.py:232`)
- **Signature**: `compute_session_reward(session_events: List[Dict]) -> float`
- **Computes**: `(sum(compute_event_reward(e)) + completion_bonus) * quality_multiplier * SESSION_MULTIPLIER`. Completion bonus = 100 if both start_starlog and end_starlog events present. Quality multiplier = `1.0 - (errors / len(events))`.
- **Dependencies**: Calls `compute_event_reward()` per event. Reads `SESSION_MULTIPLIER` constant (3.0).
- **Flat/Recursive**: **RECURSIVE** — iterates over event list calling A1.
- **Shape**: Python expression with aggregation over list.
- **Arity**: 1 (list of event dicts).

---

#### A3. `compute_mission_reward(mission_events: List[Dict]) -> float`

- **File:line**: `reward_system.py:1674` (also `scoring.py:261`)
- **Signature**: `compute_mission_reward(mission_events: List[Dict]) -> float`
- **Computes**: `(sum(compute_event_reward(e)) + mission_completion_bonus + mission_extraction_penalty) * MISSION_MULTIPLIER`. Completion bonus = 500 if `mission_report_progress` present. Extraction penalty = -500 if `mission_request_extraction` present.
- **Dependencies**: Calls `compute_event_reward()` per event. Reads `MISSION_MULTIPLIER` constant (10.0).
- **Flat/Recursive**: **RECURSIVE** — iterates over event list calling A1.
- **Shape**: Python expression with aggregation over list.
- **Arity**: 1 (list of event dicts).

---

#### A4. `compute_fitness(registry_service, date: str) -> Dict[str, Any]`

- **File:line**: `reward_system.py:1699` (also `scoring.py:286`)
- **Signature**: `compute_fitness(registry_service, date: str) -> Dict[str, Any]`
- **Computes**: Fitness = `(home_rewards + session_rewards + mission_rewards) * quality_factor`. Gets events from 3 registries, delegates to A1/A2/A3. Quality factor = `1.0 - (errors / total_events)`.
- **Dependencies**: `get_events_from_registry()`, `compute_event_reward()`, `compute_session_reward()`, `compute_mission_reward()`. Requires `registry_service` (RegistryService instance).
- **Flat/Recursive**: **RECURSIVE** — calls A1, A2, A3.
- **Shape**: Python + external registry reads.
- **Arity**: 2 (registry_service + date string).

---

#### A5. `compute_stats(registry_service, start_date: str, end_date: str = None) -> Dict[str, Any]`

- **File:line**: `reward_system.py:1512` (also `scoring.py:99`)
- **Signature**: `compute_stats(registry_service, start_date: str, end_date: str = None) -> Dict[str, Any]`
- **Computes**: Aggregated counts and rates: mission_extraction_rate, mission_completion_rate, session_completion_rate, waypoint_abandon_rate, error_rate. All are `count_a / count_b` with zero-division guards.
- **Dependencies**: `get_events_from_registry()`. Requires `registry_service`.
- **Flat/Recursive**: **RECURSIVE** — iterates over all events with internal `count_tool()` closure.
- **Shape**: Python aggregation over event lists.
- **Arity**: 2-3 (registry_service + start_date + optional end_date).

---

### CATEGORY B: State-based starsystem health scoring (CURRENT)

All in `starsystem/reward_system.py`.

---

#### B1. `get_starsystem_health(path: Optional[str] = None) -> Dict[str, Any]`

- **File:line**: `reward_system.py:41`
- **Signature**: `get_starsystem_health(path: Optional[str] = None) -> Dict[str, Any]`
- **Computes**: `health = emanation*0.25 + smells*0.20 + arch*0.15 + complexity*0.15 + kg_depth*0.10 + consistency*0.15`. Each component is 0.0-1.0.
- **Dependencies**: Calls B2, B3, B4, B5, B6, B7 (all sub-scoring functions). Also `check_graph_filesystem_consistency()`.
- **Flat/Recursive**: **RECURSIVE** — top-level aggregator calling 6 sub-scoring rules.
- **Shape**: Python weighted sum.
- **Arity**: 1 (optional path, defaults to cwd).

---

#### B2. `_get_emanation_score(path: Path) -> Dict[str, Any]`

- **File:line**: `reward_system.py:311`
- **Signature**: `_get_emanation_score(path: Path) -> Dict[str, Any]`
- **Computes**: Scans .claude/{skills,rules,hooks,agents} on disk, derives CartON concept names, queries CartON for relationships, calls YOUKNOW daemon /validate on each, score = `CODE_count / total_disk_items`. Heals gaps via `_heal_emanation_gaps()`.
- **Dependencies**: CartON (Cypher query), YOUKNOW daemon (HTTP POST to localhost:8102/validate), filesystem scan.
- **Flat/Recursive**: **RECURSIVE** — iterates over disk items, queries CartON per item, validates per item.
- **Shape**: Cypher + HTTP + filesystem.
- **Arity**: 1 (path).

---

#### B3. `_get_smell_score(path: Path) -> float`

- **File:line**: `reward_system.py:489`
- **Signature**: `_get_smell_score(path: Path) -> float`
- **Computes**: If codenose available: `CodeNose().scan(path).cleanliness_score`. Fallback: count files > 500 lines, `clean_ratio = (total - smelly) / total`.
- **Dependencies**: Optional `codenose.CodeNose`. Filesystem scan.
- **Flat/Recursive**: **RECURSIVE** in fallback (iterates over .py files). If codenose available, delegates to codenose.
- **Shape**: Python with optional external library.
- **Arity**: 1 (path).

---

#### B4. `_get_architecture_score(path: Path) -> float`

- **File:line**: `reward_system.py:537`
- **Signature**: `_get_architecture_score(path: Path) -> float`
- **Computes**: Checks for existence of `core.py` and `utils.py` in path. Both = 0.7, one = 0.5, neither = 0.3. Placeholder.
- **Dependencies**: Filesystem only.
- **Flat/Recursive**: **FLAT**. Two `exists()` checks, three-branch conditional.
- **Shape**: Pure Python expression.
- **Arity**: 1 (path).

---

#### B5. `_get_complexity_score(path: Path) -> dict`

- **File:line**: `reward_system.py:646`
- **Signature**: `_get_complexity_score(path: Path) -> dict`
- **Computes**: Inventories .claude/skills and .claude/agents, queries CartON for skills/flights/personas/MCPs linked to starsystem, delegates to `_detect_complexity_level()`.
- **Dependencies**: CartON (Cypher), filesystem, `_detect_complexity_level()`.
- **Flat/Recursive**: **RECURSIVE** — delegates to helper that chains conditions.
- **Shape**: Cypher + filesystem + Python.
- **Arity**: 1 (path).

---

#### B5a. `_detect_complexity_level(total_skills, total_flights, total_mcps, total_personas, path, emanation_score) -> dict`

- **File:line**: `reward_system.py:578`
- **Signature**: `_detect_complexity_level(total_skills: int, total_flights: int, total_mcps: int, total_personas: int, path: Path = None, emanation_score: float = None) -> dict`
- **Computes**: Progressive level L0-L6 detection. L1=skills, L2=L1+flights, L3=L2+MCPs, L4=L3+persona, L5=emanation>=0.6, L6=CICD. Score = `level / 6.0`.
- **Dependencies**: `_check_cicd()` for L6. All inputs are pre-computed integers/floats passed in.
- **Flat/Recursive**: **FLAT** once inputs are provided. Sequential boolean checks, no recursion, no sub-calls to other scoring rules. However, in practice it is always called with pre-computed partial scores.
- **Shape**: Pure Python conditionals.
- **Arity**: 6 (4 ints + optional path + optional float).

---

#### B6. `_get_kg_depth_score(path: Path, complexity_score: float = None) -> float`

- **File:line**: `reward_system.py:709`
- **Signature**: `_get_kg_depth_score(path: Path, complexity_score: float = None) -> float`
- **Computes**: `kg_depth = giint_completeness*0.40 + emanation_level*0.40 + inter_starsystem*0.20`.
- **Dependencies**: Calls `_get_giint_hierarchy_completeness()`, `_get_inter_starsystem_relations()`, uses pre-passed complexity_score.
- **Flat/Recursive**: **RECURSIVE** — calls two sub-scoring rules.
- **Shape**: Python weighted sum.
- **Arity**: 2 (path + optional complexity score).

---

#### B6a. `_get_giint_hierarchy_completeness(path: Path) -> float`

- **File:line**: `reward_system.py:742`
- **Signature**: `_get_giint_hierarchy_completeness(path: Path) -> float`
- **Computes**: Queries CartON for GIINT hierarchy: projects, features, components, deliverables linked to starsystem. Score = 0.25 per level that has >= 1 non-Unnamed element. Max 1.0.
- **Dependencies**: CartON (single Cypher query with PART_OF traversal).
- **Flat/Recursive**: **FLAT** (single Cypher query, then 4 conditionals on the result). No iteration over partials, no sub-calls.
- **Shape**: Cypher + Python conditionals.
- **Arity**: 1 (path).

---

#### B6b. `_get_inter_starsystem_relations(path: Path) -> float`

- **File:line**: `reward_system.py:852`
- **Signature**: `_get_inter_starsystem_relations(path: Path) -> float`
- **Computes**: Queries CartON for outgoing relationships to other Starsystem_ nodes (DEPENDS_ON, USES, INTEGRATES_WITH, RELATES_TO). Score: 0=0.0, 1-2=0.5, 3+=1.0.
- **Dependencies**: CartON (single Cypher query).
- **Flat/Recursive**: **FLAT** (single Cypher query, then 3-branch conditional).
- **Shape**: Cypher + Python conditional.
- **Arity**: 1 (path).

---

#### B7. `check_graph_filesystem_consistency(path: Path, auto_repair: bool = True) -> Dict[str, Any]`

- **File:line**: `reward_system.py:891`
- **Signature**: `check_graph_filesystem_consistency(path: Path, auto_repair: bool = True) -> Dict[str, Any]`
- **Computes**: Checks GIINT hierarchy exists, skills are mirrored, rules exist for skills. Coverage = `mirrored / total`. Auto-repairs by copying missing skills and generating rules.
- **Dependencies**: CartON (3 Cypher queries), filesystem (skill/rule dirs), shutil for repair.
- **Flat/Recursive**: **RECURSIVE** — iterates over skills checking mirror/rule status.
- **Shape**: Cypher + filesystem + auto-repair side-effects.
- **Arity**: 2 (path + optional auto_repair bool).

---

#### B8. `_get_deepening_score(path: Path) -> dict`

- **File:line**: `reward_system.py:805`
- **Signature**: `_get_deepening_score(path: Path) -> dict`
- **Computes**: Queries CartON for GIINT components, classifies each as L0 (Unnamed), L1 (named), L3 (has deliverables). Score = `avg_level / 3.0`.
- **Dependencies**: CartON (single Cypher query).
- **Flat/Recursive**: **RECURSIVE** — iterates over Cypher result rows classifying each component.
- **Shape**: Cypher + Python aggregation.
- **Arity**: 1 (path).

---

#### B9. `_compute_giint_from_kg(kg_data: dict) -> float`

- **File:line**: `reward_system.py:1355`
- **Signature**: `_compute_giint_from_kg(kg_data: dict) -> float`
- **Computes**: Identical logic to B6a but from pre-fetched dict: 0.25 per level (projects, features, components, deliverables) that has count > 0.
- **Dependencies**: None (pure function on dict).
- **Flat/Recursive**: **FLAT**. Four conditionals on dict values.
- **Shape**: Pure Python expression.
- **Arity**: 1 (dict).

---

#### B10. `_compute_inter_from_kg(kg_data: dict) -> float`

- **File:line**: `reward_system.py:1369`
- **Signature**: `_compute_inter_from_kg(kg_data: dict) -> float`
- **Computes**: Identical logic to B6b but from pre-fetched dict: 0=0.0, 1-2=0.5, 3+=1.0.
- **Dependencies**: None (pure function on dict).
- **Flat/Recursive**: **FLAT**. Three-branch conditional on `kg_data["inter_relations"]`.
- **Shape**: Pure Python expression.
- **Arity**: 1 (dict).

---

#### B11. `_compute_kardashev_level(path: str, fleet_health: dict) -> str`

- **File:line**: `score_compiler.py:151`
- **Signature**: `_compute_kardashev_level(path: str, fleet_health: dict) -> str`
- **Computes**: Three-tier classification: Unterraformed (no .claude/), Planetary (has .claude/), Stellar (emanation >= 0.6). Reads emanation from pre-computed fleet_health dict.
- **Dependencies**: Filesystem (.claude/ existence), fleet_health dict.
- **Flat/Recursive**: **FLAT**. Two filesystem checks + one dict lookup + three-branch conditional.
- **Shape**: Pure Python conditional.
- **Arity**: 2 (path string + fleet_health dict).

---

#### B12. `_compute_fleet_xp(starships: dict, health_cache: dict = None) -> dict`

- **File:line**: `starlog_mcp.py:15`
- **Signature**: `_compute_fleet_xp(starships: dict, health_cache: dict = None) -> dict`
- **Computes**: `total_xp = sum(health_score * 1000)` per starship. `level = total_xp // 1000`.
- **Dependencies**: Pre-computed health_cache or falls back to `get_starsystem_health()`.
- **Flat/Recursive**: **RECURSIVE** — iterates over starships.
- **Shape**: Python aggregation.
- **Arity**: 2 (starships dict + optional health_cache dict).

---

### CATEGORY C: Sanctuary / Life Architecture scoring

---

#### C1. `SANCTUM.overall_score` (computed property)

- **File:line**: `sanctum_builder/models.py:156`
- **Signature**: `@computed_field @property overall_score(self) -> int`
- **Computes**: `sum(domain_scores.values()) // len(domain_scores)`. Average of 6 domain scores (health, wealth, relationships, purpose, growth, environment), each 0-100.
- **Dependencies**: `self.domain_scores` dict.
- **Flat/Recursive**: **FLAT**. Sum and integer divide on a dict of 6 values.
- **Shape**: Pure Python expression (Pydantic computed_field).
- **Arity**: 0 (property on model, reads self).

---

#### C2. `SANCTUM.is_complete` (computed property)

- **File:line**: `sanctum_builder/models.py:164`
- **Signature**: `@computed_field @property is_complete(self) -> bool`
- **Computes**: `all(score >= 80 for score in domain_scores.values())`. True when all 6 domains are >= 80.
- **Dependencies**: `self.domain_scores` dict.
- **Flat/Recursive**: **FLAT**. Single `all()` with threshold check.
- **Shape**: Pure Python expression (Pydantic computed_field).
- **Arity**: 0 (property on model, reads self).

---

#### C3. `GEARScore.total` (computed property)

- **File:line**: `sanctum_builder/models.py:96`
- **Signature**: `@computed_field @property total(self) -> int`
- **Computes**: `(growth + experience + awareness + reality) // 4`. Average of 4 GEAR components, each 0-100.
- **Dependencies**: `self.growth`, `self.experience`, `self.awareness`, `self.reality`.
- **Flat/Recursive**: **FLAT**. Sum of 4 integers, integer divide by 4.
- **Shape**: Pure Python expression (Pydantic computed_field).
- **Arity**: 0 (property on model, reads self).

---

#### C4. `SANCTUMBuilder.log_experience(daily_log, life_plan) -> str`

- **File:line**: `sanctum_builder/core.py:296`
- **Signature**: `log_experience(self, daily_log: DailyLog, life_plan: Optional[LifePlan] = None) -> str`
- **Computes**: E score = `(metrics_met / metrics_total) * 100` (% of life_plan goals met). A score = average of `mood_score*10, energy_score*10, focus_score*10`.
- **Dependencies**: `DailyLog` fields (sleep_hours, hydration_ml, etc.), `LifePlan` goals. Self state for existing GEAR.
- **Flat/Recursive**: **FLAT** for E (iterates 4 fixed metric checks, not recursion over sub-structures). **FLAT** for A (average of up to 3 scores).
- **Shape**: Pure Python expression.
- **Arity**: 3 (self + daily_log + optional life_plan).

---

#### C5. `SANCTUMBuilder.log_reality(day_schedule, completed_items) -> str`

- **File:line**: `sanctum_builder/core.py:389`
- **Signature**: `log_reality(self, day_schedule: DaySchedule, completed_items: List[str]) -> str`
- **Computes**: `reality_score = (matched / scheduled_count) * 100`. Set intersection of scheduled item names vs completed item names.
- **Dependencies**: `DaySchedule.items`, `completed_items` list.
- **Flat/Recursive**: **FLAT**. Set intersection + ratio.
- **Shape**: Pure Python expression.
- **Arity**: 3 (self + day_schedule + completed_items).

---

#### C6. `SANCTUMBuilder.calculate_growth() -> str`

- **File:line**: `sanctum_builder/core.py:417`
- **Signature**: `calculate_growth(self) -> str`
- **Computes**: If <= 7 entries: `improvement = ((last_total - first_total) / first_total) * 100`, score = `50 + improvement`. If > 7 entries: compares average of last 7 vs prior 7 entries, score = `50 + improvement/2`. Clamped 0-100.
- **Dependencies**: `self.experience_log` (sorted by date), each entry's `gear.total`.
- **Flat/Recursive**: **RECURSIVE** — iterates over experience_log entries.
- **Shape**: Python aggregation with time-windowed comparison.
- **Arity**: 1 (self only).

---

#### C7. `compute_sanctuary_degree(days: int = 7) -> Dict[str, Any]`

- **File:line**: `sanctuary_degree_calculator.py:248`
- **Signature**: `compute_sanctuary_degree(days: int = 7) -> Dict[str, Any]`
- **Computes**: `completion_rate = completions / total_due`. Completions from CartON (Ritual_Completion_ concepts), total_due from sanctum rituals * days. Maps rate to identity via thresholds: >= 0.4 = Sanctuary (OVP/OVA), >= 0.1 = Demon Champion, >= 0.02 = Demon Elite, below = Moloch. SD float = completion_rate clamped 0-1.
- **Dependencies**: `_get_active_sanctum()` (reads JSON from HEAVEN_DATA_DIR), `_query_carton_completions()` (CartON Cypher), `_count_rituals_due()` (iterates sanctum rituals), `_get_latest_journal_score()` (CartON Cypher — fetched but currently unused in final score).
- **Flat/Recursive**: **RECURSIVE** — calls multiple helper functions, each of which may query CartON.
- **Shape**: Cypher + JSON + Python thresholds.
- **Arity**: 1 (days integer, defaults to 7).

---

#### C7a. `_completion_rate_to_identity(completion_rate: float, has_vec: bool = False) -> Tuple[str, str, str]`

- **File:line**: `sanctuary_degree_calculator.py:229`
- **Signature**: `_completion_rate_to_identity(completion_rate: float, has_vec: bool = False) -> Tuple[str, str, str]`
- **Computes**: Maps float to identity triple. `>= 0.4` + vec = ("ova", "OVA", "sanctuary"), `>= 0.4` = ("ovp", "OVP", "sanctuary"), `>= 0.1` = DC, `>= 0.02` = DE, else = Moloch.
- **Dependencies**: Three module-level threshold constants.
- **Flat/Recursive**: **FLAT**. Four-branch conditional.
- **Shape**: Pure Python expression.
- **Arity**: 2 (float + bool).

---

#### C7b. `_count_rituals_due(sanctum: Dict[str, Any], days: int = 7) -> int`

- **File:line**: `sanctuary_degree_calculator.py:114`
- **Signature**: `_count_rituals_due(sanctum: Dict[str, Any], days: int = 7) -> int`
- **Computes**: Iterates active rituals, multiplies by frequency: daily=days, weekly=days//7, monthly=days//30.
- **Dependencies**: Sanctum dict (rituals list).
- **Flat/Recursive**: **RECURSIVE** — iterates over rituals.
- **Shape**: Python iteration.
- **Arity**: 2 (sanctum dict + days int).

---

### CATEGORY D: PAIA GEAR scoring

---

#### D1. `sync_gear(paia: PAIA) -> None`

- **File:line**: `gear_ops.py:54`
- **Signature**: `sync_gear(paia: PAIA) -> None`
- **Computes**: E = `base_exp + recency_bonus + variety_bonus` (capped 100). G = `min(100, total_components)` if experience exists. A = weighted tier sum / max tier sum * 100.
- **Dependencies**: `get_all_components(paia)`, `paia.gear_state.experience_events`.
- **Flat/Recursive**: **RECURSIVE** — iterates over components and events.
- **Shape**: Pure Python.
- **Arity**: 1 (PAIA model).

---

#### D2. `recalculate_points(paia: PAIA, legendary_count: int = 0) -> int`

- **File:line**: `gear_ops.py:39`
- **Signature**: `recalculate_points(paia: PAIA, legendary_count: int = 0) -> int`
- **Computes**: `tier_points + legendary_bonus`. Tier points from component.points sum. Legendary bonus = legendary_count * 1,000,000.
- **Dependencies**: `get_all_components(paia)`, `AchievementTier`.
- **Flat/Recursive**: **RECURSIVE** — iterates over components.
- **Shape**: Pure Python.
- **Arity**: 2 (PAIA + optional int).

---

### CATEGORY E: Starsystem calculator (lab/toy)

---

#### E1. `calculate_title_and_type(navy: Navy) -> tuple[Title, int]`

- **File:line**: `starsystem_calculator.py:189`
- **Signature**: `calculate_title_and_type(navy: Navy) -> tuple[Title, int]`
- **Computes**: Cascading title check: Grand Admiral (all fleets stellar) > Admiral (fleet with admiral) > Commodore (squadron with leader) > Captain (1+ dyson) > Ensign (1+ planetary) > Cadet.
- **Dependencies**: Calls `count_stellar_fleets()`, `count_fleets_with_admirals()`, `count_squadrons_with_leaders()`, `count_committed_dysons()`.
- **Flat/Recursive**: **RECURSIVE** — each counter iterates over navy collections.
- **Shape**: Pure Python.
- **Arity**: 1 (Navy dataclass).

---

#### E2. `calculate_level(xp: int) -> int`

- **File:line**: `starsystem_calculator.py:220`
- **Signature**: `calculate_level(xp: int) -> int`
- **Computes**: `xp // 1000`
- **Dependencies**: None.
- **Flat/Recursive**: **FLAT**. One integer division.
- **Shape**: Pure Python expression.
- **Arity**: 1 (int).

---

### CATEGORY F: Batch/fleet scoring (wrappers calling the above)

---

#### F1. `get_fleet_health(paths: List[str]) -> Dict[str, Dict[str, Any]]`

- **File:line**: `reward_system.py:1162`
- **Signature**: `get_fleet_health(paths: List[str]) -> Dict[str, Dict[str, Any]]`
- **Computes**: Same formula as B1 but batched: single UNWIND Cypher for all starsystems, then per-path assembly. Calls B2, B3, B4, B5a, B8, B9, B10, B11, B7.
- **Dependencies**: CartON (batch Cypher), all B-category sub-scoring rules, filesystem.
- **Flat/Recursive**: **RECURSIVE** — iterates over paths, calls multiple sub-rules per path.
- **Shape**: Cypher + Python.
- **Arity**: 1 (list of path strings).

---

## First migration candidate

### Winner: `_compute_inter_from_kg` (B10)

**The lowest-arity flat rule with the simplest shape.**

```python
def _compute_inter_from_kg(kg_data: dict) -> float:
    """Compute inter-starsystem relations from pre-fetched KG data."""
    outgoing = kg_data.get("inter_relations", 0)
    if outgoing >= 3:
        return 1.0
    elif outgoing >= 1:
        return 0.5
    return 0.0
```

**Why this is the best first candidate:**

1. **Flat**: No recursion, no iteration over sub-structures, no calls to other scoring rules.
2. **Lowest arity**: 1 input (a dict with one relevant key: `inter_relations`). In practice the d-chain only needs one integer.
3. **Self-contained**: Does not require any other scoring rule to fire first. Reads from a pre-fetched dict (which itself comes from a single Cypher COUNT query).
4. **Pure function**: No side effects, no CartON writes, no filesystem access, no HTTP calls.
5. **Exercises the int type + comparison operators**: The body uses `>=` comparisons on an integer, which directly exercises the XML char constraint (`>` in Prolog/OWL) and janus int serialization that Round 13 identified as the target.
6. **Three-branch conditional returning float**: Simple enough to encode as a Prolog rule with three clauses (or `succ/2` threshold checks), yet non-trivial enough to prove the d-chain pattern works on real production code.

**Runner-up:** `_compute_giint_from_kg` (B9) — same arity (1 dict), also flat, but 4 conditionals adding 0.25 each makes it slightly more complex. Still an excellent second migration target.

**Second runner-up:** `compute_event_reward` (A1) — arity 1, flat (dict lookup + two conditionals), but requires the EVENT_REWARDS constant dict which adds surface area for the first migration.

**Third runner-up:** `_completion_rate_to_identity` (C7a) — arity 2, flat, pure conditional, but returns a tuple of three strings which adds polymorphic complexity.

---

## Notes / surprises

### D-chain-like patterns already present

1. **Threshold-gated classification is the dominant pattern.** Almost every scoring rule follows the shape: query some count/ratio -> compare against thresholds -> return a score or label. This maps directly to Prolog rule clauses with guard conditions.

2. **Two-tier architecture**: Many scores exist in two forms — a "heavy" version that queries CartON/filesystem directly (e.g., `_get_inter_starsystem_relations` B6b) and a "light" version that reads from a pre-fetched dict (e.g., `_compute_inter_from_kg` B10). The light versions are the natural d-chain candidates because they are already pure functions on typed inputs.

3. **Weighted sum is the composition pattern.** The top-level `get_starsystem_health` is `sum(component_i * weight_i)`. If each component becomes a d-chain, the top-level becomes a d-chain that aggregates sub-chain results with weights. This is a natural Prolog pattern: `health(X, H) :- emanation(X, E), smells(X, S), ..., H is E*0.25 + S*0.20 + ...`

4. **EVENT_REWARDS dict is a lookup table** — maps directly to Prolog facts: `event_reward(mission_start, 100). event_reward(mission_complete, 500).` etc.

5. **Deprecated vs current duplication.** The entire event-based scoring (Category A) is duplicated across `starsystem_reward_system/scoring.py` and `starsystem/reward_system.py`. Both are marked deprecated. The state-based scoring (Category B) is the current system. Migration effort should focus on Category B and C only.

6. **The lab calculator (Category E) is a standalone toy** with no production dependencies. Useful as a reference for the Navy/Fleet progression model but not a migration target.

### Common shapes across rules

| Shape | Examples | D-chain mapping |
|-------|----------|----------------|
| `count >= threshold -> score` | B10, B6b, C7a, B4, B11 | Prolog clauses with guard: `rule(X, 1.0) :- count(X, N), N >= 3.` |
| `sum(items) / len(items)` | C1, C3, C4-E, C4-A | Prolog aggregate: `rule(X, S) :- findall(V, item(X, V), Vs), sumlist(Vs, Sum), length(Vs, L), S is Sum / L.` |
| `weighted_sum(components * weights)` | B1, B6 | Prolog arithmetic: `rule(X, H) :- c1(X, A), c2(X, B), H is A*W1 + B*W2.` |
| `dict_lookup(key) -> reward` | A1 | Prolog facts: `reward(key, value).` |
| `iterate_list + aggregate` | A2, A3, B8, C6, D1 | Prolog `findall/3` + `sumlist/2` or recursive predicate |

### XML char constraint note

The `>=` operator used in B10 (and pervasive across all threshold rules) is the specific operator that surfaces the XML char constraint in OWL/Prolog representation. The `>` character must be escaped or worked around (e.g., `succ/2` or `N1 >= N2` encoded as `not(N1 < N2)`) when embedded in OWL XML. B10 uses `>=` twice, making it a perfect test case for this constraint.
