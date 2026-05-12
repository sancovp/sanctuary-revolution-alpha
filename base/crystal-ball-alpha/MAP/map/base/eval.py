"""MAP evaluator — the interpreter core.

Special forms:
  {bind name expr}         — bind value in current env
  {morph | params | body}  — lambda (closure over current env)
  {def name | params | body} — named morph (sugar for bind+morph)
  {when | cond | then}     — conditional (one branch)
  {when | cond | then | else} — conditional (two branches)
  {seq expr1 expr2 ...}    — sequence, returns last
  {loop | init | cond | step} — loop while cond, return last step
  {quote expr} / ~expr     — return unevaluated
  {eval expr} / @expr      — evaluate a quoted expression
  {env}                    — return current env as map data (homoiconic!)
  {apply fn args-list}     — apply function to list of args
  {macro | params | body}  — like morph but args are NOT evaluated (fexpr)

Tail-call optimization: seq and when in tail position reuse the loop.
"""

from .types import Atom, Cell, NIL, Nil, Morph, Builtin, MAPObj, make_list
from .env import Env

class MAPError(Exception):
    pass

class TailCall:
    """Sentinel for tail-call optimization."""
    __slots__ = ('expr', 'env')
    def __init__(self, expr, env):
        self.expr = expr
        self.env = env

class Macro(MAPObj):
    """Fexpr — like Morph but args are passed unevaluated."""
    __slots__ = ('params', 'body', 'env', 'name')
    def __init__(self, params, body, env, name=None):
        self.params = params
        self.body = body
        self.env = env
        self.name = name
    def __repr__(self):
        n = self.name or 'ANON'
        return f'<macro {n}>'


def map_eval(expr, env, tail=False):
    """Evaluate a MAP expression in an environment.

    The `tail` parameter enables TCO: when True, returns TailCall
    instead of recursing, and the trampoline in _trampoline() handles it.
    """
    while True:  # trampoline loop
        # --- Atoms ---
        if isinstance(expr, Nil):
            return NIL

        if isinstance(expr, Atom):
            if expr.is_num:
                return expr  # numbers self-evaluate
            if expr.is_keyword:
                return expr  # keywords self-evaluate
            if expr.is_str:
                return expr  # strings self-evaluate
            # Symbol lookup
            return env.lookup(expr)

        # --- First-class values self-evaluate (already reduced) ---
        if isinstance(expr, (Morph, Builtin)):
            return expr  # morphs and builtins are values, not expressions

        # --- Cell (function application or special form) ---
        if not isinstance(expr, Cell):
            raise MAPError(f"Cannot evaluate: {expr}")

        head = expr.head
        args_cell = expr.tail

        # --- Special forms (head is a symbol) ---
        if isinstance(head, Atom) and head.is_sym:
            form = head.val

            if form == 'QUOTE':
                # {quote expr} -> expr unevaluated
                if not isinstance(args_cell, Cell):
                    raise MAPError("QUOTE needs 1 arg")
                return args_cell.head

            if form == 'EVAL':
                # {eval expr} -> evaluate the result of evaluating expr
                if not isinstance(args_cell, Cell):
                    raise MAPError("EVAL needs 1 arg")
                inner = map_eval(args_cell.head, env)
                expr = inner  # trampoline
                continue

            if form == 'BIND':
                # {bind NAME expr}
                args = _collect_args(args_cell)
                if len(args) != 2:
                    raise MAPError("BIND needs name and value")
                name = args[0]
                if not isinstance(name, Atom) or not name.is_sym:
                    raise MAPError(f"BIND name must be symbol, got {name}")
                val = map_eval(args[1], env)
                # Mutate env in-place by consing new binding
                from .env import Frame
                frame = Frame(name, val, env.head)
                env.head = frame
                return val

            if form == 'SET!':
                # {set! NAME expr} — mutate existing binding
                args = _collect_args(args_cell)
                if len(args) != 2:
                    raise MAPError("SET! needs name and value")
                name = args[0]
                val = map_eval(args[1], env)
                env.mutate(name, val)
                return val

            if form == 'MORPH':
                # {morph {params...} body} — already restructured by parser
                args = _collect_args(args_cell)
                if len(args) < 2:
                    raise MAPError("MORPH needs params and body")
                params = _collect_args(args[0]) if isinstance(args[0], Cell) else []
                body = args[1]
                return Morph(params, body, env)

            if form == 'MACRO':
                args = _collect_args(args_cell)
                if len(args) < 2:
                    raise MAPError("MACRO needs params and body")
                params = _collect_args(args[0]) if isinstance(args[0], Cell) else []
                body = args[1]
                return Macro(params, body, env)

            if form == 'DEF':
                # {def NAME {params...} body}
                args = _collect_args(args_cell)
                if len(args) < 3:
                    raise MAPError("DEF needs name, params, body")
                name = args[0]
                params = _collect_args(args[1]) if isinstance(args[1], Cell) else []
                body = args[2]
                morph = Morph(params, body, env, name=repr(name))
                # Self-reference for recursion
                morph.env = env.bind(name, morph)
                from .env import Frame
                frame = Frame(name, morph, env.head)
                env.head = frame
                return morph

            if form == 'WHEN':
                # {when cond then} or {when cond then else}
                args = _collect_args(args_cell)
                if len(args) < 2:
                    raise MAPError("WHEN needs at least cond and then")
                cond_val = map_eval(args[0], env)
                if _truthy(cond_val):
                    expr = args[1]  # trampoline (TCO)
                    continue
                elif len(args) >= 3:
                    expr = args[2]  # trampoline (TCO)
                    continue
                else:
                    return NIL

            if form == 'SEQ':
                # {seq expr1 expr2 ... exprN} — evaluate all, return last
                args = _collect_args(args_cell)
                if not args:
                    return NIL
                for a in args[:-1]:
                    map_eval(a, env)
                expr = args[-1]  # trampoline (TCO)
                continue

            if form == 'LOOP':
                # {loop init-expr cond-expr step-expr}
                args = _collect_args(args_cell)
                if len(args) < 3:
                    raise MAPError("LOOP needs init, cond, step")
                init, cond, step = args[0], args[1], args[2]
                result = map_eval(init, env)
                while _truthy(map_eval(cond, env)):
                    result = map_eval(step, env)
                return result

            if form == 'ENV':
                # {env} — return current env as map data
                return env.as_map()

            if form == 'APPLY':
                # {apply fn args-list}
                args = _collect_args(args_cell)
                if len(args) != 2:
                    raise MAPError("APPLY needs fn and args-list")
                fn = map_eval(args[0], env)
                arg_list = map_eval(args[1], env)
                evaled_args = _collect_args(arg_list) if isinstance(arg_list, Cell) else []
                result = _apply(fn, evaled_args, env)
                if isinstance(result, TailCall):
                    expr = result.expr
                    env = result.env
                    continue
                return result

            if form == 'LOAD':
                # {load "path.map"} — evaluate file, return its bindings as alist
                args = _collect_args(args_cell)
                if len(args) != 1:
                    raise MAPError("LOAD needs 1 arg (file path)")
                path_atom = map_eval(args[0], env)
                if not isinstance(path_atom, Atom) or not path_atom.is_str:
                    raise MAPError("LOAD arg must be a string")
                return _load_module(path_atom.val[1:], env)  # strip " prefix

        # --- Function application ---
        fn = map_eval(head, env)

        if isinstance(fn, Macro):
            # Fexpr: pass args UNEVALUATED, evaluate body in CALLER's env
            # (not the macro's captured env). This is the standard fexpr
            # semantics: the macro has access to the call site's bindings.
            raw_args = _collect_args(args_cell)
            call_env = env.extend(fn.params, raw_args)
            expr = fn.body
            env = call_env
            continue

        evaled_args = _eval_args(args_cell, env)

        result = _apply(fn, evaled_args, env)
        if isinstance(result, TailCall):
            expr = result.expr
            env = result.env
            continue
        return result


def _apply(fn, args, caller_env):
    """Apply a function to evaluated arguments."""
    if isinstance(fn, Builtin):
        return fn.fn(args)

    if isinstance(fn, Morph):
        if len(args) != len(fn.params):
            raise MAPError(
                f"{fn} expects {len(fn.params)} args, got {len(args)}")
        call_env = fn.env.extend(fn.params, args)
        # Return TailCall for TCO
        return TailCall(fn.body, call_env)

    raise MAPError(f"Cannot call {fn} (type {type(fn).__name__})")


def _eval_args(args_cell, env):
    """Evaluate a cell chain of arguments."""
    result = []
    cur = args_cell
    while isinstance(cur, Cell):
        result.append(map_eval(cur.head, env))
        cur = cur.tail
    return result


def _collect_args(cell):
    """Collect cell chain into Python list without evaluating."""
    result = []
    cur = cell
    while isinstance(cur, Cell):
        result.append(cur.head)
        cur = cur.tail
    return result


def _truthy(val):
    """MAP truthiness."""
    if isinstance(val, Nil):
        return False
    if isinstance(val, Atom) and val.is_num and val.val == 0:
        return False
    return True


# --- Module loading ---

# Stack of directories for resolving relative paths in nested loads
_load_dirs = []

def _load_module(path, caller_env):
    """Load a .map file, evaluate it in a fresh env, return bindings as alist."""
    import os
    from .parser import parse
    from .stdlib import make_stdlib

    # Resolve relative path against current load dir or cwd
    if not os.path.isabs(path):
        if _load_dirs:
            path = os.path.join(_load_dirs[-1], path)
        else:
            path = os.path.abspath(path)

    if not os.path.exists(path):
        raise MAPError(f"LOAD: file not found: {path}")

    with open(path) as f:
        source = f.read()

    # Push this file's directory for nested loads
    _load_dirs.append(os.path.dirname(os.path.abspath(path)))

    try:
        mod_env = make_stdlib()
        exprs = parse(source)
        for expr in exprs:
            map_eval(expr, mod_env)
    finally:
        _load_dirs.pop()

    # Return bindings as an association list: {{NAME val} {NAME val} ...}
    # Skip stdlib builtins — only return user-defined bindings
    stdlib_names = set(make_stdlib().to_dict().keys())
    user_bindings = {k: v for k, v in mod_env.to_dict().items() if k not in stdlib_names}

    result = NIL
    for name, val in reversed(list(user_bindings.items())):
        pair = Cell(Atom(name), Cell(val, NIL))
        result = Cell(pair, result)
    return result


# --- Top-level interface ---

def run(source, env=None):
    """Parse and evaluate MAP source. Returns (result, env)."""
    from .parser import parse
    from .stdlib import make_stdlib

    if env is None:
        env = make_stdlib()

    exprs = parse(source)
    result = NIL
    for expr in exprs:
        result = map_eval(expr, env)
    return result, env


def repl():
    """Interactive MAP REPL."""
    from .stdlib import make_stdlib
    from .parser import parse, ParseError

    env = make_stdlib()
    print("MAP REPL — type expressions in {braces}. Ctrl-D to exit.")
    print("  ~expr to quote, @expr to eval, # for comments")

    while True:
        try:
            line = input("map> ")
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break
        if not line.strip():
            continue
        try:
            exprs = parse(line)
            for expr in exprs:
                result = map_eval(expr, env)
                if result is not NIL:
                    print(f"  => {result}")
        except (MAPError, ParseError, NameError, TypeError, ZeroDivisionError) as e:
            print(f"  !! {e}")
