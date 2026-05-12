#!/usr/bin/env python3
"""
CartON Prescan Hook - Auto-inject concept GPS on user message.

Uses ChromaDB HttpClient (port 8101) to query the already-running chroma server.
Queries all routed collections, merges by inverse rank.
"""

import json
import os
import sys
from pathlib import Path


HEAVEN_DATA_DIR = os.getenv('HEAVEN_DATA_DIR', '/tmp/heaven_data')
CHROMA_PORT = 8101
MAX_RESULTS = 5

_ALL_COLLECTIONS = [
    "domain_knowledge",
    "skillgraphs",
    "flightgraphs",
    "toolgraphs",
    "patterns",
    "observations",
]


def is_gps_enabled():
    """Check if GPS auto-injection is enabled."""
    return (Path(HEAVEN_DATA_DIR) / 'carton_gps_enabled').exists()


def query_all_collections(user_message: str) -> str:
    """Query all ChromaDB collections via HttpClient, merge by inverse rank."""
    try:
        import chromadb
        client = chromadb.HttpClient(host="localhost", port=CHROMA_PORT)

        merged = {}
        for coll_name in _ALL_COLLECTIONS:
            try:
                collection = client.get_collection(coll_name)
                if collection.count() == 0:
                    continue

                results = collection.query(
                    query_texts=[user_message],
                    n_results=MAX_RESULTS,
                )

                if not results or not results.get('ids') or not results['ids'][0]:
                    continue

                ids = results['ids'][0]
                for idx, doc_id in enumerate(ids):
                    name = doc_id
                    if '/' in name:
                        name = name.split('/')[-1].replace('_itself.md', '').split('::')[0]
                    merged.setdefault(name, 0.0)
                    merged[name] += 1.0 / (idx + 1)
            except Exception:
                continue

        if not merged:
            return ""

        ranked = sorted(merged.items(), key=lambda x: -x[1])[:MAX_RESULTS]
        lines = ["CartON prescan:"]
        for name, score in ranked:
            lines.append(f"  [{round(score, 3)}] {name}")

        return "\n".join(lines)
    except Exception:
        import traceback
        print(f"Prescan error: {traceback.format_exc()}", file=sys.stderr)
        return ""


def main():
    try:
        hook_data = json.load(sys.stdin)
    except Exception:
        import traceback
        print(f"Prescan stdin error: {traceback.format_exc()}", file=sys.stderr)
        sys.exit(0)

    if not is_gps_enabled():
        sys.exit(0)

    user_message = hook_data.get('prompt', '')
    if not user_message or len(user_message) < 10:
        sys.exit(0)

    gps = query_all_collections(user_message)
    if not gps:
        sys.exit(0)

    result = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": gps
        }
    }

    print(json.dumps(result))
    sys.exit(0)


if __name__ == "__main__":
    main()
