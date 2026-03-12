"""
Business logic for OpenAI conversation ingestion - V2

Data files:
- canonical_registry.json: Source of truth for canonical frameworks
- state.json: Conversations, emergent frameworks, publishing sets, concept tags
- ingestion_waitlist.json: Claude Code conversations flagged for ingestion
"""
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Literal

from .models import (
    Registry, StrataEntry, StrataSlots,
    Pair, EmergentFramework, Conversation, PublishingSet,
    CanonicalFramework, JourneyMetadata
)

logger = logging.getLogger(__name__)

# =============================================================================
# FILE PATHS
# =============================================================================

CONV_DIR = "/tmp/conversation_ingestion_openai_paiab"
STATE_FILE = f"{CONV_DIR}/state.json"
REGISTRY_FILE = f"{CONV_DIR}/canonical_registry.json"


# =============================================================================
# REGISTRY FUNCTIONS
# =============================================================================

def load_registry() -> Registry:
    """Load canonical registry from JSON file."""
    if not os.path.exists(REGISTRY_FILE):
        # Return default registry with 3 strata
        return Registry(strata={
            "paiab": StrataEntry(
                name="PAIAB",
                description="Technical domain knowledge - AI, agents, tools, infrastructure",
                slots=StrataSlots()
            ),
            "sanctum": StrataEntry(
                name="SANCTUM",
                description="Personal philosophy - life architecture, coordination, integration",
                slots=StrataSlots()
            ),
            "cave": StrataEntry(
                name="CAVE",
                description="Business model - structure, positioning, content, automation, economics",
                slots=StrataSlots()
            )
        })

    with open(REGISTRY_FILE, 'r') as f:
        data = json.load(f)

    return Registry.model_validate(data)


def save_registry(registry: Registry):
    """Save canonical registry to JSON file."""
    with open(REGISTRY_FILE, 'w') as f:
        json.dump(registry.model_dump(), f, indent=2)


def validate_strata(strata_key: str, registry: Registry) -> bool:
    """Check if strata exists in registry."""
    return strata_key in registry.strata


def get_strata_keys(registry: Registry) -> List[str]:
    """Get list of valid strata keys from registry."""
    return list(registry.strata.keys())


# =============================================================================
# STATE FUNCTIONS (V2 Format)
# =============================================================================

def get_empty_state_v2() -> Dict:
    """Return empty V2 state structure."""
    return {
        "version": 2,
        "current_conversation": None,
        "current_index": 0,
        "concept_tags": [],
        "emergent_frameworks": {},
        "publishing_sets": {},
        "journey_metadata": {},
        "conversations": {}
    }


def load_state() -> Dict:
    """Load state file, auto-detecting version."""
    if not os.path.exists(STATE_FILE):
        return get_empty_state_v2()

    with open(STATE_FILE, 'r') as f:
        data = json.load(f)

    # Check version
    if data.get("version") == 2:
        return data

    # V1 format detected - keep as-is for backward compat
    # Migration happens explicitly via migrate_state_v1_to_v2()
    return data


def save_state(state: Dict):
    """Save state to disk."""
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def is_v2_state(state: Dict) -> bool:
    """Check if state is V2 format."""
    return state.get("version") == 2


def migrate_state_v1_to_v2(old_state: Dict) -> Dict:
    """
    Migrate V1 state to V2 format.

    V1 format:
    - tag_enum: flat list of all tags
    - tagged_pairs: {conv_name: {index: [tag1, tag2, ...]}}
    - injected_pairs: {conv_name: {index: true}}

    V2 format:
    - concept_tags: list (formerly tag_enum, minus strata/state tags)
    - emergent_frameworks: {} (fresh start)
    - publishing_sets: {} (fresh start)
    - conversations: {conv_name: {authorized_phase, publishing_set, pairs}}
    """
    new_state = get_empty_state_v2()

    # Preserve current conversation/index
    new_state["current_conversation"] = old_state.get("current_conversation")
    new_state["current_index"] = old_state.get("current_index", 0)

    # Migrate tag_enum to concept_tags (filter out meta tags)
    meta_tags = {"evolving", "definition", "paiab", "sanctum", "cave"}
    old_tags = old_state.get("tag_enum", [])
    new_state["concept_tags"] = [t for t in old_tags if t not in meta_tags]

    # Migrate tagged_pairs to conversations
    old_tagged = old_state.get("tagged_pairs", {})
    for conv_name, pairs_dict in old_tagged.items():
        new_state["conversations"][conv_name] = {
            "authorized_phase": 3,  # Start fresh
            "publishing_set": None,
            "pairs": pairs_dict  # Keep tag arrays as-is (will need prefix update)
        }

    return new_state


# =============================================================================
# CONVERSATION LOADING (unchanged from V1)
# =============================================================================

def load_conversations() -> Dict:
    """Load all conversation JSON files."""
    convs = {}
    for filepath in Path(CONV_DIR).glob("*.json"):
        # Skip state/registry files
        if filepath.name in ("state.json", "canonical_registry.json"):
            continue
        name = filepath.stem
        with open(filepath, 'r') as f:
            convs[name] = json.load(f)
    return convs


def load_conversation(name: str) -> Dict:
    """Load a single conversation JSON file by name."""
    filepath = Path(CONV_DIR) / f"{name}.json"
    if not filepath.exists():
        raise FileNotFoundError(f"Conversation '{name}' not found")
    with open(filepath, 'r') as f:
        return json.load(f)


def extract_io_pairs(conv_data: Dict) -> List[Tuple[str, str, str, str]]:
    """
    Extract IO pairs from conversation.
    Returns: [(user_id, user_msg, assistant_id, assistant_msg), ...]
    """
    mapping = conv_data['mapping']

    # Find root
    root_id = None
    for node_id, node in mapping.items():
        if node.get('parent') is None:
            root_id = node_id
            break

    if not root_id:
        return []

    # Iterative tree traversal
    pairs = []
    current_user = None
    current_user_id = None
    stack = [root_id]

    while stack:
        node_id = stack.pop()
        node = mapping.get(node_id)

        if not node:
            continue

        msg = node.get('message')
        if msg and msg.get('author'):
            role = msg['author']['role']
            content_obj = msg.get('content', {})

            # OpenAI format has content_type - skip non-text (thoughts, reasoning_recap)
            # Claude format has no content_type - proceed normally
            content_type = content_obj.get('content_type')
            if content_type is not None and content_type != 'text':
                for child_id in reversed(node.get('children', [])):
                    stack.append(child_id)
                continue

            content = content_obj.get('parts', [''])[0]

            if role == 'user':
                current_user = content
                current_user_id = node_id
            elif role == 'assistant' and current_user:
                pairs.append((current_user_id, current_user, node_id, content))
                current_user = None
                current_user_id = None

        # Add children to stack (reverse order for left-to-right traversal)
        for child_id in reversed(node.get('children', [])):
            stack.append(child_id)

    return pairs


# =============================================================================
# TAG PARSING
# =============================================================================

def parse_pair_tags(tags: List[str]) -> Pair:
    """Parse tag array into Pair model for validation."""
    return Pair.from_tag_array(tags)


def get_pair_tags(state: Dict, conv_name: str, index: int) -> List[str]:
    """Get raw tag array for a pair."""
    if is_v2_state(state):
        conv = state.get("conversations", {}).get(conv_name, {})
        return conv.get("pairs", {}).get(str(index), [])
    else:
        # V1 format
        return state.get("tagged_pairs", {}).get(conv_name, {}).get(str(index), [])


def get_pair_parsed(state: Dict, conv_name: str, index: int) -> Pair:
    """Get parsed Pair model for a pair."""
    tags = get_pair_tags(state, conv_name, index)
    return parse_pair_tags(tags)


# =============================================================================
# DISPLAY FORMATTING
# =============================================================================

def format_pair_display(
    index: int,
    user_msg: str,
    asst_msg: str,
    tags: List[str],
    phase: Optional[int] = None
) -> str:
    """Format a single pair for display."""
    tag_str = f" [tags: {', '.join(tags)}]" if tags else ""
    phase_str = f" (phase {phase})" if phase else ""

    return f"""Pair {index}{phase_str}{tag_str}
USER: {user_msg}
ASST: {asst_msg}"""


def format_pair_display_v2(
    index: int,
    user_msg: str,
    asst_msg: str,
    pair: Pair
) -> str:
    """Format a single pair with parsed Pair model."""
    parts = []
    if pair.strata:
        parts.append(f"strata:{pair.strata}")
    if pair.evolving:
        parts.append("evolving")
    if pair.definition:
        parts.append("definition")
    if pair.concept_tags:
        parts.extend(pair.concept_tags)
    if pair.emergent_framework:
        parts.append(f"emergent:{pair.emergent_framework}")

    tag_str = f" [{', '.join(parts)}]" if parts else ""
    phase = pair.get_phase()

    return f"""Pair {index} (phase {phase}){tag_str}
USER: {user_msg}
ASST: {asst_msg}"""


# =============================================================================
# COLLECTION HELPERS
# =============================================================================

def get_conversation_names(state: Dict) -> List[str]:
    """Get list of conversation names in state."""
    if is_v2_state(state):
        return list(state.get("conversations", {}).keys())
    else:
        return list(state.get("tagged_pairs", {}).keys())


def collect_pairs_by_concept_tag(
    state: Dict,
    concept_tag: str
) -> List[Dict]:
    """Collect all pairs with given concept tag."""
    if not is_v2_state(state):
        raise ValueError("collect_pairs_by_concept_tag requires V2 state format")

    collected = []

    for conv_name, conv_data in state.get("conversations", {}).items():
        try:
            conv = load_conversation(conv_name)
            pairs = extract_io_pairs(conv)
        except FileNotFoundError:
            continue

        for idx_str, tags in conv_data.get("pairs", {}).items():
            pair = parse_pair_tags(tags)
            if concept_tag in pair.concept_tags:
                idx = int(idx_str)
                if idx < len(pairs):
                    _, user_msg, _, asst_msg = pairs[idx]
                    collected.append({
                        'conversation': conv_name,
                        'index': idx,
                        'tags': tags,
                        'pair': pair.model_dump(),
                        'user': user_msg,
                        'assistant': asst_msg
                    })

    return collected


def collect_pairs_by_emergent_framework(
    state: Dict,
    emergent_name: str
) -> List[Dict]:
    """Collect all pairs assigned to an emergent framework."""
    if not is_v2_state(state):
        raise ValueError("collect_pairs_by_emergent_framework requires V2 state format")

    collected = []

    for conv_name, conv_data in state.get("conversations", {}).items():
        try:
            conv = load_conversation(conv_name)
            pairs = extract_io_pairs(conv)
        except FileNotFoundError:
            continue

        for idx_str, tags in conv_data.get("pairs", {}).items():
            pair = parse_pair_tags(tags)
            if pair.emergent_framework == emergent_name:
                idx = int(idx_str)
                if idx < len(pairs):
                    _, user_msg, _, asst_msg = pairs[idx]
                    collected.append({
                        'conversation': conv_name,
                        'index': idx,
                        'tags': tags,
                        'pair': pair.model_dump(),
                        'user': user_msg,
                        'assistant': asst_msg
                    })

    return collected


# =============================================================================
# EMERGENT FRAMEWORK HELPERS
# =============================================================================

def get_emergent_framework(state: Dict, name: str) -> Optional[Dict]:
    """Get emergent framework by name."""
    return state.get("emergent_frameworks", {}).get(name)


def save_emergent_framework(state: Dict, framework: EmergentFramework):
    """Save emergent framework to state."""
    if "emergent_frameworks" not in state:
        state["emergent_frameworks"] = {}
    state["emergent_frameworks"][framework.name] = framework.model_dump()


# =============================================================================
# PUBLISHING SET HELPERS
# =============================================================================

def get_publishing_set(state: Dict, name: str) -> Optional[Dict]:
    """Get publishing set by name."""
    return state.get("publishing_sets", {}).get(name)


def save_publishing_set(state: Dict, name: str, pub_set: PublishingSet):
    """Save publishing set to state."""
    if "publishing_sets" not in state:
        state["publishing_sets"] = {}
    state["publishing_sets"][name] = pub_set.model_dump()


# =============================================================================
# DEPRECATED (kept for backward compat)
# =============================================================================

PASS_TRACKER_FILE = f"{CONV_DIR}/pass_tracker.json"


def load_pass_tracker() -> Dict:
    """DEPRECATED: Pass tracking removed in V2."""
    if os.path.exists(PASS_TRACKER_FILE):
        with open(PASS_TRACKER_FILE, 'r') as f:
            return json.load(f)
    return {"conversations": {}, "meta": {"last_updated": None}}


def save_pass_tracker(tracker: Dict):
    """DEPRECATED: Pass tracking removed in V2."""
    tracker["meta"]["last_updated"] = datetime.now().isoformat()
    with open(PASS_TRACKER_FILE, 'w') as f:
        json.dump(tracker, f, indent=2)
