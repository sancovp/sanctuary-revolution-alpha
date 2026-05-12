"""
Futamura REPL
=============
Boots the full MAP stack (base → meta → super),
installs the partial evaluator as builtins,
and drops into an interactive session where you can call
{PE-SPECIALIZE}, {FUTAMURA-1}, {FUTAMURA-2}, {FUTAMURA-3} directly.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fractions import Fraction
from base.types import Atom, Cell, NIL, Morph, Builtin, make_list
from base.stdlib import make_stdlib
from base.eval import run as map_run, map_eval

from meta.partial_eval import (
    specialize, SEnv, is_pe_s, is_pe_d, pe_val,
    futamura_1st, futamura_2nd, futamura_3rd,
    load_meta_eval, pe_s, pe_d, python_list_to_map
)


def make_pe_builtins(base_env):
    """Install PE functions as builtins into a MAP env."""
    env = base_env

    # ── PE-SPECIALIZE: takes a quoted expr and an alist of static bindings ──
    def pe_specialize_builtin(args):
        if len(args) < 1:
            return NIL
        expr = args[0]
        bindings_alist = args[1] if len(args) > 1 else NIL

        # Build SEnv from alist: list of {NAME val} pairs
        senv = SEnv.with_stdlib()
        node = bindings_alist
        while isinstance(node, Cell):
            pair = node.head
            if isinstance(pair, Cell):
                name = str(pair.head)
                val = pair.tail.head if isinstance(pair.tail, Cell) else NIL
                senv = senv.extend(name, val)
            node = node.tail

        result = specialize(expr, senv)
        return pe_val(result)  # return the residual (or value)

    env = env.bind(Atom('PE-SPECIALIZE'), Builtin(pe_specialize_builtin, 'PE-SPECIALIZE'))

    # ── PE-FOLD: specialize with empty senv + stdlib only (constant fold) ──
    def pe_fold_builtin(args):
        if not args:
            return NIL
        senv = SEnv.with_stdlib()
        result = specialize(args[0], senv)
        return pe_val(result)

    env = env.bind(Atom('PE-FOLD'), Builtin(pe_fold_builtin, 'PE-FOLD'))

    # ── FUTAMURA-1: 1st projection ──
    def futamura1_builtin(args):
        if not args:
            return Atom(':NEED-PROGRAM')
        prog_expr = args[0]
        # Convert AST to source string for futamura_1st
        prog_src = str(prog_expr)
        result, info = futamura_1st(prog_src, verbose=False)
        residual = pe_val(result)
        return residual

    env = env.bind(Atom('FUTAMURA-1'), Builtin(futamura1_builtin, 'FUTAMURA-1'))

    # ── FUTAMURA-DESCRIBE: print projection descriptions ──
    def futamura_desc_builtin(args):
        n = int(args[0].val) if args and isinstance(args[0], Atom) and args[0].is_num else 1
        if n == 2:
            print(futamura_2nd())
        elif n == 3:
            print(futamura_3rd())
        else:
            print(futamura_2nd())
        return Atom(':OK')

    env = env.bind(Atom('FUTAMURA-DESCRIBE'), Builtin(futamura_desc_builtin, 'FUTAMURA-DESCRIBE'))

    # ── PE-STATIC?: check if a PE result is fully static ──
    def pe_static_builtin(args):
        # We can't tag values from outside, but we can ask: is this expr self-evaluating?
        if not args:
            return NIL
        v = args[0]
        if isinstance(v, Atom) and (v.is_num or (v.is_sym and v.val.startswith(':'))):
            return Atom(Fraction(1))
        return NIL

    env = env.bind(Atom('STATIC-VAL?'), Builtin(pe_static_builtin, 'STATIC-VAL?'))

    return env


def run_repl():
    print("\n" + "═" * 62)
    print("  FUTAMURA REPL — MAP Partial Evaluation System")
    print("  base/ → meta/ → super/ + PE builtins")
    print("═" * 62 + "\n")

    # Boot base env with stdlib + PE builtins
    print("[*] Booting base environment...")
    env = make_stdlib()
    env = make_pe_builtins(env)
    print("[✓] PE builtins installed\n")

    # Load meta-circular evaluator
    print("[*] Loading META-EVAL from meta_circular.map...")
    meta_env = load_meta_eval(verbose=False)
    # Merge meta env into base env
    cur = meta_env.head
    while cur is not None:
        env = env.bind(cur.key, cur.val)
        cur = cur.nxt
    print("[✓] META-EVAL ready\n")

    # Run built-in demonstration
    print("── Built-in Demo ──")
    demo_cases = [
        # (description, map_expr, note)
        ("Constant folding",
         "{PE-FOLD ~{+ 2 3}}",
         "2+3 both static → 5"),
        ("Partial reduction",
         "{PE-SPECIALIZE ~{+ X 1} {list {list ~X 10}}}",
         "X=10 static → {<+> 10 1} evaluable"),
        ("Branch elimination",
         "{PE-SPECIALIZE ~{when | {= N 0} | 1 | {* N {FACT {- N 1}}}} {list {list ~N 0}}}",
         "N=0 → 1 (branch collapsed)"),
        ("Branch partial",
         "{PE-SPECIALIZE ~{when | {= N 0} | 1 | {* N {FACT {- N 1}}}} {list {list ~N 3}}}",
         "N=3 → {* 3 {FACT 2}} (one step unrolled)"),
        ("1st Futamura — {+ 1 2}",
         "{FUTAMURA-1 ~{+ 1 2}}",
         "program frozen in, META-ENV stays dynamic"),
        ("1st Futamura — {* 6 7}",
         "{FUTAMURA-1 ~{* 6 7}}",
         "program frozen in"),
    ]

    map_env = env
    for desc, expr, note in demo_cases:
        print(f"\n  [{desc}]")
        print(f"  {expr}")
        try:
            result, map_env = map_run(expr, map_env)
            print(f"  → {result}")
            print(f"  ({note})")
        except Exception as e:
            print(f"  → ERROR: {e}")

    print("\n── 2nd & 3rd Projections ──")
    print(futamura_2nd())
    print(futamura_3rd())

    print("── REPL ──")
    print("Try: {PE-FOLD ~{* 3 {+ 1 1}}}")
    print("     {PE-SPECIALIZE ~{+ X Y} {list {list ~X 42}}}")
    print("     {FUTAMURA-1 ~{when | {= X 0} | :ZERO | :NONZERO}}")
    print("     {FUTAMURA-DESCRIBE 2}")
    print("     {FUTAMURA-DESCRIBE 3}")
    print()

    while True:
        try:
            raw = input("futamura> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[bye]")
            break
        if not raw:
            continue
        if raw in ('quit', 'exit', 'q'):
            print("[bye]")
            break
        try:
            result, map_env = map_run(raw, map_env)
            print(f"=> {result}")
        except Exception as e:
            print(f"[error] {e}")


if __name__ == '__main__':
    run_repl()
