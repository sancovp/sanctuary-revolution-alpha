"""
Emergent framework tools for conversation ingestion.

Tools: add_or_update_emergent_framework, assign_canonical_to_emergent
"""

from . import utils


def add_emergent_from_kg(
    name: str,
    strata: str,
    description: str,
    collection_ref: str,
    part_of: str = None,
    has_parts: list = None,
    related_to: list = None
) -> str:
    """
    Add an emergent framework sourced from a knowledge graph collection.

    KG-sourced emergents skip Phases 1-4 (no conversation extraction needed).
    They start directly at Phase 5 synthesis.

    The collection_ref tells you where to retrieve the distilled content from.
    For CartON: use format "carton://collections/{collection_name}"

    Args:
        name: Framework name
        strata: paiab | sanctum | cave
        description: Short definition of what this framework IS
        collection_ref: URI to the KG collection (e.g., "carton://collections/PAIA_Architecture")
        part_of: Optional parent framework
        has_parts: Optional child frameworks
        related_to: Optional related frameworks

    Returns:
        Success message with next steps for synthesis
    """
    state = utils.load_state()
    registry = utils.load_registry()

    if not description or not description.strip():
        return (
            f"BLOCKED: Description is REQUIRED for emergent framework '{name}'.\n"
            f"→ Provide a short definition of what this framework IS."
        )

    valid_strata = list(registry.strata.keys())
    if strata not in valid_strata:
        return (
            f"BLOCKED: Invalid strata '{strata}'.\n"
            f"Valid strata: {valid_strata}\n"
            f"→ Use add_strata('{strata}', 'description') to add it first."
        )

    if not utils.is_v2_state(state):
        return "BLOCKED: add_emergent_from_kg requires V2 state format."

    if "emergent_frameworks" not in state:
        state["emergent_frameworks"] = {}

    is_update = name in state["emergent_frameworks"]

    # Preserve existing fields if updating
    existing = state["emergent_frameworks"].get(name, {})
    existing_canonical = existing.get("canonical_framework")
    existing_document = existing.get("document")

    state["emergent_frameworks"][name] = {
        "name": name,
        "strata": strata,
        "description": description.strip(),
        "source_type": "kg_collection",
        "source_ref": collection_ref,
        "canonical_framework": existing_canonical,
        "bundled_pairs": {},  # KG sources don't have bundled pairs
        "document": existing_document,
        "part_of": part_of,
        "has_parts": has_parts or [],
        "related_to": related_to or []
    }

    utils.save_state(state)

    action = "Updated" if is_update else "Added"

    return (
        f"✓ {action} KG-sourced emergent framework: {name}\n"
        f"  strata: {strata}\n"
        f"  source: {collection_ref}\n"
        f"  description: {description.strip()[:100]}...\n\n"
        f"NEXT STEPS (starts at Phase 5):\n"
        f"1. Retrieve the collection: {collection_ref}\n"
        f"2. Create synthesis skeleton: set_emergent_document('{name}')\n"
        f"3. Fill in the JSON fields iteratively\n"
        f"4. Score with framework-scorer until 6/6\n"
        f"5. Assign to canonical: assign_canonical_to_emergent('{name}', canonical_name)"
    )


def add_or_update_emergent_framework(
    name: str,
    strata: str,
    description: str,
    part_of: str = None,
    has_parts: list = None,
    related_to: list = None
) -> str:
    """
    Add new or update existing emergent framework.

    REQUIRES description - emergent frameworks MUST have a definition of what they ARE.
    Type/state belong to canonicals, not emergents.
    Emergent = discovered cluster of content in a domain.

    Args:
        name: Framework name (e.g., "SOSEEH_Framework")
        strata: paiab | sanctum | cave (validated against registry)
        description: REQUIRED - Short definition of what this framework IS
        part_of: Optional parent framework this is a component of
        has_parts: Optional list of child frameworks that are components of this
        related_to: Optional list of sibling/related frameworks
    """
    state = utils.load_state()
    registry = utils.load_registry()

    # Validate description is not empty
    if not description or not description.strip():
        return (
            f"BLOCKED: Description is REQUIRED for emergent framework '{name}'.\n"
            f"→ Provide a short definition of what this framework IS."
        )

    # Validate strata
    valid_strata = list(registry.strata.keys())
    if strata not in valid_strata:
        return (
            f"BLOCKED: Invalid strata '{strata}'.\n"
            f"Valid strata: {valid_strata}\n"
            f"→ Use add_strata('{strata}', 'description') to add it first."
        )

    if not utils.is_v2_state(state):
        return "BLOCKED: add_or_update_emergent_framework requires V2 state format."

    if "emergent_frameworks" not in state:
        state["emergent_frameworks"] = {}

    is_update = name in state["emergent_frameworks"]

    # Preserve fields if updating
    existing = state["emergent_frameworks"].get(name, {})
    existing_canonical = existing.get("canonical_framework")
    existing_document = existing.get("document")
    existing_part_of = existing.get("part_of")
    existing_has_parts = existing.get("has_parts", [])
    existing_related_to = existing.get("related_to", [])

    # bundled_pairs is always computed dynamically from emergent_framework: tags
    # No caching - always recompute when needed via _compute_bundled_pairs
    bundled_pairs = _compute_bundled_pairs(state, name)
    pairs_found = sum(len(p) for p in bundled_pairs.values())

    # Use provided values or preserve existing
    final_part_of = part_of if part_of is not None else existing_part_of
    final_has_parts = has_parts if has_parts is not None else existing_has_parts
    final_related_to = related_to if related_to is not None else existing_related_to

    state["emergent_frameworks"][name] = {
        "name": name,
        "strata": strata,
        "description": description.strip(),
        "canonical_framework": existing_canonical,
        "bundled_pairs": bundled_pairs,
        "document": existing_document,
        "part_of": final_part_of,
        "has_parts": final_has_parts,
        "related_to": final_related_to
    }

    utils.save_state(state)

    action = "Updated" if is_update else "Added"
    total_pairs = sum(len(p) for p in bundled_pairs.values())

    # Build relationship info for output
    rel_info = []
    if final_part_of:
        rel_info.append(f"part_of: {final_part_of}")
    if final_has_parts:
        rel_info.append(f"has_parts: {final_has_parts}")
    if final_related_to:
        rel_info.append(f"related_to: {final_related_to}")
    rel_str = "\n  ".join(rel_info) if rel_info else "no relationships"

    return f"✓ {action} emergent framework: {name} (strata: {strata})\n  Description: {description.strip()[:100]}...\n  Auto-found {pairs_found} new pairs (total: {total_pairs})\n  {rel_str}"


def assign_canonical_to_emergent(emergent_name: str, canonical_name: str) -> str:
    """
    Assign a canonical framework to an emergent framework.

    Only allowed when conversation is in Phase 5.
    Validates:
    - Canonical exists in registry
    - Emergent's strata matches canonical's strata

    Args:
        emergent_name: Name of the emergent framework
        canonical_name: Name of the canonical framework from registry
    """
    state = utils.load_state()
    registry = utils.load_registry()

    if not utils.is_v2_state(state):
        return "BLOCKED: assign_canonical_to_emergent requires V2 state format."

    # Check current conversation phase
    conv_name = state.get('current_conversation')
    if not conv_name:
        return "BLOCKED: No conversation selected.\n→ Use set_conversation() first."

    conv_data = state.get("conversations", {}).get(conv_name, {})
    current_phase = conv_data.get("authorized_phase", 3)

    if current_phase < 5:
        return (
            f"BLOCKED: Cannot assign canonical to emergent '{emergent_name}'.\n"
            f"Conversation '{conv_name}' is not in Phase 5.\n"
            f"Current phase: {current_phase}\n"
            f"→ Complete Phase 4 and get user authorization for Phase 5 first."
        )

    # Check emergent exists
    emergent = state.get("emergent_frameworks", {}).get(emergent_name)
    if not emergent:
        return (
            f"BLOCKED: Emergent framework '{emergent_name}' does not exist.\n"
            f"→ First create it using: add_or_update_emergent_framework('{emergent_name}', strata)"
        )

    # Check canonical exists in registry
    canonical_info = registry.get_canonical(canonical_name)
    if not canonical_info:
        return (
            f"BLOCKED: Cannot assign canonical '{canonical_name}' to emergent '{emergent_name}'.\n"
            f"Canonical framework '{canonical_name}' does not exist in registry.\n"
            f"→ First add the canonical using: add_canonical_framework(strata, slot_type, '{canonical_name}', framework_state)"
        )

    # Check strata match
    emergent_strata = emergent.get("strata")
    canonical_strata = canonical_info[1]  # (type, strata, framework_state)

    if emergent_strata != canonical_strata:
        return (
            f"BLOCKED: Cannot assign canonical '{canonical_name}' to emergent '{emergent_name}'.\n"
            f"Strata mismatch: Emergent is '{emergent_strata}', canonical is '{canonical_strata}'.\n"
            f"→ Emergent frameworks can only be assigned to canonicals in the same strata."
        )

    # Assign
    state["emergent_frameworks"][emergent_name]["canonical_framework"] = canonical_name
    utils.save_state(state)

    return f"✓ Assigned canonical '{canonical_name}' to emergent '{emergent_name}'"


# =============================================================================
# EMERGENT FRAMEWORK SYNTHESIS TOOLS (Phase 4b)
# =============================================================================

def list_emergent_frameworks() -> str:
    """
    List all emergent frameworks with pair counts and synthesis status.

    Shows:
    - Name and strata
    - Pair count (how many pairs assigned)
    - Synthesis status (has document or not)
    - Canonical assignment (if any)
    """
    state = utils.load_state()

    if not utils.is_v2_state(state):
        return "BLOCKED: list_emergent_frameworks requires V2 state format."

    emergents = state.get("emergent_frameworks", {})

    if not emergents:
        return "No emergent frameworks found."

    lines = ["Emergent Frameworks:", "=" * 60]

    for name, data in sorted(emergents.items()):
        strata = data.get("strata", "?")
        description = data.get("description", "⚠️ NO DESCRIPTION")
        canonical = data.get("canonical_framework")
        document = data.get("document")
        bundled_pairs = data.get("bundled_pairs", {})
        part_of = data.get("part_of")
        has_parts = data.get("has_parts", [])
        related_to = data.get("related_to", [])
        source_type = data.get("source_type", "conversation")
        source_ref = data.get("source_ref")

        # Count total pairs across all conversations
        pair_count = sum(len(pairs) for pairs in bundled_pairs.values())

        # Status indicators
        doc_status = "✓ document" if document else "○ no document"
        canon_status = f"→ {canonical}" if canonical else "○ no canonical"
        source_indicator = f"📚 {source_ref}" if source_type == "kg_collection" else f"💬 {pair_count} pairs"

        lines.append(f"\n{name}")
        lines.append(f"  description: {description[:150]}...")
        lines.append(f"  strata: {strata}")
        lines.append(f"  source: {source_indicator}")
        lines.append(f"  synthesis: {doc_status}")
        lines.append(f"  canonical: {canon_status}")
        # Relationship fields
        if part_of:
            lines.append(f"  part_of: {part_of}")
        if has_parts:
            lines.append(f"  has_parts: {has_parts}")
        if related_to:
            lines.append(f"  related_to: {related_to}")

    # Summary
    total = len(emergents)
    with_docs = sum(1 for e in emergents.values() if e.get("document"))
    with_canon = sum(1 for e in emergents.values() if e.get("canonical_framework"))

    lines.append("\n" + "=" * 60)
    lines.append(f"Total: {total} emergents")
    lines.append(f"With documents: {with_docs}/{total}")
    lines.append(f"Assigned to canonicals: {with_canon}/{total}")

    return "\n".join(lines)


def delete_emergent_framework(name: str) -> str:
    """
    Delete an emergent framework.

    Args:
        name: Name of the emergent framework to delete
    """
    state = utils.load_state()

    if not utils.is_v2_state(state):
        return "BLOCKED: delete_emergent_framework requires V2 state format."

    emergents = state.get("emergent_frameworks", {})

    if name not in emergents:
        return f"BLOCKED: Emergent framework '{name}' does not exist."

    # Check if it has pairs - warn but allow
    bundled_pairs = emergents[name].get("bundled_pairs", {})
    pair_count = sum(len(p) for p in bundled_pairs.values())

    del state["emergent_frameworks"][name]
    utils.save_state(state)

    if pair_count > 0:
        return f"✓ Deleted emergent framework '{name}' (had {pair_count} pairs - pair tags NOT removed)"
    else:
        return f"✓ Deleted emergent framework '{name}'"


def get_emergent_pairs(emergent_name: str) -> str:
    """
    Get all pairs assigned to an emergent framework.

    Returns pairs formatted for LLM to read and synthesize.
    Grouped by conversation.

    Args:
        emergent_name: Name of the emergent framework
    """
    state = utils.load_state()

    if not utils.is_v2_state(state):
        return "BLOCKED: get_emergent_pairs requires V2 state format."

    emergent = state.get("emergent_frameworks", {}).get(emergent_name)
    if not emergent:
        return f"BLOCKED: Emergent framework '{emergent_name}' does not exist."

    # Always compute bundled_pairs from emergent_framework: tags (never trust cache)
    bundled_pairs = _compute_bundled_pairs(state, emergent_name)

    if not bundled_pairs:
        return f"No pairs assigned to emergent framework '{emergent_name}'."

    lines = [f"Pairs for emergent framework: {emergent_name}", "=" * 60]

    total_pairs = 0
    for conv_name, pair_indices in sorted(bundled_pairs.items()):
        lines.append(f"\n## Conversation: {conv_name}")

        # Load conversation file to get actual pair content
        try:
            conv_data = utils.load_conversation(conv_name)
            pairs = utils.extract_io_pairs(conv_data)
        except FileNotFoundError:
            lines.append(f"  (conversation file not found)")
            continue
        except Exception as e:
            import traceback
            lines.append(f"  (error loading pairs: {e})\n{traceback.format_exc()}")
            continue

        for idx in sorted(pair_indices):
            if idx < len(pairs):
                # pairs is list of tuples: (user_id, user_msg, assistant_id, assistant_msg)
                pair = pairs[idx]
                user = pair[1] or ""
                assistant = pair[3] or ""
                lines.append(f"\n--- Pair {idx} ---")
                lines.append(f"User: {user}")
                lines.append(f"Assistant: {assistant}")
                total_pairs += 1

    lines.append("\n" + "=" * 60)
    lines.append(f"Total: {total_pairs} pairs")

    return "\n".join(lines)


def _compute_bundled_pairs(state: dict, emergent_name: str) -> dict:
    """
    Compute bundled pairs from tagged pairs in state.

    Scans all conversations for pairs tagged with this emergent framework.
    Returns: {conversation_name: [pair_indices]}
    """
    bundled = {}
    conversations = state.get("conversations", {})

    for conv_name, conv_data in conversations.items():
        pairs = conv_data.get("pairs", {})
        matching_indices = []

        for pair_idx, tags in pairs.items():
            # Check if this pair is tagged with this emergent
            for tag in tags:
                if tag == f"emergent_framework:{emergent_name}":
                    matching_indices.append(int(pair_idx))
                    break

        if matching_indices:
            bundled[conv_name] = sorted(matching_indices)

    return bundled


def synthesize_emergent(emergent_name: str) -> str:
    """
    Synthesize a document for an emergent framework from its bundled pairs.

    This is a manual synthesis step - the LLM reads the pairs via get_emergent_pairs()
    and then writes a synthesized document via set_emergent_document().

    This tool returns guidance for how to synthesize.

    Args:
        emergent_name: Name of the emergent framework
    """
    state = utils.load_state()

    if not utils.is_v2_state(state):
        return "BLOCKED: synthesize_emergent requires V2 state format."

    emergent = state.get("emergent_frameworks", {}).get(emergent_name)
    if not emergent:
        return f"BLOCKED: Emergent framework '{emergent_name}' does not exist."

    # Check if already has document
    existing_doc = emergent.get("document")
    if existing_doc:
        return (
            f"Emergent '{emergent_name}' already has a document.\n"
            f"Current document:\n{existing_doc[:500]}...\n\n"
            f"To update, use set_emergent_document('{emergent_name}', new_document)"
        )

    # Always compute bundled_pairs from emergent_framework: tags
    bundled_pairs = _compute_bundled_pairs(state, emergent_name)
    pair_count = sum(len(p) for p in bundled_pairs.values())

    return (
        f"SYNTHESIS WORKFLOW for '{emergent_name}':\n"
        f"=" * 60 + "\n\n"
        f"1. Review pairs: get_emergent_pairs('{emergent_name}')\n"
        f"   ({pair_count} pairs across {len(bundled_pairs)} conversations)\n\n"
        f"2. Read the pairs and extract the coherent meaning\n"
        f"   - What IS this emergent framework?\n"
        f"   - What are its core components?\n"
        f"   - How does it work?\n\n"
        f"3. Write the synthesized document:\n"
        f"   set_emergent_document('{emergent_name}', document)\n\n"
        f"The document should capture the essence of what was discovered\n"
        f"in these pairs - this will be composed into the canonical later."
    )


def set_emergent_document(emergent_name: str) -> str:
    """
    Create the JSON file for an emergent framework (Phase 5).

    Vendors a JSON skeleton at the known path. You then edit the JSON
    directly to fill in the content.

    Args:
        emergent_name: Name of the emergent framework (must exist in state)

    Returns:
        Path to the JSON file, or error if already exists
    """
    import os
    import json

    state = utils.load_state()

    if not utils.is_v2_state(state):
        return "BLOCKED: set_emergent_document requires V2 state format."

    emergent = state.get("emergent_frameworks", {}).get(emergent_name)
    if not emergent:
        return f"BLOCKED: Emergent framework '{emergent_name}' does not exist.\n→ First create it using: add_or_update_emergent_framework('{emergent_name}', strata, description)"

    # Get path from environment
    heaven_data_dir = os.environ["HEAVEN_DATA_DIR"]
    frameworks_dir = os.path.join(heaven_data_dir, "frameworks")
    json_path = os.path.join(frameworks_dir, f"emergent_{emergent_name}.json")

    # Check if already exists
    if os.path.exists(json_path):
        return f"JSON already exists at: {json_path}\n→ Edit that file directly to modify content."

    # Create frameworks directory if needed
    os.makedirs(frameworks_dir, exist_ok=True)

    # Create skeleton JSON with Hero's Journey instruction placeholders
    # CRITICAL: Fields must be filled ONE AT A TIME, iteratively, across MULTIPLE RESPONSES
    skeleton = {
        "name": emergent_name,
        "strata": emergent.get("strata", ""),
        "_CRITICAL_PROCESS": "⚠️ DO NOT FILL ALL FIELDS AT ONCE! This is an ITERATIVE process that takes MULTIPLE RESPONSES and may span MULTIPLE CONVERSATIONS. Each field is a CHAPTER of a BOOK, not a form to fill. Process: (1) Write dream field ONLY → review → expand until complete. (2) Write proof field ONLY (expect 1000-2000+ words, multiple paragraphs per Act) → review → expand. (3) Write each term definition as a FULL PARAGRAPH → review → expand. (4) Write each requirement subfield as a FULL PARAGRAPH → review → expand. (5) Write examples as complete experimental protocol → review → expand. NO SINGLE SENTENCES. NO FRAGMENTS. EVERY ENTRY IS A COMPLETE EXPOUNDED PARAGRAPH.",
        "dream": "<!-- FIELD 1 OF 5: Write 3-5 complete sentences. The RETURN - Master of Two Worlds. The end state after applying this framework. STOP after this field. Review. Expand. THEN move to proof. -->",
        "proof": "<!-- FIELD 2 OF 5: THE MAIN CONTENT - Expect 1000-2000+ WORDS. This is NOT a summary. Write Act 1 (Discovery) as MULTIPLE PARAGRAPHS with quotes. STOP. Review. Expand. Then write Act 2 (Development) as MULTIPLE PARAGRAPHS with quotes. STOP. Review. Expand. Then write Act 3 (Proof) as MULTIPLE PARAGRAPHS. STOP. Review. Expand. The origin IS the logic. THEN move to terms. -->",
        "terms": [
            {
                "word": "<!-- FIELD 3 OF 5: One term at a time -->",
                "definition": "<!-- Each definition is a FULL PARAGRAPH (5-10 sentences). NOT a single sentence. Write one term. Review. Expand. Then next term. -->"
            }
        ],
        "requirements": [
            {
                "requirement": "<!-- FIELD 4 OF 5: Each of these 4 subfields is a FULL PARAGRAPH -->",
                "obstacle": "<!-- A full paragraph describing the obstacle. Not a sentence. -->",
                "overcome": "<!-- A full paragraph describing how it was overcome. Not a sentence. -->",
                "support": "<!-- A full paragraph with evidence from the proof. Not a sentence. -->"
            }
        ],
        "diagrams": "<!-- FIELD 5 OF 6: Create a Mermaid diagram showing the framework structure. Use ```mermaid code blocks. Show KEY ENTITIES and RELATIONSHIPS. Types: flowchart TD (top-down flow), flowchart LR (left-right), graph (concept map), sequenceDiagram (interactions). The diagram should make the framework's logic VISIBLE at a glance. Example:\n```mermaid\nflowchart TD\n    A[Extreme Environment] --> B[System of Systems]\n    B --> C[Vehicle]\n    B --> D[Pilot]\n    B --> E[Support]\n    C <--> D\n    D <--> E\n```\nTHEN move to examples. -->",
        "examples": "<!-- FIELD 6 OF 6: A complete EXPERIMENTAL PROTOCOL. Multiple paragraphs. Step-by-step instructions. Someone should be able to run this experiment. Review. Expand. -->"
    }

    with open(json_path, 'w') as f:
        json.dump(skeleton, f, indent=2)

    return (
        f"✓ Created emergent framework JSON at: {json_path}\n\n"
        "⚠️ ITERATIVE PROCESS - DO NOT FILL ALL FIELDS AT ONCE!\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "Each field is a CHAPTER, not a form field.\n"
        "This process takes MULTIPLE RESPONSES and may span MULTIPLE CONVERSATIONS.\n\n"
        "Process:\n"
        "1. Write ONLY the dream field → Review → Expand → STOP\n"
        "2. Write ONLY the proof field (expect 1000-2000+ words) → Review → Expand → STOP\n"
        "3. Write each term definition as a FULL PARAGRAPH → Review → Expand\n"
        "4. Write each requirement subfield as a FULL PARAGRAPH → Review → Expand\n"
        "5. Write examples as complete experimental protocol → Review → Expand\n\n"
        "NO SINGLE SENTENCES. NO FRAGMENTS. EVERY ENTRY IS A COMPLETE EXPOUNDED PARAGRAPH."
    )


def preview_emergent(emergent_name: str, output_path: str) -> str:
    """
    Render emergent framework JSON to markdown for review (Phase 6).

    Loads the JSON from the known path, renders via metastack to markdown,
    and writes to the specified output path.

    Args:
        emergent_name: Name of the emergent framework
        output_path: Where to write the rendered markdown

    Returns:
        The output path, or error if JSON doesn't exist
    """
    import os
    import json

    # Get path from environment
    heaven_data_dir = os.environ["HEAVEN_DATA_DIR"]
    json_path = os.path.join(heaven_data_dir, "frameworks", f"emergent_{emergent_name}.json")

    if not os.path.exists(json_path):
        return f"BLOCKED: JSON file does not exist at: {json_path}\n→ First call set_emergent_document('{emergent_name}') to create it."

    with open(json_path, 'r') as f:
        data = json.load(f)

    # Render to markdown
    # TODO: Replace with actual metastack rendering when integrated
    md_lines = [
        f"# {data.get('name', emergent_name)}",
        f"**Strata:** {data.get('strata', '')}",
        "",
        "## Dream",
        data.get('dream', '') or '_Not yet filled in_',
        "",
        "## Proof",
        data.get('proof', '') or '_Not yet filled in_',
        "",
        "## Terms",
    ]

    terms = data.get('terms', [])
    if terms and any(t.get('word') for t in terms):
        for term in terms:
            if term.get('word'):
                md_lines.append(f"- **{term['word']}**: {term.get('definition', '')}")
    else:
        md_lines.append("_No terms defined yet_")

    md_lines.extend(["", "## Requirements"])

    requirements = data.get('requirements', [])
    if requirements and any(r.get('requirement') for r in requirements):
        for i, req in enumerate(requirements, 1):
            if req.get('requirement'):
                md_lines.append(f"### Requirement {i}: {req['requirement']}")
                md_lines.append(f"**Obstacle:** {req.get('obstacle', '')}")
                md_lines.append(f"**Overcome:** {req.get('overcome', '')}")
                md_lines.append(f"**Support:** {req.get('support', '')}")
                md_lines.append("")
    else:
        md_lines.append("_No requirements defined yet_")

    md_lines.extend(["", "## Diagrams"])
    md_lines.append(data.get('diagrams', '') or '_No diagrams yet_')

    md_lines.extend(["", "## Examples"])
    md_lines.append(data.get('examples', '') or '_No examples yet_')

    markdown = "\n".join(md_lines)

    # Write to output path
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        f.write(markdown)

    return f"✓ Rendered emergent '{emergent_name}' to: {output_path}"


def validate_emergent_complete(json_path: str) -> tuple:
    """
    Check if emergent JSON is complete (no instruction placeholders, no empty required fields).

    Returns:
        (is_valid, issues_list)
    """
    import json

    with open(json_path, 'r') as f:
        data = json.load(f)

    issues = []

    # Check for instruction placeholders
    def check_placeholder(value, field_name):
        if isinstance(value, str) and "<!-- INSTRUCTION:" in value:
            issues.append(f"{field_name}: still has instruction placeholder")
        elif isinstance(value, str) and value.strip() == "":
            # Empty is ok for optional fields
            if field_name not in ["diagrams", "examples"]:
                issues.append(f"{field_name}: is empty")

    # Required string fields
    check_placeholder(data.get("dream", ""), "dream")
    check_placeholder(data.get("proof", ""), "proof")

    # Terms - at least one valid term required
    terms = data.get("terms", [])
    valid_terms = 0
    for i, term in enumerate(terms):
        word = term.get("word", "")
        defn = term.get("definition", "")
        if "<!-- INSTRUCTION:" in word or "<!-- INSTRUCTION:" in defn:
            issues.append(f"terms[{i}]: still has instruction placeholder")
        elif word.strip() and defn.strip():
            valid_terms += 1
    if valid_terms == 0:
        issues.append("terms: no valid terms defined")

    # Requirements - at least one valid requirement required
    requirements = data.get("requirements", [])
    valid_reqs = 0
    for i, req in enumerate(requirements):
        has_placeholder = False
        has_empty_required = False
        for field in ["requirement", "obstacle", "overcome", "support"]:
            val = req.get(field, "")
            if "<!-- INSTRUCTION:" in val:
                has_placeholder = True
            elif val.strip() == "":
                has_empty_required = True
        if has_placeholder:
            issues.append(f"requirements[{i}]: still has instruction placeholder")
        elif has_empty_required:
            issues.append(f"requirements[{i}]: has empty required fields")
        elif not has_placeholder and not has_empty_required:
            valid_reqs += 1
    if valid_reqs == 0:
        issues.append("requirements: no valid requirements defined")

    # Optional fields - just check for placeholders, empty is ok
    for field in ["diagrams", "examples"]:
        val = data.get(field, "")
        if "<!-- INSTRUCTION:" in val:
            issues.append(f"{field}: still has instruction placeholder (delete the line if not needed)")

    return (len(issues) == 0, issues)


def set_canonical_document(canonical_name: str, emergents: list) -> str:
    """
    Create the JSON file for a canonical framework (Phase 7).

    Vendors a JSON skeleton with refs to emergent JSONs.
    BLOCKED if any emergent JSON is incomplete (has placeholders or empty required fields).

    Args:
        canonical_name: Name of the canonical framework
        emergents: List of emergent framework names to include

    Returns:
        Path to the JSON file, or error if already exists or emergents incomplete
    """
    import os
    import json

    # Get path from environment
    heaven_data_dir = os.environ["HEAVEN_DATA_DIR"]
    frameworks_dir = os.path.join(heaven_data_dir, "frameworks")
    json_path = os.path.join(frameworks_dir, f"canonical_{canonical_name}.json")

    # Check if already exists
    if os.path.exists(json_path):
        return f"JSON already exists at: {json_path}\n→ Edit that file directly to modify content."

    # Validate emergents exist and are complete
    missing = []
    incomplete = {}
    for name in emergents:
        emergent_path = os.path.join(frameworks_dir, f"emergent_{name}.json")
        if not os.path.exists(emergent_path):
            missing.append(name)
        else:
            is_valid, issues = validate_emergent_complete(emergent_path)
            if not is_valid:
                incomplete[name] = issues

    if missing:
        return f"BLOCKED: Emergent JSON files missing: {missing}\n→ First call set_emergent_document() for each missing emergent."

    if incomplete:
        lines = ["BLOCKED: Emergent frameworks incomplete (Phase 6 not done):"]
        for name, issues in incomplete.items():
            lines.append(f"\n  {name}:")
            for issue in issues:
                lines.append(f"    - {issue}")
        lines.append("\n→ Edit the emergent JSON files to complete them before creating canonical.")
        return "\n".join(lines)

    # Create frameworks directory if needed
    os.makedirs(frameworks_dir, exist_ok=True)

    # Build emergent refs
    emergent_refs = [f"emergent_{name}.json" for name in emergents]

    # Determine strata from first emergent
    first_emergent_path = os.path.join(frameworks_dir, f"emergent_{emergents[0]}.json")
    with open(first_emergent_path, 'r') as f:
        first_data = json.load(f)
    strata = first_data.get('strata', '')

    # Create skeleton JSON
    skeleton = {
        "name": canonical_name,
        "strata": strata,
        "dream": "",
        "proof": "",
        "bridging_explanation": "" if len(emergents) > 1 else None,
        "emergent_refs": emergent_refs
    }

    # Remove bridging_explanation if only one emergent
    if len(emergents) == 1:
        del skeleton["bridging_explanation"]

    with open(json_path, 'w') as f:
        json.dump(skeleton, f, indent=2)

    return f"✓ Created canonical framework JSON at: {json_path}\n→ Edit this file to fill in dream, proof" + (", bridging_explanation" if len(emergents) > 1 else "") + "."


def preview_canonical(canonical_name: str, output_path: str) -> str:
    """
    Render canonical framework + emergents to markdown for review (Phase 7).

    Loads the canonical JSON and all referenced emergent JSONs,
    composes them into a single markdown document.

    Args:
        canonical_name: Name of the canonical framework
        output_path: Where to write the rendered markdown

    Returns:
        The output path, or error if JSON doesn't exist
    """
    import os
    import json

    # Get path from environment
    heaven_data_dir = os.environ["HEAVEN_DATA_DIR"]
    frameworks_dir = os.path.join(heaven_data_dir, "frameworks")
    json_path = os.path.join(frameworks_dir, f"canonical_{canonical_name}.json")

    if not os.path.exists(json_path):
        return f"BLOCKED: JSON file does not exist at: {json_path}\n→ First call set_canonical_document('{canonical_name}', emergents) to create it."

    with open(json_path, 'r') as f:
        canonical = json.load(f)

    # Start markdown
    md_lines = [
        f"# {canonical.get('name', canonical_name)}",
        f"**Strata:** {canonical.get('strata', '')}",
        "",
        "## Dream",
        canonical.get('dream', '') or '_Not yet filled in_',
        "",
        "## Proof",
        canonical.get('proof', '') or '_Not yet filled in_',
        "",
    ]

    # Bridging explanation if multiple emergents
    if canonical.get('bridging_explanation') is not None:
        md_lines.extend([
            "## How These Frameworks Connect",
            canonical.get('bridging_explanation', '') or '_Not yet filled in_',
            "",
        ])

    # Render each emergent inline
    emergent_refs = canonical.get('emergent_refs', [])
    for ref in emergent_refs:
        emergent_path = os.path.join(frameworks_dir, ref)
        if not os.path.exists(emergent_path):
            md_lines.extend([f"## ⚠️ Missing: {ref}", ""])
            continue

        with open(emergent_path, 'r') as f:
            emergent = json.load(f)

        md_lines.extend([
            f"---",
            f"## Framework: {emergent.get('name', ref)}",
            "",
            "### Dream",
            emergent.get('dream', '') or '_Not yet filled in_',
            "",
            "### Proof",
            emergent.get('proof', '') or '_Not yet filled in_',
            "",
            "### Terms",
        ])

        terms = emergent.get('terms', [])
        if terms and any(t.get('word') for t in terms):
            for term in terms:
                if term.get('word'):
                    md_lines.append(f"- **{term['word']}**: {term.get('definition', '')}")
        else:
            md_lines.append("_No terms defined_")

        md_lines.extend(["", "### Requirements"])

        requirements = emergent.get('requirements', [])
        if requirements and any(r.get('requirement') for r in requirements):
            for i, req in enumerate(requirements, 1):
                if req.get('requirement'):
                    md_lines.append(f"#### Requirement {i}: {req['requirement']}")
                    md_lines.append(f"**Obstacle:** {req.get('obstacle', '')}")
                    md_lines.append(f"**Overcome:** {req.get('overcome', '')}")
                    md_lines.append(f"**Support:** {req.get('support', '')}")
                    md_lines.append("")
        else:
            md_lines.append("_No requirements defined_")

        if emergent.get('diagrams'):
            md_lines.extend(["", "### Diagrams", emergent['diagrams']])

        if emergent.get('examples'):
            md_lines.extend(["", "### Examples", emergent['examples']])

        md_lines.append("")

    markdown = "\n".join(md_lines)

    # Write to output path
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        f.write(markdown)

    return f"✓ Rendered canonical '{canonical_name}' to: {output_path}"
