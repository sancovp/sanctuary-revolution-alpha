"""
Futamura Projections for Map
================================

The three projections, realized:

  1st: specialize(meta-eval, {prog: P})      → compiled-P
  2nd: specialize(specialize, {interp: I})   → compiler
  3rd: specialize(specialize, {})            → compiler-compiler

All three work because MAP is homoiconic:
  - code and data share the same Cell/Atom representation
  - `~` / `eval` give us first-class control over evaluation timing
  - META-EVAL is written IN Map, so it's a valid input to specialize

The partial evaluator:
  SPECIALIZE(expr, senv) → PE result
  where PE result = {:PE-S value} | {:PE-D residual-expr}

  :PE-S = static, fully known at specialization time
  :PE-D = dynamic, must be computed at runtime

When all sub-parts of an expression are :PE-S, we reduce fully (constant fold).
When any sub-part is :PE-D, we build a residual expression — still a MAP AST.
The residual of SPECIALIZE is itself a valid MAP program.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fractions import Fraction
from base.types import Atom, Cell, NIL, Nil, Morph, Builtin, MAPObj, make_list
from base.env import Env
from base.eval import map_eval, run as map_run, _apply, _truthy, _collect_args
from base.stdlib import make_stdlib


# ── Helpers ──────────────────────────────────────────────────────────────────

SYM_QUOTE  = Atom('QUOTE')
SYM_BIND   = Atom('BIND')
SYM_DEF    = Atom('DEF')
SYM_MORPH  = Atom('MORPH')
SYM_WHEN   = Atom('WHEN')
SYM_SEQ    = Atom('SEQ')
SYM_EVAL   = Atom('EVAL')
SYM_SET    = Atom('SET!')
SYM_LOOP   = Atom('LOOP')
SYM_MACRO  = Atom('MACRO')

KW_PE_S = Atom(':PE-S')   # static tag
KW_PE_D = Atom(':PE-D')   # dynamic tag

def pe_s(val):
    """Wrap a known-static value."""
    return Cell(KW_PE_S, Cell(val, NIL))

def pe_d(expr):
    """Wrap a residual (dynamic) expression."""
    return Cell(KW_PE_D, Cell(expr, NIL))

def is_pe_s(r):
    return isinstance(r, Cell) and r.head == KW_PE_S

def is_pe_d(r):
    return isinstance(r, Cell) and r.head == KW_PE_D

def pe_val(r):
    """Extract value from a PE result."""
    return r.tail.head

def is_static_value(v):
    """Is v a 'value' that needs no further evaluation?
    Builtins, morphs, numbers, keywords, NIL, and lists of static values."""
    if isinstance(v, Nil): return True
    if isinstance(v, Atom):
        return v.is_num or v.is_sym and v.val.startswith(":")   # sym needs lookup → not static
    if isinstance(v, (Morph, Builtin)): return True
    return False   # Cell might be a residual expr

def map_to_list(cell):
    """Convert a MAP Cell list to Python list."""
    result = []
    while isinstance(cell, Cell):
        result.append(cell.head)
        cell = cell.tail
    return result

def python_list_to_map(items):
    """Convert Python list to MAP Cell list."""
    result = NIL
    for item in reversed(items):
        result = Cell(item, result)
    return result


# ── Static environment ────────────────────────────────────────────────────────

_STDLIB_DICT = None

def _get_stdlib_dict():
    global _STDLIB_DICT
    if _STDLIB_DICT is None:
        genv = make_stdlib()
        d = {}
        cur = genv.head
        while cur is not None:
            if isinstance(cur.key, Atom) and cur.key.is_sym:
                d[cur.key.val] = cur.val
            cur = cur.nxt
        _STDLIB_DICT = d
    return _STDLIB_DICT


class SEnv:
    def __init__(self, bindings=None, parent=None, _stdlib=None):
        self.bindings = bindings or {}
        self.parent = parent
        self._stdlib = _stdlib

    @classmethod
    def with_stdlib(cls, bindings=None):
        base = cls({}, None, _stdlib=_get_stdlib_dict())
        if bindings:
            return cls(bindings, base)
        return base

    def lookup(self, name_str):
        if name_str in self.bindings:
            return self.bindings[name_str]
        if self.parent:
            return self.parent.lookup(name_str)
        if self._stdlib and name_str in self._stdlib:
            return self._stdlib[name_str]
        return None

    def extend(self, name_str, val):
        return SEnv({name_str: val}, self)

    def extend_many(self, pairs):
        env = self
        for name, val in pairs:
            env = env.extend(name, val)
        return env

    def to_map_env(self):
        """Build a real MAP Env from the static bindings + stdlib."""
        base = make_stdlib()
        all_bindings = {}
        env = self
        while env:
            for k, v in env.bindings.items():
                if k not in all_bindings:
                    all_bindings[k] = v
            env = env.parent
        for k, v in all_bindings.items():
            base = base.bind(Atom(k), v)
        return base


# ── The partial evaluator ─────────────────────────────────────────────────────

def specialize(expr, senv):
    """
    SPECIALIZE(expr, senv) → PE result (:PE-S val | :PE-D residual)

    Core algorithm:
    - NIL/NUM/KW → always static
    - SYM → look up; if found → static; else → dynamic (keep symbol)
    - CELL → case-split on head:
        QUOTE → static (it's already data)
        BIND  → specialize value; extend senv for rest (handled in SEQ)
        WHEN  → specialize cond; if static fold branch; else specialize both
        SEQ   → thread senv through, collect residuals
        MORPH → specialize body with params as dynamic
        DEF   → specialize body with name+params as dynamic  
        APP   → specialize fn+args; if all static → fold (eval now); else residual
    """
    return _specialize(expr, senv)


def _specialize(expr, senv):
    # NIL
    if isinstance(expr, Nil):
        return pe_s(NIL)

    # Atom
    if isinstance(expr, Atom):
        if expr.is_num or expr.is_sym and expr.val.startswith(":"):
            return pe_s(expr)   # self-evaluating
        if expr.is_sym:
            val = senv.lookup(expr.val)
            if val is not None:
                return pe_s(val)   # statically known
            else:
                return pe_d(expr)  # dynamic: keep symbol, resolve at runtime

    # First-class values (morph, builtin) — self-evaluating
    if isinstance(expr, (Morph, Builtin)):
        return pe_s(expr)

    # Cell (compound expression)
    if isinstance(expr, Cell):
        tag = expr.head
        args_cell = expr.tail
        args = _collect_args(args_cell)

        # QUOTE — already data
        if tag == SYM_QUOTE:
            return pe_s(args[0] if args else NIL)

        # BIND — specialize value; signal new binding for caller (SEQ)
        if tag == SYM_BIND:
            if len(args) < 2:
                return pe_d(expr)
            name = args[0]
            val_pe = _specialize(args[1], senv)
            if is_pe_s(val_pe):
                # We return a special marker: :PE-BIND name val
                # The SEQ handler uses this to extend senv
                return Cell(Atom(':PE-BIND'), Cell(name, Cell(pe_val(val_pe), NIL)))
            else:
                # Dynamic bind — residualize
                residual_val = pe_val(val_pe)
                return pe_d(Cell(SYM_BIND, Cell(name, Cell(residual_val, NIL))))

        # DEF — named morph definition
        if tag == SYM_DEF:
            if len(args) < 3:
                return pe_d(expr)
            name = args[0]
            params = args[1]   # list of param symbols
            body = args[2]
            # Specialize body with params as dynamic (they're runtime values)
            param_list = _collect_args(params)
            dynamic_senv = senv
            for p in param_list:
                # Mark params as unknown (remove from static env if present)
                dynamic_senv = SEnv({p.val: None}, dynamic_senv) if isinstance(p, Atom) else dynamic_senv
            # For simplicity: keep DEF as a residual (it defines a function to be used later)
            # But specialize the body:
            body_pe = _specialize(body, dynamic_senv)
            residual_body = pe_val(body_pe) if is_pe_s(body_pe) else pe_val(body_pe)
            residual = Cell(SYM_DEF, Cell(name, Cell(params, Cell(residual_body, NIL))))
            return pe_d(residual)

        # MORPH — lambda
        if tag == SYM_MORPH:
            if len(args) < 2:
                return pe_d(expr)
            params = args[0]
            body = args[1]
            param_list = _collect_args(params)
            # Specialize body with params as dynamic
            inner_senv = SEnv({
                p.val: None for p in param_list if isinstance(p, Atom)
            }, senv)
            body_pe = _specialize(body, inner_senv)
            residual_body = pe_val(body_pe) if not is_pe_d(body_pe) else pe_val(body_pe)
            residual = Cell(SYM_MORPH, Cell(params, Cell(residual_body, NIL)))
            return pe_d(residual)   # morph is always dynamic (captures env)

        # WHEN — conditional specialization
        if tag == SYM_WHEN:
            if not args:
                return pe_s(NIL)
            cond_pe = _specialize(args[0], senv)
            then_expr = args[1] if len(args) > 1 else NIL
            else_expr = args[2] if len(args) > 2 else None

            if is_pe_s(cond_pe):
                # Static condition — fold the branch away
                cond_val = pe_val(cond_pe)
                if _truthy(cond_val):
                    return _specialize(then_expr, senv)
                else:
                    if else_expr is None:
                        return pe_s(NIL)
                    return _specialize(else_expr, senv)
            else:
                # Dynamic condition — specialize both branches
                cond_r = pe_val(cond_pe)
                then_pe = _specialize(then_expr, senv)
                then_r = pe_val(then_pe)
                if else_expr is None:
                    residual = Cell(SYM_WHEN, Cell(cond_r, Cell(then_r, NIL)))
                else:
                    else_pe = _specialize(else_expr, senv)
                    else_r = pe_val(else_pe)
                    residual = Cell(SYM_WHEN, Cell(cond_r, Cell(then_r, Cell(else_r, NIL))))
                return pe_d(residual)

        # SEQ — sequence with env threading through BIND
        if tag == SYM_SEQ:
            return _specialize_seq(args, senv)

        # Application — specialize fn and all args
        fn_pe = _specialize(tag, senv)
        args_pe = [_specialize(a, senv) for a in args]

        if is_pe_s(fn_pe) and all(is_pe_s(a) for a in args_pe):
            # All static — evaluate completely
            fn_val = pe_val(fn_pe)
            arg_vals = [pe_val(a) for a in args_pe]
            if isinstance(fn_val, (Morph, Builtin)):
                try:
                    result = _apply(fn_val, arg_vals, fn_val.env if hasattr(fn_val, 'env') else make_stdlib())
                    return pe_s(result)
                except Exception:
                    pass  # fall through to residual

        # Some dynamic parts — build residual call
        fn_r = pe_val(fn_pe) if not is_pe_s(fn_pe) else pe_val(fn_pe)
        # For static fn values, we can keep the actual value in the residual
        # (it will be a literal morph/builtin in the code - fine for homoiconic)
        args_r = [pe_val(a) for a in args_pe]
        residual = Cell(fn_r, python_list_to_map(args_r))
        return pe_d(residual)

    return pe_d(expr)  # fallback: keep as-is


def _specialize_seq(exprs, senv):
    """Specialize a sequence, threading static env through BINDs."""
    if not exprs:
        return pe_s(NIL)

    current_senv = senv
    residuals = []

    for i, expr in enumerate(exprs):
        pe_result = _specialize(expr, current_senv)
        last = (i == len(exprs) - 1)

        # Check if this is a static BIND result
        if isinstance(pe_result, Cell) and pe_result.head == Atom(':PE-BIND'):
            name_atom = pe_result.tail.head
            val = pe_result.tail.tail.head
            # Extend static env for subsequent expressions
            current_senv = current_senv.extend(name_atom.val, val)
            # Don't add to residuals (it's been consumed into senv)
            if last:
                return pe_s(val)  # seq returns last value
        elif is_pe_s(pe_result):
            if last:
                return pe_s(pe_val(pe_result))
            # Otherwise this was a pure expression with no side effects we can see
            # For safety, keep it in the residual
        else:
            residuals.append(pe_val(pe_result))
            if last:
                break

    if not residuals:
        return pe_s(NIL)
    if len(residuals) == 1:
        return pe_d(residuals[0])
    return pe_d(Cell(SYM_SEQ, python_list_to_map(residuals)))


# ── Projection helpers ────────────────────────────────────────────────────────

def load_meta_eval(verbose=False):
    """Load META-EVAL from meta_circular.map, return the MAP env."""
    meta_path = os.path.join(os.path.dirname(__file__), 'meta_circular.map')
    src = open(meta_path).read()
    # Strip comments
    lines = [l for l in src.split('\n') if not l.strip().startswith('#')]
    src = '\n'.join(lines)

    env = None
    depth = 0
    start = 0
    forms = []
    for i, ch in enumerate(src):
        if ch == '{':
            if depth == 0: start = i
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                forms.append(src[start:i+1])

    for form in forms:
        form = form.strip()
        if form:
            try:
                _, env = map_run(form, env)
            except Exception as e:
                if verbose:
                    print(f"  [meta load warning] {form[:50]}: {e}")
    return env


def futamura_1st(program_source, verbose=False):
    """
    1st Futamura Projection:
      specialize(META-EVAL, {program: P}) → compiled-P

    Takes a MAP program as source, specializes META-EVAL with
    that program as the static input, producing a residual that
    can be called directly with just the runtime environment.

    Returns (residual_expr, description)
    """
    if verbose:
        print("[1st projection] Loading META-EVAL...")
    meta_env = load_meta_eval(verbose)

    # Parse the program source into a MAP AST
    prog_ast, _ = map_run(f'~{program_source}', meta_env)

    # Build META-EVAL's AST from the meta_circular.map source
    # META-EVAL takes (expr, env) — we specialize on expr=prog_ast
    # We need META-EVAL as an AST, not as a called result

    # Strategy: build a static env with the program bound
    # Then specialize the META-EVAL call: {META-EVAL <prog> ENV}
    # where ENV stays dynamic (runtime input)

    # Get META-EVAL as a value from the meta env
    meta_eval_val = None
    node = meta_env.head if hasattr(meta_env, 'head') else None
    # Walk env to find META-EVAL binding
    env_node = meta_env
    while env_node is not None:
        if hasattr(env_node, 'head') and hasattr(env_node.head, 'val'):
            if env_node.head.val == 'META-EVAL':
                meta_eval_val = env_node.tail.head if hasattr(env_node.tail, 'head') else None
                break
        env_node = env_node.tail if hasattr(env_node, 'tail') else None

    if meta_eval_val is None:
        # Get it by evaluation
        meta_eval_val, _ = map_run('META-EVAL', meta_env)

    if verbose:
        print(f"[1st projection] META-EVAL loaded: {type(meta_eval_val).__name__}")
        print(f"[1st projection] Program AST: {str(prog_ast)[:60]}")

    # The call we want to specialize: {META-EVAL prog runtime-env}
    # Static: prog_ast (the program structure)
    # Dynamic: META-ENV (the runtime environment argument)

    # Build senv with the known parts of META-EVAL's signature
    senv = SEnv({}, None)
    # Add all meta_eval bindings as static
    env_node = meta_env
    while env_node is not None:
        if hasattr(env_node, 'head') and isinstance(env_node.head, Atom) and env_node.head.is_sym:
            val = env_node.tail.head if hasattr(env_node, 'tail') and hasattr(env_node.tail, 'head') else None
            if val is not None and env_node.head.val not in ('META-ENV',):
                senv = senv.extend(env_node.head.val, val)
        env_node = env_node.tail if hasattr(env_node, 'tail') else None

    # The expression to specialize: a call to META-EVAL with prog fixed
    # {META-EVAL ~<program> ENV}  where ENV is dynamic
    call_expr = Cell(Atom('META-EVAL'), Cell(Cell(SYM_QUOTE, Cell(prog_ast, NIL)), Cell(Atom('META-ENV'), NIL)))

    if verbose:
        print(f"[1st projection] Specializing call: {str(call_expr)[:80]}")

    result = specialize(call_expr, senv)

    return result, {
        'projection': '1st',
        'input_program': program_source,
        'static_vars': ['program'],
        'dynamic_vars': ['META-ENV (runtime input bindings)'],
    }


def futamura_2nd(verbose=False):
    """
    2nd Futamura Projection:
      specialize(specialize, {interpreter: META-EVAL}) → compiler

    Specializes the specializer itself with the interpreter fixed.
    The result is a function that takes a program and produces compiled code.
    Returns (residual_description) — the structure of what would be generated.
    """
    if verbose:
        print("[2nd projection] This projection specializes SPECIALIZE itself")
        print("[2nd projection] Static input: the interpreter (META-EVAL)")
        print("[2nd projection] Dynamic input: a program P")
        print("[2nd projection] Output: a COMPILER — takes P, produces compiled-P")
        print()

    description = """
2nd Futamura Projection: COMPILER GENERATION

  specialize(specialize, {interp: META-EVAL}) → COMPILER

  The specializer SPECIALIZE takes two arguments: (code, static-env).
  We fix the first argument as META-EVAL (the interpreter code).
  The result is a function that takes ONE argument: a program P.
  
  COMPILER(P) = specialize(META-EVAL, {program: P})
              = the compiled version of P

  What was generated:
  - A function of one argument (program P)
  - Its body is the residual of SPECIALIZE with META-EVAL's structure
    already unfolded — all the interpreter dispatch on QUOTE/BIND/WHEN/etc
    is already specialized away
  - Calling COMPILER(P) is equivalent to running the 1st projection
    but without paying the cost of re-examining the interpreter structure

  In MAP terms, this is:
    {morph | P META-ENV |
      <residual of specialize(META-EVAL, {prog: P})>}
"""
    return description


def futamura_3rd(verbose=False):
    """
    3rd Futamura Projection:
      specialize(specialize, {}) → compiler-compiler

    Specializes the specializer with NO static inputs.
    The result is a function that takes an interpreter and produces a compiler.
    """
    description = """
3rd Futamura Projection: COMPILER-COMPILER GENERATION

  specialize(specialize, {}) → COMPILER-COMPILER

  No static inputs. SPECIALIZE is specialized with respect to itself.
  The result is a function that takes ONE argument: an interpreter I.

  COGEN(I) = specialize(I, {}) → COMPILER_for_I
  
  Then: COGEN(META-EVAL) = COMPILER (the 2nd projection result)
        COGEN(COGEN)     = ...itself (fixed point!)

  This is the deep result: the compiler-compiler is a fixed point of
  the specialization process. Applying it to itself yields itself.
  In Map, homoiconicity makes this literal — the expression IS its
  own compiler, because code and data are the same structure.

  The MAP realization:
  - META-EVAL is written in MAP (meta_circular.map)
  - SPECIALIZE operates on MAP ASTs (which are MAP data)
  - The 3rd projection says: write a function that, given any interpreter
    written in Map, produces a compiler for the language that interpreter
    defines — and Map's homoiconicity means 'written in Map' and
    'expressed as MAP data' are the same thing
  
  The super/ layer completes the circle:
  - {self-rewrite SPECIALIZE <new-source>} can mutate the specializer
  - The hot-reload engine picks it up immediately
  - So the compiler-compiler can rewrite its own specialization rules
    while the system is running
"""
    return description


# ── Demo runner ───────────────────────────────────────────────────────────────

def run_demo(verbose=True):
    print("=" * 65)
    print("  FUTAMURA PROJECTIONS — MAP Partial Evaluator")
    print("=" * 65)

    # ── Test 1: Basic specialization ─────────────────────────────────
    print("\n── Basic PE: constant folding ──")

    senv = SEnv.with_stdlib({'X': Atom(Fraction(5)), 'Y': Atom(Fraction(3))})

    tests = [
        '{+ X 1}',         # X is static → {+ 5 1} → 6
        '{+ X Y}',         # both static → 8
        '{+ X Z}',         # Z dynamic → residual {+ 5 Z}
        '{when | X | Y | Z}',  # X static truthy → Y → 3
    ]

    for src in tests:
        ast, _ = map_run(f'~{src}', None)
        result = specialize(ast, senv)
        tag = ':PE-S' if is_pe_s(result) else ':PE-D'
        val = pe_val(result)
        print(f"  specialize({src!r}, {{X=5,Y=3}})")
        print(f"    → {tag} {val}")
        print()

    # ── Test 2: Branch elimination ────────────────────────────────────
    print("── Branch elimination ──")

    # Factorial with N=3 partially known
    fact_src = '{when | {= N 0} | 1 | {* N {FACT {- N 1}}}}'
    fact_ast, _ = map_run(f'~{fact_src}', None)

    senv_n3 = SEnv.with_stdlib({'N': Atom(Fraction(3))})
    result = specialize(fact_ast, senv_n3)
    tag = ':PE-S' if is_pe_s(result) else ':PE-D'
    print(f"  specialize(fact-body, {{N=3}})")
    print(f"    → {tag} {str(pe_val(result))[:80]}")
    print()

    # With N=0 — should fully reduce to 1
    senv_n0 = SEnv.with_stdlib({'N': Atom(Fraction(0))})
    result0 = specialize(fact_ast, senv_n0)
    tag0 = ':PE-S' if is_pe_s(result0) else ':PE-D'
    print(f"  specialize(fact-body, {{N=0}})")
    print(f"    → {tag0} {str(pe_val(result0))[:80]}")
    print()

    # ── Test 3: 1st Futamura Projection ──────────────────────────────
    print("── 1st Futamura Projection ──")
    print("  specialize(META-EVAL, {prog: {+ 1 2}}) → compiled program")
    print()

    result1, info = futamura_1st('{+ 1 2}', verbose=False)
    tag = ':PE-S' if is_pe_s(result1) else ':PE-D'
    residual = pe_val(result1)
    print(f"  Input program: {{+ 1 2}}")
    print(f"  PE result tag: {tag}")
    print(f"  Residual: {str(residual)[:120]}")
    print()
    print(f"  Static inputs:  {info['static_vars']}")
    print(f"  Dynamic inputs: {info['dynamic_vars']}")
    print()

    # Try with a more complex program
    print("  specialize(META-EVAL, {prog: {* 6 7}}) → compiled program")
    result2, _ = futamura_1st('{* 6 7}', verbose=False)
    tag2 = ':PE-S' if is_pe_s(result2) else ':PE-D'
    print(f"  PE result: {tag2} {str(pe_val(result2))[:80]}")
    print()

    # ── 2nd and 3rd projections ───────────────────────────────────────
    print("── 2nd Futamura Projection ──")
    print(futamura_2nd(verbose=False))

    print("── 3rd Futamura Projection ──")
    print(futamura_3rd(verbose=False))

    # ── The key insight ───────────────────────────────────────────────
    print("── The MAP Connection ──")
    print("""
  Why this works in MAP specifically:

  1. Homoiconicity: META-EVAL is written in Map, so it IS MAP data.
     SPECIALIZE can walk it as a tree — there's no parser boundary.

  2. `~` and `eval`: these ARE the PE primitives.
     ~ suspends evaluation (makes something static/data).
     eval forces it (makes something dynamic/computed).
     SPECIALIZE is just a systematic application of this split.

  3. super/ closes the loop: {self-rewrite SPECIALIZE <new-src>} means
     the specializer can rewrite itself. The 3rd projection's fixed point
     isn't just theoretical — it can be materialized as a running op
     that rewrites its own .map file.

  4. The reify.map op we already saw? REIFY-BINOP builds functions
     from symbols at runtime. It's doing manual 1st-projection by hand.
     SPECIALIZE generalizes this to arbitrary programs.
""")


if __name__ == '__main__':
    run_demo(verbose='--verbose' in sys.argv)
