"""MAP compiler — queue-driven enrich/instance compilation loop.

The compiler manages a queue of names to resolve. Each name is either:
- Undefined: needs to be enriched (broken into sub-parts) or instanced directly
- Defined: has sub-parts via enrich, each sub-part needs resolving
- Instanced: done, has content

The two moves:
- enrich NAME -> PART-1 PART-2 PART-3  (break into sub-parts, sub-parts enter queue)
- instance NAME -> "content"            (produce content, name is done)

The queue IS the compilation. The KV store IS the codebase.
The LLM's only decision: instance or enrich?
"""

import json
import os
from datetime import datetime

STATE_DIR = '.map-state'
COMPILER_FILE = 'compiler.json'


def _state_path():
    os.makedirs(STATE_DIR, exist_ok=True)
    return os.path.join(STATE_DIR, COMPILER_FILE)


def _load_state():
    """Load compiler state from disk."""
    path = _state_path()
    if not os.path.exists(path):
        return {'nodes': {}, 'queue': [], 'root': None}
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {'nodes': {}, 'queue': [], 'root': None}


def _save_state(state):
    """Save compiler state to disk."""
    path = _state_path()
    with open(path, 'w') as f:
        json.dump(state, f, indent=2)


def _resolve_path(name):
    """Normalize a dotted path name to uppercase."""
    return '.'.join(part.upper().replace('-', '_') for part in name.split('.'))


def _child_path(parent, child):
    """Create a dotted child path."""
    if parent:
        return f"{parent}.{child}"
    return child


def define(name, parts):
    """Define a root task as a sequence of named parts.

    This is the entry point — sets up the initial queue.
    Example: define("ESSAY", ["INTRO", "BODY-1", "BODY-2", "CONCLUSION"])
    """
    state = _load_state()
    name = _resolve_path(name)

    # Create the root node
    part_names = [_resolve_path(p) for p in parts]
    child_paths = [_child_path(name, p) for p in part_names]

    state['nodes'][name] = {
        'status': 'defined',
        'parts': child_paths,
        'content': None,
        'parent': None,
        'created': datetime.now().isoformat(),
    }

    # Create child nodes (undefined)
    for child_path in child_paths:
        if child_path not in state['nodes']:
            state['nodes'][child_path] = {
                'status': 'undefined',
                'parts': [],
                'content': None,
                'parent': name,
                'created': datetime.now().isoformat(),
            }

    # Set root and initialize queue with children
    state['root'] = name
    # Add children to queue (only if not already there and not instanced)
    for cp in child_paths:
        if cp not in state['queue']:
            node = state['nodes'].get(cp, {})
            if node.get('status') != 'instanced':
                state['queue'].append(cp)

    _save_state(state)
    return name, child_paths


def enrich(name, parts):
    """Enrich a name by breaking it into sub-parts.

    The name gets status 'defined' and its sub-parts enter the queue.
    Example: enrich("ESSAY.INTRO", ["HOOK", "THESIS", "ROADMAP"])

    RATCHET: if the node is already instanced, this is a re-enrich.
    The sub-parts go to the END of the queue — you must process
    everything else first. No going back and fiddling.
    """
    state = _load_state()
    name = _resolve_path(name)

    # Check ratchet: instanced nodes get re-enriched at queue end
    was_instanced = (name in state['nodes']
                     and state['nodes'][name]['status'] == 'instanced')

    part_names = [_resolve_path(p) for p in parts]
    child_paths = [_child_path(name, p) for p in part_names]

    # Update or create the node
    if name not in state['nodes']:
        state['nodes'][name] = {
            'status': 'defined',
            'parts': child_paths,
            'content': None,
            'parent': None,
            'created': datetime.now().isoformat(),
        }
    else:
        state['nodes'][name]['status'] = 'defined'
        state['nodes'][name]['parts'] = child_paths
        state['nodes'][name]['content'] = None  # clear any prior instance

    # Create child nodes
    for child_path in child_paths:
        if child_path not in state['nodes']:
            state['nodes'][child_path] = {
                'status': 'undefined',
                'parts': [],
                'content': None,
                'parent': name,
                'created': datetime.now().isoformat(),
            }

    if was_instanced:
        # RATCHET: sub-parts go to END of queue only
        # You already instanced this — now you have to wait
        if name in state['queue']:
            state['queue'].remove(name)
        for cp in child_paths:
            if cp not in state['queue']:
                state['queue'].append(cp)
    elif name in state['queue']:
        # Normal: replace parent in queue with children at same position
        idx = state['queue'].index(name)
        state['queue'] = (
            state['queue'][:idx]
            + [cp for cp in child_paths if cp not in state['queue']]
            + state['queue'][idx + 1:]
        )
    else:
        # Not in queue: add children to end
        for cp in child_paths:
            if cp not in state['queue']:
                node = state['nodes'].get(cp, {})
                if node.get('status') != 'instanced':
                    state['queue'].append(cp)

    _save_state(state)
    return name, child_paths, was_instanced


def instance(name, content):
    """Instance a name — produce its content. Name is done.

    Example: instance("ESSAY.INTRO.HOOK", "The morning the water turned brown...")
    """
    state = _load_state()
    name = _resolve_path(name)

    if name not in state['nodes']:
        state['nodes'][name] = {
            'status': 'instanced',
            'parts': [],
            'content': content,
            'parent': None,
            'created': datetime.now().isoformat(),
        }
    else:
        state['nodes'][name]['status'] = 'instanced'
        state['nodes'][name]['content'] = content

    # Remove from queue
    if name in state['queue']:
        state['queue'].remove(name)

    _save_state(state)
    return name


def next_item():
    """Get the next item in the queue to resolve.

    Returns (name, node_info) or (None, None) if queue empty.
    """
    state = _load_state()
    if not state['queue']:
        return None, None

    name = state['queue'][0]
    node = state['nodes'].get(name, {})

    # Gather context: parent, siblings
    parent_name = node.get('parent')
    context = {}
    if parent_name and parent_name in state['nodes']:
        parent = state['nodes'][parent_name]
        context['parent'] = parent_name
        context['siblings'] = parent.get('parts', [])
        # Gather already-instanced siblings for context
        context['completed'] = {}
        for sib in parent.get('parts', []):
            sib_node = state['nodes'].get(sib, {})
            if sib_node.get('status') == 'instanced':
                context['completed'][sib] = sib_node.get('content', '')[:200]

    return name, {
        'status': node.get('status', 'undefined'),
        'parent': parent_name,
        'context': context,
    }


def queue():
    """Return the current queue as a list of names."""
    state = _load_state()
    return list(state['queue'])


def show(name=None):
    """Show a node or the entire tree.

    If name given: show that node's definition/instance.
    If no name: show the full tree.
    """
    state = _load_state()

    if name:
        name = _resolve_path(name)
        node = state['nodes'].get(name)
        if not node:
            return None
        return {
            'name': name,
            'status': node['status'],
            'parts': node.get('parts', []),
            'content': node.get('content'),
            'parent': node.get('parent'),
        }

    # Full tree
    return _build_tree(state)


def _build_tree(state):
    """Build a display tree from state."""
    if not state['root']:
        return {'root': None, 'nodes': {}}

    def _tree_node(name, depth=0):
        node = state['nodes'].get(name, {})
        status = node.get('status', 'undefined')
        result = {
            'name': name,
            'status': status,
            'depth': depth,
        }
        if status == 'instanced':
            content = node.get('content', '')
            result['preview'] = content[:100] + ('...' if len(content) > 100 else '')
        if status == 'defined' and node.get('parts'):
            result['children'] = [_tree_node(p, depth + 1) for p in node['parts']]
        return result

    return _tree_node(state['root'])


def format_tree(tree, indent=0):
    """Format a tree node for display."""
    if tree is None or tree.get('name') is None:
        return "No compilation in progress. Use 'define' to start."

    lines = []
    name = tree['name']
    status = tree['status']
    prefix = '  ' * indent

    if status == 'instanced':
        preview = tree.get('preview', '')
        lines.append(f"{prefix}[done] {name}: {preview}")
    elif status == 'defined':
        lines.append(f"{prefix}[enriched] {name}")
        for child in tree.get('children', []):
            lines.append(format_tree(child, indent + 1))
    else:
        lines.append(f"{prefix}[pending] {name}")

    return '\n'.join(lines)


def format_next(name, info):
    """Format the next queue item for display to LLM."""
    if name is None:
        return "Queue empty. Compilation complete."

    lines = [f"Next: {name}"]
    lines.append(f"Status: {info['status']}")

    ctx = info.get('context', {})
    if ctx.get('parent'):
        lines.append(f"Parent: {ctx['parent']}")
    if ctx.get('siblings'):
        lines.append(f"Siblings: {', '.join(ctx['siblings'])}")
    if ctx.get('completed'):
        lines.append("Already completed:")
        for sib, preview in ctx['completed'].items():
            lines.append(f"  {sib}: {preview}")

    lines.append("")
    lines.append("Decision: enrich (break into sub-parts) or instance (produce content)?")
    return '\n'.join(lines)


def clear():
    """Clear all compiler state."""
    state = {'nodes': {}, 'queue': [], 'root': None}
    _save_state(state)


def stats():
    """Return compilation stats."""
    state = _load_state()
    total = len(state['nodes'])
    instanced = sum(1 for n in state['nodes'].values() if n['status'] == 'instanced')
    defined = sum(1 for n in state['nodes'].values() if n['status'] == 'defined')
    undefined = sum(1 for n in state['nodes'].values() if n['status'] == 'undefined')
    return {
        'total': total,
        'instanced': instanced,
        'defined': defined,
        'undefined': undefined,
        'queue_length': len(state['queue']),
        'root': state.get('root'),
    }
