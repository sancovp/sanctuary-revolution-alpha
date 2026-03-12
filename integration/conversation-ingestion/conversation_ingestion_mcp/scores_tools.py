"""
Scores registry tools - tracks mimetic desire chain scores for emergent frameworks.

Simple tool: returns path to JSON + current contents.
The AI edits the JSON directly using Edit tool after running framework-scorer.
"""

import os
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def get_scores_registry() -> str:
    """
    Get the scores registry path and current contents.

    The scores registry tracks mimetic desire chain scores (X/6 links held)
    for each emergent framework. After running framework-scorer on a rendered MD,
    update this registry using the Edit tool.

    Returns:
        Path to JSON file + current contents (or instructions if file doesn't exist)
    """
    heaven_data_dir = os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data")
    scores_path = os.path.join(heaven_data_dir, "frameworks", "scores_registry.json")

    if not os.path.exists(scores_path):
        # Create empty registry with structure
        logger.info(f"Creating new scores registry at {scores_path}")
        os.makedirs(os.path.dirname(scores_path), exist_ok=True)
        initial = {
            "_description": "Mimetic desire chain scores for emergent frameworks",
            "_instructions": "After running framework-scorer on a rendered MD, update this file using Edit tool",
            "_workflow": "1. preview_emergent(name, path) → 2. framework-scorer reads MD → 3. Edit this JSON with score",
            "scores": {}
        }
        with open(scores_path, 'w') as f:
            json.dump(initial, f, indent=2)

        return (
            f"✓ Created new scores registry at: {scores_path}\n\n"
            "Registry is empty. To add a score after running framework-scorer:\n"
            "1. Use Edit tool to add entry under 'scores' key\n"
            "2. Format: \"FrameworkName\": {\"links_held\": X, \"first_break\": \"Link N - reason\" or null}\n"
        )

    # Read and return current contents
    with open(scores_path, 'r') as f:
        data = json.load(f)

    scores = data.get("scores", {})

    lines = [
        f"Scores Registry: {scores_path}",
        "=" * 60,
        ""
    ]

    if not scores:
        lines.append("No scores recorded yet.")
    else:
        # Summary table
        lines.append("Framework Scores:")
        lines.append("-" * 40)

        passing = []
        failing = []

        for name, score_data in sorted(scores.items()):
            links = score_data.get("links_held", 0)
            first_break = score_data.get("first_break")

            if links == 6:
                passing.append(name)
                lines.append(f"  ✓ {name}: 6/6")
            else:
                failing.append((name, links, first_break))
                lines.append(f"  ✗ {name}: {links}/6 - {first_break or 'no details'}")

        lines.append("")
        lines.append(f"Passing (6/6): {len(passing)}")
        lines.append(f"Failing: {len(failing)}")

        if failing:
            lines.append("")
            lines.append("⚠️ Frameworks needing revision:")
            for name, links, reason in failing:
                lines.append(f"  - {name}: {reason}")

    lines.append("")
    lines.append("To update after scoring:")
    lines.append(f"  Edit {scores_path}")
    lines.append('  Add/update: "FrameworkName": {"links_held": X, "first_break": "Link N - reason" or null}')

    return "\n".join(lines)
