"""
Business logic for conversation ingestion - V2

Storage: CartON (Neo4j + ChromaDB). No JSON fallbacks.
Converters: JSON transcript files (OpenAI, Claude Code, Anthropic) → CartON concepts.
"""
import json
import logging
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Literal

from .models import (
    Registry, StrataEntry, StrataSlots,
    Pair, EmergentFramework, Conversation, PublishingSet,
    CanonicalFramework, JourneyMetadata
)

logger = logging.getLogger(__name__)

# Bundle output directory (used by bundle_tools for output artifacts)
CONV_DIR = "/tmp/conversation_ingestion_openai_paiab"

# CartON concept names for state storage
_STATE_CONCEPT = "Ingestion_State"
_REGISTRY_CONCEPT = "Ingestion_Registry"


def _read_concept_json(concept_name: str) -> Optional[Dict]:
    """Read a CartON concept description as JSON via carton_mcp."""
    try:
        from carton_mcp.carton_utils import shared_neo4j
        with shared_neo4j.driver.session() as s:
            result = s.run("MATCH (c:Wiki {n: $name}) RETURN c.d AS desc", name=concept_name).single()
        if result and result["desc"]:
            return json.loads(result["desc"])
    except json.JSONDecodeError:
        logger.warning("CartON concept %s description is not valid JSON", concept_name)
    except Exception as e:
        logger.warning("CartON read failed for %s: %s", concept_name, e)
    return None


def _write_concept_json(concept_name: str, data: Dict, is_a: str = "Ingestion_Data"):
    """Write a dict as JSON to a CartON concept via add_concept_tool_func."""
    from carton_mcp.add_concept_tool import add_concept_tool_func
    desc = json.dumps(data, indent=2, default=str)
    add_concept_tool_func(
        concept_name=concept_name,
        description=desc,
        relationships=[
            {"relationship": "is_a", "related": [is_a]},
            {"relationship": "part_of", "related": ["Ingestion_System"]},
            {"relationship": "instantiates", "related": [f"{is_a}_Template"]},
        ],
        desc_update_mode="replace",
        hide_youknow=True,
    )


# =============================================================================
# REGISTRY FUNCTIONS
# =============================================================================

_DEFAULT_REGISTRY = Registry(strata={
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


def load_registry() -> Registry:
    """Load canonical registry from CartON."""
    data = _read_concept_json(_REGISTRY_CONCEPT)
    if data:
        return Registry.model_validate(data)
    return _DEFAULT_REGISTRY


def save_registry(registry: Registry):
    """Save canonical registry to CartON."""
    data = registry.model_dump()
    _write_concept_json(_REGISTRY_CONCEPT, data, is_a="Ingestion_Registry")


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
    """Load state from CartON."""
    data = _read_concept_json(_STATE_CONCEPT)
    if data and data.get("version") == 2:
        return data
    return get_empty_state_v2()


def save_state(state: Dict):
    """Save state to CartON."""
    _write_concept_json(_STATE_CONCEPT, state, is_a="Ingestion_State")


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
# CONVERSATION LOADING — CartON first, JSON file fallback
# =============================================================================

def load_conversations() -> Dict:
    """Load all conversations from CartON."""
    convs = {}
    from carton_mcp.carton_utils import shared_neo4j
    with shared_neo4j.driver.session() as s:
        result = s.run(
            "MATCH (c:Wiki)-[:IS_A]->(:Wiki {n: 'Conversation'}) "
            "RETURN c.n AS name"
        )
        for r in result:
            convs[r["name"]] = {"source": "carton", "name": r["name"]}
    return convs


def load_conversation(name: str) -> Dict:
    """Load a single conversation from CartON."""
    from carton_mcp.carton_utils import shared_neo4j
    with shared_neo4j.driver.session() as s:
        result = s.run(
            "MATCH (conv:Wiki {n: $name})-[ir]->(iter:Wiki) "
            "WHERE type(ir) STARTS WITH 'HAS_ITERATION_' "
            "OPTIONAL MATCH (iter)-[mr]->(msg:Wiki) "
            "WHERE type(mr) STARTS WITH 'HAS_USER_MESSAGE_' "
            "   OR type(mr) STARTS WITH 'HAS_AGENT_MESSAGE_' "
            "RETURN iter.n AS iter_name, type(mr) AS msg_type, "
            "       msg.n AS msg_name, msg.d AS msg_content "
            "ORDER BY iter.n, msg_type",
            name=name,
        )
        rows = list(result)

    if not rows or not rows[0]["iter_name"]:
        raise FileNotFoundError(f"Conversation '{name}' not found in CartON")

    iterations = {}
    for row in rows:
        iter_name = row["iter_name"]
        if iter_name not in iterations:
            iterations[iter_name] = {"user": "", "agent": ""}
        msg_type = row.get("msg_type") or ""
        content = row.get("msg_content") or ""
        if "USER_MESSAGE" in msg_type:
            iterations[iter_name]["user"] += content + "\n"
        elif "AGENT_MESSAGE" in msg_type:
            iterations[iter_name]["agent"] += content + "\n"

    return {
        "source": "carton",
        "name": name,
        "iterations": [
            {"user": v["user"].strip(), "agent": v["agent"].strip()}
            for v in iterations.values()
        ],
    }


def extract_io_pairs(conv_data: Dict) -> List[Tuple[str, str, str, str]]:
    """
    Extract IO pairs from CartON conversation data.
    Returns: [(user_id, user_msg, assistant_id, assistant_msg), ...]
    """
    pairs = []
    for i, iteration in enumerate(conv_data.get("iterations", [])):
        user_msg = iteration.get("user", "")
        agent_msg = iteration.get("agent", "")
        if user_msg and agent_msg:
            pairs.append((f"u_{i}", user_msg, f"a_{i}", agent_msg))
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
# CONVERTERS — JSON transcript files → CartON concepts
# =============================================================================

def _extract_pairs_from_openai_mapping(mapping: Dict) -> List[Tuple[str, str, str, str]]:
    """Walk OpenAI mapping tree and extract (user_id, user_msg, asst_id, asst_msg) tuples."""
    root_id = None
    for node_id, node in mapping.items():
        if node.get('parent') is None:
            root_id = node_id
            break
    if not root_id:
        return []

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

        for child_id in reversed(node.get('children', [])):
            stack.append(child_id)

    return pairs


def _ingest_pairs_to_carton(conv_name: str, pairs: List[Tuple[str, str, str, str]]) -> int:
    """Create typed CartON concepts for a conversation and its iterations/messages."""
    from carton_mcp.add_concept_tool import add_concept_tool_func

    # Create Conversation concept
    add_concept_tool_func(
        concept_name=conv_name,
        description=f"Ingested conversation with {len(pairs)} iterations",
        relationships=[
            {"relationship": "is_a", "related": ["Conversation"]},
            {"relationship": "part_of", "related": ["Ingestion_System"]},
            {"relationship": "instantiates", "related": ["Conversation_Template"]},
        ],
        desc_update_mode="replace",
        hide_youknow=True,
    )

    for i, (u_id, user_msg, a_id, asst_msg) in enumerate(pairs):
        iter_name = f"Iteration_{conv_name}_{i}"
        user_name = f"User_Message_{conv_name}_{i}"
        agent_name = f"Agent_Message_{conv_name}_{i}"

        # Iteration
        add_concept_tool_func(
            concept_name=iter_name,
            description=f"Iteration {i} of {conv_name}",
            relationships=[
                {"relationship": "is_a", "related": ["Iteration"]},
                {"relationship": "part_of", "related": [conv_name]},
                {"relationship": "instantiates", "related": ["Iteration_Template"]},
                {"relationship": f"has_user_message_1", "related": [user_name]},
                {"relationship": f"has_agent_message_1", "related": [agent_name]},
            ],
            desc_update_mode="replace",
            hide_youknow=True,
        )

        # User message
        add_concept_tool_func(
            concept_name=user_name,
            description=user_msg,
            relationships=[
                {"relationship": "is_a", "related": ["User_Message"]},
                {"relationship": "part_of", "related": [iter_name]},
                {"relationship": "instantiates", "related": ["User_Message_Template"]},
            ],
            desc_update_mode="replace",
            hide_youknow=True,
        )

        # Agent message
        add_concept_tool_func(
            concept_name=agent_name,
            description=asst_msg,
            relationships=[
                {"relationship": "is_a", "related": ["Agent_Message"]},
                {"relationship": "part_of", "related": [iter_name]},
                {"relationship": "instantiates", "related": ["Agent_Message_Template"]},
            ],
            desc_update_mode="replace",
            hide_youknow=True,
        )

    # Add HAS_ITERATION_N relationships to conversation
    iter_rels = [
        {"relationship": f"has_iteration_{i+1}", "related": [f"Iteration_{conv_name}_{i}"]}
        for i in range(len(pairs))
    ]
    if iter_rels:
        add_concept_tool_func(
            concept_name=conv_name,
            description=f"Ingested conversation with {len(pairs)} iterations",
            relationships=[
                {"relationship": "is_a", "related": ["Conversation"]},
                {"relationship": "part_of", "related": ["Ingestion_System"]},
                {"relationship": "instantiates", "related": ["Conversation_Template"]},
            ] + iter_rels,
            desc_update_mode="replace",
            hide_youknow=True,
        )

    return len(pairs)


def ingest_openai_transcript(filepath: str, conv_name: Optional[str] = None) -> str:
    """Convert OpenAI JSON export to CartON concepts.

    Reads the OpenAI mapping tree format, extracts user/assistant pairs,
    and creates typed CartON concepts (Conversation, Iteration, User_Message, Agent_Message).

    Args:
        filepath: Path to OpenAI JSON export file.
        conv_name: Optional name for the conversation concept. Defaults to filename stem.

    Returns:
        Summary of ingested data.
    """
    path = Path(filepath)
    if not path.exists():
        return f"File not found: {filepath}"

    with open(path, 'r') as f:
        data = json.load(f)

    if 'mapping' not in data:
        return f"Not an OpenAI export (no 'mapping' key): {filepath}"

    if not conv_name:
        conv_name = f"Conversation_{path.stem}"

    pairs = _extract_pairs_from_openai_mapping(data['mapping'])
    if not pairs:
        return f"No user/assistant pairs found in {filepath}"

    count = _ingest_pairs_to_carton(conv_name, pairs)
    return f"Ingested {count} pairs from OpenAI export → CartON as {conv_name}"


def ingest_claude_transcript(filepath: str, slug: Optional[str] = None) -> str:
    """Convert Claude Code .jsonl transcript to CartON concepts.

    Uses claude_transcript_utils to parse the JSONL, segments by slug,
    and creates typed CartON concepts for each conversation.

    Args:
        filepath: Path to Claude Code .jsonl transcript file.
        slug: Optional specific slug to ingest. If None, ingests all conversations.

    Returns:
        Summary of ingested data.
    """
    from .claude_transcript_utils import (
        parse_transcript_file, segment_by_slug
    )

    path = Path(filepath)
    if not path.exists():
        return f"File not found: {filepath}"

    entries = parse_transcript_file(filepath)
    if not entries:
        return f"No entries found in {filepath}"

    conversations = segment_by_slug(entries)
    if slug:
        if slug not in conversations:
            return f"Slug '{slug}' not found. Available: {list(conversations.keys())}"
        conversations = {slug: conversations[slug]}

    results = []
    for conv_slug, conv in conversations.items():
        conv_name = f"Conversation_{conv_slug}"

        # Extract user/assistant pairs from transcript entries
        pairs = []
        user_entries = conv.user_entries
        asst_entries = conv.assistant_entries

        # Pair up user and assistant messages in order
        for i, (u_entry, a_entry) in enumerate(zip(user_entries, asst_entries)):
            user_text = u_entry.extract_text()
            asst_text = a_entry.extract_text()
            if user_text and asst_text:
                pairs.append((u_entry.uuid, user_text, a_entry.uuid, asst_text))

        if pairs:
            count = _ingest_pairs_to_carton(conv_name, pairs)
            results.append(f"  {conv_name}: {count} pairs")

    if not results:
        return f"No pairs extracted from {filepath}"

    return f"Ingested Claude transcript → CartON:\n" + "\n".join(results)
