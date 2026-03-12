"""
SEED v0 Publishing Platform - Core Module
Transforms GIINT QA files into Carton concepts for knowledge publishing.
"""

import json
import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import traceback

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@dataclass
class IOPair:
    """Represents a single input/output pair from a QA conversation with complete GIINT metadata."""
    # Core conversation data
    input: str  # User prompt
    output: str  # Assistant response  
    qa_id: str  # Parent QA identifier
    sequence: int  # Order in conversation
    
    # Response metadata from GIINT
    response_id: int  # GIINT response ID
    timestamp: str  # When response was created
    one_liner: str  # Brief description
    key_tags: List[str]  # Tags from GIINT respond()
    involved_files: List[str]  # Files involved in response
    response_file: Optional[str]  # Path to response file
    
    # Project tracking metadata (from QA level, repeated for convenience)
    project_id: str
    created_at: str  # QA creation time
    is_from_waypoint: bool
    
    # GIINT tracking hierarchy
    feature: Optional[str] = None
    component: Optional[str] = None
    deliverable: Optional[str] = None
    subtask: Optional[str] = None
    task: Optional[str] = None
    workflow_id: Optional[str] = None


def _find_qa_file_path(qa_id: str) -> Path:
    """Find the QA JSON file path, trying multiple locations."""
    # Get base directory from environment variable
    base_dir = os.environ.get('LLM_INTELLIGENCE_DIR', '/tmp/llm_intelligence_responses')
    
    paths_to_try = [
        Path(base_dir) / "qa_sets" / qa_id / "qa.json",
        Path(base_dir) / qa_id / "qa.json"
    ]
    
    for path in paths_to_try:
        if path.exists():
            logger.debug(f"Found QA file at {path}")
            return path
    
    raise FileNotFoundError(f"QA file not found for {qa_id} at expected locations in {base_dir}")


def _load_qa_json(qa_path: Path) -> Dict[str, Any]:
    """Load and parse QA JSON file."""
    try:
        with open(qa_path, 'r') as f:
            qa_data = json.load(f)
        logger.debug(f"Successfully loaded QA JSON from {qa_path}")
        return qa_data
    except json.JSONDecodeError as e:
        logger.error(f"Malformed JSON in {qa_path}: {e}")
        raise json.JSONDecodeError(f"Malformed JSON in QA file: {e}", e.doc, e.pos)


def _create_io_pair_from_response(
    response: Dict[str, Any], 
    idx: int, 
    qa_id: str, 
    user_prompt: str,
    qa_data: Dict[str, Any]
) -> IOPair:
    """Create a single IOPair from response data with complete metadata."""
    # Determine input text
    if idx == 0:
        input_text = user_prompt
    else:
        input_text = f"[Continuation of conversation {qa_id}]"
    
    # Extract all response metadata
    output_text = response.get("response_content", "")
    response_id = response.get("response_id", idx + 1)
    timestamp = response.get("timestamp", datetime.now().isoformat())
    one_liner = response.get("one_liner", "")
    key_tags = response.get("key_tags", [])
    involved_files = response.get("involved_files", [])
    response_file = response.get("response_file", None)
    
    # Extract QA-level metadata
    project_id = qa_data.get("project_id", "")
    created_at = qa_data.get("created_at", "")
    tracking = qa_data.get("tracking", {})
    is_from_waypoint = tracking.get("is_from_waypoint", False)
    
    # Extract tracking hierarchy
    feature = tracking.get("feature", None)
    component = tracking.get("component", None)
    deliverable = tracking.get("deliverable", None)
    subtask = tracking.get("subtask", None)
    task = tracking.get("task", None)
    workflow_id = tracking.get("workflow_id", None)
    
    return IOPair(
        input=input_text,
        output=output_text,
        qa_id=qa_id,
        sequence=idx + 1,  # 1-indexed
        response_id=response_id,
        timestamp=timestamp,
        one_liner=one_liner,
        key_tags=key_tags,
        involved_files=involved_files,
        response_file=response_file,
        project_id=project_id,
        created_at=created_at,
        is_from_waypoint=is_from_waypoint,
        feature=feature,
        component=component,
        deliverable=deliverable,
        subtask=subtask,
        task=task,
        workflow_id=workflow_id
    )


def parse_qa_json(qa_id: str) -> List[IOPair]:
    """
    Parse GIINT QA JSON file into structured IO pairs.
    
    Args:
        qa_id: GIINT QA identifier (e.g., 'giint_explanation_2025')
        
    Returns:
        List of IOPair objects representing the conversation
    """
    logger.info(f"Parsing QA JSON for {qa_id}")
    
    # Find and load the QA file
    qa_path = _find_qa_file_path(qa_id)
    qa_data = _load_qa_json(qa_path)
    
    # Extract user prompt and responses
    user_prompt = qa_data.get("user_prompt_description", "")
    responses = qa_data.get("responses", [])
    
    # Create IO pairs with complete metadata
    io_pairs = []
    for idx, response in enumerate(responses):
        io_pair = _create_io_pair_from_response(response, idx, qa_id, user_prompt, qa_data)
        io_pairs.append(io_pair)
    
    logger.info(f"Created {len(io_pairs)} IO pairs from {qa_id}")
    return io_pairs


def _format_io_pair_description(io_pair: IOPair) -> str:
    """Format the description for an IO pair concept with complete metadata."""
    description = f"**Q**: {io_pair.input}\n\n**A**: {io_pair.output[:500]}..."
    if len(io_pair.output) > 500:
        description += f"\n\n[Full response contains {len(io_pair.output)} characters]"
    
    # Add metadata section
    description += f"\n\n## Metadata\n"
    description += f"- **One-liner**: {io_pair.one_liner}\n"
    description += f"- **Response ID**: {io_pair.response_id}\n"
    description += f"- **Project**: {io_pair.project_id}\n"
    description += f"- **Timestamp**: {io_pair.timestamp}\n"
    description += f"- **From Waypoint**: {io_pair.is_from_waypoint}\n"
    
    # Add tracking hierarchy
    if any([io_pair.feature, io_pair.component, io_pair.deliverable]):
        description += f"\n## Tracking Hierarchy\n"
        if io_pair.feature:
            description += f"- **Feature**: {io_pair.feature}\n"
        if io_pair.component:
            description += f"- **Component**: {io_pair.component}\n"
        if io_pair.deliverable:
            description += f"- **Deliverable**: {io_pair.deliverable}\n"
        if io_pair.subtask:
            description += f"- **Subtask**: {io_pair.subtask}\n"
        if io_pair.task:
            description += f"- **Task**: {io_pair.task}\n"
        if io_pair.workflow_id:
            description += f"- **Workflow ID**: {io_pair.workflow_id}\n"
    
    # Add involved files
    if io_pair.involved_files:
        description += f"\n## Involved Files\n"
        for file in io_pair.involved_files:
            description += f"- {file}\n"
    
    return description


def _build_io_pair_relationships(io_pair: IOPair, topic: str = None) -> List[Dict[str, Any]]:
    """Build relationships for an IO pair concept."""
    relationships = []
    
    # Link to parent QA file
    qa_file_concept = f"QA_File_{io_pair.qa_id}"
    if topic:
        qa_file_concept = f"QA_File_{io_pair.qa_id}_{topic.replace(' ', '_')}"
    
    relationships.append({
        "relationship": "part_of",
        "related": [qa_file_concept]
    })
    
    # Add tags as relationships
    if io_pair.key_tags:
        relationships.append({
            "relationship": "tagged_with",
            "related": io_pair.key_tags
        })
    
    # Link to next IO pair in sequence
    if io_pair.sequence > 0:
        relationships.append({
            "relationship": "followed_by",
            "related": [f"IO_Pair_{io_pair.qa_id}_{io_pair.sequence + 1:03d}"]
        })
    
    return relationships


def create_io_pair_concept_data(io_pair: IOPair, topic: str = None) -> Dict[str, Any]:
    """
    Create Carton concept data for a single IO pair.
    
    Args:
        io_pair: The IOPair to convert
        topic: Optional topic name for the QA conversation
        
    Returns:
        Dict with concept_name, description, and relationships
    """
    concept_name = f"IO_Pair_{io_pair.qa_id}_{io_pair.sequence:03d}"
    description = _format_io_pair_description(io_pair)
    relationships = _build_io_pair_relationships(io_pair, topic)
    
    return {
        "concept_name": concept_name,
        "description": description,
        "relationships": relationships
    }


def _extract_topic_from_qa_data(qa_data: Dict[str, Any]) -> str:
    """Extract topic from QA tracking data."""
    tracking = qa_data.get("tracking", {})
    return tracking.get("feature", "General_Discussion").replace(" ", "_")


def _format_rollup_description(qa_data: Dict[str, Any], io_pairs: List[IOPair]) -> str:
    """Format the description for a rollup QA concept."""
    user_prompt = qa_data.get("user_prompt_description", "Conversation")
    created_at = qa_data.get("created_at", "")
    project_id = qa_data.get("project_id", "")
    
    description = f"Full conversation about: {user_prompt}\n\n"
    description += f"Project: {project_id}\n"
    description += f"Created: {created_at}\n"
    description += f"Contains {len(io_pairs)} responses\n"
    
    # Add tracking hierarchy if available
    tracking = qa_data.get("tracking", {})
    if tracking:
        description += f"\nTracking Hierarchy:\n"
        description += f"- Feature: {tracking.get('feature', 'N/A')}\n"
        description += f"- Component: {tracking.get('component', 'N/A')}\n"
        description += f"- Deliverable: {tracking.get('deliverable', 'N/A')}\n"
    
    return description


def _collect_unique_tags(io_pairs: List[IOPair]) -> List[str]:
    """Collect all unique tags from IO pairs."""
    all_tags = set()
    for io_pair in io_pairs:
        all_tags.update(io_pair.key_tags)
    return list(all_tags)


def _build_rollup_relationships(
    qa_id: str, 
    io_pairs: List[IOPair], 
    tracking: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Build relationships for rollup QA concept."""
    relationships = []
    
    # Link to all IO pairs
    io_pair_concepts = [f"IO_Pair_{qa_id}_{i+1:03d}" for i in range(len(io_pairs))]
    if io_pair_concepts:
        relationships.append({
            "relationship": "contains",
            "related": io_pair_concepts
        })
    
    # Add tags
    all_tags = _collect_unique_tags(io_pairs)
    if all_tags:
        relationships.append({
            "relationship": "tagged_with",
            "related": all_tags
        })
    
    # Add high-level topic relationships
    if tracking:
        feature = tracking.get("feature", "").replace(" ", "_")
        component = tracking.get("component", "").replace(" ", "_")
        
        about_concepts = []
        if feature:
            about_concepts.append(feature)
        if component and component != feature:
            about_concepts.append(component)
            
        if about_concepts:
            relationships.append({
                "relationship": "about",
                "related": about_concepts
            })
    
    return relationships


def create_rollup_qa_concept_data(io_pairs: List[IOPair], qa_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create rollup QA file concept that links all IO pairs.
    
    Args:
        io_pairs: List of all IOPair objects in conversation
        qa_data: Original QA JSON data for metadata
        
    Returns:
        Dict with concept_name, description, and relationships
    """
    qa_id = qa_data.get("qa_id", "unknown")
    topic = _extract_topic_from_qa_data(qa_data)
    tracking = qa_data.get("tracking", {})
    
    concept_name = f"QA_File_{qa_id}_{topic}"
    description = _format_rollup_description(qa_data, io_pairs)
    relationships = _build_rollup_relationships(qa_id, io_pairs, tracking)
    
    return {
        "concept_name": concept_name,
        "description": description,
        "relationships": relationships
    }


def ingest_qaid_to_carton(qa_id: str) -> bool:
    """
    Main SEED ingestion function: transforms GIINT QA into Carton concepts.
    
    Args:
        qa_id: GIINT QA identifier
        
    Returns:
        bool: True if ingestion successful, False otherwise
    """
    logger.info(f"Starting SEED ingestion for QA {qa_id}")
    
    try:
        # Parse QA file into IO pairs with complete metadata
        io_pairs = parse_qa_json(qa_id)
        if not io_pairs:
            logger.warning(f"No IO pairs found for QA {qa_id}")
            return False
        
        # Load original QA data for rollup concept
        qa_path = _find_qa_file_path(qa_id)
        qa_data = _load_qa_json(qa_path)
        
        # Create individual IO pair concepts
        created_concepts = []
        for io_pair in io_pairs:
            try:
                concept_data = create_io_pair_concept_data(io_pair)
                
                # Import Carton function from installed package
                from carton_mcp.add_concept_tool import add_concept_tool_func

                result = add_concept_tool_func(
                    concept_name=concept_data["concept_name"],
                    description=concept_data["description"],
                    relationships=concept_data["relationships"]
                )
                
                created_concepts.append(concept_data["concept_name"])
                logger.info(f"Created IO pair concept: {concept_data['concept_name']}")
                
            except Exception as e:
                logger.error(f"Failed to create IO pair concept for sequence {io_pair.sequence}: {e}")
                # Continue with other concepts
        
        # Create rollup QA file concept
        try:
            rollup_data = create_rollup_qa_concept_data(io_pairs, qa_data)
            
            # Import Carton function from installed package
            from carton_mcp.add_concept_tool import add_concept_tool_func

            result = add_concept_tool_func(
                concept_name=rollup_data["concept_name"],
                description=rollup_data["description"],
                relationships=rollup_data["relationships"]
            )
            
            created_concepts.append(rollup_data["concept_name"])
            logger.info(f"Created rollup concept: {rollup_data['concept_name']}")
            
        except Exception as e:
            logger.error(f"Failed to create rollup concept: {e}")
            return False
        
        # Add to quarantine system (placeholder for now)
        try:
            _add_to_quarantine(rollup_data["concept_name"], qa_id, len(io_pairs))
            logger.info(f"Added {rollup_data['concept_name']} to quarantine")
        except Exception as e:
            logger.warning(f"Failed to add to quarantine: {e}")
            # Not critical - continue
        
        logger.info(f"Successfully ingested QA {qa_id}: created {len(created_concepts)} concepts")
        return True
        
    except Exception as e:
        logger.error(f"Failed to ingest QA {qa_id}: {e}")
        logger.debug(traceback.format_exc())
        return False


def _add_to_quarantine(concept_name: str, qa_id: str, io_pair_count: int):
    """Add concept to quarantine system using QuarantineManager."""
    from seed_quarantine import QuarantineManager, QuarantineEntry
    
    manager = QuarantineManager()
    entry = QuarantineEntry(
        concept_name=concept_name,
        qa_id=qa_id,
        created_at=datetime.now().isoformat(),
        io_pair_count=io_pair_count,
        concept_type="qa_file"
    )
    
    if manager.add_to_quarantine(entry):
        logger.debug(f"Added {concept_name} to quarantine")
    else:
        logger.warning(f"Failed to add {concept_name} to quarantine")


# Test the parser with example data
if __name__ == "__main__":
    # Test with a real QA file
    test_qa_id = "giint_explanation_2025"
    
    try:
        io_pairs = parse_qa_json(test_qa_id)
        print(f"Successfully parsed {len(io_pairs)} IO pairs from {test_qa_id}")
        
        # Test concept creation for first IO pair
        if io_pairs:
            io_concept = create_io_pair_concept_data(io_pairs[0], "GIINT_Documentation")
            print(f"\nFirst IO Pair Concept:")
            print(f"  Name: {io_concept['concept_name']}")
            print(f"  Tags: {io_pairs[0].tags}")
            
            # Test rollup concept
            qa_path = Path(f"/tmp/llm_intelligence_responses/qa_sets/{test_qa_id}/qa.json")
            with open(qa_path, 'r') as f:
                qa_data = json.load(f)
            
            rollup_concept = create_rollup_qa_concept_data(io_pairs, qa_data)
            print(f"\nRollup QA Concept:")
            print(f"  Name: {rollup_concept['concept_name']}")
            print(f"  Contains: {len(io_pairs)} IO pairs")
            
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()