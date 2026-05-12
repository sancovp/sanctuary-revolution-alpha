"""MAP — a homoiconic Lisp with idiosyncratic syntax.

Syntax:
  {op args...}        — s-expression (uses braces, not parens)
  {morph | x y | body} — lambda with pipe-delimited sections
  ~expr               — quote
  @expr               — eval/unquote
  #                   — line comment
  UPPERCASE           — atoms/symbols
  123, 3/4            — numbers (always Fraction internally)
  :keyword            — keyword atoms (self-evaluating)

Special forms: bind, morph, when, seq, loop, quote, eval, def
Built-ins: +, -, *, /, =, <, >, head, tail, cons, list, type?, nil?, print
"""

from .types import *
from .env import Env, Frame
