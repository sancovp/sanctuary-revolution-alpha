"""MAP environment persistence — serialize/deserialize user bindings.

Serializes user-defined bindings (everything beyond stdlib) to JSON.
Handles: Atom (num, sym, keyword, string), Cell, NIL, Morph.
Builtins and Macros are NOT serialized (builtins come from stdlib).
Morph closures serialize params + body; env is reconstructed on load.
"""

import json
import os
from fractions import Fraction

from .types import Atom, Cell, NIL, Nil, Morph, Builtin, MAPObj
from .env import Env, Frame
from .stdlib import make_stdlib

STATE_DIR = '.map-state'
ENV_FILE = 'env.json'


def _serialize_value(val):
    """Serialize a MAPObj to a JSON-compatible dict."""
    if isinstance(val, Nil):
        return {'type': 'nil'}

    if isinstance(val, Atom):
        if val.is_num:
            # Store as string fraction to preserve exact value
            return {'type': 'atom_num', 'val': str(val.val)}
        # sym, keyword, or string — all stored as their raw val
        return {'type': 'atom_str', 'val': val.val}

    if isinstance(val, Cell):
        items = []
        cur = val
        while isinstance(cur, Cell):
            items.append(_serialize_value(cur.head))
            cur = cur.tail
        tail = _serialize_value(cur)
        return {'type': 'cell', 'items': items, 'tail': tail}

    if isinstance(val, Morph):
        return {
            'type': 'morph',
            'params': [_serialize_value(p) for p in val.params],
            'body': _serialize_value(val.body),
            'name': val.name,
        }

    # Builtins and other types can't be serialized
    return None


def _deserialize_value(data):
    """Deserialize a JSON dict back to a MAPObj."""
    if data is None:
        return None

    t = data['type']

    if t == 'nil':
        return NIL

    if t == 'atom_num':
        return Atom(Fraction(data['val']))

    if t == 'atom_str':
        # bypass __init__ to preserve raw val (keywords, strings, symbols)
        a = Atom.__new__(Atom)
        a.val = data['val']
        return a

    if t == 'cell':
        tail = _deserialize_value(data['tail'])
        for item_data in reversed(data['items']):
            tail = Cell(_deserialize_value(item_data), tail)
        return tail

    if t == 'morph':
        params = [_deserialize_value(p) for p in data['params']]
        body = _deserialize_value(data['body'])
        # Env will be patched after all bindings are loaded
        return Morph(params, body, None, name=data.get('name'))

    return None


def get_state_path(state_dir=None):
    """Get the path to the state directory."""
    if state_dir is None:
        state_dir = STATE_DIR
    return state_dir


def save_env(env, state_dir=None):
    """Save user-defined bindings from env to disk.

    Only saves bindings not in the stdlib.
    """
    state_path = get_state_path(state_dir)
    os.makedirs(state_path, exist_ok=True)

    stdlib_names = set(make_stdlib().to_dict().keys())

    bindings = []
    cur = env.head
    seen = set()
    while cur is not None:
        if isinstance(cur.key, Atom):
            name = repr(cur.key)
            if name not in stdlib_names and name not in seen:
                seen.add(name)
                serialized = _serialize_value(cur.val)
                if serialized is not None:
                    bindings.append({'name': cur.key.val, 'val': serialized})
        cur = cur.nxt

    filepath = os.path.join(state_path, ENV_FILE)
    with open(filepath, 'w') as f:
        json.dump({'bindings': bindings}, f, indent=2)


def load_env(state_dir=None):
    """Load persisted bindings into a fresh stdlib env.

    Returns the env with all persisted bindings restored.
    """
    state_path = get_state_path(state_dir)
    filepath = os.path.join(state_path, ENV_FILE)

    env = make_stdlib()

    if not os.path.exists(filepath):
        return env

    try:
        with open(filepath) as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return env

    bindings = data.get('bindings', [])

    # First pass: deserialize all values
    deserialized = []
    for entry in bindings:
        name = entry['name']
        val = _deserialize_value(entry['val'])
        if val is not None:
            deserialized.append((name, val))

    # Second pass: add bindings to env, patch Morph envs
    for name, val in reversed(deserialized):
        key = Atom.__new__(Atom)
        key.val = name
        frame = Frame(key, val, env.head)
        env.head = frame

    # Third pass: patch Morph environments to include all bindings
    cur = env.head
    while cur is not None:
        if isinstance(cur.val, Morph) and cur.val.env is None:
            cur.val.env = env
        cur = cur.nxt

    return env


def clear_env(state_dir=None):
    """Remove persisted environment state."""
    state_path = get_state_path(state_dir)
    filepath = os.path.join(state_path, ENV_FILE)
    if os.path.exists(filepath):
        os.unlink(filepath)
