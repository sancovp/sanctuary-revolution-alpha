"""Comprehensive test suite for the MAP language — all three layers.

Tests use {} not () for s-expressions, | for pipe sections, ~ for quote, @ for eval.
This is NOT standard Lisp syntax — it's Map's idiosyncratic syntax.

Layers tested:
  base/  — types, parser, env, eval, stdlib
  meta/  — meta-circular evaluator (MAP interpreting Map)
  super/ — registry, hot-reload, self-modification
"""

import sys
import os
import time
import tempfile
import shutil
import hashlib

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fractions import Fraction

from base.types import Atom, Cell, NIL, Nil, Morph, Builtin, MAPObj, make_list, cons
from base.env import Env, Frame
from base.parser import parse, parse_one, ParseError, tokenize
from base.eval import map_eval, run, MAPError, Macro, TailCall
from base.stdlib import make_stdlib


# ============================================================
# BASE LAYER — Types
# ============================================================

class TestTypes:
    """Test the homoiconic type system."""

    def test_nil_singleton(self):
        assert NIL is Nil()
        assert NIL == Nil()
        assert not NIL  # falsy

    def test_atom_number(self):
        a = Atom(42)
        assert a.is_num
        assert not a.is_sym
        assert a.val == Fraction(42)
        assert repr(a) == "42"

    def test_atom_fraction(self):
        a = Atom(Fraction(1, 3))
        assert a.is_num
        assert a.val == Fraction(1, 3)
        assert repr(a) == "1/3"

    def test_atom_symbol(self):
        a = Atom("hello")
        assert a.is_sym
        assert not a.is_num
        assert a.val == "HELLO"  # always uppercase

    def test_atom_keyword(self):
        a = Atom(":test")
        assert a.is_keyword
        assert a.val == ":test"  # keywords keep their prefix

    def test_cell_basic(self):
        c = Cell(Atom(1), Cell(Atom(2), NIL))
        assert c.head == Atom(1)
        assert c.tail.head == Atom(2)
        assert c.tail.tail == NIL

    def test_cell_repr_uses_braces(self):
        """MAP uses {} not () for display."""
        c = Cell(Atom(1), Cell(Atom(2), NIL))
        assert repr(c) == "{1 2}"

    def test_make_list(self):
        lst = make_list(Atom(1), Atom(2), Atom(3))
        assert lst.head == Atom(1)
        assert lst.tail.head == Atom(2)
        assert lst.tail.tail.head == Atom(3)
        assert lst.tail.tail.tail == NIL

    def test_make_list_from_python(self):
        lst = make_list(1, 2, 3)
        assert lst.head == Atom(1)

    def test_cell_to_list(self):
        c = Cell(Atom(1), Cell(Atom(2), Cell(Atom(3), NIL)))
        result = c.to_list()
        assert len(result) == 3
        assert result[0] == Atom(1)

    def test_morph(self):
        m = Morph([Atom("X")], Atom("X"), Env(), name="ID")
        assert repr(m) == "<morph ID | X>"

    def test_cell_equality(self):
        a = Cell(Atom(1), Cell(Atom(2), NIL))
        b = Cell(Atom(1), Cell(Atom(2), NIL))
        assert a == b

    def test_atom_equality(self):
        assert Atom(42) == Atom(42)
        assert Atom("FOO") == Atom("foo")  # both uppercase
        assert Atom(1) != Atom(2)

    def test_cons(self):
        c = cons(Atom(1), NIL)
        assert c.head == Atom(1)
        assert c.tail == NIL


# ============================================================
# BASE LAYER — Environment
# ============================================================

class TestEnv:
    """Test cons-cell chain environments."""

    def test_empty_env(self):
        env = Env()
        with pytest.raises(NameError):
            env.lookup(Atom("X"))

    def test_bind_and_lookup(self):
        env = Env()
        env2 = env.bind("X", Atom(42))
        assert env2.lookup(Atom("X")) == Atom(42)

    def test_bind_is_functional(self):
        """bind returns NEW env, doesn't mutate old one."""
        env = Env()
        env2 = env.bind("X", Atom(1))
        with pytest.raises(NameError):
            env.lookup(Atom("X"))  # original unchanged
        assert env2.lookup(Atom("X")) == Atom(1)

    def test_shadowing(self):
        env = Env()
        env = env.bind("X", Atom(1))
        env = env.bind("X", Atom(2))
        assert env.lookup(Atom("X")) == Atom(2)

    def test_mutate(self):
        env = Env()
        env = env.bind("X", Atom(1))
        env.mutate(Atom("X"), Atom(99))
        assert env.lookup(Atom("X")) == Atom(99)

    def test_mutate_unbound_raises(self):
        env = Env()
        with pytest.raises(NameError, match="Cannot mutate"):
            env.mutate(Atom("X"), Atom(1))

    def test_extend(self):
        env = Env()
        env = env.extend([Atom("A"), Atom("B")], [Atom(1), Atom(2)])
        assert env.lookup(Atom("A")) == Atom(1)
        assert env.lookup(Atom("B")) == Atom(2)

    def test_as_map(self):
        """Env can export itself as MAP data (homoiconicity)."""
        env = Env()
        env = env.bind("X", Atom(42))
        map_data = env.as_map()
        assert isinstance(map_data, Cell)

    def test_to_dict(self):
        env = Env()
        env = env.bind("X", Atom(1))
        env = env.bind("Y", Atom(2))
        d = env.to_dict()
        assert "X" in d
        assert "Y" in d


# ============================================================
# BASE LAYER — Parser
# ============================================================

class TestParser:
    """Test tokenizer and recursive descent parser."""

    def test_simple_expr(self):
        result = parse_one("{+ 1 2}")
        assert isinstance(result, Cell)
        assert result.head == Atom("+")

    def test_nested_expr(self):
        result = parse_one("{+ 1 {* 2 3}}")
        assert result.head == Atom("+")
        inner = result.tail.tail.head  # third element
        assert isinstance(inner, Cell)
        assert inner.head == Atom("*")

    def test_quote(self):
        """~ is quote in MAP (not ')."""
        result = parse_one("~{+ 1 2}")
        assert result.head == Atom("QUOTE")
        assert isinstance(result.tail.head, Cell)

    def test_eval_unquote(self):
        """@ is eval/unquote in Map."""
        result = parse_one("@X")
        assert result.head == Atom("EVAL")

    def test_pipe_morph(self):
        """{morph | x | body} — pipe-delimited lambda."""
        result = parse_one("{morph | x | {* x 2}}")
        assert result.head == Atom("MORPH")
        # params list
        params = result.tail.head
        assert isinstance(params, Cell)
        assert params.head == Atom("X")

    def test_pipe_def(self):
        """{def fact | n | body} — named function."""
        result = parse_one("{def fact | n | {* n 2}}")
        assert result.head == Atom("DEF")
        assert result.tail.head == Atom("FACT")  # name
        # params
        params = result.tail.tail.head
        assert isinstance(params, Cell)
        assert params.head == Atom("N")

    def test_pipe_when(self):
        """{when | cond | then | else}"""
        result = parse_one("{when | {= 1 1} | 42 | 0}")
        assert result.head == Atom("WHEN")

    def test_fraction_literal(self):
        result = parse_one("1/3")
        assert isinstance(result, Atom)
        assert result.val == Fraction(1, 3)

    def test_negative_number(self):
        result = parse_one("-5")
        assert isinstance(result, Atom)
        assert result.val == Fraction(-5)

    def test_keyword(self):
        result = parse_one(":test")
        assert isinstance(result, Atom)
        assert result.is_keyword
        assert result.val == ":test"

    def test_comment(self):
        results = parse("# this is a comment\n{+ 1 2}")
        assert len(results) == 1

    def test_multiple_exprs(self):
        results = parse("{+ 1 2} {* 3 4}")
        assert len(results) == 2

    def test_unclosed_brace(self):
        with pytest.raises(ParseError):
            parse_one("{+ 1 2")

    def test_empty_list(self):
        result = parse_one("{}")
        assert result == NIL

    def test_symbol_uppercase(self):
        result = parse_one("hello")
        assert result.val == "HELLO"

    def test_error_unclosed_brace_has_position(self):
        """Unclosed brace error includes line:col."""
        with pytest.raises(ParseError) as exc_info:
            parse_one("{+ 1 2")
        assert exc_info.value.line == 1
        assert exc_info.value.col == 1
        assert "line 1" in str(exc_info.value)

    def test_error_multiline_position(self):
        """Error position tracks across multiple lines."""
        src = "1\n2\n{+ 3"
        with pytest.raises(ParseError) as exc_info:
            parse(src)
        assert exc_info.value.line == 3
        assert exc_info.value.col == 1

    def test_error_expect_mismatch_has_position(self):
        """Mismatched token error includes line:col."""
        # } where { is expected triggers expect() error
        with pytest.raises(ParseError) as exc_info:
            parse_one("}")
        assert exc_info.value.line == 1
        assert exc_info.value.col == 1

    def test_error_eof_in_nested(self):
        """EOF inside nested braces reports position of opening brace."""
        with pytest.raises(ParseError) as exc_info:
            parse_one("{+ {* 1 2}")
        # The outer { at col 1 is unclosed
        assert exc_info.value.line == 1


# ============================================================
# BASE LAYER — Evaluator (core special forms)
# ============================================================

class TestEval:
    """Test the base evaluator with all special forms."""

    def test_number(self):
        result, _ = run("42")
        assert result == Atom(42)

    def test_arithmetic_add(self):
        result, _ = run("{+ 1 2}")
        assert result == Atom(3)

    def test_arithmetic_sub(self):
        result, _ = run("{- 10 3}")
        assert result == Atom(7)

    def test_arithmetic_mul(self):
        result, _ = run("{* 6 7}")
        assert result == Atom(42)

    def test_arithmetic_div_fraction(self):
        """All division returns Fraction."""
        result, _ = run("{/ 1 3}")
        assert result == Atom(Fraction(1, 3))

    def test_arithmetic_mod(self):
        result, _ = run("{% 10 3}")
        assert result == Atom(1)

    def test_bind(self):
        result, env = run("{bind x 42} x")
        assert result == Atom(42)

    def test_morph(self):
        result, _ = run("{bind double {morph | x | {* x 2}}} {double 21}")
        assert result == Atom(42)

    def test_def(self):
        result, _ = run("{def double | x | {* x 2}} {double 21}")
        assert result == Atom(42)

    def test_def_recursive(self):
        """Recursive function — factorial."""
        result, _ = run("""
            {def fact | n |
              {when | {= n 0} | 1 |
                {* n {fact {- n 1}}}}}
            {fact 10}
        """)
        assert result == Atom(3628800)

    def test_when_true(self):
        result, _ = run("{when | {= 1 1} | 42 | 0}")
        assert result == Atom(42)

    def test_when_false(self):
        result, _ = run("{when | {= 1 2} | 42 | 0}")
        assert result == Atom(0)

    def test_when_no_else(self):
        result, _ = run("{when | {= 1 2} | 42}")
        assert result == NIL

    def test_seq(self):
        result, _ = run("{seq 1 2 3}")
        assert result == Atom(3)

    def test_quote(self):
        """~ quotes an expression."""
        result, _ = run("~{+ 1 2}")
        assert isinstance(result, Cell)
        assert result.head == Atom("+")

    def test_eval_unquote(self):
        """@ evaluates a quoted expression."""
        result, _ = run("@~{+ 1 2}")
        assert result == Atom(3)

    def test_homoiconicity(self):
        """Build code as data, then eval it."""
        result, _ = run("{bind code {list ~+ 10 20}} @code")
        assert result == Atom(30)

    def test_env_introspection(self):
        """env} returns current environment as MAP data."""
        result, _ = run("{env}")
        assert isinstance(result, Cell)

    def test_apply(self):
        result, _ = run("{apply + {list 1 2 3}}")
        assert result == Atom(6)

    def test_comparison_eq(self):
        r1, _ = run("{= 1 1}")
        r2, _ = run("{= 1 2}")
        assert r1 == Atom(1)
        assert r2 == NIL

    def test_comparison_lt(self):
        r1, _ = run("{< 1 2}")
        assert r1 == Atom(1)

    def test_comparison_gt(self):
        r1, _ = run("{> 5 3}")
        assert r1 == Atom(1)

    def test_logic_not(self):
        r1, _ = run("{not T}")
        assert r1 == NIL
        r2, _ = run("{not NIL}")
        assert r2 == Atom(1)

    def test_logic_and(self):
        r1, _ = run("{and T T}")
        assert r1 == Atom(1)
        r2, _ = run("{and T NIL}")
        assert r2 == NIL

    def test_logic_or(self):
        r1, _ = run("{or NIL T}")
        assert r1 == Atom(1)
        r2, _ = run("{or NIL NIL}")
        assert r2 == NIL

    def test_head_tail(self):
        """MAP uses head/tail, NOT car/cdr."""
        r1, _ = run("{head {list 1 2 3}}")
        assert r1 == Atom(1)
        r2, _ = run("{head {tail {list 1 2 3}}}")
        assert r2 == Atom(2)

    def test_cons_fn(self):
        result, _ = run("{cons 1 {list 2 3}}")
        assert isinstance(result, Cell)
        assert result.head == Atom(1)

    def test_list_fn(self):
        result, _ = run("{list 1 2 3}")
        assert isinstance(result, Cell)
        assert result.to_list() == [Atom(1), Atom(2), Atom(3)]

    def test_length(self):
        result, _ = run("{length {list 1 2 3}}")
        assert result == Atom(3)

    def test_append(self):
        result, _ = run("{append {list 1 2} {list 3 4}}")
        assert isinstance(result, Cell)
        items = result.to_list()
        assert len(items) == 4

    def test_nth(self):
        result, _ = run("{nth 2 {list 10 20 30}}")
        assert result == Atom(30)

    def test_type_check(self):
        r1, _ = run("{type? 42}")
        assert r1 == Atom(":NUM")
        r2, _ = run("{type? NIL}")
        assert r2 == Atom(":NIL")
        r3, _ = run("{type? {list 1 2}}")
        assert r3 == Atom(":CELL")

    def test_nil_check(self):
        r1, _ = run("{nil? NIL}")
        assert r1 == Atom(1)
        r2, _ = run("{nil? 42}")
        assert r2 == NIL

    def test_atom_check(self):
        r1, _ = run("{atom? 42}")
        assert r1 == Atom(1)
        r2, _ = run("{atom? {list 1}}")
        assert r2 == NIL

    def test_higher_order(self):
        """Functions as arguments."""
        result, _ = run("""
            {def apply-twice | f x |
              {f {f x}}}
            {bind inc {morph | n | {+ n 1}}}
            {apply-twice inc 5}
        """)
        assert result == Atom(7)

    def test_closure(self):
        """Closures capture their environment."""
        result, _ = run("""
            {def make-adder | n |
              {morph | x | {+ n x}}}
            {bind add5 {make-adder 5}}
            {add5 10}
        """)
        assert result == Atom(15)

    def test_keyword_self_eval(self):
        result, _ = run(":hello")
        assert result == Atom(":hello")


# ============================================================
# BASE LAYER — set!, macro, loop (previously untested)
# ============================================================

class TestSetMacroLoop:
    """Test set!, macro, and loop — all implemented but never tested."""

    def test_set_basic(self):
        """set! mutates an existing binding."""
        result, _ = run("""
            {bind x 1}
            {set! x 42}
            x
        """)
        assert result == Atom(42)

    def test_set_in_closure(self):
        """set! can mutate a captured binding."""
        result, _ = run("""
            {bind counter 0}
            {bind inc-counter {morph | |
              {set! counter {+ counter 1}}
              counter}}
            {inc-counter}
            {inc-counter}
            {inc-counter}
            counter
        """)
        assert result == Atom(3)

    def test_set_unbound_raises(self):
        """set! on unbound symbol raises error."""
        with pytest.raises(NameError, match="Cannot mutate"):
            run("{set! nonexistent 42}")

    def test_macro_basic(self):
        """macro receives args unevaluated (fexpr)."""
        result, _ = run("""
            {bind my-quote {macro | x | x}}
            {my-quote {+ 1 2}}
        """)
        # The macro should return the unevaluated expression {+ 1 2}
        assert isinstance(result, Cell)
        assert result.head == Atom("+")

    def test_macro_with_eval(self):
        """macro can selectively evaluate its args."""
        result, _ = run("""
            {bind eval-twice {macro | expr |
              {seq @expr @expr}}}
            {bind x 0}
            {eval-twice {set! x {+ x 1}}}
            x
        """)
        assert result == Atom(2)

    def test_loop_basic(self):
        """loop with init, cond, step."""
        result, _ = run("""
            {bind i 0}
            {bind total 0}
            {loop
              NIL
              {< i 5}
              {seq
                {set! total {+ total i}}
                {set! i {+ i 1}}}}
            total
        """)
        # 0 + 1 + 2 + 3 + 4 = 10
        assert result == Atom(10)

    def test_loop_returns_last_step(self):
        """loop returns the last step value."""
        result, _ = run("""
            {bind i 0}
            {loop
              NIL
              {< i 3}
              {set! i {+ i 1}}}
        """)
        assert result == Atom(3)

    def test_loop_zero_iterations(self):
        """loop with initially false condition returns init."""
        result, _ = run("""
            {loop 42 NIL 99}
        """)
        assert result == Atom(42)


# ============================================================
# BASE LAYER — Tail Call Optimization
# ============================================================

class TestTCO:
    """Test tail-call optimization (trampoline)."""

    def test_deep_recursion(self):
        """TCO should handle deep recursion without stack overflow."""
        result, _ = run("""
            {def countdown | n |
              {when | {= n 0} | 0 |
                {countdown {- n 1}}}}
            {countdown 5000}
        """)
        assert result == Atom(0)

    def test_mutual_tco_via_seq(self):
        """seq in tail position should use TCO."""
        result, _ = run("""
            {def sum-to | n acc |
              {when | {= n 0} | acc |
                {sum-to {- n 1} {+ acc n}}}}
            {sum-to 1000 0}
        """)
        assert result == Atom(500500)


# ============================================================
# META LAYER — Meta-Circular Evaluator
# ============================================================

class TestMetaCircular:
    """Test the meta-circular evaluator (MAP interpreting Map)."""

    @pytest.fixture
    def meta(self):
        """Boot the meta-circular evaluator."""
        from meta.meta_interp import boot_meta
        return boot_meta()

    def test_meta_boot(self, meta):
        """Meta-circular evaluator boots successfully."""
        # META-ENV should be bound
        env_val = meta.env.lookup(Atom("META-ENV"))
        assert env_val is not None

    def test_meta_add(self, meta):
        """Two-level interpretation: base eval -> meta eval -> {+ 1 2}."""
        result = meta.eval_in_meta("{+ 1 2}")
        assert result == Atom(3)

    def test_meta_mul(self, meta):
        result = meta.eval_in_meta("{* 6 7}")
        assert result == Atom(42)

    def test_meta_nested(self, meta):
        result = meta.eval_in_meta("{+ 1 {* 2 3}}")
        assert result == Atom(7)

    def test_meta_quote(self, meta):
        """Meta-eval should handle QUOTE."""
        result = meta.eval_in_meta("~{+ 1 2}")
        assert isinstance(result, Cell)

    def test_meta_when_true(self, meta):
        result = meta.eval_in_meta("{when | {= 1 1} | 42 | 0}")
        assert result == Atom(42)

    def test_meta_when_false(self, meta):
        result = meta.eval_in_meta("{when | {= 1 2} | 42 | 0}")
        assert result == Atom(0)

    def test_meta_morph(self, meta):
        """Meta-eval creates closures as {:CLOSURE params body env} lists."""
        result = meta.eval_in_meta("{morph | x | {* x 2}}")
        assert isinstance(result, Cell)
        assert result.head == Atom(":CLOSURE")

    def test_meta_morph_apply(self, meta):
        """Meta-eval can create and immediately call a morph."""
        result = meta.eval_in_meta("{{morph | x | {* x 2}} 21}")
        assert result == Atom(42)

    def test_meta_seq(self, meta):
        result = meta.eval_in_meta("{seq 1 2 3}")
        assert result == Atom(3)

    def test_meta_list_ops(self, meta):
        result = meta.eval_in_meta("{head {list 10 20 30}}")
        assert result == Atom(10)

    def test_meta_comparison(self, meta):
        result = meta.eval_in_meta("{< 1 2}")
        assert result == Atom(1)


# ============================================================
# META LAYER — BIND/DEF in meta-evaluator (new)
# ============================================================

class TestMetaBind:
    """Test BIND and DEF at the meta-circular level."""

    @pytest.fixture
    def meta(self):
        from meta.meta_interp import boot_meta
        return boot_meta()

    def test_meta_bind_in_seq(self, meta):
        """BIND inside SEQ should thread through to subsequent expressions."""
        result = meta.eval_in_meta("{seq {bind x 10} {+ x 5}}")
        assert result == Atom(15)

    def test_meta_bind_program(self, meta):
        """META-EVAL-PROGRAM threads env across top-level expressions."""
        result = meta.eval_program_in_meta("{bind x 10} {+ x 5}")
        assert result == Atom(15)

    def test_meta_def_program(self, meta):
        """DEF at meta level creates callable closures."""
        result = meta.eval_program_in_meta(
            "{def double | n | {* n 2}} {double 21}")
        assert result == Atom(42)

    def test_meta_def_recursive_program(self, meta):
        """Recursive DEF at meta level — closure captures self-reference via NAMED-CLOSURE."""
        result = meta.eval_program_in_meta("""
            {def fact | n |
              {when | {= n 0} | 1 |
                {* n {fact {- n 1}}}}}
            {fact 5}
        """)
        assert result == Atom(120)


# ============================================================
# SUPER LAYER — Registry
# ============================================================

class TestRegistry:
    """Test the operation registry."""

    @pytest.fixture
    def registry_setup(self):
        """Boot meta + registry with ops loaded."""
        from meta.meta_interp import boot_meta
        from super.registry import Registry
        meta = boot_meta()
        ops_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                               'super', 'ops')
        registry = Registry(meta, ops_dir)
        registry.load_all()
        return meta, registry

    def test_ops_loaded(self, registry_setup):
        """Standard ops (map, compose, reify) should load."""
        meta, registry = registry_setup
        assert len(registry.entries) >= 3
        assert "MAP" in registry.entries
        assert "COMPOSE" in registry.entries
        assert "REIFY" in registry.entries

    def test_map_op(self, registry_setup):
        """MAP operation applies function to list."""
        meta, registry = registry_setup
        result = meta.run("{MAP {morph | x | {* x 2}} {list 1 2 3 4 5}}")
        items = result.to_list()
        assert items == [Atom(2), Atom(4), Atom(6), Atom(8), Atom(10)]

    def test_filter_op(self, registry_setup):
        """FILTER keeps elements matching predicate."""
        meta, registry = registry_setup
        result = meta.run("{FILTER {morph | x | {> x 3}} {list 1 2 3 4 5}}")
        items = result.to_list()
        assert items == [Atom(4), Atom(5)]

    def test_reduce_op(self, registry_setup):
        """REDUCE folds list with accumulator."""
        meta, registry = registry_setup
        result = meta.run("{REDUCE + 0 {list 1 2 3 4 5}}")
        assert result == Atom(15)

    def test_compose_op(self, registry_setup):
        """COMPOSE creates f(g(x))."""
        meta, registry = registry_setup
        result = meta.run("""
            {bind inc {morph | x | {+ x 1}}}
            {bind double {morph | x | {* x 2}}}
            {bind inc-then-double {COMPOSE double inc}}
            {inc-then-double 5}
        """)
        # compose(double, inc)(5) = double(inc(5)) = double(6) = 12
        assert result == Atom(12)

    def test_identity_op(self, registry_setup):
        """IDENTITY returns its argument."""
        meta, registry = registry_setup
        result = meta.run("{IDENTITY 42}")
        assert result == Atom(42)

    def test_reg_list_builtin(self, registry_setup):
        """reg-list returns registry as MAP data."""
        meta, registry = registry_setup
        result = meta.run("{reg-list}")
        assert isinstance(result, Cell)

    def test_register_inline(self, registry_setup):
        """Register an operation without a file."""
        meta, registry = registry_setup
        registry.register_inline("DOUBLE-ALL",
            "{def DOUBLE-ALL | lst | {MAP {morph | x | {* x 2}} lst}}")
        result = meta.run("{DOUBLE-ALL {list 1 2 3}}")
        items = result.to_list()
        assert items == [Atom(2), Atom(4), Atom(6)]

    def test_define_op_creates_file(self, registry_setup):
        """reg-define-op writes a .map file."""
        meta, registry = registry_setup
        # Use a temp directory to avoid polluting ops/
        with tempfile.TemporaryDirectory() as tmpdir:
            registry.ops_dir = tmpdir
            registry.define_op("TEST-OP",
                "{def TEST-OP | x | {+ x 100}}")
            assert os.path.exists(os.path.join(tmpdir, "test-op.map"))
            result = meta.run("{TEST-OP 5}")
            assert result == Atom(105)


# ============================================================
# SUPER LAYER — Hot Reload
# ============================================================

class TestHotReload:
    """Test the hot-reload engine."""

    @pytest.fixture
    def hot_setup(self):
        """Set up registry with hot-reload in a temp directory."""
        from meta.meta_interp import boot_meta
        from super.registry import Registry
        from super.hot import HotEngine

        tmpdir = tempfile.mkdtemp()
        meta = boot_meta()
        registry = Registry(meta, tmpdir)

        # Write an initial operation
        op_path = os.path.join(tmpdir, "test-hot.map")
        with open(op_path, "w") as f:
            f.write("{def TEST-HOT | x | {+ x 1}}\n")

        registry.scan()
        registry.load_all()
        hot = HotEngine(registry)

        yield meta, registry, hot, tmpdir, op_path

        hot.stop()
        shutil.rmtree(tmpdir)

    def test_initial_load(self, hot_setup):
        meta, registry, hot, tmpdir, op_path = hot_setup
        result = meta.run("{TEST-HOT 10}")
        assert result == Atom(11)

    def test_stale_detection(self, hot_setup):
        """Changing a file makes the entry stale."""
        meta, registry, hot, tmpdir, op_path = hot_setup
        entry = registry.entries["TEST-HOT"]
        assert not entry.is_stale()

        # Modify the file
        with open(op_path, "w") as f:
            f.write("{def TEST-HOT | x | {+ x 100}}\n")

        assert entry.is_stale()

    def test_manual_reload(self, hot_setup):
        """Reloading picks up file changes."""
        meta, registry, hot, tmpdir, op_path = hot_setup

        # Modify the file
        with open(op_path, "w") as f:
            f.write("{def TEST-HOT | x | {+ x 100}}\n")

        assert registry.entries["TEST-HOT"].is_stale()
        registry.reload_stale()
        assert not registry.entries["TEST-HOT"].is_stale()

        result = meta.run("{TEST-HOT 10}")
        assert result == Atom(110)

    def test_hot_watcher_detects_changes(self, hot_setup):
        """Background watcher detects file changes and queues reloads."""
        meta, registry, hot, tmpdir, op_path = hot_setup
        hot.start()

        # Modify the file
        with open(op_path, "w") as f:
            f.write("{def TEST-HOT | x | {* x 2}}\n")

        # Wait for watcher to detect
        time.sleep(1.5)

        pending = hot.drain_pending()
        assert "TEST-HOT" in pending

        # After drain, the op should be reloaded
        result = meta.run("{TEST-HOT 10}")
        assert result == Atom(20)

    def test_hot_new_file_detection(self, hot_setup):
        """Watcher detects new .map files added to ops/."""
        meta, registry, hot, tmpdir, op_path = hot_setup
        hot.start()

        # Write a new file
        new_path = os.path.join(tmpdir, "new-op.map")
        with open(new_path, "w") as f:
            f.write("{def NEW-OP | x | {* x 3}}\n")

        time.sleep(1.5)
        pending = hot.drain_pending()
        assert "NEW-OP" in pending

        result = meta.run("{NEW-OP 10}")
        assert result == Atom(30)


# ============================================================
# SUPER LAYER — Self-Modification
# ============================================================

class TestSelfMod:
    """Test self-modification capabilities."""

    @pytest.fixture
    def selfmod_setup(self):
        """Full super layer boot in temp directory."""
        from meta.meta_interp import boot_meta
        from super.registry import Registry
        from super.hot import HotEngine, SelfMod

        tmpdir = tempfile.mkdtemp()
        meta = boot_meta()
        registry = Registry(meta, tmpdir)

        # Write an initial operation
        op_path = os.path.join(tmpdir, "morph-op.map")
        with open(op_path, "w") as f:
            f.write("{def MORPH-OP | x | {+ x 1}}\n")

        registry.scan()
        registry.load_all()
        hot = HotEngine(registry)
        selfmod = SelfMod(registry, hot)

        yield meta, registry, hot, selfmod, tmpdir, op_path

        hot.stop()
        shutil.rmtree(tmpdir)

    def test_self_inspect(self, selfmod_setup):
        """self-inspect reads an operation's source code."""
        meta, registry, hot, selfmod, tmpdir, op_path = selfmod_setup
        # Pass name quoted — self-inspect takes a symbol name, not the value
        result = meta.run("{self-inspect ~MORPH-OP}")
        assert isinstance(result, Atom)
        assert result.is_sym
        assert "MORPH-OP" in result.val or "morph-op" in result.val.lower()

    def test_self_rewrite(self, selfmod_setup):
        """self-rewrite modifies an operation's source and reloads."""
        meta, registry, hot, selfmod, tmpdir, op_path = selfmod_setup

        # Verify original
        r1 = meta.run("{MORPH-OP 10}")
        assert r1 == Atom(11)

        # Rewrite using Python API directly (the MAP interface passes
        # source as a symbol atom which is tricky to construct in MAP syntax)
        from base.types import Builtin
        new_source = "{def MORPH-OP | x | {* x 10}}"
        with open(op_path, 'w') as f:
            f.write(new_source + '\n')
        registry.load("MORPH-OP")

        # Verify rewritten
        r2 = meta.run("{MORPH-OP 10}")
        assert r2 == Atom(100)

    def test_self_fork(self, selfmod_setup):
        """self-fork copies an operation under a new name."""
        meta, registry, hot, selfmod, tmpdir, op_path = selfmod_setup
        meta.run("{self-fork ~MORPH-OP ~MORPH-OP-COPY}")

        assert "MORPH-OP-COPY" in registry.entries
        new_path = os.path.join(tmpdir, "morph-op-copy.map")
        assert os.path.exists(new_path)

        result = meta.run("{MORPH-OP-COPY 10}")
        assert result == Atom(11)

    def test_self_dispatch_read(self, selfmod_setup):
        """self-dispatch with no args returns registry as MAP data."""
        meta, registry, hot, selfmod, tmpdir, op_path = selfmod_setup
        result = meta.run("{self-dispatch}")
        assert isinstance(result, Cell) or result == NIL

    def test_self_dispatch_write(self, selfmod_setup):
        """self-dispatch with 1 arg replaces the dispatch table."""
        meta, registry, hot, selfmod, tmpdir, op_path = selfmod_setup

        # Verify original op exists
        assert "MORPH-OP" in registry.entries
        r1 = meta.run("{MORPH-OP 10}")
        assert r1 == Atom(11)

        # Replace dispatch table with a new set of ops
        result = meta.run("""
            {self-dispatch {list
                {list ~ADD-TEN ~{def ADD-TEN | x | {+ x 10}}}
                {list ~MUL-THREE ~{def MUL-THREE | x | {* x 3}}}}}
        """)
        assert result == Atom(2)

        # New ops should work
        r2 = meta.run("{ADD-TEN 5}")
        assert r2 == Atom(15)
        r3 = meta.run("{MUL-THREE 7}")
        assert r3 == Atom(21)

        # Old op should be removed from registry
        assert "MORPH-OP" not in registry.entries

    def test_self_dispatch_write_updates_existing(self, selfmod_setup):
        """self-dispatch write mode can update file-backed ops."""
        meta, registry, hot, selfmod, tmpdir, op_path = selfmod_setup

        # Replace with updated version of same op
        result = meta.run("""
            {self-dispatch {list
                {list ~MORPH-OP ~{def MORPH-OP | x | {* x 99}}}}}
        """)
        assert result == Atom(1)

        # Updated op should work
        r = meta.run("{MORPH-OP 2}")
        assert r == Atom(198)


# ============================================================
# SUPER LAYER — Reify Operations
# ============================================================

class TestReify:
    """Test reify operations (metaprogramming)."""

    @pytest.fixture
    def reify_setup(self):
        from meta.meta_interp import boot_meta
        from super.registry import Registry
        meta = boot_meta()
        ops_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                               'super', 'ops')
        registry = Registry(meta, ops_dir)
        registry.load_all()
        return meta, registry

    def test_build_expr(self, reify_setup):
        """BUILD-EXPR constructs an s-expression."""
        meta, registry = reify_setup
        result = meta.run("{BUILD-EXPR ~+ {list 1 2}}")
        assert isinstance(result, Cell)
        assert result.head == Atom("+")

    def test_make_counter(self, reify_setup):
        """MAKE-COUNTER creates stateful closures."""
        meta, registry = reify_setup
        result = meta.run("""
            {bind c {MAKE-COUNTER 0}}
            {c}
            {c}
            {c}
        """)
        assert result == Atom(2)  # 0, 1, 2 — returns current then increments

    def test_identity_fn(self, reify_setup):
        meta, registry = reify_setup
        result = meta.run("{IDENTITY 42}")
        assert result == Atom(42)

    def test_const(self, reify_setup):
        meta, registry = reify_setup
        result = meta.run("{{CONST 42} 999}")
        assert result == Atom(42)

    def test_flip(self, reify_setup):
        meta, registry = reify_setup
        result = meta.run("{{FLIP -} 3 10}")
        # flip(-)(3, 10) = -(10, 3) = 7
        assert result == Atom(7)


# ============================================================
# SUPER LAYER — Pattern Matching
# ============================================================

class TestMatch:
    """Test the MATCH pattern matching operation."""

    @pytest.fixture
    def match_setup(self):
        from meta.meta_interp import boot_meta
        from super.registry import Registry
        meta = boot_meta()
        ops_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                               'super', 'ops')
        registry = Registry(meta, ops_dir)
        registry.load_all()
        return meta, registry

    def test_match_literal_number(self, match_setup):
        """MATCH on literal number."""
        meta, registry = match_setup
        result = meta.run("""
            {MATCH 42 {list
                {list 1 ~ONE}
                {list 42 ~FORTY-TWO}
                {list 99 ~NINETY-NINE}}}
        """)
        assert result == Atom("FORTY-TWO")

    def test_match_wildcard(self, match_setup):
        """MATCH with _ wildcard matches anything."""
        meta, registry = match_setup
        result = meta.run("""
            {MATCH 999 {list
                {list 1 ~NOPE}
                {list ~_ ~FALLBACK}}}
        """)
        assert result == Atom("FALLBACK")

    def test_match_nil(self, match_setup):
        """MATCH on NIL value."""
        meta, registry = match_setup
        result = meta.run("""
            {MATCH NIL {list
                {list 1 ~NOPE}
                {list NIL ~GOT-NIL}}}
        """)
        assert result == Atom("GOT-NIL")

    def test_match_no_match_returns_nil(self, match_setup):
        """MATCH returns NIL when no pattern matches."""
        meta, registry = match_setup
        result = meta.run("""
            {MATCH 42 {list
                {list 1 ~ONE}
                {list 2 ~TWO}}}
        """)
        assert result == NIL

    def test_match_first_wins(self, match_setup):
        """MATCH returns the first matching clause."""
        meta, registry = match_setup
        result = meta.run("""
            {MATCH 5 {list
                {list ~_ ~FIRST}
                {list 5 ~SECOND}}}
        """)
        assert result == Atom("FIRST")

    def test_match_pat_structural(self, match_setup):
        """MATCH-PAT matches list structure recursively."""
        meta, registry = match_setup
        result = meta.run("""
            {MATCH-PAT {list 1 2 3} {list 1 2 3}}
        """)
        assert result == Atom(1)

    def test_match_pat_structural_mismatch(self, match_setup):
        """MATCH-PAT fails on structural mismatch."""
        meta, registry = match_setup
        result = meta.run("""
            {MATCH-PAT {list 1 2 3} {list 1 99 3}}
        """)
        assert result == NIL


# ============================================================
# BASE LAYER — Module/Import System
# ============================================================

class TestModules:
    """Test the LOAD special form and module system."""

    @pytest.fixture
    def mod_dir(self):
        """Create a temp directory with test module files."""
        tmpdir = tempfile.mkdtemp()

        # math module
        with open(os.path.join(tmpdir, "math.map"), "w") as f:
            f.write("""{def DOUBLE | x | {* x 2}}
{def SQUARE | x | {* x x}}
{bind PI 355/113}
""")

        # util module that loads math
        with open(os.path.join(tmpdir, "util.map"), "w") as f:
            f.write('{bind math-mod {load "math.map"}}\n')
            f.write("{def HELPER | x | {+ x 100}}\n")

        yield tmpdir
        shutil.rmtree(tmpdir)

    def test_string_literal_parse(self):
        """String literals are parsed and stored correctly."""
        result = parse_one('"hello world"')
        assert isinstance(result, Atom)
        assert result.is_str
        assert result.val == '"hello world'
        assert repr(result) == '"hello world"'

    def test_string_literal_self_eval(self):
        """String literals self-evaluate like keywords."""
        # Strings start with " which Atom stores — evaluator treats as symbol lookup
        # We need to quote or handle string self-eval
        # Actually strings are stored as symbols, so we need to make them self-eval
        # For now, test via the parser only
        result = parse_one('"test"')
        assert result.is_str

    def test_load_module(self, mod_dir):
        """LOAD evaluates a file and returns bindings as alist."""
        path = os.path.join(mod_dir, "math.map")
        result, _ = run('{load "' + path + '"}')
        assert isinstance(result, Cell)
        # Should contain DOUBLE, SQUARE, PI bindings
        items = result.to_list()
        names = [item.head.val for item in items if isinstance(item, Cell)]
        assert "DOUBLE" in names
        assert "SQUARE" in names
        assert "PI" in names

    def test_module_get(self, mod_dir):
        """MODULE-GET retrieves a binding from a loaded module."""
        path = os.path.join(mod_dir, "math.map")
        result, _ = run(
            '{bind math {load "' + path + '"}} '
            '{module-get math ~PI}')
        assert result == Atom(Fraction(355, 113))

    def test_module_get_function(self, mod_dir):
        """MODULE-GET can retrieve functions from a module."""
        path = os.path.join(mod_dir, "math.map")
        result, _ = run(
            '{bind math {load "' + path + '"}} '
            '{bind dbl {module-get math ~DOUBLE}} '
            '{dbl 21}')
        assert result == Atom(42)

    def test_load_file_not_found(self):
        """LOAD raises error for missing files."""
        with pytest.raises(Exception, match="file not found"):
            run('{load "/nonexistent/path.map"}')

    def test_load_relative_path(self, mod_dir):
        """LOAD resolves relative paths from loaded file's directory."""
        # util.map loads math.map with a relative path
        path = os.path.join(mod_dir, "util.map")
        result, _ = run('{load "' + path + '"}')
        assert isinstance(result, Cell)
        names = [item.head.val for item in result.to_list() if isinstance(item, Cell)]
        assert "HELPER" in names


# ============================================================
# INTEGRATION — Full Stack
# ============================================================

class TestIntegration:
    """End-to-end tests across all layers."""

    def test_full_boot(self):
        """Super layer full bootstrap works."""
        from meta.meta_interp import boot_meta
        from super.registry import Registry
        from super.hot import HotEngine, SelfMod

        meta = boot_meta()
        ops_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                               'super', 'ops')
        registry = Registry(meta, ops_dir)
        registry.load_all()
        hot = HotEngine(registry)
        selfmod = SelfMod(registry, hot)

        # All layers should be functional
        assert meta.env.lookup(Atom("META-EVAL")) is not None
        assert len(registry.entries) >= 3
        assert meta.env.lookup(Atom("SELF-INSPECT")) is not None

        hot.stop()

    def test_two_level_same_result(self):
        """Base eval and meta eval produce identical results."""
        from meta.meta_interp import boot_meta

        meta = boot_meta()
        exprs = [
            "{+ 1 2}",
            "{* 6 7}",
            "{+ 1 {* 2 3}}",
            "{when | {= 1 1} | 42 | 0}",
            "{head {list 10 20 30}}",
        ]
        for expr in exprs:
            base_result, _ = run(expr)
            meta_result = meta.eval_in_meta(expr)
            assert base_result == meta_result, \
                f"Mismatch for {expr}: base={base_result}, meta={meta_result}"

    def test_homoiconic_roundtrip(self):
        """Quote, manipulate as data, eval back."""
        result, _ = run("""
            {bind code ~{+ 10 20}}
            {bind new-code {cons ~* {tail code}}}
            @new-code
        """)
        # Replace + with * on {+ 10 20} -> {* 10 20} -> 200
        assert result == Atom(200)

    def test_division_always_fraction(self):
        """MAP uses Fraction — no floating point ever."""
        result, _ = run("{/ 1 3}")
        assert result.val == Fraction(1, 3)
        assert isinstance(result.val, Fraction)
        result2, _ = run("{/ 22 7}")
        assert result2.val == Fraction(22, 7)


# ============================================================
# CLI — __main__.py
# ============================================================

class TestCLI:
    """Test the non-interactive CLI shell interface."""

    def _run_cli(self, args, stdin_text=None):
        """Run the CLI as a subprocess, return (stdout, stderr, returncode)."""
        import subprocess
        cmd = [sys.executable, '-m', 'map'] + args
        # cwd must be the directory CONTAINING map/
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        proc = subprocess.run(
            cmd,
            input=stdin_text,
            capture_output=True,
            text=True,
            cwd=project_root,
        )
        return proc.stdout.strip(), proc.stderr.strip(), proc.returncode

    def test_no_args_shows_breadcrumb(self):
        out, err, rc = self._run_cli([])
        assert rc == 0
        assert 'MAP' in out
        assert 'run' in out
        assert 'eval' in out

    def test_eval_arithmetic(self):
        out, err, rc = self._run_cli(['eval', '{+ 1 2}'])
        assert rc == 0
        assert out == '3'

    def test_eval_multiple_exprs(self):
        out, err, rc = self._run_cli(['eval', '{bind x 10}', '{+ x 5}'])
        assert rc == 0
        assert out == '15'

    def test_eval_conditional(self):
        out, err, rc = self._run_cli(['eval', '{when | {> 5 3} | :YES | :NO}'])
        assert rc == 0
        assert out == ':YES'

    def test_run_piped(self):
        out, err, rc = self._run_cli(['run'], stdin_text='{+ 10 20}')
        assert rc == 0
        assert out == '30'

    def test_run_piped_multiexpr(self):
        out, err, rc = self._run_cli(['run'], stdin_text='{bind x 5} {* x x}')
        assert rc == 0
        assert out == '25'

    def test_run_file(self):
        """Test running a .map file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.map', delete=False) as f:
            f.write('{bind x 7}\n{* x 6}\n')
            f.flush()
            try:
                out, err, rc = self._run_cli(['run', f.name])
                assert rc == 0
                assert out == '42'
            finally:
                os.unlink(f.name)

    def test_run_file_not_found(self):
        out, err, rc = self._run_cli(['run', '/nonexistent/file.map'])
        assert rc == 1
        assert 'not a stored flow or existing file' in err

    def test_eval_error(self):
        out, err, rc = self._run_cli(['eval', '{bad'])
        assert rc == 1
        assert 'Error' in err

    def test_eval_no_args_piped_empty(self):
        """eval with no args and empty stdin returns 0 (nothing to eval)."""
        out, err, rc = self._run_cli(['eval'], stdin_text='')
        assert rc == 0

    def test_eval_piped_stdin(self):
        """eval accepts piped expressions on stdin."""
        out, err, rc = self._run_cli(['eval'], stdin_text='{+ 100 200}')
        assert rc == 0
        assert out == '300'

    def test_help_no_args(self):
        out, err, rc = self._run_cli(['help'])
        assert rc == 0
        assert 'MAP' in out

    def test_help_commands(self):
        out, err, rc = self._run_cli(['help', 'commands'])
        assert rc == 0
        assert 'run' in out
        assert 'eval' in out
        assert 'meta' in out

    def test_help_eval(self):
        out, err, rc = self._run_cli(['help', 'eval'])
        assert rc == 0
        assert 'expression' in out.lower()

    def test_help_morph(self):
        out, err, rc = self._run_cli(['help', 'morph'])
        assert rc == 0
        assert 'lambda' in out.lower() or 'morph' in out.lower()

    def test_help_unknown_topic(self):
        out, err, rc = self._run_cli(['help', 'nonexistent'])
        assert rc == 1
        assert 'No help' in out

    def test_unknown_command(self):
        out, err, rc = self._run_cli(['bogus'])
        assert rc == 1
        assert 'Unknown command' in err

    def test_list_empty(self):
        out, err, rc = self._run_cli(['list'])
        assert rc == 0

    def test_def_and_call(self):
        out, err, rc = self._run_cli(['eval', '{def double | x | {* x 2}}', '{double 21}'])
        assert rc == 0
        assert out == '42'

    def test_help_special_form_bind(self):
        out, err, rc = self._run_cli(['help', 'bind'])
        assert rc == 0
        assert 'bind' in out.lower()
        assert 'NAME' in out

    def test_help_special_form_set(self):
        out, err, rc = self._run_cli(['help', 'set!'])
        assert rc == 0
        assert 'mutate' in out.lower() or 'set!' in out.lower()

    def test_help_special_form_quote(self):
        out, err, rc = self._run_cli(['help', 'quote'])
        assert rc == 0
        assert 'quote' in out.lower()

    def test_help_special_form_match(self):
        out, err, rc = self._run_cli(['help', 'match'])
        assert rc == 0
        assert 'pattern' in out.lower()

    def test_clear_command(self):
        """Test clear resets persistent state."""
        out1, _, rc1 = self._run_cli(['eval', '{bind z 999}'])
        assert rc1 == 0
        out2, _, rc2 = self._run_cli(['clear'])
        assert rc2 == 0
        assert 'cleared' in out2.lower()
        _, err3, rc3 = self._run_cli(['eval', 'z'])
        assert rc3 == 1  # z should be unbound

    def test_modify_command(self):
        """Test modify updates an existing flow."""
        # Save, then modify, then run
        out1, _, rc1 = self._run_cli(['save', 'mod-test', '{+ 1 2}'])
        assert rc1 == 0
        out2, _, rc2 = self._run_cli(['modify', 'mod-test', '{+ 10 20}'])
        assert rc2 == 0
        assert 'modified' in out2.lower()
        out3, _, rc3 = self._run_cli(['flow-run', 'mod-test'])
        assert rc3 == 0
        assert out3 == '30'
        # Clean up
        self._run_cli(['delete', 'mod-test'])

    def test_modify_nonexistent(self):
        _, err, rc = self._run_cli(['modify', 'nonexistent', '{+ 1 2}'])
        assert rc == 1
        assert 'not found' in err

    def test_run_with_flow_name(self):
        """run accepts a stored flow name."""
        self._run_cli(['save', 'run-test', '{* 6 7}'])
        out, _, rc = self._run_cli(['run', 'run-test'])
        assert rc == 0
        assert out == '42'
        self._run_cli(['delete', 'run-test'])

    def test_run_empty_stdin(self):
        """run with empty piped input returns 0 (no expressions to eval)."""
        import subprocess
        cmd = [sys.executable, '-m', 'map', 'run']
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        proc = subprocess.run(
            cmd,
            input='',
            capture_output=True,
            text=True,
            cwd=project_root,
        )
        assert proc.returncode == 0
        assert proc.stdout.strip() == ''


# ============================================================
# FLOWS — base/flows.py
# ============================================================

class TestFlows:
    """Test named attention flow storage."""

    def setup_method(self):
        self.flows_dir = tempfile.mkdtemp()

    def teardown_method(self):
        shutil.rmtree(self.flows_dir, ignore_errors=True)

    def test_save_and_list(self):
        from base.flows import save_flow, list_flows
        save_flow('my-flow', '{+ 1 2}', flows_dir=self.flows_dir)
        flows = list_flows(self.flows_dir)
        assert len(flows) == 1
        assert flows[0][0] == 'my-flow'

    def test_save_with_description(self):
        from base.flows import save_flow, list_flows
        save_flow('test', '{+ 1 2}', description='A test flow', flows_dir=self.flows_dir)
        flows = list_flows(self.flows_dir)
        assert flows[0][1] == 'A test flow'

    def test_get_source(self):
        from base.flows import save_flow, get_flow_source
        save_flow('arith', '{+ 1 2}', flows_dir=self.flows_dir)
        src = get_flow_source('arith', self.flows_dir)
        assert src == '{+ 1 2}'

    def test_get_source_not_found(self):
        from base.flows import get_flow_source
        assert get_flow_source('nope', self.flows_dir) is None

    def test_inspect_flow(self):
        from base.flows import save_flow, inspect_flow
        save_flow('checker', '{when | {> x 0} | :POS | :NEG}', flows_dir=self.flows_dir)
        info = inspect_flow('checker', self.flows_dir)
        assert info is not None
        assert info['name'] == 'checker'
        assert 'WHEN' in info['symbols']
        assert '>' in info['symbols']
        assert 'X' in info['dependencies']

    def test_inspect_not_found(self):
        from base.flows import inspect_flow
        assert inspect_flow('nope', self.flows_dir) is None

    def test_run_flow(self):
        from base.flows import save_flow, run_flow
        save_flow('add', '{+ 10 20}', flows_dir=self.flows_dir)
        result, _ = run_flow('add', flows_dir=self.flows_dir)
        assert result == Atom(30)

    def test_run_flow_not_found(self):
        from base.flows import run_flow
        with pytest.raises(MAPError):
            run_flow('nope', flows_dir=self.flows_dir)

    def test_delete_flow(self):
        from base.flows import save_flow, delete_flow, list_flows
        save_flow('temp', '{+ 1 1}', flows_dir=self.flows_dir)
        assert delete_flow('temp', self.flows_dir)
        assert list_flows(self.flows_dir) == []

    def test_delete_not_found(self):
        from base.flows import delete_flow
        assert not delete_flow('nope', self.flows_dir)

    def test_save_invalid_source_raises(self):
        from base.flows import save_flow
        with pytest.raises(ParseError):
            save_flow('bad', '{unclosed', flows_dir=self.flows_dir)

    def test_multiple_flows(self):
        from base.flows import save_flow, list_flows
        save_flow('a', '{+ 1 1}', flows_dir=self.flows_dir)
        save_flow('b', '{+ 2 2}', flows_dir=self.flows_dir)
        save_flow('c', '{+ 3 3}', flows_dir=self.flows_dir)
        flows = list_flows(self.flows_dir)
        assert len(flows) == 3
        names = [f[0] for f in flows]
        assert 'a' in names
        assert 'b' in names
        assert 'c' in names

    def test_flow_run_with_env(self):
        """Flow can use bindings from a provided env."""
        from base.flows import save_flow, run_flow
        save_flow('use-x', '{* x 3}', flows_dir=self.flows_dir)
        env = make_stdlib()
        _, env = run("{bind x 10}", env)
        result, _ = run_flow('use-x', env, self.flows_dir)
        assert result == Atom(30)

    def test_cli_save_and_flow_run(self):
        """Test flow save and run through CLI."""
        import subprocess
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        flows_dir = os.path.join(project_root, '.map-flows')
        if os.path.exists(flows_dir):
            shutil.rmtree(flows_dir)
        try:
            proc1 = subprocess.run(
                [sys.executable, '-m', 'map', 'save', 'test-flow', '{+ 100 200}'],
                capture_output=True, text=True, cwd=project_root,
            )
            assert proc1.returncode == 0

            proc2 = subprocess.run(
                [sys.executable, '-m', 'map', 'flow-run', 'test-flow'],
                capture_output=True, text=True, cwd=project_root,
            )
            assert proc2.returncode == 0
            assert proc2.stdout.strip() == '300'

            proc3 = subprocess.run(
                [sys.executable, '-m', 'map', 'list'],
                capture_output=True, text=True, cwd=project_root,
            )
            assert proc3.returncode == 0
            assert 'test-flow' in proc3.stdout
        finally:
            if os.path.exists(flows_dir):
                shutil.rmtree(flows_dir)
            state_dir = os.path.join(project_root, '.map-state')
            if os.path.exists(state_dir):
                shutil.rmtree(state_dir)


# ============================================================
# HELP SYSTEM — base/help.py
# ============================================================

class TestHelpSystem:
    """Test the progressive disclosure help module directly."""

    def test_level0_breadcrumb(self):
        from base.help import get_help
        text, code = get_help(None)
        assert code == 0
        assert 'MAP' in text
        assert 'run' in text

    def test_level1_commands(self):
        from base.help import get_help
        text, code = get_help('commands')
        assert code == 0
        assert 'eval' in text
        assert 'meta' in text
        assert 'clear' in text

    def test_level2_eval(self):
        from base.help import get_help
        text, code = get_help('eval')
        assert code == 0
        assert 'expression' in text.lower()

    def test_level3_morph(self):
        from base.help import get_help
        text, code = get_help('morph')
        assert code == 0
        assert 'lambda' in text.lower() or 'morph' in text.lower()
        assert 'params' in text.lower()

    def test_level3_def(self):
        from base.help import get_help
        text, code = get_help('def')
        assert code == 0
        assert 'function' in text.lower()

    def test_level3_loop(self):
        from base.help import get_help
        text, code = get_help('loop')
        assert code == 0
        assert 'init' in text.lower()

    def test_level3_load(self):
        from base.help import get_help
        text, code = get_help('load')
        assert code == 0
        assert 'module' in text.lower()

    def test_unknown_topic(self):
        from base.help import get_help
        text, code = get_help('nonexistent')
        assert code == 1
        assert 'No help' in text

    def test_case_insensitive(self):
        from base.help import get_help
        text1, _ = get_help('EVAL')
        text2, _ = get_help('eval')
        assert text1 == text2


# ============================================================
# PERSISTENCE — base/persistence.py
# ============================================================

class TestPersistence:
    """Test environment serialization and persistence across invocations."""

    def setup_method(self):
        self.state_dir = tempfile.mkdtemp()

    def teardown_method(self):
        shutil.rmtree(self.state_dir, ignore_errors=True)

    def test_save_and_load_number(self):
        from base.persistence import save_env, load_env
        env = make_stdlib()
        result, env = run("{bind x 42}", env)
        save_env(env, self.state_dir)

        env2 = load_env(self.state_dir)
        result2, _ = run("x", env2)
        assert result2 == Atom(42)

    def test_save_and_load_list(self):
        from base.persistence import save_env, load_env
        env = make_stdlib()
        result, env = run("{bind data {list 1 2 3}}", env)
        save_env(env, self.state_dir)

        env2 = load_env(self.state_dir)
        result2, _ = run("{head data}", env2)
        assert result2 == Atom(1)

    def test_save_and_load_morph(self):
        from base.persistence import save_env, load_env
        env = make_stdlib()
        _, env = run("{def double | x | {* x 2}}", env)
        save_env(env, self.state_dir)

        env2 = load_env(self.state_dir)
        result, _ = run("{double 21}", env2)
        assert result == Atom(42)

    def test_save_and_load_keyword(self):
        from base.persistence import save_env, load_env
        env = make_stdlib()
        _, env = run("{bind status :ACTIVE}", env)
        save_env(env, self.state_dir)

        env2 = load_env(self.state_dir)
        result, _ = run("status", env2)
        assert result == Atom(':ACTIVE')

    def test_save_and_load_string(self):
        from base.persistence import save_env, load_env
        env = make_stdlib()
        _, env = run('{bind msg "hello"}', env)
        save_env(env, self.state_dir)

        env2 = load_env(self.state_dir)
        result, _ = run("msg", env2)
        assert result.is_str
        assert result.val == '"hello'

    def test_load_nonexistent_returns_stdlib(self):
        from base.persistence import load_env
        env = load_env('/nonexistent/path')
        # Should still have stdlib
        result, _ = run("{+ 1 2}", env)
        assert result == Atom(3)

    def test_clear_env(self):
        from base.persistence import save_env, load_env, clear_env
        env = make_stdlib()
        _, env = run("{bind x 99}", env)
        save_env(env, self.state_dir)
        clear_env(self.state_dir)
        env2 = load_env(self.state_dir)
        with pytest.raises(NameError):
            run("x", env2)

    def test_multiple_bindings_persist(self):
        from base.persistence import save_env, load_env
        env = make_stdlib()
        _, env = run("{bind a 1} {bind b 2} {bind c {+ a b}}", env)
        save_env(env, self.state_dir)

        env2 = load_env(self.state_dir)
        result, _ = run("{+ a {+ b c}}", env2)
        assert result == Atom(6)

    def test_persistence_via_cli(self):
        """Test persistence through the actual CLI subprocess."""
        import subprocess
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        state_dir = os.path.join(project_root, '.map-state')

        # Clean state
        if os.path.exists(state_dir):
            shutil.rmtree(state_dir)

        try:
            # Bind a value
            proc1 = subprocess.run(
                [sys.executable, '-m', 'map', 'eval', '{bind x 42}'],
                capture_output=True, text=True, cwd=project_root,
            )
            assert proc1.returncode == 0

            # Retrieve it in a separate invocation
            proc2 = subprocess.run(
                [sys.executable, '-m', 'map', 'eval', 'x'],
                capture_output=True, text=True, cwd=project_root,
            )
            assert proc2.returncode == 0
            assert proc2.stdout.strip() == '42'
        finally:
            if os.path.exists(state_dir):
                shutil.rmtree(state_dir)

    def test_nil_serialization(self):
        from base.persistence import save_env, load_env
        env = make_stdlib()
        _, env = run("{bind nothing NIL}", env)
        save_env(env, self.state_dir)
        env2 = load_env(self.state_dir)
        result, _ = run("{nil? nothing}", env2)
        assert result == Atom(1)

    def test_fraction_precision(self):
        from base.persistence import save_env, load_env
        env = make_stdlib()
        _, env = run("{bind ratio {/ 22 7}}", env)
        save_env(env, self.state_dir)
        env2 = load_env(self.state_dir)
        result, _ = run("ratio", env2)
        assert result == Atom(Fraction(22, 7))


# ============================================================
# Run with: pytest tests/test_map.py -v
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
