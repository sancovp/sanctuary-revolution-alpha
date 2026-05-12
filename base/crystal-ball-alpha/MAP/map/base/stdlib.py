"""MAP standard library — built-in functions.

All arithmetic operates on Fraction. No strings.
Type checking via TYPE? which returns a keyword atom.
"""

from fractions import Fraction
from .types import Atom, Cell, NIL, Nil, Builtin, MAPObj, Morph, cons, make_list
from .env import Env

def _ensure_num(x, op):
    if not isinstance(x, Atom) or not x.is_num:
        raise TypeError(f"{op} expects number, got {x}")
    return x.val

def _ensure_atom(x, op):
    if not isinstance(x, Atom):
        raise TypeError(f"{op} expects atom, got {x}")
    return x

def _to_bool(x):
    """MAP truthiness: NIL and Atom(0) are false, everything else true."""
    if isinstance(x, Nil):
        return False
    if isinstance(x, Atom) and x.is_num and x.val == 0:
        return False
    return True

def _from_bool(b):
    return Atom(1) if b else NIL

def make_stdlib():
    """Build the standard environment with all builtins."""
    env = Env()

    # --- Arithmetic (all Fraction) ---
    def add(args):
        return Atom(sum(_ensure_num(a, '+') for a in args))

    def sub(args):
        if len(args) == 1:
            return Atom(-_ensure_num(args[0], '-'))
        return Atom(_ensure_num(args[0], '-') - sum(_ensure_num(a, '-') for a in args[1:]))

    def mul(args):
        result = Fraction(1)
        for a in args:
            result *= _ensure_num(a, '*')
        return Atom(result)

    def div(args):
        if len(args) < 2:
            raise TypeError("/ needs at least 2 args")
        result = _ensure_num(args[0], '/')
        for a in args[1:]:
            d = _ensure_num(a, '/')
            if d == 0:
                raise ZeroDivisionError("Division by zero")
            result /= d
        return Atom(result)

    def mod(args):
        if len(args) != 2:
            raise TypeError("% needs exactly 2 args")
        a, b = _ensure_num(args[0], '%'), _ensure_num(args[1], '%')
        return Atom(a % b)

    # --- Comparison ---
    def eq(args):
        if len(args) != 2:
            raise TypeError("= needs 2 args")
        return _from_bool(args[0] == args[1])

    def lt(args):
        if len(args) != 2:
            raise TypeError("< needs 2 args")
        return _from_bool(_ensure_num(args[0], '<') < _ensure_num(args[1], '<'))

    def gt(args):
        if len(args) != 2:
            raise TypeError("> needs 2 args")
        return _from_bool(_ensure_num(args[0], '>') > _ensure_num(args[1], '>'))

    def lte(args):
        return _from_bool(not _to_bool(gt(args)))

    def gte(args):
        return _from_bool(not _to_bool(lt(args)))

    # --- Logic ---
    def not_fn(args):
        if len(args) != 1:
            raise TypeError("NOT needs 1 arg")
        return _from_bool(not _to_bool(args[0]))

    def and_fn(args):
        for a in args:
            if not _to_bool(a):
                return NIL
        return args[-1] if args else NIL

    def or_fn(args):
        for a in args:
            if _to_bool(a):
                return a
        return NIL

    # --- List operations ---
    def head_fn(args):
        if len(args) != 1:
            raise TypeError("HEAD needs 1 arg")
        x = args[0]
        if isinstance(x, Cell):
            return x.head
        raise TypeError(f"HEAD expects list, got {x}")

    def tail_fn(args):
        if len(args) != 1:
            raise TypeError("TAIL needs 1 arg")
        x = args[0]
        if isinstance(x, Cell):
            return x.tail
        raise TypeError(f"TAIL expects list, got {x}")

    def cons_fn(args):
        if len(args) != 2:
            raise TypeError("CONS needs 2 args")
        return Cell(args[0], args[1])

    def list_fn(args):
        return make_list(*args)

    def length_fn(args):
        if len(args) != 1:
            raise TypeError("LENGTH needs 1 arg")
        x = args[0]
        count = 0
        while isinstance(x, Cell):
            count += 1
            x = x.tail
        return Atom(count)

    def append_fn(args):
        if len(args) < 2:
            raise TypeError("APPEND needs at least 2 args")
        # Append all lists together
        result_items = []
        for lst in args:
            cur = lst
            while isinstance(cur, Cell):
                result_items.append(cur.head)
                cur = cur.tail
        return make_list(*result_items)

    def nth_fn(args):
        if len(args) != 2:
            raise TypeError("NTH needs 2 args (n list)")
        n = int(_ensure_num(args[0], 'NTH'))
        lst = args[1]
        for _ in range(n):
            if not isinstance(lst, Cell):
                raise IndexError(f"NTH: index {n} out of range")
            lst = lst.tail
        if not isinstance(lst, Cell):
            raise IndexError(f"NTH: index {n} out of range")
        return lst.head

    # --- Type checking ---
    def type_fn(args):
        if len(args) != 1:
            raise TypeError("TYPE? needs 1 arg")
        x = args[0]
        if isinstance(x, Nil):
            return Atom(':NIL')
        if isinstance(x, Atom):
            if x.is_num:
                return Atom(':NUM')
            if x.is_keyword:
                return Atom(':KW')
            return Atom(':SYM')
        if isinstance(x, Cell):
            return Atom(':CELL')
        if isinstance(x, Morph):
            return Atom(':MORPH')
        if isinstance(x, Builtin):
            return Atom(':BUILTIN')
        return Atom(':UNKNOWN')

    def nil_fn(args):
        if len(args) != 1:
            raise TypeError("NIL? needs 1 arg")
        return _from_bool(isinstance(args[0], (Nil,)))

    def atom_fn(args):
        if len(args) != 1:
            raise TypeError("ATOM? needs 1 arg")
        return _from_bool(isinstance(args[0], Atom))

    def cell_fn(args):
        if len(args) != 1:
            raise TypeError("CELL? needs 1 arg")
        return _from_bool(isinstance(args[0], Cell))

    def num_fn(args):
        if len(args) != 1:
            raise TypeError("NUM? needs 1 arg")
        return _from_bool(isinstance(args[0], Atom) and args[0].is_num)

    # --- IO ---
    def print_fn(args):
        print(' '.join(repr(a) for a in args))
        return args[-1] if args else NIL

    def repr_fn(args):
        """Return the printed representation as a list of symbol atoms."""
        if len(args) != 1:
            raise TypeError("REPR needs 1 arg")
        return Atom(repr(args[0]))

    # --- Module access ---
    def module_get(args):
        """Look up a binding in a module (association list).
        {module-get mod NAME} => value bound to NAME in mod."""
        if len(args) != 2:
            raise TypeError("MODULE-GET needs 2 args (module name)")
        mod = args[0]
        name = args[1]
        if not isinstance(name, Atom) or not name.is_sym:
            raise TypeError(f"MODULE-GET: name must be a symbol, got {name}")
        target = name.val
        cur = mod
        while isinstance(cur, Cell):
            pair = cur.head
            if isinstance(pair, Cell):
                key = pair.head
                if isinstance(key, Atom) and key.val == target:
                    return pair.tail.head if isinstance(pair.tail, Cell) else NIL
            cur = cur.tail
        from .eval import MAPError
        raise MAPError(f"MODULE-GET: {target} not found in module")

    def str_fn(args):
        """Check if argument is a string literal."""
        if len(args) != 1:
            raise TypeError("STR? needs 1 arg")
        return _from_bool(isinstance(args[0], Atom) and args[0].is_str)

    # --- Environment introspection (homoiconic!) ---
    # These get injected by the evaluator since they need env access

    # --- Register everything ---
    builtins = {
        '+': add, '-': sub, '*': mul, '/': div, '%': mod,
        '=': eq, '<': lt, '>': gt, '<=': lte, '>=': gte,
        'NOT': not_fn, 'AND': and_fn, 'OR': or_fn,
        'HEAD': head_fn, 'TAIL': tail_fn, 'CONS': cons_fn,
        'LIST': list_fn, 'LENGTH': length_fn, 'APPEND': append_fn,
        'NTH': nth_fn,
        'TYPE?': type_fn, 'NIL?': nil_fn, 'ATOM?': atom_fn,
        'CELL?': cell_fn, 'NUM?': num_fn,
        'PRINT': print_fn, 'REPR': repr_fn,
        'MODULE-GET': module_get, 'STR?': str_fn,
        'T': Atom(1),       # true constant
        'NIL': NIL,         # nil constant
    }

    for name, val in builtins.items():
        if callable(val) and not isinstance(val, MAPObj):
            env = env.bind(name, Builtin(name, val))
        else:
            env = env.bind(name, val)

    return env
