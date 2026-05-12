"""MAP type system — homoiconic, everything is a Cell or Atom.

Homoiconicity: code and data share the same Cell/Atom representation.
A program `{+ 1 2}` is literally a Cell chain: Cell(Atom('+'), Cell(Atom(1), Cell(Atom(2), NIL)))
You can build that chain with `cons`, inspect it with `head`/`tail`, then `@`-eval it.
"""

from fractions import Fraction

class MAPObj:
    """Base for all MAP values."""
    pass

class Nil(MAPObj):
    """The empty list / false / nothing. Singleton."""
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    def __repr__(self): return "NIL"
    def __bool__(self): return False
    def __eq__(self, other): return isinstance(other, Nil)
    def __hash__(self): return hash(None)

NIL = Nil()

class Atom(MAPObj):
    """Symbol or number. Numbers are always Fraction."""
    __slots__ = ('val',)
    def __init__(self, val):
        if isinstance(val, (int, float)):
            self.val = Fraction(val)
        elif isinstance(val, Fraction):
            self.val = val
        else:
            s = str(val)
            # Keywords (:foo) and strings ("foo) keep their prefix, symbols go UPPER
            if s.startswith(':') or s.startswith('"'):
                self.val = s
            else:
                self.val = s.upper()

    @property
    def is_num(self):
        return isinstance(self.val, Fraction)

    @property
    def is_sym(self):
        return isinstance(self.val, str)

    @property
    def is_keyword(self):
        return self.is_sym and self.val.startswith(':')

    @property
    def is_str(self):
        return self.is_sym and self.val.startswith('"')

    def __repr__(self):
        if self.is_num:
            if self.val.denominator == 1:
                return str(self.val.numerator)
            return str(self.val)
        if self.is_str:
            return f'"{self.val[1:]}"'  # strip internal prefix, add real quotes
        return self.val

    def __eq__(self, other):
        return isinstance(other, Atom) and self.val == other.val

    def __hash__(self):
        return hash(self.val)

class Cell(MAPObj):
    """Cons cell — the universal container. A list is a chain of Cells ending in NIL."""
    __slots__ = ('head', 'tail')
    def __init__(self, head, tail=None):
        self.head = head
        self.tail = tail if tail is not None else NIL

    def __repr__(self):
        parts = []
        cur = self
        while isinstance(cur, Cell):
            parts.append(repr(cur.head))
            cur = cur.tail
        if cur != NIL:
            parts.append('.')
            parts.append(repr(cur))
        return '{' + ' '.join(parts) + '}'

    def __eq__(self, other):
        if not isinstance(other, Cell):
            return False
        return self.head == other.head and self.tail == other.tail

    def __hash__(self):
        return hash((self.head, self.tail))

    def to_list(self):
        """Convert cell chain to Python list."""
        result = []
        cur = self
        while isinstance(cur, Cell):
            result.append(cur.head)
            cur = cur.tail
        return result

class Morph(MAPObj):
    """Lambda / closure. Params + body + captured env."""
    __slots__ = ('params', 'body', 'env', 'name')
    def __init__(self, params, body, env, name=None):
        self.params = params   # list of Atom symbols
        self.body = body       # MAPObj (unevaluated)
        self.env = env         # Env (cons-cell chain)
        self.name = name

    def __repr__(self):
        pnames = ' '.join(repr(p) for p in self.params)
        n = self.name or 'ANON'
        return f'<morph {n} | {pnames}>'

class Builtin(MAPObj):
    """Built-in function wrapping a Python callable."""
    __slots__ = ('name', 'fn')
    def __init__(self, name, fn):
        self.name = name
        self.fn = fn
    def __repr__(self):
        return f'<builtin {self.name}>'

# --- Constructors ---

def make_list(*items):
    """Build a Cell chain from Python values."""
    result = NIL
    for item in reversed(items):
        if isinstance(item, MAPObj):
            result = Cell(item, result)
        elif isinstance(item, (int, float, Fraction)):
            result = Cell(Atom(item), result)
        elif isinstance(item, str):
            result = Cell(Atom(item), result)
        else:
            raise TypeError(f"Can't convert {type(item)} to Map")
    return result

def cons(h, t):
    return Cell(h, t)
