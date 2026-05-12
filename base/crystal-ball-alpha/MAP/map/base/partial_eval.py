"""
partial_eval.py — MAP partial evaluator (SPECIALIZE).

This is the kernel of the Futamura projections.
Written in a deliberately Map-idiomatic style:
  - No dicts, only alists (Cell chains of {key val} pairs)
  - No loops, only recursion
  - isinstance checks mirror nil?/atom?/cell?/num?/type? exactly
  - Cell construction mirrors {cons a b} exactly
  - The MAP lift in specialize.map is a 1:1 syntactic translation.

SPECIALIZE(expr, static-env, dyn-vars) → residual-expr

  static-env: alist of (name . value) — what we know at specialization time
  dyn-vars:   Cell list of Atom symbols — what remains unknown (runtime input)
  residual:   a MAP expression that, when @-eval'd with dyn-vars bound,
              gives the same result as fully evaluating expr

The three Futamura projections are just:
  proj1 = SPECIALIZE(META-EVAL,   static-program, {INPUT})
  proj2 = SPECIALIZE(SPECIALIZE,  META-EVAL,      {PROGRAM INPUT})
  proj3 = SPECIALIZE(proj2,       SPECIALIZE,     {INTERPRETER PROGRAM INPUT})
"""

from base.types import Atom, Cell, NIL, Nil, Morph, Builtin, make_list
from base.stdlib import make_stdlib
from base.eval import map_eval, _apply
from base.env import Env
from fractions import Fraction


# ── Alist operations (mirror ENV-BIND / ENV-LOOKUP from meta_circular.map) ─

def ALIST_EMPTY():
    return NIL

def ALIST_BIND(alist, name, val):
    # {cons {list name val} alist}
    return Cell(Cell(name, Cell(val, NIL)), alist)

def ALIST_LOOKUP(alist, name):
    # {when | {nil? alist} | NIL |
    #   {when | {= {head {head alist}} name} | {head {tail {head alist}}} |
    #     {ALIST-LOOKUP {tail alist} name}}}
    if isinstance(alist, Nil):
        return NIL
    pair = alist.head
    if isinstance(pair, Cell) and pair.head == name:
        return pair.tail.head
    return ALIST_LOOKUP(alist.tail, name)


# ── List utilities (mirror head/tail/nil?/cons) ───────────────────────────────

def MEMBER(atom, lst):
    # {when | {nil? lst} | NIL |
    #   {when | {= {head lst} atom} | T |
    #     {MEMBER atom {tail lst}}}}
    if isinstance(lst, Nil):
        return NIL
    if lst.head == atom:
        return Atom('T')
    return MEMBER(atom, lst.tail)

def EXTEND_DYN(dyn_vars, params):
    # {when | {nil? params} | dyn-vars |
    #   {EXTEND-DYN {cons {head params} dyn-vars} {tail params}}}
    if isinstance(params, Nil):
        return dyn_vars
    return EXTEND_DYN(Cell(params.head, dyn_vars), params.tail)

def LIST_TO_PY(cell):
    result = []
    while isinstance(cell, Cell):
        result.append(cell.head)
        cell = cell.tail
    return result

def PY_TO_LIST(items):
    result = NIL
    for item in reversed(items):
        result = Cell(item, result)
    return result


# ── Sentinel for statically-resolved BINDs ────────────────────────────────────
# Mirrors {:META-BIND name val} pattern from meta_circular.map.
# SPECIALIZE returns {:STATIC-BIND name val} when a BIND/DEF is fully reduced.
# SPECIALIZE-SEQ threads these into the static-env for subsequent expressions.

def MAKE_STATIC_BIND(name, val):
    # {list :STATIC-BIND name val}
    return make_list(Atom(':STATIC-BIND'), name, val)

def IS_STATIC_BIND(val):
    # {when | {cell? val} | {= {head val} :STATIC-BIND} | NIL}
    return (isinstance(val, Cell) and
            isinstance(val.head, Atom) and
            val.head.val == ':STATIC-BIND')

def STATIC_BIND_NAME(sentinel):
    # {nth 1 sentinel}
    return sentinel.tail.head

def STATIC_BIND_VAL(sentinel):
    # {nth 2 sentinel}
    return sentinel.tail.tail.head


# ── Static check and evaluation ───────────────────────────────────────────────

def IS_STATIC(expr, dyn_vars):
    """
    True if expr contains no dynamic variable references.
    Mirrors: {def IS-STATIC? | expr dyn-vars | ...}

    {when | {nil? expr}  | T |
    {when | {atom? expr} |
      {when | {num? expr}             | T |
      {when | {= {type? expr} :KW}   | T |
      {when | {= expr ~T}            | T |
      {when | {= expr ~NIL}          | T |
        {when | {MEMBER? expr dyn-vars} | NIL | T}}}}} |
    {when | {cell? expr} |
      {when | {= {head expr} ~QUOTE} | T |
        {IS-STATIC-LIST? expr dyn-vars}} |
    T}}}   ; Morph/Builtin: already evaluated, always static
    """
    if isinstance(expr, Nil):
        return True
    if isinstance(expr, Atom):
        if expr.is_num:
            return True
        if expr.is_keyword:
            return True
        if expr.val in ('T', 'NIL', 'F'):
            return True
        return isinstance(MEMBER(expr, dyn_vars), Nil)
    if isinstance(expr, Cell):
        # Quoted data: always static
        if isinstance(expr.head, Atom) and expr.head.val == 'QUOTE':
            return True
        # MORPH form: its body still references dynamic vars — conservative
        if isinstance(expr.head, Atom) and expr.head.val == 'MORPH':
            return False
        return IS_STATIC_LIST(expr, dyn_vars)
    # Morph, Builtin, other evaluated values: always static
    return True

def IS_STATIC_LIST(cell, dyn_vars):
    # {when | {nil? cell} | T |
    #   {when | {IS-STATIC? {head cell} dyn-vars} |
    #     {IS-STATIC-LIST? {tail cell} dyn-vars} | NIL}}
    if isinstance(cell, Nil):
        return True
    if not IS_STATIC(cell.head, dyn_vars):
        return False
    return IS_STATIC_LIST(cell.tail, dyn_vars)

def TRUTHY(val):
    return not isinstance(val, Nil) and val != Atom(0)

def STATIC_EVAL(expr, static_env):
    """
    Evaluate a known-static expression.
    Builds a real MAP Env from the alist, then calls map_eval.
    """
    try:
        env = make_stdlib()
        # Convert alist to Env (walk alist in reverse so first binding wins)
        bindings = []
        cur = static_env
        while isinstance(cur, Cell):
            pair = cur.head
            if isinstance(pair, Cell):
                bindings.append((pair.head, pair.tail.head))
            cur = cur.tail
        for name, val in reversed(bindings):
            env = env.bind(name, val)
        return map_eval(expr, env)
    except Exception:
        return None

def STATIC_APPLY(fn, args_cell, static_env):
    """Try to apply fn to args immediately. Returns None on failure."""
    try:
        # Build as application and let map_eval resolve builtins from stdlib
        app = Cell(fn, args_cell)
        return STATIC_EVAL(app, static_env)
    except Exception:
        return None


# ── SPECIALIZE ────────────────────────────────────────────────────────────────

def SPECIALIZE(expr, static_env, dyn_vars):
    """
    Partially evaluate expr.
    Returns a residual MAP expression (or a :STATIC-BIND sentinel for BIND/DEF).
    """

    # NIL — self-evaluating
    # {when | {nil? expr} | NIL | ...}
    if isinstance(expr, Nil):
        return NIL

    # Already-evaluated value (Morph/Builtin) — always static
    # (In Map: the "else" of the nil?/atom?/cell? chain — it's a value)
    if isinstance(expr, (Morph, Builtin)):
        return expr

    # Atom
    # {when | {atom? expr} | ... | ...}
    if isinstance(expr, Atom):
        # Number: self-evaluating, static
        # {when | {num? expr} | expr | ...}
        if expr.is_num:
            return expr
        # Keyword: self-evaluating, static
        # {when | {= {type? expr} :KW} | expr | ...}
        if expr.is_keyword:
            return expr
        # NIL/T literals
        if expr.val == 'NIL':
            return NIL
        if expr.val == 'T':
            return expr
        # Symbol: check dynamic vs static
        # {when | {MEMBER? expr dyn-vars} | expr | ...}
        if not isinstance(MEMBER(expr, dyn_vars), Nil):
            return expr  # dynamic — leave as symbol reference
        # {bind val {ALIST-LOOKUP static-env expr}}
        val = ALIST_LOOKUP(static_env, expr)
        # {when | {nil? val} | expr | val}
        if isinstance(val, Nil):
            return expr  # unknown — treat as dynamic (conservative)
        return val  # static — inline the value

    # Cell — compound expression
    # {when | {cell? expr} | ... | expr}
    if not isinstance(expr, Cell):
        return expr  # shouldn't happen, but safe fallback

    tag = expr.head      # {head expr}
    args = expr.tail     # {tail expr}

    # Non-atom head: specialize the head too
    # {when | {atom? tag} | ... | {SPECIALIZE-APP tag args ...}}
    if not isinstance(tag, Atom):
        return SPECIALIZE_APP(tag, args, static_env, dyn_vars)

    tag_name = tag.val

    # QUOTE — quoted data, never reduce inside
    # {when | {= tag ~QUOTE} | expr | ...}
    if tag_name == 'QUOTE':
        return expr

    # EVAL — @expr: specialize the inner expression
    # {when | {= tag ~EVAL} | ...}
    if tag_name == 'EVAL':
        inner = args.head if isinstance(args, Cell) else NIL
        r_inner = SPECIALIZE(inner, static_env, dyn_vars)
        # If inner is a static QUOTE, unwrap and specialize
        if (isinstance(r_inner, Cell) and
                isinstance(r_inner.head, Atom) and r_inner.head.val == 'QUOTE'):
            return SPECIALIZE(r_inner.tail.head, static_env, dyn_vars)
        if IS_STATIC(r_inner, dyn_vars):
            val = STATIC_EVAL(r_inner, static_env)
            if val is not None:
                return SPECIALIZE(val, static_env, dyn_vars)
        return Cell(Atom('EVAL'), Cell(r_inner, NIL))

    # BIND — {bind NAME val-expr}
    # If val is static, return sentinel for SEQ threading; else residual BIND
    # {when | {= tag ~BIND} | ...}
    if tag_name == 'BIND':
        # {bind name {head args}}
        name = args.head
        # {bind val-expr {head {tail args}}}
        val_expr = args.tail.head
        r_val = SPECIALIZE(val_expr, static_env, dyn_vars)
        if IS_STATIC(r_val, dyn_vars):
            val = STATIC_EVAL(r_val, static_env)
            if val is not None:
                # Return sentinel: {:STATIC-BIND name val}
                return MAKE_STATIC_BIND(name, val)
        return Cell(Atom('BIND'), Cell(name, Cell(r_val, NIL)))

    # DEF — {def NAME params body}
    # Params are dynamic for the body; return sentinel for SEQ threading
    # {when | {= tag ~DEF} | ...}
    if tag_name == 'DEF':
        name = args.head
        params = args.tail.head
        body = args.tail.tail.head
        # Params become dynamic for the body
        new_dyn = EXTEND_DYN(dyn_vars, params)
        r_body = SPECIALIZE(body, static_env, new_dyn)
        r_def = Cell(Atom('DEF'), Cell(name, Cell(params, Cell(r_body, NIL))))
        return MAKE_STATIC_BIND(name, r_def)

    # MORPH — {morph params body}
    # Params are dynamic for the body; return residual morph
    # {when | {= tag ~MORPH} | ...}
    if tag_name == 'MORPH':
        params = args.head
        body = args.tail.head
        new_dyn = EXTEND_DYN(dyn_vars, params)
        r_body = SPECIALIZE(body, static_env, new_dyn)
        return Cell(Atom('MORPH'), Cell(params, Cell(r_body, NIL)))

    # WHEN — {when cond then else?}
    # KEY REDUCTION: if cond is static, eliminate the branch entirely
    # {when | {= tag ~WHEN} | ...}
    if tag_name == 'WHEN':
        cond_expr = args.head
        then_expr = args.tail.head if isinstance(args.tail, Cell) else NIL
        else_expr = (args.tail.tail.head
                     if isinstance(args.tail, Cell) and isinstance(args.tail.tail, Cell)
                     else NIL)

        r_cond = SPECIALIZE(cond_expr, static_env, dyn_vars)

        # Static condition: eliminate branch at specialization time
        if IS_STATIC(r_cond, dyn_vars):
            cond_val = STATIC_EVAL(r_cond, static_env)
            if cond_val is None:
                cond_val = r_cond  # fallback: use residual directly
            if TRUTHY(cond_val):
                return SPECIALIZE(then_expr, static_env, dyn_vars)
            else:
                if not isinstance(else_expr, Nil):
                    return SPECIALIZE(else_expr, static_env, dyn_vars)
                return NIL

        # Dynamic condition: specialize both branches, keep WHEN
        r_then = SPECIALIZE(then_expr, static_env, dyn_vars)
        r_else = (SPECIALIZE(else_expr, static_env, dyn_vars)
                  if not isinstance(else_expr, Nil) else NIL)
        if isinstance(r_else, Nil):
            return Cell(Atom('WHEN'), Cell(r_cond, Cell(r_then, NIL)))
        return Cell(Atom('WHEN'), Cell(r_cond, Cell(r_then, Cell(r_else, NIL))))

    # SEQ — {seq e1 e2 ...}
    # Thread static BINDs into env for subsequent expressions
    # {when | {= tag ~SEQ} | {SPECIALIZE-SEQ args ...} | ...}
    if tag_name == 'SEQ':
        return SPECIALIZE_SEQ(args, static_env, dyn_vars)

    # Application — {fn arg1 arg2 ...}
    return SPECIALIZE_APP(tag, args, static_env, dyn_vars)


def SPECIALIZE_LIST(cell, static_env, dyn_vars):
    """
    Specialize each element of a Cell list.
    {when | {nil? cell} | NIL |
      {cons {SPECIALIZE {head cell} ...} {SPECIALIZE-LIST {tail cell} ...}}}
    """
    if isinstance(cell, Nil):
        return NIL
    r_head = SPECIALIZE(cell.head, static_env, dyn_vars)
    r_tail = SPECIALIZE_LIST(cell.tail, static_env, dyn_vars)
    return Cell(r_head, r_tail)


def SPECIALIZE_SEQ(exprs, static_env, dyn_vars):
    """
    Specialize a SEQ body, threading :STATIC-BIND sentinels into static-env.
    This is what makes BIND/DEF specialization work across expression boundaries.
    """
    if isinstance(exprs, Nil):
        return NIL

    r = SPECIALIZE(exprs.head, static_env, dyn_vars)
    rest = exprs.tail

    # :STATIC-BIND sentinel: thread name=val into static-env for the rest
    if IS_STATIC_BIND(r):
        name = STATIC_BIND_NAME(r)
        val  = STATIC_BIND_VAL(r)
        new_env = ALIST_BIND(static_env, name, val)
        if isinstance(rest, Nil):
            # Last was a DEF/BIND — return the value
            return val
        return SPECIALIZE_SEQ(rest, new_env, dyn_vars)

    # Last expression in SEQ
    if isinstance(rest, Nil):
        return r

    # More expressions: build residual SEQ, flattening nested SEQs
    r_rest = SPECIALIZE_SEQ(rest, static_env, dyn_vars)
    return SEQ_CONS(r, r_rest)


def SEQ_CONS(head, tail):
    """
    Build {seq head tail...}, flattening if tail is already a SEQ.
    """
    if isinstance(tail, Nil):
        return head
    if isinstance(tail, Cell) and isinstance(tail.head, Atom) and tail.head.val == 'SEQ':
        # Flatten: {seq head e1 e2 ...}
        return Cell(Atom('SEQ'), Cell(head, tail.tail))
    return Cell(Atom('SEQ'), Cell(head, Cell(tail, NIL)))


def SPECIALIZE_APP(fn_expr, args_cell, static_env, dyn_vars):
    """
    Specialize a function application.
    If fn and all args are static: inline the call (evaluate immediately).
    Otherwise: return residual application.
    """
    r_fn   = SPECIALIZE(fn_expr,  static_env, dyn_vars)
    r_args = SPECIALIZE_LIST(args_cell, static_env, dyn_vars)

    # All static: try to inline
    if IS_STATIC(r_fn, dyn_vars) and IS_STATIC_LIST(r_args, dyn_vars):
        val = STATIC_APPLY(r_fn, r_args, static_env)
        if val is not None:
            return val

    return Cell(r_fn, r_args)


# ── The three Futamura projections ────────────────────────────────────────────

def load_meta_eval():
    """Load META-EVAL from meta_circular.map into an alist."""
    import os
    from base.eval import run
    path = os.path.join(os.path.dirname(__file__), 'meta/meta_circular.map')
    src = open(path).read()
    env = None
    from base.parser import parse
    for expr in parse(src):
        try:
            _, env = run(expr, env)
        except Exception:
            pass
    # Convert Env to alist
    alist = ALIST_EMPTY()
    if env:
        cur = env.head
        while cur is not None:
            alist = ALIST_BIND(alist, cur.key, cur.val)
            cur = cur.nxt
    return alist

def proj1(meta_eval_alist, static_program_quoted, dynamic_input_vars):
    """
    First projection: SPECIALIZE(META-EVAL, static-program) → compiled-program.
    meta_eval_alist: alist containing META-EVAL (the interpreter)
    static_program_quoted: a quoted MAP expression (the static program)
    dynamic_input_vars: Cell list of Atom symbols (runtime inputs)
    """
    from base.parser import parse_one
    meta_eval_expr = parse_one('META-EVAL')
    return SPECIALIZE(meta_eval_expr, meta_eval_alist, dynamic_input_vars)

def proj2(specialize_alist, meta_eval_quoted, dynamic_vars):
    """
    Second projection: SPECIALIZE(SPECIALIZE, META-EVAL) → compiler.
    The result is a function that takes a program and produces compiled code.
    """
    from base.parser import parse_one
    spec_expr = parse_one('SPECIALIZE')
    return SPECIALIZE(spec_expr, specialize_alist, dynamic_vars)
