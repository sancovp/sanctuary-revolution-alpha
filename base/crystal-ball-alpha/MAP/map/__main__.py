"""MAP CLI — non-interactive shell tool for AI.

Compiler (enrich/instance loop):
    map define <name> <part1> <part2> ...  — define a task as a sequence of parts
    map enrich <name> <part1> <part2> ...  — break a name into sub-parts
    map instance <name> '<content>'        — produce content for a name
    map next                               — show next item in queue
    map queue                              — show the full queue
    map tree                               — show the compilation tree
    map show <name>                        — show a node's definition/instance
    map stats                              — compilation progress
    map reset                              — clear compiler state

MAP language (Turing-complete Lisp):
    map eval '<expr>'        — evaluate expression in persistent env
    map run [FILE|FLOW]      — run a .map file, named flow, or piped expression
    map save <name> '<expr>' — save a named attention flow
    map list                 — show all stored attention flows
    map inspect <name>       — show a flow's structure
    map compose <f1> <f2>    — combine flows into pipeline
    map modify <name> '<e>'  — replace a flow's source
    map delete <name>        — delete a stored flow
    map meta '<expr>'        — eval through meta-circular evaluator
    map super '<expr>'       — eval in super layer (registry access)
    map clear                — clear persistent MAP environment
    map help [topic]         — progressive disclosure help
"""

import sys
import os

from map.base.parser import parse, ParseError
from map.base.eval import map_eval, run, MAPError
from map.base.stdlib import make_stdlib
from map.base.types import NIL, Atom, Cell
from map.base.persistence import load_env, save_env, clear_env
from map.base.help import get_help, BREADCRUMB
from map.base.flows import (
    save_flow, list_flows, get_flow_source, inspect_flow,
    run_flow, delete_flow,
)
from map.base import compiler


def _format_result(val):
    """Format a MAP value for CLI output."""
    if val is NIL or val is None:
        return "NIL"
    return repr(val)


def cmd_run(args):
    """Run a .map file, named flow, or piped stdin expression."""
    env = load_env()

    if args:
        target = args[0]
        # Check if it's a stored flow name first
        flow_source = get_flow_source(target)
        if flow_source is not None:
            source = flow_source
        elif os.path.exists(target):
            # It's a file path
            with open(target) as f:
                source = f.read()
        else:
            print(f"Error: '{target}' is not a stored flow or existing file", file=sys.stderr)
            return 1
    elif not sys.stdin.isatty():
        # Piped input
        source = sys.stdin.read()
    else:
        print("Error: run needs a file/flow argument or piped input", file=sys.stderr)
        print("Usage: echo '{+ 1 2}' | python3 -m map run", file=sys.stderr)
        return 1

    source = source.strip()
    if not source:
        return 0

    try:
        result, env = run(source, env)
        save_env(env)
        if result is not NIL:
            print(_format_result(result))
        return 0
    except (MAPError, ParseError, NameError, TypeError, ZeroDivisionError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_eval(args):
    """Evaluate an expression in the persistent environment."""
    if args:
        source = ' '.join(args)
    elif not sys.stdin.isatty():
        source = sys.stdin.read().strip()
    else:
        print("Error: eval needs an expression argument or piped input", file=sys.stderr)
        print("Usage: python3 -m map eval '{+ 1 2}'", file=sys.stderr)
        return 1

    if not source:
        return 0

    env = load_env()

    try:
        result, env = run(source, env)
        save_env(env)
        if result is not NIL:
            print(_format_result(result))
        return 0
    except (MAPError, ParseError, NameError, TypeError, ZeroDivisionError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_meta(args):
    """Evaluate through the meta-circular evaluator."""
    if not args:
        print("Error: meta needs an expression argument", file=sys.stderr)
        return 1

    source = ' '.join(args)

    try:
        from map.meta.meta_interp import boot_meta
        meta = boot_meta()
        result = meta.eval_in_meta(source)
        if result is not NIL:
            print(_format_result(result))
        return 0
    except (MAPError, ParseError, NameError, TypeError, ZeroDivisionError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}", file=sys.stderr)
        return 1


def cmd_super(args):
    """Evaluate in the super layer with registry access."""
    if not args:
        print("Error: super needs an expression argument", file=sys.stderr)
        return 1

    source = ' '.join(args)

    try:
        from map.meta.meta_interp import boot_meta
        from map.super.registry import Registry
        meta = boot_meta()
        ops_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'super', 'ops')
        registry = Registry(meta, ops_dir)
        registry.load_all()

        exprs = parse(source)
        result = NIL
        for expr in exprs:
            result = map_eval(expr, meta.env)
        if result is not NIL:
            print(_format_result(result))
        return 0
    except (MAPError, ParseError, NameError, TypeError, ZeroDivisionError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}", file=sys.stderr)
        return 1


def cmd_save(args):
    """Save a named attention flow."""
    if len(args) < 2:
        print("Error: save needs a name and expression", file=sys.stderr)
        print("Usage: python3 -m map save <name> '<expression>'", file=sys.stderr)
        return 1

    name = args[0]
    source = ' '.join(args[1:])

    try:
        save_flow(name, source)
        print(f"Flow '{name}' saved.")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_list(args):
    """List all stored attention flows."""
    flows = list_flows()
    if not flows:
        print("No stored attention flows.")
        return 0

    for name, desc in flows:
        if desc:
            print(f"  {name} -- {desc}")
        else:
            print(f"  {name}")
    return 0


def cmd_inspect(args):
    """Inspect an attention flow's structure."""
    if not args:
        print("Error: inspect needs a flow name", file=sys.stderr)
        return 1

    name = args[0]
    info = inspect_flow(name)
    if info is None:
        print(f"Flow '{name}' not found.", file=sys.stderr)
        return 1

    print(f"Flow: {info['name']}")
    if info['description']:
        print(f"Description: {info['description']}")
    if info['created']:
        print(f"Created: {info['created']}")
    print(f"Source:\n  {info['source']}")
    if info['symbols']:
        print(f"Symbols: {', '.join(info['symbols'])}")
    if info['dependencies']:
        print(f"Dependencies: {', '.join(info['dependencies'])}")
    return 0


def cmd_compose(args):
    """Compose attention flows into a pipeline."""
    if len(args) < 2:
        print("Error: compose needs at least 2 flow names", file=sys.stderr)
        return 1

    # Verify all flows exist
    sources = []
    for name in args:
        source = get_flow_source(name)
        if source is None:
            print(f"Error: flow '{name}' not found", file=sys.stderr)
            return 1
        sources.append(source)

    # Create a composed flow: evaluate each in sequence
    composed = '\n'.join(sources)
    composed_name = '-'.join(args)

    try:
        save_flow(composed_name, composed,
                  description=f"Composed from: {', '.join(args)}")
        print(f"Flow '{composed_name}' saved (composed from {', '.join(args)}).")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_modify(args):
    """Modify (replace) a stored flow's source."""
    if len(args) < 2:
        print("Error: modify needs a flow name and new expression", file=sys.stderr)
        print("Usage: python3 -m map modify <name> '<expression>'", file=sys.stderr)
        return 1

    name = args[0]
    # Verify flow exists
    existing = get_flow_source(name)
    if existing is None:
        print(f"Error: flow '{name}' not found", file=sys.stderr)
        return 1

    new_source = ' '.join(args[1:])

    try:
        save_flow(name, new_source)
        print(f"Flow '{name}' modified.")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_delete(args):
    """Delete a named attention flow."""
    if not args:
        print("Error: delete needs a flow name", file=sys.stderr)
        return 1

    name = args[0]
    if delete_flow(name):
        print(f"Flow '{name}' deleted.")
        return 0
    else:
        print(f"Flow '{name}' not found.", file=sys.stderr)
        return 1


def cmd_flow_run(args):
    """Run a named attention flow."""
    if not args:
        print("Error: needs a flow name", file=sys.stderr)
        return 1

    name = args[0]
    env = load_env()

    try:
        result, env = run_flow(name, env)
        save_env(env)
        if result is not NIL:
            print(_format_result(result))
        return 0
    except (MAPError, ParseError, NameError, TypeError, ZeroDivisionError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_clear(args):
    """Clear persistent environment state."""
    clear_env()
    print("Environment cleared.")
    return 0


def cmd_help(args):
    """Progressive disclosure help system."""
    topic = args[0] if args else None
    text, code = get_help(topic)
    print(text)
    return code


def cmd_define(args):
    """Define a task as a sequence of named parts."""
    if len(args) < 2:
        print("Usage: map define <name> <part1> <part2> ...", file=sys.stderr)
        return 1
    name, child_paths = compiler.define(args[0], args[1:])
    print(f"Defined {name} -> {', '.join(child_paths)}")
    print(f"Queue: {len(compiler.queue())} items")
    return 0


def cmd_enrich(args):
    """Enrich a name by breaking it into sub-parts."""
    if len(args) < 2:
        print("Usage: map enrich <name> <part1> <part2> ...", file=sys.stderr)
        return 1
    name, child_paths, was_ratcheted = compiler.enrich(args[0], args[1:])
    if was_ratcheted:
        print(f"RATCHET: {name} was already instanced. Sub-parts added to END of queue.")
    print(f"Enriched {name} -> {', '.join(child_paths)}")
    print(f"Queue: {len(compiler.queue())} items")
    return 0


def cmd_instance(args):
    """Instance a name — produce its content."""
    if len(args) < 2:
        print("Usage: map instance <name> '<content>'", file=sys.stderr)
        return 1
    name = args[0]
    content = ' '.join(args[1:])
    result = compiler.instance(name, content)
    print(f"Instanced {result}")

    # Show next item automatically
    next_name, next_info = compiler.next_item()
    if next_name:
        print()
        print(compiler.format_next(next_name, next_info))
    else:
        print("\nQueue empty. Compilation complete.")
        s = compiler.stats()
        print(f"  {s['instanced']}/{s['total']} nodes instanced")
    return 0


def cmd_next(args):
    """Show next item in the compilation queue."""
    name, info = compiler.next_item()
    print(compiler.format_next(name, info))
    return 0


def cmd_queue(args):
    """Show the full compilation queue."""
    q = compiler.queue()
    if not q:
        print("Queue empty.")
        return 0
    for i, name in enumerate(q):
        node = compiler.show(name)
        status = node['status'] if node else 'unknown'
        marker = '*' if i == 0 else ' '
        print(f"  {marker} {i+1}. [{status}] {name}")
    return 0


def cmd_tree(args):
    """Show the compilation tree."""
    tree = compiler.show()
    print(compiler.format_tree(tree))
    return 0


def cmd_show(args):
    """Show a node's definition or instance."""
    if not args:
        # No args = show tree
        return cmd_tree(args)
    name = args[0]
    node = compiler.show(name)
    if not node:
        print(f"Not found: {name}", file=sys.stderr)
        return 1
    print(f"Name: {node['name']}")
    print(f"Status: {node['status']}")
    if node['parent']:
        print(f"Parent: {node['parent']}")
    if node['parts']:
        print(f"Parts: {', '.join(node['parts'])}")
    if node['content']:
        print(f"Content:\n{node['content']}")
    return 0


def cmd_stats(args):
    """Show compilation progress."""
    s = compiler.stats()
    if not s['root']:
        print("No compilation in progress.")
        return 0
    print(f"Root: {s['root']}")
    print(f"Total nodes: {s['total']}")
    print(f"  Instanced: {s['instanced']}")
    print(f"  Enriched:  {s['defined']}")
    print(f"  Pending:   {s['undefined']}")
    print(f"Queue: {s['queue_length']} items remaining")
    return 0


def cmd_reset(args):
    """Clear compiler state."""
    compiler.clear()
    print("Compiler state cleared.")
    return 0


COMMANDS = {
    # Compiler (enrich/instance loop)
    'define': cmd_define,
    'enrich': cmd_enrich,
    'instance': cmd_instance,
    'next': cmd_next,
    'queue': cmd_queue,
    'tree': cmd_tree,
    'show': cmd_show,
    'stats': cmd_stats,
    'reset': cmd_reset,
    # MAP language
    'run': cmd_run,
    'eval': cmd_eval,
    'save': cmd_save,
    'list': cmd_list,
    'inspect': cmd_inspect,
    'compose': cmd_compose,
    'modify': cmd_modify,
    'flow-run': cmd_flow_run,
    'delete': cmd_delete,
    'meta': cmd_meta,
    'super': cmd_super,
    'clear': cmd_clear,
    'help': cmd_help,
}


COMPILER_BREADCRUMB = """MAP — attention programming shell + compiler.

Compiler:  define | enrich | instance | next | queue | tree | show | stats | reset
Language:  eval | run | save | list | inspect | compose | meta | super | help

Start: map define <task> <part1> <part2> ...
Then:  map next"""


def main():
    args = sys.argv[1:]

    if not args:
        print(COMPILER_BREADCRUMB)
        return 0

    cmd = args[0].lower()
    cmd_args = args[1:]

    if cmd in COMMANDS:
        return COMMANDS[cmd](cmd_args)
    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        print(COMPILER_BREADCRUMB, file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main() or 0)
