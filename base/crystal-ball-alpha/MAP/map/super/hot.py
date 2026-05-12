"""Hot-reload engine — watches ops/ and auto-reloads on change.

Also provides the self-modification interface: programs running on
the meta-interpreter can rewrite their own operations and trigger
reload, achieving genuine runtime self-modification.

The watcher runs in a background thread. The REPL checks for
pending reloads on each prompt.
"""

import os
import time
import threading

from .registry import Registry


class HotEngine:
    """Watches ops/ directory and triggers reload on changes."""

    def __init__(self, registry):
        self.registry = registry
        self.poll_interval = 0.5  # seconds
        self._running = False
        self._thread = None
        self._pending_reloads = []
        self._lock = threading.Lock()

    def start(self):
        """Start background watcher thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop background watcher."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None

    def _watch_loop(self):
        """Poll for changes and queue reloads."""
        while self._running:
            stale = []
            for name, entry in self.registry.entries.items():
                if entry.is_stale():
                    stale.append(name)

            # Also scan for new files
            if os.path.exists(self.registry.ops_dir):
                for fname in os.listdir(self.registry.ops_dir):
                    if fname.endswith('.map'):
                        name = fname[:-4].upper()
                        if name not in self.registry.entries:
                            stale.append(name)

            if stale:
                with self._lock:
                    self._pending_reloads.extend(stale)

            time.sleep(self.poll_interval)

    def drain_pending(self):
        """Process any pending reloads. Called from REPL loop."""
        with self._lock:
            pending = list(set(self._pending_reloads))
            self._pending_reloads.clear()

        if pending:
            for name in pending:
                self.registry.load(name)
            return pending
        return []


class SelfMod:
    """Interface for programs to modify themselves.

    Exposes operations that let a running MAP program:
    - Rewrite operation source files
    - Create new operations
    - Modify the dispatch logic itself
    - Inspect and alter the registry
    """

    def __init__(self, registry, hot_engine):
        self.registry = registry
        self.hot = hot_engine
        self._install()

    def _install(self):
        """Add self-modification builtins to the meta-interpreter."""
        from base.types import Atom, Builtin, NIL, Cell, make_list
        sm = self

        def self_rewrite(args):
            """Rewrite an operation's source. Takes name + new-source-sym."""
            if len(args) != 2:
                raise TypeError("SELF-REWRITE needs name and source")
            name = repr(args[0]).upper()
            source = repr(args[1])
            if name in sm.registry.entries:
                entry = sm.registry.entries[name]
                if entry.source_path:
                    with open(entry.source_path, 'w') as f:
                        f.write(source)
                    sm.registry.load(name)
                    return Atom(1)
            return NIL

        def self_inspect(args):
            """Return the source code of an operation as a symbol atom."""
            if len(args) != 1:
                raise TypeError("SELF-INSPECT needs 1 arg (name)")
            name = repr(args[0]).upper()
            if name in sm.registry.entries:
                entry = sm.registry.entries[name]
                if entry.source_path and os.path.exists(entry.source_path):
                    with open(entry.source_path) as f:
                        return Atom(f.read())
            return NIL

        def self_fork(args):
            """Fork an operation: copy source to new name, register it."""
            if len(args) != 2:
                raise TypeError("SELF-FORK needs old-name and new-name")
            old = repr(args[0]).upper()
            new = repr(args[1]).upper()
            if old in sm.registry.entries:
                entry = sm.registry.entries[old]
                if entry.source_path and os.path.exists(entry.source_path):
                    with open(entry.source_path) as f:
                        source = f.read()
                    # Replace old name with new name in source so the
                    # forked file defines the function under its new name
                    source = source.replace(old, new)
                    return Atom(1) if sm.registry.define_op(new, source) else NIL
            return NIL

        def self_dispatch(args):
            """Get/set the dispatch table as MAP data.
            With 0 args: returns registry as list of entries.
            With 1 arg (list of {NAME SOURCE} pairs): replace/register ops.
              Each element should be a two-element list: {NAME source-symbol}.
              Operations not in the new list are removed (full replacement).
            """
            if len(args) == 0:
                return make_list(*[entry.to_map() for entry in sm.registry.entries.values()])

            if len(args) != 1:
                raise TypeError("SELF-DISPATCH takes 0 or 1 arg (dispatch table)")

            table = args[0]
            if not isinstance(table, Cell):
                raise TypeError("SELF-DISPATCH arg must be a list of {NAME SOURCE} pairs")

            # Parse the new dispatch table
            new_ops = {}
            cur = table
            while isinstance(cur, Cell):
                pair = cur.head
                if not isinstance(pair, Cell):
                    raise TypeError("Each dispatch entry must be {NAME SOURCE}")
                items = pair.to_list()
                if len(items) < 2:
                    raise TypeError("Each dispatch entry must be {NAME SOURCE}")
                name = repr(items[0]).upper()
                source = repr(items[1])
                new_ops[name] = source
                cur = cur.tail

            # Remove ops not in the new table
            old_names = set(sm.registry.entries.keys())
            for removed in old_names - set(new_ops.keys()):
                entry = sm.registry.entries.pop(removed)
                # Remove from meta-env by shadowing with NIL
                sm.registry.meta.env = sm.registry.meta.env.bind(removed, NIL)

            # Register/update each op
            for name, source in new_ops.items():
                if name in sm.registry.entries and sm.registry.entries[name].source_path:
                    # Update existing file-based op
                    entry = sm.registry.entries[name]
                    with open(entry.source_path, 'w') as f:
                        f.write(source + '\n')
                    sm.registry.load(name)
                else:
                    # Register as inline op
                    sm.registry.register_inline(name, source)

            return Atom(len(new_ops))

        builtins = {
            'SELF-REWRITE': self_rewrite,
            'SELF-INSPECT': self_inspect,
            'SELF-FORK': self_fork,
            'SELF-DISPATCH': self_dispatch,
        }

        for name, fn in builtins.items():
            sm.registry.meta.env = sm.registry.meta.env.bind(name, Builtin(name, fn))
