#!/usr/bin/env python3
"""Promote domain.owl types to foundation uarl.owl.

DEV-ONLY script. Reads domain.owl for classes/properties marked for promotion,
appends them to uarl.owl, removes them from domain.owl.

Usage:
    python3 promote_domain_to_foundation.py [--dry-run] [--class ClassName] [--all-marked]

The script looks for owl:Class and owl:ObjectProperty entries in domain.owl that have
rdfs:comment containing "PROMOTE_TO_FOUNDATION" marker. Or you can specify --class explicitly.

Since domain.owl imports foundation via owl:imports, everything that was valid before
promotion is still valid after — the type just moved from domain layer to foundation layer.
"""

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime

# Paths
KERNEL_DIR = Path(__file__).parent.parent / "youknow_kernel"
FOUNDATION_OWL = KERNEL_DIR / "uarl.owl"
DOMAIN_OWL = Path("/tmp/heaven_data/ontology/domain.owl")

# XML namespaces
NS = {
    'owl': 'http://www.w3.org/2002/07/owl#',
    'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
    'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
    'xsd': 'http://www.w3.org/2001/XMLSchema#',
}

UARL_NS = "http://sanctuary.ai/uarl#"
PROMOTE_MARKER = "PROMOTE_TO_FOUNDATION"


def _strip_ns(uri: str) -> str:
    if "#" in uri:
        return uri.split("#")[-1]
    return uri


def find_promotable_elements(domain_tree: ET.ElementTree, specific_class: str = None) -> list:
    """Find OWL classes/properties in domain.owl marked for promotion."""
    root = domain_tree.getroot()
    promotable = []

    for cls_elem in root.iter(f"{{{NS['owl']}}}Class"):
        about = cls_elem.get(f"{{{NS['rdf']}}}about")
        if not about:
            continue
        name = _strip_ns(about)

        if specific_class and name != specific_class:
            continue

        # Check for PROMOTE marker in comment
        comment = cls_elem.find(f"{{{NS['rdfs']}}}comment")
        if specific_class or (comment is not None and PROMOTE_MARKER in (comment.text or "")):
            promotable.append(("Class", name, cls_elem))

    for prop_elem in root.iter(f"{{{NS['owl']}}}ObjectProperty"):
        about = prop_elem.get(f"{{{NS['rdf']}}}about")
        if not about:
            continue
        name = _strip_ns(about)
        comment = prop_elem.find(f"{{{NS['rdfs']}}}comment")
        if comment is not None and PROMOTE_MARKER in (comment.text or ""):
            promotable.append(("ObjectProperty", name, prop_elem))

    return promotable


def append_to_foundation(elements: list, dry_run: bool = False):
    """Append promoted elements to uarl.owl."""
    if not elements:
        print("Nothing to promote.")
        return

    # Read foundation as text to insert before closing </rdf:RDF>
    foundation_text = FOUNDATION_OWL.read_text()
    closing_tag = "</rdf:RDF>"
    if closing_tag not in foundation_text:
        print("ERROR: Cannot find closing </rdf:RDF> in foundation OWL")
        sys.exit(1)

    insert_lines = [
        f"\n    <!-- PROMOTED from domain.owl {datetime.now().strftime('%Y-%m-%d %H:%M')} -->"
    ]

    for elem_type, name, elem in elements:
        # Serialize the element
        xml_str = ET.tostring(elem, encoding='unicode')
        # Indent
        xml_str = "    " + xml_str.replace("\n", "\n    ")
        insert_lines.append(xml_str)
        print(f"  {'[DRY RUN] ' if dry_run else ''}Promoting {elem_type}: {name}")

    insert_text = "\n".join(insert_lines) + "\n\n"

    if dry_run:
        print(f"\nWould insert {len(elements)} elements into {FOUNDATION_OWL}")
        print(f"Insert text preview:\n{insert_text[:500]}")
        return

    new_text = foundation_text.replace(closing_tag, insert_text + closing_tag)
    FOUNDATION_OWL.write_text(new_text)
    print(f"\nInserted {len(elements)} elements into {FOUNDATION_OWL}")


def remove_from_domain(elements: list, domain_tree: ET.ElementTree, dry_run: bool = False):
    """Remove promoted elements from domain.owl."""
    if dry_run:
        print(f"[DRY RUN] Would remove {len(elements)} elements from domain.owl")
        return

    root = domain_tree.getroot()
    for elem_type, name, elem in elements:
        root.remove(elem)

    domain_tree.write(str(DOMAIN_OWL), xml_declaration=True, encoding='unicode')
    print(f"Removed {len(elements)} elements from {DOMAIN_OWL}")


def main():
    parser = argparse.ArgumentParser(description="Promote domain.owl types to foundation uarl.owl")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be promoted without doing it")
    parser.add_argument("--class", dest="class_name", help="Promote a specific class by name")
    parser.add_argument("--all-marked", action="store_true", help="Promote all elements with PROMOTE_TO_FOUNDATION marker")
    args = parser.parse_args()

    if not args.class_name and not args.all_marked:
        parser.print_help()
        print("\nSpecify --class ClassName or --all-marked")
        sys.exit(1)

    if not DOMAIN_OWL.exists():
        print(f"ERROR: Domain OWL not found: {DOMAIN_OWL}")
        sys.exit(1)

    if not FOUNDATION_OWL.exists():
        print(f"ERROR: Foundation OWL not found: {FOUNDATION_OWL}")
        sys.exit(1)

    # Register namespaces for clean output
    for prefix, uri in NS.items():
        ET.register_namespace(prefix, uri)
    ET.register_namespace('uarl', UARL_NS)

    domain_tree = ET.parse(str(DOMAIN_OWL))
    promotable = find_promotable_elements(domain_tree, specific_class=args.class_name)

    if not promotable:
        if args.class_name:
            print(f"Class '{args.class_name}' not found in domain.owl")
        else:
            print(f"No elements with {PROMOTE_MARKER} marker found in domain.owl")
        sys.exit(0)

    print(f"Found {len(promotable)} elements to promote:")
    append_to_foundation(promotable, dry_run=args.dry_run)
    remove_from_domain(promotable, domain_tree, dry_run=args.dry_run)

    if not args.dry_run:
        print("\nDone. Run: pip install youknow_kernel && /mcp to reload.")


if __name__ == "__main__":
    main()
