"""CLI entrypoint for mermaid evolution system validation.

Usage:
    python -m compoctopus.validate_mermaid /path/to/mermaid.md

Reads a file containing a mermaid sequence diagram (with or without
```mermaid fences), validates it against the evolution system rules,
and prints results.

Exit code 0 = valid (prints "VALID: <path>")
Exit code 1 = violations found (prints each violation)
"""

import sys
from pathlib import Path

from compoctopus.mermaid import MermaidParser, MermaidValidator


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python -m compoctopus.validate_mermaid <path>", file=sys.stderr)
        return 2

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"ERROR: File not found: {path}", file=sys.stderr)
        return 2

    text = path.read_text()

    # Parse
    parser = MermaidParser()
    try:
        spec = parser.parse(text)
    except Exception as e:
        print(f"PARSE ERROR: {e}", file=sys.stderr)
        return 1

    # Validate
    validator = MermaidValidator()

    # Basic syntax first
    syntax_violations = validator.check_syntax(spec)
    if syntax_violations:
        print(f"SYNTAX ERRORS ({len(syntax_violations)}):")
        for v in syntax_violations:
            print(f"  - {v}")
        return 1

    # Evolution system compliance
    es_violations = validator.check_evolution_system_compliance(spec)
    errors = [v for v in es_violations if v.severity == "ERROR"]
    warnings = [v for v in es_violations if v.severity == "WARNING"]
    infos = [v for v in es_violations if v.severity == "INFO"]

    if errors:
        print(f"ERRORS ({len(errors)}):")
        for v in errors:
            print(f"  {v}")
        if warnings:
            print(f"\nWARNINGS ({len(warnings)}):")
            for v in warnings:
                print(f"  {v}")
        return 1

    if warnings:
        print(f"WARNINGS ({len(warnings)}):")
        for v in warnings:
            print(f"  {v}")

    if infos:
        print(f"INFO ({len(infos)}):")
        for v in infos:
            print(f"  {v}")

    print(f"VALID: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
