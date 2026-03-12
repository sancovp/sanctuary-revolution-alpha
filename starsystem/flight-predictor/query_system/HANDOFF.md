# Handoff Notes - QuerySystem Session

## What We Did This Session

### 1. Fixed CartON Wiki Sync (Root Cause Found)
- **Problem:** SOSEEH concepts in Neo4j but not in ChromaDB
- **Root cause:** Daemon creates Neo4j entries but never created wiki files
- **Fix:** Added `create_wiki_files_for_concepts()` to `/home/GOD/carton_mcp/observation_worker_daemon.py`
- **Backfill:** Created script, ran it, generated 161,766 wiki files

### 2. Fixed MILO Score-Based Fallback
- **Problem:** Used hacky word-diff instead of actual RAG scores
- **Fix:** Now checks `best_overall_score` against thresholds (0.5, 0.7, 0.95)
- **File:** `/tmp/rag_tool_discovery/flight_predictor/predictor.py`

### 3. Built QuerySystem Framework
New package at `/tmp/rag_tool_discovery/query_system/`:
- `core.py` - EmbeddingSource, Layer, QuerySystem, QueryResult
- `algorithms.py` - ScoreAlgorithm, CartONAlgorithm factories
- `milo.py` - MILO reimplemented as QuerySystem instance
- `ARCHITECTURE.md` - Full vision document

### Key Concepts
- **EmbeddingSource** = CartON scope → ChromaDB collection bridge
- **Layer** = source + score_algorithm + carton_algorithm + threshold
- **QuerySystem** = stack of layers, run query through all
- **Named systems:** MILO (capabilities), ORACLE (knowledge), PILOT (navigation), SCRIBE (content)
- **CRYSTAL BALL** = interactive QuerySystem composer/debugger
- **Homotopy framing:** quasifibration → ablation → fibration = consistent lift

## What's NOT Done
- [ ] ChromaDB sync not run ($21 cost for 161k files with text-embedding-3-large)
- [ ] MILO QuerySystem not tested against original predictor
- [ ] ORACLE not built (should replace carton_scan_hook)
- [ ] CRYSTAL BALL not built

## Next Session Should
1. Test `/tmp/rag_tool_discovery/query_system/milo.py` against original
2. Build ORACLE as separate QuerySystem
3. Compose MILO → ORACLE pipeline
4. Consider cheaper embedding model for sync (text-embedding-3-small = $3 vs $21)
