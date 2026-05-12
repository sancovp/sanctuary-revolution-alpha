"""Meta-interpreter — wraps base eval with introspection hooks.

This is the Python-side meta layer. It intercepts every eval step,
allowing you to trace, modify, or redirect evaluation. The meta-circular
evaluator (meta_circular.map) runs ON TOP of this.

Key hooks:
  pre_eval(expr, env)   -> (expr, env) or None to skip
  post_eval(expr, env, result) -> result (can transform)
  on_bind(name, val, env)
  on_apply(fn, args)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base.types import Atom, Cell, NIL, Nil, Morph, Builtin, MAPObj
from base.env import Env
from base import eval as base_eval

class MetaInterpreter:
    """Wraps map_eval with interceptable hooks."""

    def __init__(self, env=None):
        from base.stdlib import make_stdlib
        self.env = env or make_stdlib()
        self.hooks_pre = []
        self.hooks_post = []
        self.hooks_bind = []
        self.hooks_apply = []
        self.trace = []
        self.depth = 0
        self._patch()

    def _patch(self):
        """Monkey-patch base eval to route through our hooks."""
        original_eval = base_eval.map_eval
        meta = self

        def hooked_eval(expr, env, tail=False):
            meta.depth += 1
            # Pre-eval hooks
            for hook in meta.hooks_pre:
                result = hook(expr, env, meta.depth)
                if result is not None:
                    expr, env = result

            # Record trace
            meta.trace.append({
                'depth': meta.depth,
                'expr': repr(expr)[:200],
                'type': type(expr).__name__
            })

            # Actual eval
            val = original_eval(expr, env, tail)

            # Post-eval hooks
            for hook in meta.hooks_post:
                val = hook(expr, env, val, meta.depth)

            meta.depth -= 1
            return val

        base_eval.map_eval = hooked_eval
        self._original_eval = original_eval

    def unpatch(self):
        """Restore original eval."""
        base_eval.map_eval = self._original_eval

    def on_pre_eval(self, fn):
        """Register pre-eval hook. fn(expr, env, depth) -> (expr, env) | None"""
        self.hooks_pre.append(fn)
        return fn

    def on_post_eval(self, fn):
        """Register post-eval hook. fn(expr, env, result, depth) -> result"""
        self.hooks_post.append(fn)
        return fn

    def run(self, source):
        """Evaluate MAP source with hooks active."""
        from base.parser import parse
        exprs = parse(source)
        result = NIL
        for expr in exprs:
            result = base_eval.map_eval(expr, self.env)
        return result

    def run_file(self, path):
        """Evaluate a .map file."""
        with open(path) as f:
            return self.run(f.read())

    def get_trace(self, max_depth=None):
        """Return trace entries, optionally filtered by depth."""
        if max_depth is None:
            return self.trace
        return [t for t in self.trace if t['depth'] <= max_depth]

    def clear_trace(self):
        self.trace = []

    def eval_in_meta(self, map_source):
        """Evaluate a MAP expression through the meta-circular evaluator.

        This does TWO levels of interpretation:
        1. Base interpreter runs META-EVAL
        2. META-EVAL interprets the quoted expression

        This is the key test: the same program runs through two interpreters
        and should produce the same result.
        """
        wrapped = f'{{META-EVAL ~{map_source} META-ENV}}'
        return self.run(wrapped)

    def eval_program_in_meta(self, map_source):
        """Evaluate a multi-expression program through the meta-circular evaluator.

        Uses META-EVAL-PROGRAM to thread environment through BIND/DEF.
        Returns the final result. Updates META-ENV with any new bindings.

        This handles programs like:
          {bind x 10} {+ x 5}  => 15
          {def double | n | {* n 2}} {double 21} => 42
        """
        from base.parser import parse
        exprs = parse(map_source)
        # Build a quoted list of expressions for META-EVAL-PROGRAM
        from base.types import Cell, Atom, NIL, make_list
        quoted_exprs = NIL
        for e in reversed(exprs):
            quoted_exprs = Cell(e, quoted_exprs)

        # Call: {META-EVAL-PROGRAM ~{expr1 expr2 ...} META-ENV}
        # But we need to pass a list, so we quote the list
        call = Cell(Atom('META-EVAL-PROGRAM'),
                    Cell(Cell(Atom('QUOTE'), Cell(quoted_exprs, NIL)),
                         Cell(Atom('META-ENV'), NIL)))
        result = base_eval.map_eval(call, self.env)
        # Result is {final-value new-env} — extract value and update META-ENV
        if isinstance(result, Cell):
            val = result.head
            new_env = result.tail
            if isinstance(new_env, Cell):
                new_env = new_env.head
                # Update META-ENV in the base env
                self.env.mutate(Atom('META-ENV'), new_env)
            return val
        return result


def boot_meta():
    """Bootstrap the meta-circular evaluator.

    Returns a MetaInterpreter with the meta_circular.map loaded,
    ready to do two-level interpretation.
    """
    meta = MetaInterpreter()
    meta_path = os.path.join(os.path.dirname(__file__), 'meta_circular.map')
    meta.run_file(meta_path)
    return meta
