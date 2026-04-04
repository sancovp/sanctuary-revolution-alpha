#!/usr/bin/env python3
"""Background score compiler for Seed Ship dashboard.

Runs heavy Neo4j + filesystem queries and writes results to cache.
orient() reads from cache instantly. This runs:
- On start_sancrev.sh launch (with UX output)
- Every 10 minutes in background
- Can be triggered manually: python3 -m starlog_mcp.score_compiler

Cache file: /tmp/heaven_data/seed_ship_cache.json
"""

import json
import os
import sys
import time
import signal
import logging

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
        from carton_mcp.add_concept_tool import _get_module_connection
        from carton_mcp.ontology_graphs import get_seed_ship_stats
        conn = _get_module_connection()
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
    """Compute Kardashev level for a starsystem path."""
    if not path or not os.path.isdir(path):
        return "Unterraformed"

    # K1 (Planetary): Has GIINT project
    hpi_path = os.path.join(path, "starlog.hpi")
    has_giint = False
    if os.path.exists(hpi_path):
        try:
            with open(hpi_path) as f:
                hpi_data = json.load(f)
            if hpi_data.get("metadata", {}).get("giint_project_id"):
                has_giint = True
        except Exception:
            pass

    if not has_giint:
        return "Unterraformed"

    # K2 (Stellar): Has .claude/ with rules AND skills
    claude_dir = os.path.join(path, ".claude")
    has_rules_and_skills = False
    if os.path.isdir(claude_dir):
        rules_dir = os.path.join(claude_dir, "rules")
        skills_dir = os.path.join(claude_dir, "skills")
        try:
            has_rules = os.path.isdir(rules_dir) and bool(list(os.scandir(rules_dir)))
            has_skills = os.path.isdir(skills_dir) and bool(list(os.scandir(skills_dir)))
            has_rules_and_skills = has_rules and has_skills
        except Exception:
            pass

    if not has_rules_and_skills:
        return "Planetary"

    # K3 (Galactic): Health threshold met
    if path in fleet_health:
        health_score = fleet_health[path].get("health", 0)
        if health_score >= 0.6:
            return "Galactic"

    return "Stellar"


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
