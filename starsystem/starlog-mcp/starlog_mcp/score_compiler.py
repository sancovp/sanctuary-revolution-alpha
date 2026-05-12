#!/usr/bin/env python3
"""Background score compiler for Seed Ship dashboard.

Runs heavy Neo4j + filesystem queries and writes results to cache.
orient() reads from cache instantly. This runs:
- On start_sancrev.sh launch (with UX output)
- Every 10 minutes in background
- Can be triggered manually: python3 -m starlog_mcp.score_compiler

# CONNECTS_TO: /tmp/heaven_data/seed_ship_cache.json (read/write) — also accessed by orient(), start_sancrev.sh
Cache file: /tmp/heaven_data/seed_ship_cache.json
"""

import json
import os
import sys
import time
import signal
import logging

# Spawnee-side env bootstrap: pull NEO4J_*, OPENAI_API_KEY, HEAVEN_DATA_DIR,
# CHROMA_PERSIST_DIR from strata carton config BEFORE any module-level env
# reads or carton imports. Works no matter who spawns this module
# (start_sancrev.sh, cron, MCP, hook subprocess). Never trust env inheritance.
try:
    from sdna.defaults import _get_strata_carton_env
    for _k, _v in _get_strata_carton_env().items():
        os.environ.setdefault(_k, _v)
except Exception:
    pass

logger = logging.getLogger(__name__)

CACHE_FILE = os.path.join(
    os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data"),
    "seed_ship_cache.json"
)
INTERVAL = 600  # 10 minutes



def _print(msg: str):
    """Print with flush for real-time output in startup scripts."""
    print(msg, flush=True)


def compile_scores(verbose: bool = False) -> dict:
    """Run all heavy queries and return compiled dashboard data."""
    result = {
        "compiled_at": time.time(),
        "seed_ship": {
            "state": "Wasteland",
            "starsystems": 0,
            "active_hcs": 0,
            "completed_hcs": 0,
            "completed_tasks": 0,
            "total_concepts": 0,
            "learnings": 0,
        },
        "fleet_health": {},
        "fleet_xp": {"xp": 0, "level": 0},
        "kardashev_levels": {},
        "sync_errors": [],
    }

    # --- Load kardashev map ---
    if verbose:
        _print("   Checking kardashev map...")
    kmap_path = os.path.join(
        os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data"),
        "kardashev_map.json"
    )
    kmap = {}
    if os.path.exists(kmap_path):
        try:
            with open(kmap_path) as f:
                kmap = json.load(f)
        except Exception:
            pass
    result["kmap"] = kmap

    # --- Seed Ship stats from CartON ---
    if verbose:
        _print("   Compiling Seed Ship stats from Neo4j...")
    try:
        from carton_mcp.ontology_graphs import get_seed_ship_stats
        from carton_mcp.observation_worker_daemon import _create_shared_neo4j
        conn = _create_shared_neo4j()
        if conn:
            result["seed_ship"] = get_seed_ship_stats(conn)
    except Exception as e:
        if verbose:
            _print(f"   WARNING: Seed Ship stats failed: {e}")

    if verbose:
        ss = result["seed_ship"]
        _print(f"   Found {ss['total_concepts']:,} concepts, {ss['starsystems']} starsystems")

    # --- Kardashev sync (validates + writes to CartON) ---
    if kmap.get("starships"):
        if verbose:
            _print("   Syncing kardashev map to CartON...")
        try:
            # Import sync function from starlog
            from starlog_mcp.starlog_mcp import _sync_kardashev_to_carton
            sync_errors = _sync_kardashev_to_carton(kmap)
            result["sync_errors"] = sync_errors or []
        except Exception as e:
            if verbose:
                _print(f"   WARNING: Kardashev sync failed: {e}")

    # --- Fleet health ---
    starships = kmap.get("starships", {})
    valid_paths = [ss.get("path", "") for ss in starships.values()
                   if ss.get("path") and os.path.isdir(ss.get("path", ""))]

    if valid_paths:
        if verbose:
            _print(f"   Computing fleet health for {len(valid_paths)} starsystems...")
        try:
            from starsystem.reward_system import get_fleet_health
            result["fleet_health"] = get_fleet_health(valid_paths)
        except Exception as e:
            if verbose:
                _print(f"   WARNING: Fleet health failed: {e}")

    # --- Fleet XP ---
    if verbose:
        _print("   Computing fleet XP...")
    try:
        from starlog_mcp.starlog_mcp import _compute_fleet_xp
        result["fleet_xp"] = _compute_fleet_xp(starships, health_cache=result["fleet_health"])
    except Exception as e:
        if verbose:
            _print(f"   WARNING: Fleet XP failed: {e}")

    # --- Kardashev levels ---
    if verbose:
        _print("   Computing Kardashev levels...")
    for name, ss in starships.items():
        path = ss.get("path", "")
        level = _compute_kardashev_level(path, result["fleet_health"])
        result["kardashev_levels"][name] = level

    if verbose:
        _print("   Score compilation complete!")

    return result


def _compute_kardashev_level(path: str, fleet_health: dict) -> str:
    """Compute Kardashev level for a starsystem path.

    Canonical scale (from STARSYSTEM_GAME_DESIGN.md):
        Unterraformed → No .claude/ (uninhabited star)
        Planetary (K1) → Has .claude/ with intent (can land)
        Stellar (K2)   → Dyson Sphere — emanation >= 0.6
        Galactic (K3)  → TODO: CICD + deployment + self-propagating
    """
    if not path or not os.path.isdir(path):
        return "Unterraformed"

    # Planetary (K1): Has .claude/ directory with intent
    claude_dir = os.path.join(path, ".claude")
    if not os.path.isdir(claude_dir):
        return "Unterraformed"

    # Stellar (K2): Dyson Sphere — emanation >= 0.6
    if path in fleet_health:
        emanation = fleet_health[path].get("components", {}).get("emanation", 0)
        if emanation >= 0.6:
            # Galactic (K3): TODO — CICD detection (pipelines, deployment, release workflow)
            # Stub: check for .github/workflows/ or Dockerfile as basic signal
            # Future: proper CICD pipeline validation
            return "Stellar"

    return "Planetary"


def write_cache(data: dict):
    """Write compiled data to cache file."""
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    tmp = CACHE_FILE + ".tmp"
    with open(tmp, 'w') as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, CACHE_FILE)


def read_cache() -> dict | None:
    """Read from cache file. Returns None if no cache."""
    if not os.path.exists(CACHE_FILE):
        return None
    try:
        with open(CACHE_FILE) as f:
            return json.load(f)
    except Exception:
        return None


def run_once(verbose: bool = False):
    """Compile and cache once."""
    data = compile_scores(verbose=verbose)
    write_cache(data)
    return data


def run_daemon():
    """Run as background daemon, recompiling every INTERVAL seconds."""
    def _handle_signal(signum, frame):
        sys.exit(0)

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    logger.info(f"Score compiler daemon started (interval: {INTERVAL}s)")
    while True:
        try:
            run_once(verbose=False)
            logger.info("Scores compiled successfully")
        except Exception as e:
            logger.warning(f"Score compilation failed: {e}")
        time.sleep(INTERVAL)


if __name__ == "__main__":
    if "--daemon" in sys.argv:
        run_daemon()
    else:
        # One-shot with verbose output for startup
        _print("   Compiling scores...")
        t0 = time.time()
        data = run_once(verbose=True)
        elapsed = time.time() - t0
        ss = data["seed_ship"]
        _print(f"   Scores cached in {elapsed:.1f}s → {CACHE_FILE}")
        _print(f"   Seed Ship: {ss['state']} | {ss['total_concepts']:,} concepts | {ss['starsystems']} starsystems")
