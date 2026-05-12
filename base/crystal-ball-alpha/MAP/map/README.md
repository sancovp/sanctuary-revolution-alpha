# introduction_to_cs

A three-layer homoiconic Lisp system called **Map**, built as a catastrophe engineering test bed.

## Why This Exists

This project implements well-known CS patterns (Lisp, meta-circular evaluation, hot-reloadable metaprogramming) in deliberately idiosyncratic ways. The code is recognizable but weird enough that you can't pattern-match it from training data — you have to actually read it.

It's designed as a test fixture for AI agent experiments: give an agent this codebase with wrong/incomplete notes and see if it catches the problems.

## Architecture

```
introduction_to_cs/
├── base/           # Map — the custom Lisp
│   ├── types.py    # Homoiconic type system: Cell, Atom, NIL, Morph
│   ├── env.py      # Environments as cons-cell chains (NOT dicts)
│   ├── parser.py   # Tokenizer + recursive descent for {brace} syntax
│   ├── stdlib.py   # Built-in functions (all arithmetic is Fraction)
│   └── eval.py     # Evaluator with TCO, special forms, REPL
├── meta/           # Meta-circular evaluator — Map interpreting Map
│   ├── meta_interp.py      # Python-side meta-interpreter with hooks
│   ├── meta_circular.map # The evaluator written IN Map
│   └── bootstrap.py        # (planned) Loader for meta layer
└── super/          # Hot-reloadable metaprogramming runtime
    ├── registry.py  # Operation registry with hot-reload
    ├── hot.py       # File watcher + self-modification interface
    ├── main.py      # Super-REPL entry point
    └── ops/         # Pluggable operations (.map files)
        ├── map.map      # MAP, FILTER, REDUCE
        ├── compose.map  # COMPOSE, PIPE, IDENTITY, CONST, FLIP
        └── reify.map    # REIFY, MAKE-COUNTER, MAKE-MEMO
```

## Map Syntax

```
{+ 1 2}                          # => 3 (braces, not parens)
{morph | x | {* x 2}}            # lambda with pipe-delimited sections
{def fact | n |                   # named function (recursive)
  {when | {= n 0} | 1 |          # conditional with pipe sections
    {* n {fact {- n 1}}}}}
~{+ 1 2}                         # quote => {+ 1 2} as data
@~{+ 1 2}                        # eval quoted => 3
{env}                             # dump environment as Map data
```

**Idiosyncrasies:**
- `{}` not `()` for s-expressions
- `|` pipe-delimited sections: `{morph | params | body}`
- `~` quote, `@` unquote/eval
- All numbers are `Fraction` internally (no floats)
- No strings — only symbols (UPPERCASE) and lists
- Environments are cons-cell linked lists, not hash maps
- Special forms: `bind`, `morph`, `when`, `seq`, `loop`, `def`, `set!`, `macro`
- `head`/`tail` not `car`/`cdr`

## Running

```bash
# Base REPL
cd introduction_to_cs
python3 -c "from base.eval import repl; repl()"

# Super REPL (all three layers)
python3 super/main.py

# Quick test
python3 -c "from base.eval import run; print(run('{+ 1 {* 2 3}}')[0])"
```

## Layers

### base/ — The Interpreter

Standard Lisp semantics with non-standard syntax. Everything is a `Cell` (cons) or `Atom`. Code and data are the same structure — that's homoiconicity. You can quote code with `~`, manipulate it as a list, then `@`-eval it.

### meta/ — The Meta-Circular Evaluator

A Map program (`meta_circular.map`) that implements a Map evaluator. Runs on the base interpreter. The meta-interpreter (`meta_interp.py`) wraps base eval with hooks for tracing and introspection, then boots the `.map` evaluator on top.

Two-level interpretation: `base eval → meta eval → your program`. Same results, twice the introspection.

### super/ — The Metaprogramming Runtime

Operations are `.map` files in `ops/` that get hot-reloaded when they change on disk. The registry exposes itself as Map data. Programs can:
- `{reg-list}` — see all operations
- `{reg-define-op NAME SOURCE}` — create new operations at runtime
- `{self-rewrite OP NEW-SOURCE}` — rewrite an operation's source file
- `{self-inspect OP}` — read an operation's source code
- `{self-fork OP NEW-NAME}` — copy an operation under a new name

This is genuine self-modification: a running program can rewrite its own operations, and the hot-reload engine picks up the changes.
