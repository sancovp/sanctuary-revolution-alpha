"""MAP attention flow storage — named programs that persist as .map files.

A flow is a named MAP program representing an attention pattern.
Flows are stored as .map files in a configurable directory.
"""

import os
import json
from datetime import datetime

from .parser import parse
from .eval import run, map_eval, MAPError
from .stdlib import make_stdlib
from .types import NIL, Atom, Cell

FLOWS_DIR = '.map-flows'


def _flows_dir(flows_dir=None):
    if flows_dir is None:
        flows_dir = FLOWS_DIR
    os.makedirs(flows_dir, exist_ok=True)
    return flows_dir


def _flow_path(name, flows_dir=None):
    return os.path.join(_flows_dir(flows_dir), f'{name}.map')


def _meta_path(name, flows_dir=None):
    return os.path.join(_flows_dir(flows_dir), f'{name}.meta.json')


def save_flow(name, source, description=None, flows_dir=None):
    """Save a named attention flow.

    Args:
        name: Flow name (alphanumeric + hyphens)
        source: MAP source code
        description: Optional description
        flows_dir: Override default flows directory
    """
    # Validate the source parses
    parse(source)

    path = _flow_path(name, flows_dir)
    with open(path, 'w') as f:
        f.write(source + '\n')

    meta = {
        'name': name,
        'created': datetime.now().isoformat(),
        'description': description or '',
    }
    meta_path = _meta_path(name, flows_dir)
    with open(meta_path, 'w') as f:
        json.dump(meta, f, indent=2)


def list_flows(flows_dir=None):
    """List all stored flows. Returns list of (name, description) tuples."""
    d = _flows_dir(flows_dir)
    flows = []
    for fname in sorted(os.listdir(d)):
        if fname.endswith('.map'):
            name = fname[:-4]
            meta_path = _meta_path(name, flows_dir)
            desc = ''
            if os.path.exists(meta_path):
                try:
                    with open(meta_path) as f:
                        meta = json.load(f)
                    desc = meta.get('description', '')
                except (json.JSONDecodeError, OSError):
                    pass
            flows.append((name, desc))
    return flows


def get_flow_source(name, flows_dir=None):
    """Get the source of a named flow. Returns None if not found."""
    path = _flow_path(name, flows_dir)
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return f.read().strip()


def inspect_flow(name, flows_dir=None):
    """Inspect a flow's structure. Returns a dict with metadata and analysis."""
    source = get_flow_source(name, flows_dir)
    if source is None:
        return None

    meta_path = _meta_path(name, flows_dir)
    meta = {}
    if os.path.exists(meta_path):
        try:
            with open(meta_path) as f:
                meta = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass

    # Analyze the source for symbols used
    exprs = parse(source)
    symbols = set()
    _collect_symbols(exprs, symbols)

    # Identify which are special forms vs user refs
    special_forms = {
        'BIND', 'MORPH', 'WHEN', 'SEQ', 'LOOP', 'QUOTE', 'EVAL',
        'DEF', 'SET!', 'MACRO', 'APPLY', 'LOAD', 'MATCH', 'ENV',
    }
    stdlib_names = set(make_stdlib().to_dict().keys())
    user_refs = symbols - special_forms - stdlib_names - {'T', 'NIL'}

    return {
        'name': name,
        'source': source,
        'description': meta.get('description', ''),
        'created': meta.get('created', ''),
        'symbols': sorted(symbols),
        'dependencies': sorted(user_refs),
    }


def run_flow(name, env=None, flows_dir=None):
    """Execute a named flow. Returns (result, env)."""
    source = get_flow_source(name, flows_dir)
    if source is None:
        raise MAPError(f"Flow not found: {name}")

    if env is None:
        env = make_stdlib()

    return run(source, env)


def delete_flow(name, flows_dir=None):
    """Delete a named flow. Returns True if deleted."""
    path = _flow_path(name, flows_dir)
    meta_path = _meta_path(name, flows_dir)
    deleted = False
    if os.path.exists(path):
        os.unlink(path)
        deleted = True
    if os.path.exists(meta_path):
        os.unlink(meta_path)
    return deleted


def _collect_symbols(obj, symbols):
    """Recursively collect symbol names from parsed expressions."""
    if isinstance(obj, list):
        for item in obj:
            _collect_symbols(item, symbols)
    elif isinstance(obj, Atom) and obj.is_sym:
        symbols.add(obj.val)
    elif isinstance(obj, Cell):
        _collect_symbols(obj.head, symbols)
        _collect_symbols(obj.tail, symbols)
