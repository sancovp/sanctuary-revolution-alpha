# Implementation Plan

This file tracks tasks for the Ralph loop. Updated by the agent each iteration.

## Priority Tasks

### Phase 1: Rebuild RAG Functions (CartON-style)

- [x] **1.1** Create skill graph schema in Neo4j (Skill, Skillset, Domain nodes)
- [x] **1.2** Sync existing skills to Neo4j with relationships (sync/sync_skills_to_neo4j.py)
- [x] **1.3** Build `skill_rag_carton_style(query)` function in capability_predictor/skill_rag.py
- [x] **1.4** Test skill RAG independently (tests/test_skill_rag.py)
- [x] **1.5** Create tool graph schema in Neo4j (Tool, Server, Domain nodes)
- [x] **1.6** Sync tool catalog to Neo4j with relationships (sync/sync_tools_to_neo4j.py)
- [x] **1.7** Build `tool_rag_carton_style(query)` function in capability_predictor/tool_rag.py
- [x] **1.8** Test tool RAG independently (tests/test_tool_rag.py)

### Phase 2: Join into One Tool with Schema

- [x] **2.1** Define Pydantic schemas in capability_predictor/models.py (PlanStep, CapabilityObservation, StepPrediction, CapabilityPrediction)
- [x] **2.2** Implement `predict_capabilities()` in capability_predictor/predictor.py joining both RAGs
- [x] **2.3** Create library facade in capability_predictor/core.py
- [x] **2.4** Create MCP server wrapper in capability_predictor/mcp_server.py
- [x] **2.5** Test end-to-end (tests/test_predictor.py + tests/test_mcp_server.py)

### Phase 3: Tuning System (Future)

- [x] **3.1** Implement usage tracking hook (PostToolUse records actual usage)
- [x] **3.2** Build observation storage (JSON/Neo4j) in capability_predictor/tracking.py
- [x] **3.3** Implement rollup aggregation
- [x] **3.4** Build mismatch detection and reporting

### Phase 4: Meta-Learning Harness (Future)

- [x] **4.1** Implement feedback loop integration
- [x] **4.2** Seed alias clusters
- [ ] **4.3** Build weight adjustment mechanism
- [ ] **4.4** Create visualization of prediction accuracy over time

## In Progress

<!-- Tasks currently being worked on -->

## Completed

- **4.2** (2026-01-23): Implemented alias clusters for capability prediction bootstrapping
  - AliasCluster and AliasClustersConfig data classes for semantic mappings
  - Default clusters for 10 domains: navigation, building, testing, publishing, documentation, debugging, configuration, data, integration, knowledge
  - match_query_to_domains() finds matching domains based on keyword overlap
  - get_bootstrap_predictions() returns skills/tools for matched domains
  - augment_with_alias_clusters() combines RAG + rollup + alias predictions
  - Integrated with FeedbackLoop.get_augmented_predictions() (default enabled)
  - Configurable weights: RAG (0.5), rollup (0.3), alias (0.2)
  - Persistence to alias_clusters.json with save/load/reset functions
  - Cluster management: add_keyword/skill/tool_to_cluster(), list_all_clusters()
  - Human-readable reports: format_bootstrap_predictions(), format_clusters_report()
  - 53 new unit tests for alias cluster functionality
  - Total: 250 tests passing across all modules

- **4.1** (2026-01-23): Implemented feedback loop integration (Phase 4 started!)
  - FeedbackLoop class manages complete prediction → tracking → rollup update cycle
  - get_augmented_predictions() combines RAG predictions with rollup-learned patterns
  - Configurable weights for RAG (0.7) vs rollup (0.3) predictions
  - start_session() and end_session_and_update() for session lifecycle
  - end_session_and_update() automatically adds observation to rollup
  - get_feedback_stats() returns precision/recall/F1 metrics
  - Global get_feedback_loop() singleton for convenience
  - augment_predictions_with_feedback() convenience function
  - 14 new unit tests for feedback loop functionality
  - Total: 196 tests passing across all modules

- **3.4** (2026-01-23): Implemented mismatch detection and reporting (Phase 3 complete!)
  - MismatchAnalysis class for aggregating prediction accuracy metrics
  - Computes precision, recall, F1 scores for both skills and tools
  - Tracks individual misses/over-predictions for pattern detection
  - compute_mismatch_analysis() analyzes all stored observations
  - get_improvement_suggestions() generates actionable tuning recommendations
  - format_mismatch_analysis_report() for comprehensive human-readable reports
  - Updated core.py facade to export mismatch detection functions
  - 27 new unit tests for mismatch detection functionality
  - Total: 182 tests passing across all modules
  - Phase 3 (Tuning System) now complete! Ready for Phase 4 (Meta-Learning)

- **3.3** (2026-01-23): Implemented rollup aggregation system
  - CapabilityRollup class for aggregating keyword → capability patterns
  - extract_keywords() for tokenizing step descriptions (with stop word filtering)
  - get_skill_probabilities(keyword) / get_tool_probabilities(keyword) for lookup
  - get_aggregated_predictions(query) for combined multi-keyword predictions
  - compute_rollup() rebuilds rollup from all observations
  - save_rollup() / load_rollup() for persistence to rollup.json
  - format_rollup_report() for human-readable pattern summary
  - 20 unit tests for rollup functionality
  - Total: 155 tests passing across all modules

- **3.1 & 3.2** (2026-01-23): Implemented usage tracking system
  - Tracking module: capability_predictor/tracking.py
  - TrackingSession class for managing session state
  - JSON-based storage in /tmp/heaven_data/capability_tracker/
  - Session lifecycle: start_tracking_session → record_tool_from_hook → end_tracking_session
  - Observation storage with mismatch analysis (true/false positives/negatives)
  - PostToolUse hook: hooks/capability_tracker_hook.py
  - format_mismatch_report() for human-readable reports
  - 21 unit tests passing (tests/test_tracking.py)
  - Total: 135 tests passing across all modules

- **2.4 & 2.5** (2026-01-23): Created MCP server wrapper and tested end-to-end
  - MCP server: capability_predictor/mcp_server.py (FastMCP)
  - Two tools: predict_capabilities_for_plan(), format_prediction()
  - Pure delegation to library facade (no logic in server)
  - 10 unit tests passing (tests/test_mcp_server.py)
  - Total: 114 tests passing across all modules
  - Phase 2 complete! Ready for Phase 3 (tuning system)

- **2.3** (2026-01-23): Created library facade in core.py
  - Main facade: capability_predictor/core.py re-exports all public API
  - Updated __init__.py for package-level convenience imports
  - Exports: predict_capabilities, format_capability_prediction, all models
  - Low-level RAG functions also accessible for advanced usage
  - 11 unit tests passing (tests/test_core.py)
  - Total: 104 tests passing across all modules

- **2.2** (2026-01-23): Implemented predict_capabilities() in predictor.py
  - Core function: predict_capabilities(observation: CapabilityObservation) -> CapabilityPrediction
  - Converts SkillRAGResult and ToolRAGResult dataclasses to Pydantic models
  - Extracts top skills/tools per step, aggregates overall domains
  - Generates natural language recommendations
  - Helper: format_capability_prediction() for human-readable output
  - 26 unit tests passing (tests/test_predictor.py)

- **2.1** (2026-01-23): Defined Pydantic schemas in models.py
  - Input: PlanStep, CapabilityObservation
  - Output: PredictedSkill, PredictedSkillset, PredictedSkillDomain, PredictedTool, PredictedServer, PredictedToolDomain
  - Combined: StepPrediction, CapabilityPrediction
  - Tracking: ActualUsage with mismatch detection properties
  - 22 unit tests passing (tests/test_models.py)

- **1.1 & 1.2** (2026-01-23): Created skill graph schema and sync script
  - Schema: :Skill, :Skillset, :SkillDomain nodes with constraints/indexes
  - Relationships: PART_OF (skill->skillset, skillset->domain), BELONGS_TO (skill->domain)
  - Synced 32 skills, 2 skillsets, 11 domains
  - Files: `sync/sync_skills_to_neo4j.py`, `tests/test_skill_sync.py`

- **1.3 & 1.4** (2026-01-23): Built CartON-style skill RAG function
  - Pattern: ChromaDB RAG → Neo4j graph traversal → Hierarchical aggregation
  - Data classes: SkillHit, SkillsetAggregation, DomainAggregation, SkillRAGResult
  - Functions: skill_rag_carton_style(), format_skill_rag_result()
  - 11 unit tests passing (mocked ChromaDB/Neo4j)
  - Graph traversal verified working with live Neo4j
  - Files: `capability_predictor/skill_rag.py`, `tests/test_skill_rag.py`

- **1.5 & 1.6** (2026-01-23): Created tool graph schema and sync script
  - Schema: :Tool, :ToolServer, :ToolDomain nodes with constraints/indexes
  - Relationships: PART_OF (tool->server), BELONGS_TO (tool->domain, server->domain)
  - Domain inference based on server name patterns and keyword matching
  - Synced 335 tools, 24 servers, 9 domains
  - 18 unit tests passing
  - Files: `sync/sync_tools_to_neo4j.py`, `tests/test_tool_sync.py`

- **1.7 & 1.8** (2026-01-23): Built CartON-style tool RAG function
  - Pattern: ChromaDB RAG → Neo4j graph traversal → Hierarchical aggregation
  - Data classes: ToolHit, ServerAggregation, ToolDomainAggregation, ToolRAGResult
  - Functions: tool_rag_carton_style(), format_tool_rag_result()
  - Graph traversal: Tool → ToolServer → ToolDomain via Neo4j
  - 12 unit tests passing (mocked ChromaDB/Neo4j)
  - Files: `capability_predictor/tool_rag.py`, `tests/test_tool_rag.py`

## Discovered Issues

<!-- Problems found during implementation that need attention -->

## Key References

- CartON pattern: `/home/GOD/carton_mcp/carton_utils.py` (scan_carton method lines 986-1185)
- Existing skill RAG: `/home/GOD/skill_manager_mcp/src/skill_manager/core.py`
- Existing tool RAG: `/home/GOD/gnosys_strata/src/strata/utils/catalog.py`
- be_myself pattern: `/tmp/llm_intelligence_mcp/llm_intelligence_package/llm_intelligence/core.py`

---

*Last updated: 2026-01-23*
*Current iteration: 13*
