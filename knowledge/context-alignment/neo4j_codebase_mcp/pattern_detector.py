"""Pattern detector — orchestrates pattern discovery, Neo4j storage, and queue flush.

AST extraction and similarity scoring live in pattern_fingerprint.py.

Usage:
    from pattern_detector import detect_patterns
    result = detect_patterns(["/path/to/repo"])
"""

import json
import logging
import os
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple

from pattern_fingerprint import (
    analyze_file, build_fingerprint, compute_similarity, find_breakpoint,
)

logger = logging.getLogger(__name__)


def detect_patterns(
    search_dirs: List[str],
    min_group_size: int = 2,
    exclude_bases: Optional[Set[str]] = None,
) -> Dict[str, Any]:
    """Auto-discover code patterns from shared base classes.

    Args:
        search_dirs: Directories to scan for Python files.
        min_group_size: Minimum files sharing a base class to count as pattern.
        exclude_bases: Base class names to ignore.

    Returns:
        Dict with discovered patterns, fingerprints, similarity, and sub-patterns.
    """
    if exclude_bases is None:
        exclude_bases = {
            "object", "ABC", "BaseModel", "Exception", "Enum",
            "TestCase", "type", "dict", "list", "str", "int",
        }

    # Phase 1: Parse all files
    all_analyses = []
    for d in search_dirs:
        for pf in sorted(Path(d).rglob("*.py")):
            if "__pycache__" in str(pf) or ".git" in str(pf):
                continue
            try:
                all_analyses.append(analyze_file(pf))
            except (SyntaxError, UnicodeDecodeError):
                pass

    # Phase 2: Group classes by base class
    base_class_groups: Dict[str, List[Tuple[str, str, Dict, Dict]]] = {}

    for analysis in all_analyses:
        for cls_name, cls_info in analysis["classes"].items():
            for base in cls_info["bases"]:
                base_leaf = base.split(".")[-1]
                if base_leaf in exclude_bases:
                    continue
                base_class_groups.setdefault(base_leaf, []).append(
                    (cls_name, analysis["file"], cls_info, analysis)
                )

    # Phase 3: Build fingerprints for groups with enough members
    patterns = {}

    for base_name, members in base_class_groups.items():
        seen = set()
        unique = []
        for cls_name, file_path, cls_info, analysis in members:
            key = (cls_name, file_path)
            if key not in seen:
                seen.add(key)
                unique.append((cls_name, file_path, cls_info, analysis))

        if len(unique) < min_group_size:
            continue

        fingerprints = []
        for cls_name, file_path, cls_info, analysis in unique:
            fingerprints.append(build_fingerprint(cls_name, cls_info, analysis))

        # Phase 4: Similarity matrix
        pairs = []
        for i in range(len(fingerprints)):
            for j in range(i + 1, len(fingerprints)):
                sim = compute_similarity(fingerprints[i], fingerprints[j])
                pairs.append({
                    "a": fingerprints[i]["class_name"],
                    "b": fingerprints[j]["class_name"],
                    "a_file": fingerprints[i]["file"],
                    "b_file": fingerprints[j]["file"],
                    "overall": round(sim["overall"], 3),
                    "details": {k: round(v, 3) for k, v in sim.items() if k != "overall"},
                })
        pairs.sort(key=lambda p: p["overall"], reverse=True)

        # Phase 5: Breakpoint detection
        breakpoint = find_breakpoint([p["overall"] for p in pairs])

        sub_patterns = []
        if breakpoint:
            threshold = breakpoint["below"]
            conforming = set()
            deviating = set()
            for p in pairs:
                if p["overall"] > threshold:
                    conforming.add(p["a"])
                    conforming.add(p["b"])
                else:
                    deviating.add(p["a"])
                    deviating.add(p["b"])
            true_deviating = deviating - conforming
            sub_patterns.append({"label": "conforming", "members": sorted(conforming)})
            if true_deviating:
                sub_patterns.append({"label": "deviating", "members": sorted(true_deviating)})

        avg_sim = sum(p["overall"] for p in pairs) / len(pairs) if pairs else 0.0

        patterns[base_name] = {
            "base_class": base_name,
            "member_count": len(fingerprints),
            "members": [
                {
                    "class": fp["class_name"],
                    "file": fp["file"],
                    "async": fp["has_async_methods"],
                    "create_classmethod": fp["has_classmethod_create"],
                    "attrs": list(fp["attrs"].keys()),
                    "methods": fp["method_names"],
                    "schema_args": fp["dict_schema_args"],
                }
                for fp in fingerprints
            ],
            "avg_similarity": round(avg_sim, 3),
            "breakpoint": breakpoint,
            "sub_patterns": sub_patterns,
            "top_pairs": pairs[:10],
        }

    return {
        "files_scanned": len(all_analyses),
        "patterns_found": len(patterns),
        "patterns": patterns,
    }


def _to_relative(abs_path: str, repo_root: Optional[str]) -> str:
    """Convert absolute path to relative (matching CA File node format)."""
    if not repo_root:
        return abs_path
    return os.path.relpath(abs_path, repo_root)


def store_patterns_neo4j(
    patterns_result: Dict[str, Any],
    repo_name: str,
    neo4j_uri: str,
    neo4j_user: str,
    neo4j_password: str,
    repo_root: Optional[str] = None,
) -> Dict[str, int]:
    """Store discovered patterns in Neo4j as Pattern nodes + FOLLOWS_PATTERN edges.

    Args:
        repo_root: Absolute path to repo root. When provided, file paths are
            converted to relative (matching CA File node path format).
    """
    from neo4j import GraphDatabase

    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    patterns_created = 0
    edges_created = 0

    with driver.session() as session:
        for pattern_name, pdata in patterns_result.get("patterns", {}).items():
            session.run(
                "MERGE (p:Pattern {name: $name, repo: $repo}) "
                "SET p.base_class = $base_class, p.member_count = $member_count, "
                "p.avg_similarity = $avg_similarity, p.updated_at = datetime()",
                name=pattern_name, repo=repo_name,
                base_class=pdata["base_class"],
                member_count=pdata["member_count"],
                avg_similarity=pdata["avg_similarity"],
            )
            patterns_created += 1

            for sp in pdata.get("sub_patterns", []):
                sp_name = f"{pattern_name}_{sp['label']}"
                session.run(
                    "MERGE (sp:SubPattern {name: $name, repo: $repo}) "
                    "SET sp.label = $label, sp.member_count = $mc, sp.updated_at = datetime() "
                    "WITH sp MATCH (p:Pattern {name: $parent, repo: $repo}) "
                    "MERGE (p)-[:HAS_SUB_PATTERN]->(sp)",
                    name=sp_name, repo=repo_name, label=sp["label"],
                    mc=len(sp["members"]), parent=pattern_name,
                )

            for member in pdata["members"]:
                rel_path = _to_relative(member["file"], repo_root)
                session.run(
                    "MATCH (f:File {path: $path}) "
                    "MATCH (p:Pattern {name: $pname, repo: $repo}) "
                    "MERGE (f)-[:FOLLOWS_PATTERN {"
                    "class_name: $cls, is_async_method: $is_async_method, "
                    "has_create: $create, updated_at: datetime()}]->(p)",
                    path=rel_path, pname=pattern_name, repo=repo_name,
                    cls=member["class"], is_async_method=member.get("async", False),
                    create=member.get("create_classmethod", False),
                )
                edges_created += 1

            for pair in pdata.get("top_pairs", []):
                rel_a = _to_relative(pair["a_file"], repo_root)
                rel_b = _to_relative(pair["b_file"], repo_root)
                session.run(
                    "MATCH (f1:File {path: $a}) MATCH (f2:File {path: $b}) "
                    "MERGE (f1)-[s:SIMILAR_TO {pattern: $p}]-(f2) "
                    "SET s.similarity = $sim, s.updated_at = datetime()",
                    a=rel_a, b=rel_b,
                    p=pattern_name, sim=pair["overall"],
                )

    driver.close()
    return {"patterns_created": patterns_created, "edges_created": edges_created}


# =============================================================================
# DEBOUNCED CA REFRESH QUEUE
# =============================================================================

CA_QUEUE_DIR = Path("/tmp/ca_refresh_queue")
CA_DEBOUNCE_SECONDS = 300  # 5 minutes


def flush_ca_queue(
    neo4j_uri: Optional[str] = None,
    neo4j_user: Optional[str] = None,
    neo4j_password: Optional[str] = None,
    force: bool = False,
) -> Dict[str, Any]:
    """Flush stale CA refresh queues. Per-codebase, 5min debounce.

    Args:
        neo4j_uri/user/password: Neo4j connection (defaults from env).
        force: Flush all queues regardless of debounce timer.

    Returns:
        Dict with flushed repos and file counts.
    """
    if not CA_QUEUE_DIR.exists():
        return {"flushed": [], "skipped": []}

    neo4j_uri = neo4j_uri or os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = neo4j_user or os.environ.get("NEO4J_USER", "neo4j")
    neo4j_password = neo4j_password or os.environ.get("NEO4J_PASSWORD", "password")

    now = time.time()
    flushed = []
    skipped = []

    for queue_file in CA_QUEUE_DIR.glob("*.jsonl"):
        repo_slug = queue_file.stem
        lock_file = CA_QUEUE_DIR / f"{repo_slug}.lock"

        # Skip if locked (another flush in progress)
        if lock_file.exists():
            skipped.append({"repo": repo_slug, "reason": "locked"})
            continue

        # Read entries
        entries = []
        try:
            with open(queue_file) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        entries.append(json.loads(line))
        except Exception:
            continue

        if not entries:
            continue

        # Check debounce: last entry must be > 5min ago
        last_time = max(e.get("time", 0) for e in entries)
        if not force and (now - last_time) < CA_DEBOUNCE_SECONDS:
            skipped.append({
                "repo": repo_slug,
                "reason": f"debounce ({int(now - last_time)}s < {CA_DEBOUNCE_SECONDS}s)",
                "files_queued": len(entries),
            })
            continue

        # Dedup file paths
        unique_files = sorted(set(e["file"] for e in entries))

        # Lock, process, unlock
        try:
            lock_file.touch()

            # Find repo root from first file
            repo_root = None
            for parent in Path(unique_files[0]).parents:
                if (parent / ".git").exists() or (parent / ".claude").exists():
                    repo_root = str(parent)
                    break

            if repo_root:
                # Run pattern detection on the repo
                result = detect_patterns([repo_root])

                # Store in Neo4j if available
                try:
                    store_result = store_patterns_neo4j(
                        result, repo_slug, neo4j_uri, neo4j_user, neo4j_password,
                        repo_root=repo_root,
                    )
                except Exception as e:
                    store_result = {"error": str(e)}

                flushed.append({
                    "repo": repo_slug,
                    "files_processed": len(unique_files),
                    "patterns_found": result.get("patterns_found", 0),
                    "neo4j": store_result,
                })

            # Clear the queue
            queue_file.unlink(missing_ok=True)

        finally:
            lock_file.unlink(missing_ok=True)

    return {"flushed": flushed, "skipped": skipped}
