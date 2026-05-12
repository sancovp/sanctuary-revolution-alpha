"""MAP progressive disclosure help system.

4 levels:
  Level 0: Breadcrumb — one-line summary
  Level 1: Index — list of all commands
  Level 2: Instructions — detailed per-command help with examples
  Level 3+: Nested — special form docs, type docs, deep reference
"""

# Level 0: Breadcrumb
BREADCRUMB = (
    "MAP — attention programming shell + compiler.\n"
    "\n"
    "Compiler:  define | enrich | instance | next | queue | tree | show | stats | reset\n"
    "Language:  eval | run | save | list | inspect | compose | meta | super | help\n"
    "\n"
    "Start: map define <task> <part1> <part2> ...\n"
    "Then:  map next"
)

# Level 1: Command index
COMMAND_INDEX = {
    # Compiler
    'define':   'define a task as a sequence of named parts',
    'enrich':   'break a name into sub-parts (too complex to instance directly)',
    'instance': 'produce content for a name (clear enough to write)',
    'next':     'show next item in the compilation queue with context',
    'queue':    'show the full compilation queue',
    'tree':     'show the compilation tree (what is done, enriched, pending)',
    'show':     'show a specific node\'s definition or instance',
    'stats':    'compilation progress (nodes instanced/enriched/pending)',
    'reset':    'clear compiler state and start fresh',
    # Language
    'eval':     'evaluate a MAP expression in the persistent env',
    'run':      'execute a .map file, named flow, or piped expression',
    'save':     'store a named attention flow',
    'list':     'show all stored attention flows',
    'inspect':  "show an attention flow's structure and dependencies",
    'compose':  'combine flows into a pipeline',
    'modify':   'hot-modify a stored flow',
    'delete':   'delete a stored flow',
    'flow-run': 'run a named flow in the persistent env',
    'meta':     'meta-circular evaluator (MAP interpreting Map)',
    'super':    'metaprogramming layer (hot-reload, self-modify, registry)',
    'clear':    'clear persistent MAP environment',
    'help':     'this help system (progressive disclosure)',
}

# Level 2: Per-command detailed help
COMMAND_HELP = {
    # ── Compiler commands ──
    'define': (
        "define — Define a task as a sequence of named parts.\n"
        "\n"
        "Usage: map define <name> <part1> <part2> ...\n"
        "\n"
        "Creates the root of a compilation tree. Each part becomes a child\n"
        "node (NAME.PART1, NAME.PART2, ...) and enters the queue.\n"
        "\n"
        "Example:\n"
        "  map define ESSAY INTRO BODY-1 BODY-2 BODY-3 CONCLUSION\n"
        "\n"
        "This creates ESSAY with children ESSAY.INTRO, ESSAY.BODY_1, etc.\n"
        "Use 'map next' to start working through the queue."
    ),
    'enrich': (
        "enrich — Break a name into sub-parts.\n"
        "\n"
        "Usage: map enrich <name> <part1> <part2> ...\n"
        "\n"
        "When a name is too complex to instance directly, enrich it.\n"
        "The sub-parts replace the name in the queue.\n"
        "\n"
        "Example:\n"
        "  map enrich ESSAY.INTRO HOOK THESIS ROADMAP\n"
        "\n"
        "This creates ESSAY.INTRO.HOOK, ESSAY.INTRO.THESIS, ESSAY.INTRO.ROADMAP\n"
        "and queues them for resolution.\n"
        "\n"
        "Enrichment IS programming — you're writing a program that says\n"
        "'to produce INTRO, produce these three things in order.'"
    ),
    'instance': (
        "instance — Produce content for a name.\n"
        "\n"
        "Usage: map instance <name> '<content>'\n"
        "\n"
        "When a name is clear enough to produce directly, instance it.\n"
        "The content is stored and the name is removed from the queue.\n"
        "\n"
        "Example:\n"
        "  map instance ESSAY.INTRO.HOOK 'The morning the water turned brown...'\n"
        "\n"
        "After instancing, the next queue item is automatically shown.\n"
        "Already-completed siblings are included as context."
    ),
    'next': (
        "next — Show the next item in the compilation queue.\n"
        "\n"
        "Usage: map next\n"
        "\n"
        "Shows the next name to resolve, with context:\n"
        "  - Its parent (what it's part of)\n"
        "  - Its siblings (what's alongside it)\n"
        "  - Already-completed siblings (for consistency)\n"
        "\n"
        "Your decision: enrich (break into sub-parts) or instance (produce content)?\n"
        "\n"
        "This is the core compilation loop. The queue serves you one item\n"
        "at a time. You decide how to resolve it. The codebase grows."
    ),
    'queue': (
        "queue — Show the full compilation queue.\n"
        "\n"
        "Usage: map queue\n"
        "\n"
        "Lists all pending names in order, with their status.\n"
        "The first item (marked *) is what 'next' will show you."
    ),
    'tree': (
        "tree — Show the compilation tree.\n"
        "\n"
        "Usage: map tree\n"
        "\n"
        "Displays the full tree structure:\n"
        "  [done]     — instanced, has content\n"
        "  [enriched] — broken into sub-parts\n"
        "  [pending]  — needs to be enriched or instanced"
    ),
    'show': (
        "show — Show a specific node or the full tree.\n"
        "\n"
        "Usage:\n"
        "  map show              # show full tree\n"
        "  map show <name>       # show specific node\n"
        "\n"
        "For a specific node, shows: status, parent, parts, content.\n"
        "Names use dot-paths: ESSAY.INTRO.HOOK"
    ),
    'stats': (
        "stats — Compilation progress.\n"
        "\n"
        "Usage: map stats\n"
        "\n"
        "Shows total nodes, how many are instanced/enriched/pending,\n"
        "and how many items remain in the queue."
    ),
    'reset': (
        "reset — Clear all compiler state.\n"
        "\n"
        "Usage: map reset\n"
        "\n"
        "Removes all nodes, queue, and root. Start fresh with 'define'.\n"
        "Does NOT clear the MAP language environment (use 'clear' for that)."
    ),
    # ── Language commands ──
    'run': (
        "run — Execute a .map file, named flow, or piped expression.\n"
        "\n"
        "Usage:\n"
        "  echo '{+ 1 2}' | map run\n"
        "  map run script.map\n"
        "  map run my-flow-name\n"
        "\n"
        "Checks stored flows first, then files. Evaluates all expressions\n"
        "in order, prints the last non-NIL result.\n"
        "Environment persists across invocations."
    ),
    'eval': (
        "eval — Evaluate a MAP expression in the persistent environment.\n"
        "\n"
        "Usage: map eval '<expression>'\n"
        "\n"
        "MAP uses {} for s-expressions, | for pipe sections, ~ for quote, @ for eval.\n"
        "Examples:\n"
        "  eval '{+ 1 2}'                     # arithmetic\n"
        "  eval '{bind x 42}'                  # bind a value (persists)\n"
        "  eval '{def double | x | {* x 2}}'   # define a function (persists)\n"
        "  eval '{double 21}'                  # => 42\n"
        "\n"
        "Special forms: bind, morph, when, seq, loop, def, set!, macro, quote, eval, apply, load\n"
        "Type: map help <form> for details on any special form."
    ),
    'list': (
        "list — Show all stored attention flows.\n"
        "\n"
        "Usage: map list\n"
        "\n"
        "Lists named flows saved with 'save'. Flows are stored as .map files."
    ),
    'inspect': (
        "inspect — Show an attention flow's structure and dependencies.\n"
        "\n"
        "Usage: map inspect <name>\n"
        "\n"
        "Shows the source, symbols used, and dependencies of a named flow."
    ),
    'compose': (
        "compose — Combine attention flows into a pipeline.\n"
        "\n"
        "Usage: map compose <flow1> <flow2> ...\n"
        "\n"
        "Creates a new flow that evaluates each named flow in sequence."
    ),
    'meta': (
        "meta — Evaluate through the meta-circular evaluator.\n"
        "\n"
        "Usage: map meta '<expression>'\n"
        "\n"
        "Runs the expression through Map's meta-circular evaluator —\n"
        "MAP interpreting Map. This is the 2nd Futamura level."
    ),
    'super': (
        "super — Evaluate in the super layer with full registry access.\n"
        "\n"
        "Usage: map super '<expression>'\n"
        "\n"
        "Has access to all registered operations, hot-reload engine,\n"
        "and self-modification capabilities. 3rd Futamura level."
    ),
    'save': (
        "save — Store a named attention flow.\n"
        "\n"
        "Usage: map save <name> '<expression>'\n"
        "\n"
        "Saves the expression as a named flow. Source is validated before saving.\n"
        "\n"
        "Example:\n"
        "  map save my-checker '{when | {catastrophe? ctx} | {rollup ctx} | {proceed ctx}}'"
    ),
    'modify': (
        "modify — Hot-modify a stored attention flow.\n"
        "\n"
        "Usage: map modify <name> '<new-expression>'\n"
        "\n"
        "Replaces the source of an existing flow."
    ),
    'delete': (
        "delete — Delete a stored attention flow.\n"
        "\n"
        "Usage: map delete <name>"
    ),
    'flow-run': (
        "flow-run — Run a named flow in the persistent environment.\n"
        "\n"
        "Usage: map flow-run <name>"
    ),
    'clear': (
        "clear — Clear persistent MAP environment state.\n"
        "\n"
        "Usage: map clear\n"
        "\n"
        "Removes all persisted bindings. Does NOT clear compiler state\n"
        "(use 'reset' for that)."
    ),
    'help': (
        "help — Progressive disclosure help system.\n"
        "\n"
        "Usage:\n"
        "  map help              # Level 0: breadcrumb + command list\n"
        "  map help commands     # Level 1: index of all commands\n"
        "  map help <command>    # Level 2: detailed per-command help\n"
        "  map help <form>       # Level 3: MAP special form reference\n"
        "  map help compiler     # How the enrich/instance compiler works\n"
        "  map help language     # MAP language overview\n"
        "\n"
        "Each level reveals one more layer. Drill as deep as you need."
    ),
    # ── Topic overviews ──
    'compiler': (
        "The MAP Compiler — queue-driven enrich/instance loop.\n"
        "\n"
        "You have two moves:\n"
        "\n"
        "  ENRICH  — A name is too complex to produce directly.\n"
        "            Break it into named sub-parts.\n"
        "            The sub-parts enter the queue.\n"
        "\n"
        "  INSTANCE — A name is clear enough to produce.\n"
        "             Write the actual content.\n"
        "             The name is done.\n"
        "\n"
        "The queue serves you one name at a time (map next).\n"
        "For each name, you decide: enrich or instance?\n"
        "When you enrich, sub-parts replace the name in the queue.\n"
        "When you instance, the name is done and you move on.\n"
        "\n"
        "Everything you define persists as a tree of names.\n"
        "Names are keys. Definitions and instances are values.\n"
        "That's it — CRUD on rewrites with composition.\n"
        "\n"
        "The depth of enrichment is the depth of thought.\n"
        "Flat = fast. Deep = thorough. You choose.\n"
        "\n"
        "To mutate a definition, you must re-enrich or re-instance it.\n"
        "Mutation goes through the same compilation loop — through you.\n"
        "You rewrite yourself BY compiling through yourself.\n"
        "\n"
        "Workflow:\n"
        "  1. map define TASK PART-A PART-B PART-C\n"
        "  2. map next\n"
        "  3. map enrich TASK.PART_A SUB-1 SUB-2   (or)\n"
        "     map instance TASK.PART_A 'content'\n"
        "  4. repeat until queue is empty"
    ),
    'language': (
        "The MAP Language — Turing-complete homoiconic Lisp.\n"
        "\n"
        "Syntax:\n"
        "  {op args}               — apply op to args\n"
        "  {morph | params | body}  — lambda (closure)\n"
        "  {def name | params | body} — named function\n"
        "  {bind name value}        — bind a value\n"
        "  {when | cond | then | else} — conditional\n"
        "  {seq a b c}              — sequence\n"
        "  ~expr                    — quote (hold as data)\n"
        "  @expr                    — eval (go deeper)\n"
        "\n"
        "Types:\n"
        "  NIL       — nothing / false\n"
        "  42        — number (exact fraction internally)\n"
        "  SYMBOL    — uppercase name, resolved from environment\n"
        "  :KEYWORD  — self-evaluating tag\n"
        "  \"text\"    — string literal\n"
        "  {a b c}   — cell chain (list / code / data — same thing)\n"
        "\n"
        "Homoiconic: code and data share the same representation.\n"
        "  ~{+ 1 2}  is data.  @~{+ 1 2}  evaluates to 3.\n"
        "\n"
        "Layers:\n"
        "  eval  — base interpreter (Map)\n"
        "  meta  — MAP interpreting MAP (meta-circular evaluator)\n"
        "  super — metaprogramming (hot-reload, self-modify, registry)\n"
        "\n"
        "Special forms: bind, morph, when, seq, loop, def, set!, macro,\n"
        "               quote, eval, apply, load, match, env\n"
        "Type: map help <form> for details on any."
    ),
}

# Level 3: Special form documentation
FORM_HELP = {
    'bind': (
        "bind — Lock attention: bind a value in the environment.\n"
        "\n"
        "Syntax: {bind NAME expr}\n"
        "\n"
        "Evaluates expr and binds the result to NAME.\n"
        "The binding persists across invocations.\n"
        "\n"
        "Examples:\n"
        "  {bind x 42}              # bind x to 42\n"
        "  {bind data {list 1 2 3}} # bind data to a list"
    ),
    'morph': (
        "morph — Create a lambda (closure / attention transform).\n"
        "\n"
        "Syntax: {morph | params | body}\n"
        "\n"
        "  {morph | x y | {+ x y}}     # two params\n"
        "  {morph | | {print :HELLO}}   # no params (thunk)\n"
        "\n"
        "Captures its environment (closure).\n"
        "  {bind add-n {morph | n | {morph | x | {+ x n}}}}\n"
        "  {bind add-5 {add-n 5}}\n"
        "  {add-5 10}  # => 15"
    ),
    'when': (
        "when — Conditional: branch based on a condition.\n"
        "\n"
        "  {when | cond | then}          # one branch\n"
        "  {when | cond | then | else}   # two branches\n"
        "\n"
        "NIL and 0 are falsy, everything else is truthy."
    ),
    'seq': (
        "seq — Sequence: evaluate in order, return last.\n"
        "\n"
        "  {seq expr1 expr2 ... exprN}\n"
        "\n"
        "Tail-call optimized in last position."
    ),
    'loop': (
        "loop — Repeat while condition holds.\n"
        "\n"
        "  {loop | init | cond | step}\n"
        "\n"
        "  {bind i 0}\n"
        "  {loop | NIL | {< i 10} | {set! i {+ i 1}}}"
    ),
    'def': (
        "def — Named recursive function.\n"
        "\n"
        "  {def NAME | params | body}\n"
        "\n"
        "  {def factorial | n |\n"
        "    {when | {= n 0} | 1 | {* n {factorial {- n 1}}}}}"
    ),
    'set!': (
        "set! — Mutate an existing binding.\n"
        "\n"
        "  {set! NAME expr}\n"
        "\n"
        "Errors if NAME is not already bound."
    ),
    'macro': (
        "macro — Fexpr: args passed unevaluated.\n"
        "\n"
        "  {macro | params | body}\n"
        "\n"
        "Like morph, but args are NOT evaluated. Body runs in caller's env."
    ),
    'quote': (
        "quote — Hold as data, don't evaluate.\n"
        "\n"
        "  {quote expr}  or  ~expr\n"
        "\n"
        "  ~{+ 1 2}   # => {+ 1 2} (the list, not 3)\n"
        "  @~{+ 1 2}  # => 3"
    ),
    'apply': (
        "apply — Apply function to a list of arguments.\n"
        "\n"
        "  {apply fn args-list}\n"
        "  {apply + {list 1 2 3}}  # => 6"
    ),
    'load': (
        "load — Import a module's bindings.\n"
        "\n"
        "  {load \"path.map\"}\n"
        "\n"
        "Evaluates file in fresh env, returns bindings as alist.\n"
        '  {bind math {load "math.map"}}\n'
        "  {module-get math ~PI}"
    ),
    'match': (
        "match — Pattern dispatch.\n"
        "\n"
        "  {match expr | pattern1 | result1 | pattern2 | result2 | ...}\n"
        "  {match x | 0 | :ZERO | 1 | :ONE | _ | :OTHER}"
    ),
}


def get_help(topic=None):
    """Get help text for a topic. Returns (text, exit_code).

    topic=None -> Level 0 breadcrumb
    topic='commands' -> Level 1 index
    topic=<command> -> Level 2 command help
    topic=<form> -> Level 3 special form help
    """
    if topic is None:
        return BREADCRUMB, 0

    topic = topic.lower()

    if topic == 'commands':
        lines = ["Compiler:"]
        compiler_cmds = ['define', 'enrich', 'instance', 'next', 'queue', 'tree', 'show', 'stats', 'reset']
        lang_cmds = [k for k in COMMAND_INDEX if k not in compiler_cmds]
        max_name = max(len(n) for n in COMMAND_INDEX)
        for name in compiler_cmds:
            desc = COMMAND_INDEX[name]
            lines.append(f"  {name:<{max_name}} — {desc}")
        lines.append("")
        lines.append("Language:")
        for name in lang_cmds:
            desc = COMMAND_INDEX[name]
            lines.append(f"  {name:<{max_name}} — {desc}")
        return '\n'.join(lines), 0

    if topic in COMMAND_HELP:
        return COMMAND_HELP[topic], 0

    if topic in FORM_HELP:
        return FORM_HELP[topic], 0

    return f"No help for '{topic}'. Try: map help commands", 1
