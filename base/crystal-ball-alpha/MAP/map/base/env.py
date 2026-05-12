"""MAP environments — cons-cell chains, NOT dicts.

An environment is a linked list of Frame cells.
Each Frame holds a single binding (key Atom, value MAPObj).
Lookup walks the chain. Mutation walks and overwrites.
New bindings cons onto the front.

This is deliberately non-standard. Most Lisps use hash maps or alists.
MAP uses raw cons cells so the environment IS a MAP data structure
that programs can inspect and manipulate (homoiconicity extends to env).
"""

from .types import MAPObj, Atom, Cell, NIL, Nil, Builtin, Fraction

class Frame(MAPObj):
    """Single binding: key -> val, with a `next` pointer."""
    __slots__ = ('key', 'val', 'nxt')
    def __init__(self, key, val, nxt=None):
        self.key = key      # Atom (symbol)
        self.val = val       # MAPObj
        self.nxt = nxt       # Frame | None

    def __repr__(self):
        return f'[{self.key}={self.val}]'

class Env:
    """Environment as a cons-cell chain of Frames.

    Lookup is O(n). This is intentional — it makes scope
    semantics visible and manipulable.
    """
    def __init__(self, head=None):
        self.head = head  # Frame | None

    def lookup(self, sym):
        """Find binding for symbol. Walks chain from head."""
        if isinstance(sym, Atom):
            name = sym.val
        else:
            name = str(sym).upper()

        cur = self.head
        while cur is not None:
            if isinstance(cur.key, Atom) and cur.key.val == name:
                return cur.val
            cur = cur.nxt
        raise NameError(f"Unbound symbol: {name}")

    def bind(self, sym, val):
        """Add new binding at head of chain. Returns new Env (functional)."""
        if isinstance(sym, str):
            sym = Atom(sym)
        new_frame = Frame(sym, val, self.head)
        return Env(new_frame)

    def mutate(self, sym, val):
        """Overwrite existing binding in-place. Raises if not found."""
        if isinstance(sym, Atom):
            name = sym.val
        else:
            name = str(sym).upper()

        cur = self.head
        while cur is not None:
            if isinstance(cur.key, Atom) and cur.key.val == name:
                cur.val = val
                return val
            cur = cur.nxt
        raise NameError(f"Cannot mutate unbound symbol: {name}")

    def extend(self, keys, vals):
        """Extend env with multiple bindings. Returns new Env."""
        env = self
        for k, v in zip(keys, vals):
            env = env.bind(k, v)
        return env

    def to_dict(self):
        """Snapshot as Python dict (for debugging). Loses shadowing info."""
        d = {}
        cur = self.head
        while cur is not None:
            key_str = repr(cur.key)
            if key_str not in d:  # first occurrence wins (most recent)
                d[key_str] = cur.val
            cur = cur.nxt
        return d

    def as_map(self):
        """Convert env chain to a MAP list of {key val} pairs.
        This is the homoiconic bridge — env IS data."""
        from .types import make_list
        result = NIL
        cur = self.head
        while cur is not None:
            pair = Cell(cur.key, Cell(cur.val, NIL))
            result = Cell(pair, result)
            cur = cur.nxt
        return result

    def __repr__(self):
        bindings = []
        cur = self.head
        depth = 0
        while cur is not None and depth < 10:
            bindings.append(repr(cur))
            cur = cur.nxt
            depth += 1
        trail = '...' if cur is not None else ''
        return f'Env({" -> ".join(bindings)}{trail})'
