"""Operation Registry — hot-reloadable metaprogramming operations.

Each operation is a named MAP program that:
  1. Lives in the ops/ directory as a .map file
  2. Gets loaded into the meta-interpreter's environment
  3. Can be invoked, reloaded, or replaced at runtime
  4. Can register NEW operations (self-extending)

The registry itself is exposed as a MAP data structure,
so programs running on the meta-interpreter can inspect and
modify it. This is the homoiconic payoff.
"""

import os
import time
import hashlib
import json
import logging
from pathlib import Path

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base.types import Atom, Cell, NIL, Builtin, MAPObj, make_list
from base.env import Env

logger = logging.getLogger(__name__)


class OpEntry:
    """A registered operation."""
    __slots__ = ('name', 'source_path', 'source_hash', 'loaded_at', 'map_val', 'invocations')

    def __init__(self, name, source_path=None):
        self.name = name
        self.source_path = source_path
        self.source_hash = None
        self.loaded_at = None
        self.map_val = NIL
        self.invocations = 0

    def is_stale(self):
        """Check if disk source has changed since last load."""
        if self.source_path is None:
            return False
        if not os.path.exists(self.source_path):
            return True
        try:
            with open(self.source_path) as f:
                current = hashlib.md5(f.read().encode()).hexdigest()
            return current != self.source_hash
        except (IOError, OSError) as e:
            logger.warning(f"Failed to check staleness of {self.source_path}: {e}")
            return True  # Treat as stale if we can't read

    def to_map(self):
        """Convert entry to MAP data (homoiconic registry)."""
        return make_list(
            Atom(self.name),
            Atom(':PATH'), Atom(str(self.source_path)) if self.source_path else NIL,
            Atom(':HASH'), Atom(self.source_hash) if self.source_hash else NIL,
            Atom(':INVOCATIONS'), Atom(self.invocations),
            Atom(':STALE'), Atom(1) if self.is_stale() else NIL
        )


class Registry:
    """The operation registry — hot, self-modifying, inspectable from Map."""

    def __init__(self, meta_interp, ops_dir=None, registry_file=None):
        self.meta = meta_interp
        self.ops_dir = ops_dir or os.path.join(os.path.dirname(__file__), 'ops')
        self.registry_file = registry_file or os.path.join(os.path.dirname(__file__), 'registry.json')
        self.entries = {}  # name -> OpEntry
        self._install_builtins()

    def _install_builtins(self):
        """Add registry control operations to the meta-interpreter's env."""
        env = self.meta.env
        registry = self

        def reg_list(args):
            """List all registered operations."""
            items = [entry.to_map() for entry in registry.entries.values()]
            result = NIL
            for item in reversed(items):
                result = Cell(item, result)
            return result

        def reg_load(args):
            """Load/reload an operation by name."""
            if len(args) != 1:
                raise TypeError("REG-LOAD needs 1 arg (name)")
            name = repr(args[0])
            return Atom(1) if registry.load(name) else NIL

        def reg_reload_all(args):
            """Reload all stale operations."""
            count = registry.reload_stale()
            return Atom(count)

        def reg_invoke(args):
            """Invoke an operation by name with arguments."""
            if len(args) < 1:
                raise TypeError("REG-INVOKE needs at least 1 arg (name)")
            name = repr(args[0])
            op_args = args[1:]
            return registry.invoke(name, op_args)

        def reg_register(args):
            """Register a new operation from MAP source string (as symbol)."""
            if len(args) != 2:
                raise TypeError("REG-REGISTER needs name and source-symbol")
            name = repr(args[0])
            source = repr(args[1])
            return Atom(1) if registry.register_inline(name, source) else NIL

        def reg_define_op(args):
            """Define a new operation as a file in ops/ dir."""
            if len(args) != 2:
                raise TypeError("REG-DEFINE-OP needs name and source")
            name = repr(args[0])
            source = repr(args[1])
            return Atom(1) if registry.define_op(name, source) else NIL

        def reg_stale(args):
            """List operations with changed source files."""
            stale = [Atom(name) for name, entry in registry.entries.items() if entry.is_stale()]
            return make_list(*stale) if stale else NIL

        def reg_save(args):
            """Save registry to disk."""
            return Atom(1) if registry.save() else NIL

        def reg_restore(args):
            """Restore registry from disk."""
            return Atom(1) if registry.restore() else NIL

        builtins = {
            'REG-LIST': reg_list,
            'REG-LOAD': reg_load,
            'REG-RELOAD-ALL': reg_reload_all,
            'REG-INVOKE': reg_invoke,
            'REG-REGISTER': reg_register,
            'REG-DEFINE-OP': reg_define_op,
            'REG-STALE': reg_stale,
            'REG-SAVE': reg_save,
            'REG-RESTORE': reg_restore,
        }

        for name, fn in builtins.items():
            self.meta.env = self.meta.env.bind(name, Builtin(name, fn))

    def scan(self):
        """Scan ops/ directory and register all .map files."""
        if not os.path.exists(self.ops_dir):
            os.makedirs(self.ops_dir, exist_ok=True)
            return 0

        count = 0
        try:
            for fname in os.listdir(self.ops_dir):
                if fname.endswith('.map'):
                    name = fname[:-4].upper()
                    if name not in self.entries:
                        self.entries[name] = OpEntry(name, os.path.join(self.ops_dir, fname))
                    count += 1
        except (IOError, OSError) as e:
            logger.warning(f"Failed to scan ops directory {self.ops_dir}: {e}")
        return count

    def load(self, name):
        """Load a single operation by name."""
        name = name.upper()
        if name not in self.entries:
            # Try to find on disk
            path = os.path.join(self.ops_dir, f'{name.lower()}.map')
            if os.path.exists(path):
                self.entries[name] = OpEntry(name, path)
            else:
                return False

        entry = self.entries[name]
        if entry.source_path and os.path.exists(entry.source_path):
            try:
                with open(entry.source_path) as f:
                    source = f.read()
                entry.source_hash = hashlib.md5(source.encode()).hexdigest()
                entry.loaded_at = time.time()
                entry.map_val = self.meta.run(source)
                return True
            except (IOError, OSError, Exception) as e:
                logger.error(f"Failed to load operation {name} from {entry.source_path}: {e}")
                return False
        return False

    def load_all(self):
        """Load all registered operations."""
        self.scan()
        for name in list(self.entries.keys()):
            self.load(name)

    def reload_stale(self):
        """Reload only operations whose source has changed."""
        count = 0
        for name, entry in self.entries.items():
            if entry.is_stale():
                self.load(name)
                count += 1
        return count

    def invoke(self, name, args):
        """Invoke a registered operation."""
        name = name.upper()
        if name not in self.entries:
            raise NameError(f"No operation: {name}")

        entry = self.entries[name]
        # Hot reload if stale
        if entry.is_stale():
            self.load(name)

        entry.invocations += 1

        # The operation should have defined a function with its name
        # in the meta-interpreter's env
        try:
            fn = self.meta.env.lookup(Atom(name))
            if callable(getattr(fn, 'fn', None)) or hasattr(fn, 'body'):
                from base.eval import map_eval, _apply
                return _apply(fn, args, self.meta.env)
            return fn
        except NameError:
            return entry.map_val

    def register_inline(self, name, source):
        """Register an operation from a MAP source string (no file)."""
        name = name.upper()
        entry = OpEntry(name)
        entry.loaded_at = time.time()
        entry.source_hash = hashlib.md5(source.encode()).hexdigest()
        entry.map_val = self.meta.run(source)
        self.entries[name] = entry
        return True

    def define_op(self, name, source):
        """Write a new .map file to ops/ and register it."""
        name_lower = name.lower().replace(' ', '-')
        path = os.path.join(self.ops_dir, f'{name_lower}.map')
        os.makedirs(self.ops_dir, exist_ok=True)
        try:
            with open(path, 'w') as f:
                f.write(f'# Operation: {name}\n')
                f.write(f'# Auto-generated at {time.strftime("%Y-%m-%d %H:%M:%S")}\n\n')
                f.write(source)
                f.write('\n')
        except (IOError, OSError) as e:
            logger.error(f"Failed to write operation file {path}: {e}")
            return False
        entry = OpEntry(name.upper(), path)
        self.entries[name.upper()] = entry
        return self.load(name.upper())

    def save(self):
        """Save registry state to disk for persistence."""
        data = {
            'entries': {
                name: {
                    'name': entry.name,
                    'source_path': entry.source_path,
                    'source_hash': entry.source_hash,
                    'loaded_at': entry.loaded_at,
                    'invocations': entry.invocations,
                }
                for name, entry in self.entries.items()
            }
        }
        try:
            with open(self.registry_file, 'w') as f:
                json.dump(data, f, indent=2)
            return True
        except (IOError, OSError, TypeError) as e:
            logger.error(f"Failed to save registry to {self.registry_file}: {e}")
            return False

    def restore(self):
        """Restore registry state from disk."""
        if not os.path.exists(self.registry_file):
            logger.info(f"Registry file {self.registry_file} does not exist")
            return False
        
        try:
            with open(self.registry_file, 'r') as f:
                data = json.load(f)
        except (IOError, OSError, json.JSONDecodeError) as e:
            logger.warning(f"Failed to load registry from {self.registry_file}: {e}")
            return False
        
        # Validate loaded data
        if not isinstance(data, dict) or 'entries' not in data:
            logger.warning(f"Invalid registry data format in {self.registry_file}")
            return False
        
        if not isinstance(data['entries'], dict):
            logger.warning(f"Invalid entries format in {self.registry_file}")
            return False
        
        # Restore entries
        count = 0
        for name, entry_data in data['entries'].items():
            if not isinstance(entry_data, dict):
                continue
            entry = OpEntry(
                entry_data.get('name', name),
                entry_data.get('source_path')
            )
            entry.source_hash = entry_data.get('source_hash')
            entry.loaded_at = entry_data.get('loaded_at')
            entry.invocations = entry_data.get('invocations', 0)
            self.entries[name] = entry
            count += 1
        
        logger.info(f"Restored {count} registry entries from {self.registry_file}")
        return True
