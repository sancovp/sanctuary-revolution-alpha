"""Super REPL — the top-level entry point.

Boots: base interpreter -> meta-circular evaluator -> registry -> hot engine
Then drops into a REPL where you can:
  - Write MAP code (runs through meta-interpreter)
  - Invoke operations: {reg-invoke OP args...}
  - Define new operations: {reg-define-op NAME SOURCE}
  - Hot-reload: edit .map files in ops/ and they auto-reload
  - Self-modify: running code can rewrite its own operations
  - Introspect: {env}, {self-dispatch}, {reg-list}
"""

import sys
import os

# Fix path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from meta.meta_interp import boot_meta
from super.registry import Registry
from super.hot import HotEngine, SelfMod
from base.types import NIL
from base.parser import parse, ParseError
from base.eval import MAPError


def boot():
    """Full bootstrap: base -> meta -> registry -> hot -> self-mod."""
    print("[super] Booting base interpreter...")
    meta = boot_meta()
    print(f"[super] Meta-circular evaluator loaded. Trace depth: {len(meta.trace)}")

    print("[super] Initializing operation registry...")
    ops_dir = os.path.join(os.path.dirname(__file__), 'ops')
    registry = Registry(meta, ops_dir)
    registry.load_all()
    print(f"[super] {len(registry.entries)} operations registered")

    print("[super] Starting hot-reload engine...")
    hot = HotEngine(registry)
    hot.start()

    print("[super] Installing self-modification interface...")
    selfmod = SelfMod(registry, hot)

    return meta, registry, hot, selfmod


def repl():
    """Interactive super-REPL with hot-reload."""
    meta, registry, hot, selfmod = boot()

    print("\n=== MAP Super-REPL ===")
    print("  Three layers active: base -> meta -> super")
    print("  Operations auto-reload from ops/")
    print("  Type :help for commands, Ctrl-D to exit\n")

    while True:
        # Check for hot reloads
        reloaded = hot.drain_pending()
        if reloaded:
            print(f"  [hot] Reloaded: {', '.join(reloaded)}")

        try:
            line = input("super> ")
        except (EOFError, KeyboardInterrupt):
            print("\n[super] Shutting down...")
            hot.stop()
            break

        line = line.strip()
        if not line:
            continue

        # Meta-commands
        if line == ':help':
            print("  :help          — this message")
            print("  :ops           — list registered operations")
            print("  :trace [N]     — show eval trace (optional depth limit)")
            print("  :stale         — show ops needing reload")
            print("  :reload        — force reload all stale ops")
            print("  :meta EXPR     — eval through meta-circular evaluator")
            print("  :new NAME      — create new operation template")
            print("  Otherwise, type MAP expressions in {braces}")
            continue

        if line == ':ops':
            for name, entry in sorted(registry.entries.items()):
                stale = " [STALE]" if entry.is_stale() else ""
                print(f"  {name}: invoked {entry.invocations}x{stale}")
            if not registry.entries:
                print("  (none)")
            continue

        if line.startswith(':trace'):
            parts = line.split()
            max_d = int(parts[1]) if len(parts) > 1 else 5
            for t in meta.get_trace(max_d)[-20:]:
                indent = '  ' * min(t['depth'], 10)
                print(f"  {indent}[{t['depth']}] {t['type']}: {t['expr'][:80]}")
            continue

        if line == ':stale':
            for name, entry in registry.entries.items():
                if entry.is_stale():
                    print(f"  {name}")
            continue

        if line == ':reload':
            count = registry.reload_stale()
            print(f"  Reloaded {count} operations")
            continue

        if line.startswith(':meta '):
            expr = line[6:]
            try:
                result = meta.eval_in_meta(expr)
                print(f"  [meta] => {result}")
            except Exception as e:
                print(f"  [meta] !! {e}")
            continue

        if line.startswith(':new '):
            name = line[5:].strip().upper()
            template = f'''# Operation: {name}
# Created from super-REPL

{{def {name} | args |
  {{print :OP-{name} :CALLED-WITH args}}
  args}}

{{print :OP-{name} :REGISTERED}}
'''
            registry.define_op(name, template)
            print(f"  Created ops/{name.lower()}.map — edit and it hot-reloads")
            continue

        # MAP expression
        try:
            exprs = parse(line)
            for expr in exprs:
                from base.eval import map_eval
                result = map_eval(expr, meta.env)
                if result is not NIL:
                    print(f"  => {result}")
        except (MAPError, ParseError, NameError, TypeError) as e:
            print(f"  !! {e}")
        except Exception as e:
            print(f"  !! Unexpected: {type(e).__name__}: {e}")


if __name__ == '__main__':
    repl()
