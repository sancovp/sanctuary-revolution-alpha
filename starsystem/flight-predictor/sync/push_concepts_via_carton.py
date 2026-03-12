"""Push generated concepts to CartON via the carton_mcp library (not raw Neo4j)."""

import json
import logging
import traceback
from pathlib import Path

# carton_mcp is pip installed
from carton_mcp.add_concept_tool import add_concept_tool_func

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def push_all_concepts(concepts_file: str, batch_size: int = 50):
    """Push all concepts from JSON file to CartON via library."""
    concepts = json.loads(Path(concepts_file).read_text())
    total = len(concepts)

    logger.info(f"Pushing {total} concepts via CartON library...")

    success = 0
    failed = 0

    for i, concept in enumerate(concepts):
        try:
            add_concept_tool_func(
                concept_name=concept['concept_name'],
                description=concept.get('concept', ''),
                relationships=concept.get('relationships', []),
                desc_update_mode="replace",
                hide_youknow=True
            )
            success += 1

            if (i + 1) % batch_size == 0:
                logger.info(f"Progress: {i + 1}/{total} (success: {success}, failed: {failed})")

        except Exception as e:
            failed += 1
            logger.error(f"Failed: {concept['concept_name']}: {e}\n{traceback.format_exc()}")

    logger.info(f"Done! Success: {success}, Failed: {failed}")
    return success, failed


if __name__ == "__main__":
    concepts_file = "/tmp/rag_tool_discovery/data/tool_concepts.json"
    push_all_concepts(concepts_file)
