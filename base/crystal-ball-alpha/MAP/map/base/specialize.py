"""MAP Partial Evaluator — engine of the Futamura projections.

specialize(expr, static_bindings[, map_env]) reduces a MAP AST with
known-static bindings, returning a residual expression with all
statically-determinable subexpressions already evaluated.

Futamura projections:
  1st: specialize(interp_body, {EXPR: program})        → compiled_program
  2nd: specialize(specialize,  {INTERP: interp})       → compiler
  3rd: specialize(specialize,  {SPECIALIZE: specialize}) → compiler_compiler
"""

from .types import Atom, Cell, NIL, Nil, Morph, Builtin, MAPObj
from .eval import _truthy


# ── Result wrappers ────────────────────────────────────────────────────────

class Static:
    __slots__ = ('val',)
    def __init__(self, val): self.val = val

class Dynamic:
    __slots__ = ('expr',)
    def __init__(self, expr): self.expr = expr


# ── Value embedding ────────────────────────────────────────────────────────

def embed(val):
    """Embed a static value as a self-evaluating residual expression."""
    if isinstance(val, Nil):   return Atom('NIL')
    if isinstance(val, Atom):
        if val.is_num or val.is_keyword or val.is_str: return val
        return Cell(Atom('QUOTE'), Cell(val, NIL))
    if isinstance(val, Builtin): return Atom(val.name)     # embed as symbol
    return Cell(Atom('QUOTE'), Cell(val, NIL))             # quote everything else

def residualize(r):
    return embed(r.val) if isinstance(r, Static) else r.expr


# ── AST utilities ──────────────────────────────────────────────────────────

def _cells(cell):
    """Collect Cell chain into list."""
    out = []
    while isinstance(cell, Cell):
        out.append(cell.head)
        cell = cell.tail
    return out

def _list(items):
    """Build Cell chain from list."""
    r = NIL
    for x in reversed(items): r = Cell(x, r)
    return r


# ── Purity ────────────────────────────────────────────────────────────────

_PURE = {'+','-','*','/','=','<','>','<=','>=',
         'CONS','HEAD','TAIL','LIST','LENGTH','APPEND','NTH',
         'NIL?','ATOM?','CELL?','NUM?','TYPE?','NOT','AND','OR','REPR'}

def _pure(val): return isinstance(val, Builtin) and val.name in _PURE


# ── Substitution (used when inlining morphs with dynamic params) ───────────

def subst(expr, subs):
    """Substitute free symbol occurrences from subs dict."""
    if not subs or isinstance(expr, (Nil, Morph, Builtin)): return expr
    if isinstance(expr, Atom):
        return subs.get(expr.val, expr) if expr.is_sym else expr
    if not isinstance(expr, Cell): return expr
    h = expr.head
    if isinstance(h, Atom) and h.val == 'QUOTE': return expr
    if isinstance(h, Atom) and h.val in ('MORPH', 'DEF'):
        args = _cells(expr.tail)
        if h.val == 'MORPH' and len(args) >= 2:
            shadowed = {p.val for p in _cells(args[0])
                        if isinstance(p, Atom) and p.is_sym}
            inner = {k:v for k,v in subs.items() if k not in shadowed}
            return Cell(h, Cell(args[0], Cell(subst(args[1], inner), NIL)))
        if h.val == 'DEF' and len(args) >= 3:
            shadowed = {p.val for p in _cells(args[1])
                        if isinstance(p, Atom) and p.is_sym}
            if isinstance(args[0], Atom) and args[0].is_sym:
                shadowed.add(args[0].val)
            inner = {k:v for k,v in subs.items() if k not in shadowed}
            return Cell(h, Cell(args[0], Cell(args[1], Cell(subst(args[2], inner), NIL))))
    return Cell(subst(h, subs), subst(expr.tail, subs))


# ── Core PE ────────────────────────────────────────────────────────────────

_MAX = 24   # max inline depth

def pe(expr, s, depth=0, inlining=None):
    """Partially evaluate expr.

    s:        dict {str -> MAPObj}  (mutated for BIND side-effects)
    depth:    recursion depth counter
    inlining: frozenset of morph ids currently being inlined (recursion guard)
    """
    if inlining is None: inlining = frozenset()
    if depth > _MAX: return Dynamic(expr)

    # NIL / atoms
    if isinstance(expr, Nil): return Static(NIL)
    if isinstance(expr, Atom):
        if expr.is_num or expr.is_keyword or expr.is_str: return Static(expr)
        n = expr.val
        if n == 'NIL': return Static(NIL)
        if n == 'T':   return Static(Atom('T'))
        return Static(s[n]) if n in s else Dynamic(expr)
    if isinstance(expr, (Morph, Builtin)): return Static(expr)
    if not isinstance(expr, Cell): return Dynamic(expr)

    h, args_cell = expr.head, expr.tail
    args = _cells(args_cell)

    # ── Special forms ──────────────────────────────────────────────────────
    if isinstance(h, Atom) and h.is_sym:
        form = h.val

        if form == 'QUOTE':
            return Static(args[0] if args else NIL)

        if form == 'BIND':
            if len(args) < 2: return Dynamic(expr)
            name_a, rhs = args[0], args[1]
            rhs_r = pe(rhs, s, depth, inlining)
            if (isinstance(rhs_r, Static) and
                    isinstance(name_a, Atom) and name_a.is_sym):
                s[name_a.val] = rhs_r.val
                return Static(NIL)
            return Dynamic(Cell(h, Cell(name_a, Cell(residualize(rhs_r), NIL))))

        if form == 'SET!':
            if len(args) < 2: return Dynamic(expr)
            return Dynamic(Cell(h, Cell(args[0],
                           Cell(residualize(pe(args[1], s, depth, inlining)), NIL))))

        if form == 'WHEN':
            if len(args) < 2: return Dynamic(expr)
            cond_r = pe(args[0], s, depth, inlining)
            if isinstance(cond_r, Static):
                if _truthy(cond_r.val): return pe(args[1], s, depth, inlining)
                elif len(args) >= 3:    return pe(args[2], s, depth, inlining)
                else:                   return Static(NIL)
            parts = [residualize(cond_r), residualize(pe(args[1], s, depth, inlining))]
            if len(args) >= 3:
                parts.append(residualize(pe(args[2], s, depth, inlining)))
            return Dynamic(Cell(h, _list(parts)))

        if form == 'SEQ':
            return pe_seq(args, s, depth, inlining)

        if form == 'MORPH':
            if len(args) < 2: return Dynamic(expr)
            params_cell, body = args[0], args[1]
            pnames = {p.val for p in _cells(params_cell)
                      if isinstance(p, Atom) and p.is_sym}
            inner = {k:v for k,v in s.items() if k not in pnames}
            body_r = pe(body, inner, depth, inlining)
            return Dynamic(Cell(h, Cell(params_cell, Cell(residualize(body_r), NIL))))

        if form == 'DEF':
            if len(args) < 3: return Dynamic(expr)
            name_a, params_cell, body = args[0], args[1], args[2]
            pnames = {p.val for p in _cells(params_cell)
                      if isinstance(p, Atom) and p.is_sym}
            name_str = name_a.val if isinstance(name_a, Atom) and name_a.is_sym else None
            inner = {k:v for k,v in s.items()
                     if k not in pnames and k != name_str}
            body_r = pe(body, inner, depth, inlining)
            return Dynamic(Cell(h, Cell(name_a, Cell(params_cell,
                           Cell(residualize(body_r), NIL)))))

        if form == 'EVAL':
            if not args: return Dynamic(expr)
            arg_r = pe(args[0], s, depth, inlining)
            if isinstance(arg_r, Static):
                try:
                    from .eval import map_eval
                    from .stdlib import make_stdlib
                    return Static(map_eval(arg_r.val, make_stdlib()))
                except Exception: pass
            return Dynamic(Cell(h, Cell(residualize(arg_r), NIL)))

    # ── Application ────────────────────────────────────────────────────────
    op_r  = pe(h, s, depth, inlining)
    args_r = [pe(a, s, depth, inlining) for a in args]

    # Pure builtin with all-static args → evaluate now
    if (isinstance(op_r, Static) and _pure(op_r.val) and
            all(isinstance(a, Static) for a in args_r)):
        try:
            return Static(op_r.val.fn([a.val for a in args_r]))
        except Exception: pass

    # Morph inlining (at least one static arg, not recursive)
    if (isinstance(op_r, Static) and isinstance(op_r.val, Morph) and
            id(op_r.val) not in inlining and
            depth < _MAX and
            len(args_r) == len(op_r.val.params) and
            any(isinstance(a, Static) for a in args_r)):
        inlined = _inline(op_r.val, args_r, s, depth, inlining)
        if inlined is not None:
            return inlined

    return Dynamic(Cell(residualize(op_r), _list([residualize(a) for a in args_r])))


def pe_seq(exprs, s, depth, inlining):
    if not exprs: return Static(NIL)
    residuals = []
    for i, sub in enumerate(exprs):
        r = pe(sub, s, depth, inlining)
        is_last = (i == len(exprs) - 1)
        if isinstance(r, Static):
            if is_last:
                if not residuals: return r
                residuals.append(embed(r.val))
            # else: non-last static → elide
        else:
            residuals.append(r.expr)
    if not residuals: return Static(NIL)
    if len(residuals) == 1: return Dynamic(residuals[0])
    return Dynamic(Cell(Atom('SEQ'), _list(residuals)))


def _inline(morph, args_r, s, depth, inlining):
    """Inline a morph: bind static params, substitute dynamic ones after PE."""
    if len(args_r) != len(morph.params): return None

    # Inner static env: morph's captured env + caller's s
    inner = {}
    if morph.env:
        cur = morph.env.head
        while cur is not None:
            if isinstance(cur.key, Atom) and cur.key.is_sym:
                inner[cur.key.val] = cur.val
            cur = cur.nxt
    inner.update(s)

    dyn_subs = {}
    for param, arg_r in zip(morph.params, args_r):
        if not isinstance(param, Atom) or not param.is_sym: continue
        pname = param.val
        if isinstance(arg_r, Static):
            inner[pname] = arg_r.val
        else:
            inner.pop(pname, None)
            dyn_subs[pname] = arg_r.expr

    new_inlining = inlining | {id(morph)}
    body_r = pe(morph.body, inner, depth + 1, new_inlining)

    if not dyn_subs: return body_r
    if isinstance(body_r, Static): return body_r
    return Dynamic(subst(body_r.expr, dyn_subs))


# ── Public interface ────────────────────────────────────────────────────────

def specialize(expr, static_bindings, map_env=None):
    """Specialize a MAP expression.

    Automatically seeds with stdlib builtins. Pass map_env to also include
    user-defined morphs (needed when specializing calls to user interpreters).
    """
    from .stdlib import make_stdlib

    s = {}
    cur = make_stdlib().head
    while cur is not None:
        if isinstance(cur.key, Atom) and cur.key.is_sym:
            s[cur.key.val] = cur.val
        cur = cur.nxt

    if map_env is not None:
        cur = map_env.head
        while cur is not None:
            if isinstance(cur.key, Atom) and cur.key.is_sym:
                s[cur.key.val] = cur.val
            cur = cur.nxt

    if isinstance(static_bindings, dict):
        s.update(static_bindings)
    else:
        c = static_bindings
        while isinstance(c, Cell):
            pair = c.head
            if isinstance(pair, Cell):
                key, val = pair.head, (pair.tail.head if isinstance(pair.tail, Cell) else NIL)
                if isinstance(key, Atom) and key.is_sym:
                    s[key.val] = val
            c = c.tail

    return residualize(pe(expr, s))
