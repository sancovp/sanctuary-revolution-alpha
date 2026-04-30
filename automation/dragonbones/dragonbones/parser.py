"""Chain parsing — claims, PIO operators, entity chains, block extraction."""

import os
import re

from dragonbones.constants import CHAIN_TYPES, DB_FENCE, SYNTAX_REF_PATH


def parse_claims(claims_str: str) -> list[str]:
    """Parse claim blocks from {..}+{..}+{..}, handling desc='''...''' values."""
    claims = []
    i = 0
    while i < len(claims_str):
        if claims_str[i] == '{':
            depth = 1
            start = i + 1
            i += 1
            in_triple_quote = False
            while i < len(claims_str) and depth > 0:
                if claims_str[i:i+3] in ('"""', "'''"):
                    in_triple_quote = not in_triple_quote
                    i += 3
                    continue
                if not in_triple_quote:
                    if claims_str[i] == '{':
                        depth += 1
                    elif claims_str[i] == '}':
                        depth -= 1
                        if depth == 0:
                            claims.append(claims_str[start:i])
                            break
                i += 1
        else:
            i += 1
    return claims


def split_claim_kvs(claim: str) -> list[str]:
    """Split a claim into KV pairs by commas, respecting triple-quote blocks."""
    kvs = []
    current = []
    in_triple = False
    i = 0
    while i < len(claim):
        if claim[i:i+3] in ('"""', "'''"):
            in_triple = not in_triple
            current.append(claim[i:i+3])
            i += 3
            continue
        if claim[i] == ',' and not in_triple:
            kvs.append("".join(current).strip())
            current = []
        else:
            current.append(claim[i])
        i += 1
    remainder = "".join(current).strip()
    if remainder:
        kvs.append(remainder)
    return kvs


def extract_pio_operators(content: str) -> tuple[list[str], list[str], str]:
    """Extract PIO operators (=>, :{) from entity chain content.

    Returns (attention_targets, containment_targets, cleaned_content).
    """
    attention_targets = []
    containment_targets = []
    cleaned = content
    depth = 0
    in_triple = False
    i = 0
    arrow_positions = []

    while i < len(cleaned):
        if cleaned[i:i+3] in ('"""', "'''"):
            in_triple = not in_triple
            i += 3
            continue
        if not in_triple:
            if cleaned[i] == '{':
                depth += 1
            elif cleaned[i] == '}':
                depth -= 1
            elif depth == 0 and cleaned[i:i+2] == '=>':
                rest = cleaned[i+2:].strip()
                target = ""
                j = 0
                while j < len(rest):
                    if rest[j:j+2] == '=>' or rest[j] == '{' or rest[j:j+2] == ':{':
                        break
                    target += rest[j]
                    j += 1
                target = target.strip()
                if target:
                    attention_targets.append(target)
                    arrow_positions.append((i, i + 2 + len(rest[:j])))
        i += 1

    # Find :{ containment blocks
    depth = 0
    in_triple = False
    i = 0
    containment_positions = []

    while i < len(cleaned):
        if cleaned[i:i+3] in ('"""', "'''"):
            in_triple = not in_triple
            i += 3
            continue
        if not in_triple:
            if cleaned[i] == '{' and i > 0 and cleaned[i-1] != ':':
                depth += 1
            elif cleaned[i] == '}' and depth > 0:
                depth -= 1
            elif depth == 0 and cleaned[i:i+2] == ':{':
                block_start = i
                j = i + 2
                block_depth = 1
                while j < len(cleaned) and block_depth > 0:
                    if cleaned[j] == '{':
                        block_depth += 1
                    elif cleaned[j] == '}':
                        block_depth -= 1
                    j += 1
                block_content = cleaned[i+2:j-1].strip()
                targets = [t.strip() for t in block_content.split(',') if t.strip()]
                containment_targets.extend(targets)
                containment_positions.append((block_start, j))
        i += 1

    # Strip PIO operators from content
    for start, end in sorted(arrow_positions + containment_positions, reverse=True):
        cleaned = cleaned[:start] + cleaned[end:]

    return attention_targets, containment_targets, cleaned


def parse_entity_chain(line: str) -> dict | None:
    """Parse an EntityChain line into a structured concept dict.

    Handles any chain type operator that compiles as EntityChain.
    Strips the operator prefix, then parses Name {claims}+{claims}.
    """
    # Strip any known operator prefix
    content = line
    for operator in CHAIN_TYPES:
        if line.startswith(operator):
            content = line[len(operator):].strip()
            break

    if not content:
        return None

    brace_pos = content.find("{")
    if brace_pos == -1:
        return None

    concept_name = content[:brace_pos].strip()
    if not concept_name:
        return None

    claims_str = content[brace_pos:]

    # Extract PIO operators before claim parsing
    pio_attention, pio_containment, claims_str = extract_pio_operators(claims_str)

    raw_claims = parse_claims(claims_str)

    concept_desc = None  # First claim's desc → source concept description
    target_descs = {}    # Subsequent claims' descs → cached KV for daemon auto-creation
    invalid_rels = []
    all_targets = []
    isa, partof, instantiates, extra_rels = [], [], [], []

    for claim in raw_claims:
        kvs = split_claim_kvs(claim)
        claim_rels = []
        claim_desc = None

        for kv in kvs:
            if "=" not in kv:
                continue
            key, _, value = kv.partition("=")
            key = key.strip().lower()
            value = value.strip()
            if value.startswith('"""') and value.endswith('"""'):
                value = value[3:-3].strip()
            # Also handle ''' (triple single quotes from output style)
            if value.startswith("'''") and value.endswith("'''"):
                value = value[3:-3].strip()

            if key in ("desc", "str"):
                claim_desc = value
            else:
                claim_rels.append((key, value))

        # First claim's desc = source concept description (SKILL.md body etc)
        # Subsequent claims' descs = cached for target concepts
        if claim_desc and concept_desc is None:
            concept_desc = claim_desc
        elif claim_desc:
            # Cache desc for each target in this claim
            for key, value in claim_rels:
                target_descs[value] = claim_desc

        for key, value in claim_rels:
            # Pass ALL relationships through — CartON/YOUKNOW validates, not Dragonbones
            all_targets.append(value)
            if key == "is_a":
                isa.append(value)
            elif key == "part_of":
                partof.append(value)
            elif key == "instantiates":
                instantiates.append(value)
            else:
                extra_rels.append({"relationship": key, "related": [value]})

    rels = []
    if isa:
        rels.append({"relationship": "is_a", "related": isa})
    if partof:
        rels.append({"relationship": "part_of", "related": partof})
    if instantiates:
        rels.append({"relationship": "instantiates", "related": instantiates})
    rels.extend(extra_rels)

    if pio_attention:
        rels.append({"relationship": "attention_chains_to", "related": pio_attention})
        all_targets.extend(pio_attention)
    if pio_containment:
        rels.append({"relationship": "has_part", "related": pio_containment})
        all_targets.extend(pio_containment)

    description = concept_desc if concept_desc else f"[NO DESC] {concept_name}"

    return {
        "concept_name": concept_name,
        "description": description,
        "relationships": rels,
        "invalid_rels": invalid_rels,
        "all_targets": all_targets,
        "target_descs": target_descs,  # KV cache: target_name → desc for daemon auto-creation
    }


def detect_chain_type(line: str) -> tuple[str, str, str] | None:
    """Detect which chain type operator a line starts with."""
    for operator, (name, status) in CHAIN_TYPES.items():
        if line.startswith(operator):
            return (operator, name, status)
    return None


def get_help_text(chain_type_name: str | None = None) -> str:
    """Read syntax reference from SYNTAX.md for --help output."""
    if os.path.exists(SYNTAX_REF_PATH):
        with open(SYNTAX_REF_PATH, 'r') as f:
            full_text = f.read()
        if chain_type_name:
            return f"🐉🦴 --help {chain_type_name}:\n\n{full_text}"
        return f"🐉🦴 --help:\n\n{full_text}"
    return "🐉🦴 --help: SYNTAX.md not found at " + SYNTAX_REF_PATH


def extract_chain_segments(chains_text: str) -> list[tuple[str, str]]:
    """Extract (operator, full_chain_text) pairs from chains text.

    Chains can span multiple lines due to desc='''...'''.
    """
    segments = []
    lines = chains_text.strip().split("\n")
    current_op = None
    current_lines = []
    in_triple = False

    for line in lines:
        stripped = line.strip()

        if not in_triple:
            detected = detect_chain_type(stripped)
            if detected:
                if current_op and current_lines:
                    segments.append((current_op, "\n".join(current_lines)))
                current_op = detected
                current_lines = [stripped]
                count = stripped.count('"""') + stripped.count("'''")
                if count % 2 == 1:
                    in_triple = not in_triple
                continue

            if stripped == "--help" or stripped.startswith("--help "):
                if current_op and current_lines:
                    segments.append((current_op, "\n".join(current_lines)))
                    current_op = None
                    current_lines = []
                segments.append(("--help", stripped))
                continue

        count = stripped.count('"""') + stripped.count("'''")
        if count % 2 == 1:
            in_triple = not in_triple

        if current_op:
            current_lines.append(stripped)

    if current_op and current_lines:
        segments.append((current_op, "\n".join(current_lines)))

    return segments


def extract_from_blocks(text: str) -> tuple[list[dict], list[str], bool, int]:
    """Extract chain declarations from fenced blocks AND bare unfenced chains.

    Returns (compiled_concepts, stub_messages, help_requested, blocks_found).
    """
    concepts = []
    stubs = []
    help_requested = False
    blocks_found = 0

    block_pattern = re.compile(
        re.escape(DB_FENCE) + r'\s*\n(.*?)' + re.escape(DB_FENCE), re.DOTALL)

    for match in block_pattern.finditer(text):
        blocks_found += 1
        block_content = match.group(1)
        halves = block_content.split("---", 1)
        chains_half = halves[0]

        for segment in extract_chain_segments(chains_half):
            if segment[0] == "--help":
                help_requested = True
                arg = segment[1][len("--help"):].strip() or None
                stubs.append(get_help_text(arg))
                continue

            operator, chain_name, status = segment[0]
            full_text = segment[1]

            if chain_name == "EntityChain":
                parsed = parse_entity_chain(full_text)
                if parsed:
                    concepts.append(parsed)
            else:
                stubs.append(
                    f"[{chain_name}] not yet implemented "
                    f"(operator: {operator}, status: {status})")

    # Second pass: bare (unfenced) EntityChains
    unfenced_text = block_pattern.sub("", text)
    bare_has_chains = any(op in unfenced_text for op in CHAIN_TYPES)
    if bare_has_chains:
        for segment in extract_chain_segments(unfenced_text):
            if segment[0] == "--help":
                continue
            operator, chain_name, status = segment[0]
            full_text = segment[1]
            if chain_name == "EntityChain":
                parsed = parse_entity_chain(full_text)
                if parsed:
                    concepts.append(parsed)
                    blocks_found += 1

    return concepts, stubs, help_requested, blocks_found
