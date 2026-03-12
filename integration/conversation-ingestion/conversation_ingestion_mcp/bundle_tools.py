"""
Bundle tools for conversation ingestion.

Tools: bundle_tagged, bundle_multi_tag
"""

import json
import os
from typing import List

from . import utils


def bundle_tagged(tag: str, output_name: str) -> str:
    """Bundle all pairs with given concept tag into a document."""
    state = utils.load_state()

    if not utils.is_v2_state(state):
        return "BLOCKED: bundle_tagged requires V2 state format."

    collected = utils.collect_pairs_by_concept_tag(state, tag)

    output_path = f"{utils.CONV_DIR}/bundles/{output_name}.json"
    os.makedirs(f"{utils.CONV_DIR}/bundles", exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump(collected, f, indent=2)

    return f"✓ Bundled {len(collected)} pairs with tag '{tag}' → {output_path}"


def bundle_multi_tag(tags: List[str], output_name: str) -> str:
    """Bundle pairs that have ANY of the given concept tags."""
    state = utils.load_state()

    if not utils.is_v2_state(state):
        return "BLOCKED: bundle_multi_tag requires V2 state format."

    # Collect pairs matching any of the tags
    collected = []
    seen_keys = set()  # (conversation, index) tuples to avoid duplicates

    for tag in tags:
        pairs = utils.collect_pairs_by_concept_tag(state, tag)
        for pair in pairs:
            key = (pair['conversation'], pair['index'])
            if key not in seen_keys:
                seen_keys.add(key)
                collected.append(pair)

    output_path = f"{utils.CONV_DIR}/bundles/{output_name}.json"
    os.makedirs(f"{utils.CONV_DIR}/bundles", exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump(collected, f, indent=2)

    return f"✓ Bundled {len(collected)} pairs with tags {tags} → {output_path}"
