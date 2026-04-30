"""NarrativeOrgan — periodic gap detection + queue processing for narrative harvest.

Installed into WakingDreamer alongside OdysseyOrgan.
Periodically queries CartON for L5 Executive_Summaries without corresponding Episode_ concepts.
Queues them. Works through queue one at a time via dispatch().

Pattern: observation_worker_daemon poll loop — check queue, process one, sleep, repeat.
"""

import logging
import os
import json
import threading
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

from cave.core.mixins.anatomy import Organ

logger = logging.getLogger(__name__)

HEAVEN_DATA_DIR = os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data")
NARRATIVE_QUEUE_DIR = Path(HEAVEN_DATA_DIR) / "narrative_queue"
CHECK_INTERVAL_SECONDS = 300  # 5 minutes


@dataclass
class NarrativeOrgan(Organ):
    """Periodic narrative harvester. Finds unnarrated L5s, queues and processes them."""

    name: str = "narrative"
    enabled: bool = True
    _thread: Optional[threading.Thread] = field(default=None, repr=False)
    _running: bool = field(default=False, repr=False)
    _processed_count: int = 0

    def start(self):
        """Start the periodic gap detection loop."""
        if self._running:
            return {"status": "already running"}
        NARRATIVE_QUEUE_DIR.mkdir(parents=True, exist_ok=True)
        self._running = True
        self._thread = threading.Thread(
            target=self._run_loop, daemon=True, name="narrative_organ"
        )
        self._thread.start()
        logger.info("NarrativeOrgan started (check every %ds)", CHECK_INTERVAL_SECONDS)
        return {"status": "started"}

    def stop(self):
        """Stop the periodic loop."""
        self._running = False
        return {"status": "stopped"}

    def status(self):
        return {
            "name": self.name,
            "enabled": self.enabled,
            "running": self._running,
            "processed_count": self._processed_count,
            "queue_size": len(list(NARRATIVE_QUEUE_DIR.glob("*.json"))) if NARRATIVE_QUEUE_DIR.exists() else 0,
        }

    def _run_loop(self):
        """Main loop: check for gaps → queue → process one → sleep → repeat."""
        while self._running:
            try:
                # Step 1: Gap detection — find unnarrated L5s
                new_items = self._detect_gaps()
                if new_items:
                    logger.info("NarrativeOrgan found %d unnarrated summaries", len(new_items))
                    for item in new_items:
                        self._enqueue(item)

                # Step 2: Process one from queue
                processed = self._process_one()
                if processed:
                    self._processed_count += 1

            except Exception as e:
                logger.error("NarrativeOrgan loop error: %s", e)

            # Sleep between checks
            for _ in range(CHECK_INTERVAL_SECONDS):
                if not self._running:
                    return
                time.sleep(1)

    def _detect_gaps(self) -> list:
        """Query CartON for narrative gaps at all levels.

        Checks:
        - Executive_Summary without Episode (L5 → harvest_episode)
        - Episode without Journey (episode accumulation → harvest_journey)
        - Journey without Epic (journey accumulation → harvest_epic)
        - Epic without Odyssey (epic accumulation → create_odyssey)
        """
        try:
            from carton_mcp.carton_utils import CartOnUtils
            carton = CartOnUtils()
            items = []

            # Level 1: Executive_Summary without Episode
            result = carton.query_wiki_graph(
                "MATCH (s:Wiki)-[:IS_A]->(:Wiki {n: 'Executive_Summary'}) "
                "WHERE NOT EXISTS { "
                "  MATCH (ep:Wiki)-[:IS_A]->(:Wiki {n: 'Episode'}) "
                "  WHERE ep.n CONTAINS s.n "
                "} "
                "RETURN s.n AS name ORDER BY s.t DESC LIMIT 10"
            )
            if result.get("success"):
                items.extend(r["name"] for r in result["data"])

            # Level 2: Episode without Journey (same GIINT_Component)
            result = carton.query_wiki_graph(
                "MATCH (ep:Wiki)-[:IS_A]->(:Wiki {n: 'Episode'}) "
                "WHERE NOT EXISTS { "
                "  MATCH (j:Wiki)-[:IS_A]->(:Wiki {n: 'Journey'}) "
                "  WHERE j.n CONTAINS ep.n "
                "} "
                "RETURN ep.n AS name ORDER BY ep.t DESC LIMIT 10"
            )
            if result.get("success"):
                items.extend(r["name"] for r in result["data"])

            # Level 3: Journey without Epic
            result = carton.query_wiki_graph(
                "MATCH (j:Wiki)-[:IS_A]->(:Wiki {n: 'Journey'}) "
                "WHERE NOT EXISTS { "
                "  MATCH (e:Wiki)-[:IS_A]->(:Wiki {n: 'Epic'}) "
                "  WHERE e.n CONTAINS j.n "
                "} "
                "RETURN j.n AS name ORDER BY j.t DESC LIMIT 10"
            )
            if result.get("success"):
                items.extend(r["name"] for r in result["data"])

            # Level 4: Epic without Odyssey
            result = carton.query_wiki_graph(
                "MATCH (e:Wiki)-[:IS_A]->(:Wiki {n: 'Epic'}) "
                "WHERE NOT EXISTS { "
                "  MATCH (o:Wiki)-[:IS_A]->(:Wiki {n: 'Odyssey'}) "
                "  WHERE o.n CONTAINS e.n "
                "} "
                "RETURN e.n AS name ORDER BY e.t DESC LIMIT 10"
            )
            if result.get("success"):
                items.extend(r["name"] for r in result["data"])

            # Level 5: Odyssey_Narrative_Decision without Episode (top-level: system narrating itself)
            result = carton.query_wiki_graph(
                "MATCH (s:Wiki)-[:IS_A]->(:Wiki {n: 'Odyssey_Narrative_Decision'}) "
                "WHERE NOT EXISTS { "
                "  MATCH (ep:Wiki)-[:IS_A]->(:Wiki {n: 'Episode'}) "
                "  WHERE ep.n CONTAINS s.n "
                "} "
                "RETURN s.n AS name ORDER BY s.t DESC LIMIT 10"
            )
            if result.get("success"):
                items.extend(r["name"] for r in result["data"])

            # Level 6: Friendship journal without Weekly_Story_Complete (weekly rollup needed)
            result = carton.query_wiki_graph(
                "MATCH (j:Wiki)-[:IS_A]->(:Wiki {n: 'Journal_Entry'}) "
                "WHERE j.n CONTAINS 'Friendship' "
                "AND NOT EXISTS { "
                "  MATCH (w:Wiki)-[:IS_A]->(:Wiki {n: 'Weekly_Story_Complete'}) "
                "  WHERE w.n CONTAINS substring(j.n, 14, 10) "
                "} "
                "RETURN j.n AS name ORDER BY j.t DESC LIMIT 5"
            )
            if result.get("success"):
                items.extend(r["name"] for r in result["data"])

            # Filter out already-queued items
            queued = {f.stem for f in NARRATIVE_QUEUE_DIR.glob("*.json")} if NARRATIVE_QUEUE_DIR.exists() else set()
            return [item for item in items if item not in queued]

        except Exception as e:
            logger.error("NarrativeOrgan gap detection failed: %s", e)
            return []

    def _enqueue(self, concept_name: str):
        """Add a concept to the narrative queue."""
        queue_file = NARRATIVE_QUEUE_DIR / f"{concept_name}.json"
        if not queue_file.exists():
            queue_file.write_text(json.dumps({
                "concept_ref": concept_name,
                "queued_at": time.time(),
                "status": "pending",
            }))
            logger.info("NarrativeOrgan queued: %s", concept_name)

    def _process_one(self) -> bool:
        """Process one item from the narrative queue."""
        if not NARRATIVE_QUEUE_DIR.exists():
            return False

        # Find oldest pending item
        pending = sorted(NARRATIVE_QUEUE_DIR.glob("*.json"), key=lambda f: f.stat().st_mtime)
        for queue_file in pending:
            try:
                data = json.loads(queue_file.read_text())
                if data.get("status") != "pending":
                    continue

                concept_ref = data["concept_ref"]
                logger.info("NarrativeOrgan processing: %s", concept_ref)

                # Mark as processing
                data["status"] = "processing"
                queue_file.write_text(json.dumps(data))

                # Check if this is a friendship journal → create Weekly_Story_Complete
                if "Journal_Entry" in concept_ref and "Friendship" in concept_ref:
                    try:
                        from carton_mcp.add_concept_tool import get_observation_queue_dir
                        import uuid
                        from datetime import datetime as _dt

                        date_str = _dt.now().strftime("%Y_%m_%d")
                        week_num = _dt.now().strftime("%Y_W%W")
                        queue_dir = get_observation_queue_dir()

                        week_data = {
                            "raw_concept": True,
                            "concept_name": f"Weekly_Story_Complete_{week_num}",
                            "description": f"Week {week_num} story completed via friendship ritual {concept_ref}. The friendship journal closes this week's narrative arc.",
                            "relationships": [
                                {"relationship": "is_a", "related": ["Weekly_Story_Complete"]},
                                {"relationship": "part_of", "related": [f"Month_{_dt.now().strftime('%Y_%m')}", "User_Autobiography_Timeline"]},
                                {"relationship": "has_friendship_journal", "related": [concept_ref]},
                            ],
                            "source": "narrative_organ",
                            "hide_youknow": True,
                        }
                        ts = _dt.now().strftime("%Y%m%d_%H%M%S%f")
                        carton_queue_file = queue_dir / f"{ts}_{uuid.uuid4().hex[:8]}.json"
                        with open(carton_queue_file, "w") as f:
                            json.dump(week_data, f)

                        logger.info("NarrativeOrgan: Weekly_Story_Complete_%s created from %s", week_num, concept_ref)
                        data["status"] = "done"
                        data["result"] = {"week": week_num, "type": "weekly_completion"}
                        queue_file_path = NARRATIVE_QUEUE_DIR / f"{concept_ref}.json"
                        queue_file_path.write_text(json.dumps(data))
                        return True
                    except Exception as e:
                        logger.error("NarrativeOrgan weekly completion error: %s", e)
                        # Fall through to normal dispatch

                # Dispatch to narrative harvest chain (episode → journey → epic → odyssey)
                from .utils import dispatch_chain
                results = dispatch_chain(concept_ref)

                # Mark as done (success if first step succeeded)
                first = results[0] if results else None
                data["status"] = "done" if (first and first.success) else "failed"
                data["result"] = {
                    "chain_length": len(results),
                    "steps": [
                        {"event_type": r.event_type, "success": r.success, "concepts": r.concepts_created}
                        for r in results
                    ],
                    "error": first.error if first and not first.success else None,
                }
                queue_file.write_text(json.dumps(data))

                logger.info("NarrativeOrgan processed: %s → %s", concept_ref, data["status"])
                return True

            except Exception as e:
                logger.error("NarrativeOrgan process error for %s: %s", queue_file.name, e)
                try:
                    data = json.loads(queue_file.read_text())
                    data["status"] = "failed"
                    data["error"] = str(e)
                    queue_file.write_text(json.dumps(data))
                except Exception:
                    pass

        return False
