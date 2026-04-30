"""Hidden connections detector — finds invisible coupling CA's AST parser misses.

Detects: HTTP calls between services, file-trigger daemons, hook bridges,
MCP tool refs in strings, cross-package imports, /tmp/ state file lifecycle,
multi-write drift. Stores results in Neo4j as edges on File nodes.
Computes annotation score (hidden connections with # TRIGGERS: or # CONNECTS_TO:).
"""
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, Any, Optional

KNOWN_SERVICES = {
    "8080": "CAVE_sancrev", "8081": "grug_server", "8090": "SOMA_Prolog",
    "8100": "YOUKNOW_validator", "8102": "YOUKNOW_daemon",
    "8103": "YOUKNOW_OWL_reasoner", "9090": "sancrev_treeshell_SSE",
    "5051": "SQLite_API_TK",
}

WATCHED_PATHS = {
    "heaven_data/carton_queue": "CartON_observation_daemon",
    "heaven_data/automations": "CronAutomation_hot_reload",
    "heaven_data/skills": "Skill_manager_mirror",
    "heaven_data/sanctums": "Sanctum_ritual_scheduler",
    "heaven_data/sanctuary": "Journal_config_SD_calculator",
    "heaven_data/conductor_dynamic": "Conductor_state",
    "heaven_data/conductor_prompt_blocks": "Conductor_prompts",
    "active_promise.md": "Autopoiesis_L1",
    "guru_loop.md": "Autopoiesis_L2",
    "flight_stabilizer_disabled": "OMNISANC_disable",
}

MONOREPO_PACKAGES = {
    "cave", "sanctuary_revolution", "heaven_base", "carton_mcp",
    "starlog_mcp", "starship_mcp", "starsystem", "waypoint",
    "canopy_mcp", "opera_mcp", "llm_intelligence", "metastack",
    "emergence_engine", "omnisanc", "autopoiesis", "conductor",
    "sdna", "youknow_kernel", "neo4j_codebase_mcp",
    "sanctuary_revolution_treeshell", "skill_manager_mcp",
    "heaven_bml_sqlite", "dragonbones",
}

MULTI_WRITE_SIGNALS = {
    "add_concept": "CartON", "write_text": "filesystem",
    "json.dump": "JSON_file", "update_task_status": "TK_board",
    "create_card": "TK_board", "add_observation": "CartON_observation",
}

ANNOTATION_RE = re.compile(r'#\s*(?:TRIGGERS|CONNECTS_TO|HIDDEN_DEP)\s*:', re.IGNORECASE)
SKIP_DIRS = {
    "__pycache__", ".git", "node_modules", ".egg-info", "build", "dist",
    ".mypy_cache", "repos", "tests", "test", "demo", "benchmark",
    "docs", "venv", "env", ".pytest_cache",
}


def _is_annotated(lines, line_idx):
    """Check if line or neighbors (3 above, 1 below) have annotation comment."""
    for j in range(max(0, line_idx - 3), min(len(lines), line_idx + 2)):
        if ANNOTATION_RE.search(lines[j]):
            return True
    return False


def scan_file(file_path, repo_root):
    """Scan one file for hidden connections."""
    try:
        content = Path(file_path).read_text(errors="ignore")
    except Exception:
        return {}

    results = defaultdict(list)
    rel = str(Path(file_path).relative_to(repo_root))
    lines = content.split("\n")

    for i, line in enumerate(lines, 1):
        s = line.strip()
        if s.startswith("#"):
            continue
        ann = _is_annotated(lines, i - 1)

        # HTTP calls
        for m in re.finditer(r'localhost:(\d+)(/[^"\'}\s,)]*)?', line):
            port, path = m.group(1), m.group(2) or "/"
            results["http"].append({"file": rel, "line": i, "annotated": ann,
                                    "target": f"{KNOWN_SERVICES.get(port, 'unknown')}:{port}{path}"})

        # Watched dir triggers
        for watched, daemon in WATCHED_PATHS.items():
            if watched in line:
                results["file_trigger"].append({"file": rel, "line": i, "annotated": ann,
                                                "triggers": daemon, "path": watched})

        # Hook bridges
        if "_post_to_omnisanc" in line or "_post_to_cave_hook" in line or "/hook/posttooluse" in line:
            results["hook_bridge"].append({"file": rel, "line": i, "annotated": ann})

        # MCP refs in strings
        for m in re.finditer(r'["\']mcp__(\w+)__(\w+)["\']', line):
            results["mcp_ref"].append({"file": rel, "line": i, "annotated": ann,
                                       "server": m.group(1), "action": m.group(2)})

        # Cross-package imports
        imp = re.match(r'^\s*(?:from|import)\s+([\w.]+)', line)
        if imp:
            pkg = imp.group(1).split(".")[0]
            if pkg in MONOREPO_PACKAGES and pkg not in rel.replace("/", ".").replace("-", "_"):
                results["cross_import"].append({"file": rel, "line": i, "annotated": ann, "imports": pkg})

        # State file refs
        for m in re.finditer(r'(/tmp/[\w/._-]+\.(?:json|md|txt|yaml|yml))', line):
            is_w = any(w in line for w in ["write_text", "json.dump", ".write(", "'w'", '"w"'])
            is_r = any(r in line for r in ["read_text", "json.load", ".read(", "exists()", "is_file"])
            rw = "write" if is_w else ("read" if is_r else "ref")
            results["state_file"].append({"file": rel, "line": i, "annotated": ann,
                                          "state_path": m.group(1), "rw": rw})

        # Multi-write signals
        for sig, store in MULTI_WRITE_SIGNALS.items():
            if sig in line:
                results["multi_write"].append({"file": rel, "line": i, "annotated": ann,
                                               "signal": sig, "store": store})

    return dict(results)


def detect_hidden_connections(repo_root):
    """Scan repo for all hidden connections. Returns results + annotation score."""
    root = Path(repo_root)
    all_results = defaultdict(list)
    files_scanned = 0

    for py_file in sorted(root.rglob("*.py")):
        if any(skip in py_file.parts for skip in SKIP_DIRS):
            continue
        if py_file.name.startswith("test_"):
            continue
        file_results = scan_file(py_file, root)
        for cat, items in file_results.items():
            all_results[cat].extend(items)
        if file_results:
            files_scanned += 1

    total = sum(len(v) for v in all_results.values())
    annotated = sum(1 for v in all_results.values() for item in v if item.get("annotated"))

    return {
        "repo": root.name,
        "files_scanned": files_scanned,
        "total_connections": total,
        "annotated": annotated,
        "unannotated": total - annotated,
        "score": round(annotated / total, 3) if total else 1.0,
        "by_type": {k: len(v) for k, v in all_results.items()},
        "connections": dict(all_results),
    }


def store_hidden_connections_neo4j(result, repo_name, neo4j_uri, neo4j_user, neo4j_password):
    """Store hidden connections in Neo4j as HIDDEN_CONNECTION edges + score on Repository."""
    from neo4j import GraphDatabase

    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    edges = 0

    with driver.session() as s:
        s.run("MATCH ()-[r:HIDDEN_CONNECTION {repo: $repo}]-() DELETE r", repo=repo_name)

        for cat, items in result.get("connections", {}).items():
            for item in items:
                rel = item["file"]
                ann = item.get("annotated", False)
                ln = item["line"]

                if cat == "http":
                    s.run("MATCH (f:File {path: $p}) MERGE (svc:Service {name: $t}) "
                          "MERGE (f)-[:HIDDEN_CONNECTION {type:'http', line:$l, annotated:$a, repo:$r}]->(svc)",
                          p=rel, t=item["target"], l=ln, a=ann, r=repo_name)
                elif cat == "file_trigger":
                    s.run("MATCH (f:File {path: $p}) MERGE (d:Daemon {name: $d}) "
                          "MERGE (f)-[:HIDDEN_CONNECTION {type:'file_trigger', line:$l, annotated:$a, repo:$r, path:$wp}]->(d)",
                          p=rel, d=item["triggers"], l=ln, a=ann, r=repo_name, wp=item["path"])
                elif cat == "state_file":
                    s.run("MATCH (f:File {path: $p}) MERGE (sf:StateFile {path: $sp}) "
                          "MERGE (f)-[:HIDDEN_CONNECTION {type:'state_file', line:$l, annotated:$a, repo:$r, rw:$rw}]->(sf)",
                          p=rel, sp=item["state_path"], l=ln, a=ann, r=repo_name, rw=item["rw"])
                elif cat == "hook_bridge":
                    s.run("MATCH (f:File {path: $p}) MERGE (h:HookBridge {name:'CAVE_PostToolUse'}) "
                          "MERGE (f)-[:HIDDEN_CONNECTION {type:'hook_bridge', line:$l, annotated:$a, repo:$r}]->(h)",
                          p=rel, l=ln, a=ann, r=repo_name)
                elif cat == "mcp_ref":
                    s.run("MATCH (f:File {path: $p}) MERGE (m:MCPTool {server:$sv, action:$ac}) "
                          "MERGE (f)-[:HIDDEN_CONNECTION {type:'mcp_ref', line:$l, annotated:$a, repo:$r}]->(m)",
                          p=rel, sv=item["server"], ac=item["action"], l=ln, a=ann, r=repo_name)
                elif cat == "cross_import":
                    s.run("MATCH (f:File {path: $p}) MERGE (pkg:Package {name: $pkg}) "
                          "MERGE (f)-[:HIDDEN_CONNECTION {type:'cross_import', line:$l, annotated:$a, repo:$r}]->(pkg)",
                          p=rel, pkg=item["imports"], l=ln, a=ann, r=repo_name)
                elif cat == "multi_write":
                    s.run("MATCH (f:File {path: $p}) MERGE (st:Store {name: $store}) "
                          "MERGE (f)-[:HIDDEN_CONNECTION {type:'multi_write', line:$l, annotated:$a, repo:$r, signal:$sig}]->(st)",
                          p=rel, store=item["store"], l=ln, a=ann, r=repo_name, sig=item["signal"])
                edges += 1

        s.run("MATCH (r:Repository {name: $repo}) "
              "SET r.hidden_total=$t, r.hidden_annotated=$a, r.hidden_unannotated=$u, "
              "r.hidden_score=$sc, r.hidden_updated=datetime()",
              repo=repo_name, t=result["total_connections"],
              a=result["annotated"], u=result["unannotated"], sc=result["score"])

    driver.close()
    return {"edges_created": edges}
