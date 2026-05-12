# Vision: Map — AI-Native Attention Programming Shell

## What This Is

Map is a **non-interactive REPL** — a shell tool that AI uses (not humans). An AI invokes Map as a tool while working on other tasks, to:

- **Represent** attention flows as persistent programs
- **Modify** them at runtime
- **Compose** them into larger programs
- **Evolve** them through self-modification

The syntax is AI-native: symbols map to attention primitives that the model already understands. The system is persistent — programs survive across invocations. It progressively discloses itself.

## Non-Interactive REPL

This is NOT a human REPL with a `map>` prompt. It's a **shell command / tool** that AI calls:

```bash
# AI writes an attention flow
echo '{bind task-context {eval observations}} {when | {catastrophe? task-context} | {rollup task-context} | {proceed task-context}}' | python3 -m map run

# AI queries existing flows
python3 -m map list

# AI modifies a flow
python3 -m map eval '{set! task-context {merge task-context new-observations}}'

# AI composes flows
python3 -m map eval '{bind pipeline {compose rollup-flow validation-flow deployment-flow}}'
```

The AI calls this while doing other work — coding, reviewing, planning. The attention flows are the AI's scratchpad for HOW it's directing its own attention.

## Progressive Disclosure

The system reveals itself in layers. An AI encountering Map for the first time sees:

**Level 0: Breadcrumb / Signpost**
```
Map: attention programming shell. Commands: run, list, eval, inspect, compose.
```

**Level 1: Index of Options**
```
run     — execute a .map file or piped expression
list    — show all stored attention flows
eval    — evaluate an expression in the persistent env
inspect — show an attention flow's structure and dependencies
compose — combine flows into a pipeline
modify  — hot-modify a running flow
meta    — access meta-circular evaluator (interpret Map IN Map)
super   — metaprogramming: create new operations, self-modify
```

**Level 2: Instructions Per Option**
```
$ map help eval
eval — Evaluate a Map expression in the persistent environment.

Syntax: map eval '<expression>'

Map uses {} for s-expressions, | for pipe sections, ~ for quote, @ for eval.
Examples:
  map eval '{+ 1 2}'                    # arithmetic
  map eval '{bind x 42}'                # bind a value (persists)
  map eval '{def double | x | {* x 2}}' # define a function (persists)
  map eval '{double x}'                 # use both

Special forms: bind, morph, when, seq, loop, def, set!, macro, quote, eval, apply, load
Type: map help <form> for details on any special form.
```

**Level 3+: Nested Disclosure**
```
$ map help morph
morph — Create a lambda (anonymous function / attention transform).

Syntax: {morph | params | body}

The pipe | separates sections:
  {morph | x y | {+ x y}}     # two params
  {morph | | {print :HELLO}}   # no params (thunk)

Closures: morph captures its environment...
[continues with examples, edge cases, composition patterns]
```

Each level reveals more. The AI drills as deep as it needs and no deeper.

## Symbol Semantics (AI-Native)

These aren't arbitrary Lisp names. They map to what AI already does:

| Symbol | Attention Primitive | What the AI Does |
|--------|-------------------|-----------------|
| `BIND` | Lock attention | "Hold this in working memory" |
| `MORPH` | Transform | "Apply this transformation to focus" |
| `WHEN` | Conditional attention | "If this condition, attend to X else Y" |
| `SEQ` | Sequential focus | "Do these in order, carry context forward" |
| `LOOP` | Iterative attention | "Keep attending until condition changes" |
| `EVAL` | Recursive descent | "Go deeper into this representation" |
| `QUOTE` / `~` | Defer attention | "Don't evaluate yet, hold as data" |
| `LOAD` | Import context | "Bring this module's bindings into scope" |
| `MATCH` | Pattern dispatch | "Route attention based on structure" |

## Futamura Tower

```
base        — the interpreter (Map)
meta        — Map interpreting Map (meta-circular evaluator)
super       — metaprogramming on the meta-interpreter (hot, self-mod, registry)
superbase   — base of base: the type system as data the super layer can rewrite
supermeta   — meta of super: the registry interpreting itself
supersuper  — futamura projection OF futamura projections compiled in the REPL
```

Each level shields the one below. You can rewrite ops but not the evaluator. You can rewrite the meta-evaluator but not the base types. Safety through structural invariance.

The fixed point: a level that can generate itself. That's the meta-specialization generator — the system writing its own attention programs for writing attention programs.

## Current State vs Vision

**What exists (base, meta, super):**
- Full interpreter with AI-native syntax
- Meta-circular evaluator (Map interpreting Map)
- Hot-reloadable operation registry with self-modification
- 148 passing tests
- Module/import system with isolated eval contexts
- Pattern matching

**What's missing:**
1. **CLI shell interface** — `python3 -m map run/eval/list/inspect/compose` (currently only Python API)
2. **Persistent environment** — env survives across invocations (serialize/deserialize)
3. **Progressive disclosure help system** — the 4-level disclosure described above
4. **Attention flow storage** — named flows that persist and can be listed/inspected
5. **super/ ops that modify META-EVAL** — current ops only define base-level functions
6. **Compilation step** — Map program -> specialized evaluator (1st projection)
7. **Self-application** — compiler applied to itself (2nd projection = generator)
