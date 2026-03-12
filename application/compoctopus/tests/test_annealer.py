"""Tests for the Annealer — .octo → target language compilation."""

import pytest
from compoctopus.annealer import (
    Annealer,
    PYTHON_SYNTAX,
    JAVASCRIPT_SYNTAX,
    StubPhase,
    anneal_source,
    scan,
)


class TestScan:
    """Test stub block detection."""

    def test_finds_single_stub(self):
        source = '''def hello():
    #>> STUB
    #| return "world"
    #<< STUB'''
        stubs = scan(source)
        assert len(stubs) == 1
        assert stubs[0].phase == StubPhase.PSEUDO
        assert len(stubs[0].pipe_lines) == 1

    def test_finds_multiple_stubs(self):
        source = '''def a():
    #>> STUB
    #| return 1
    #<< STUB

def b():
    #>> STUB
    #| return 2
    #<< STUB'''
        stubs = scan(source)
        assert len(stubs) == 2

    def test_empty_stub(self):
        source = '''def a():
    #>> STUB
    #<< STUB'''
        stubs = scan(source)
        assert len(stubs) == 1
        assert stubs[0].phase == StubPhase.EMPTY

    def test_multiline_pseudo(self):
        source = '''def add(a, b):
    #>> STUB
    #| result = a + b
    #| if result < 0:
    #|     result = 0
    #| return result
    #<< STUB'''
        stubs = scan(source)
        assert len(stubs) == 1
        assert len(stubs[0].pipe_lines) == 4

    def test_no_stubs(self):
        source = '''def hello():
    return "world"'''
        stubs = scan(source)
        assert len(stubs) == 0

    def test_javascript_syntax(self):
        source = '''function hello() {
    //>> STUB
    //| return "world";
    //<< STUB
}'''
        stubs = scan(source, JAVASCRIPT_SYNTAX)
        assert len(stubs) == 1
        assert stubs[0].phase == StubPhase.PSEUDO


class TestAnnealSource:
    """Test in-memory annealing."""

    def test_basic_unwrap(self):
        source = '''def hello():
    #>> STUB
    #| return "world"
    #<< STUB'''
        output = anneal_source(source)
        assert '#>> STUB' not in output
        assert '#<< STUB' not in output
        assert '#|' not in output
        assert 'return "world"' in output

    def test_preserves_non_stub_code(self):
        source = '''import os

def hello():
    #>> STUB
    #| return "world"
    #<< STUB

def goodbye():
    return "bye"'''
        output = anneal_source(source)
        assert 'import os' in output
        assert 'return "world"' in output
        assert 'return "bye"' in output

    def test_empty_stub_becomes_nie(self):
        source = '''def todo():
    #>> STUB
    #<< STUB'''
        output = anneal_source(source)
        assert 'raise NotImplementedError' in output

    def test_multiple_stubs(self):
        source = '''def a():
    #>> STUB
    #| return 1
    #<< STUB

def b():
    #>> STUB
    #| return 2
    #<< STUB'''
        output = anneal_source(source)
        assert 'return 1' in output
        assert 'return 2' in output
        assert '#>> STUB' not in output

    def test_javascript_anneal(self):
        source = '''function greet(name) {
    //>> STUB
    //| return `Hello, ${name}!`;
    //<< STUB
}'''
        output = anneal_source(source, JAVASCRIPT_SYNTAX)
        assert '//>> STUB' not in output
        assert 'return `Hello, ${name}!`' in output


class TestAnnealReport:
    """Test annealing reports."""

    def test_report_counts(self):
        source = '''def a():
    #>> STUB
    #| return 1
    #<< STUB

def b():
    #>> STUB
    #<< STUB'''
        _, report = Annealer().anneal_source(source)
        assert report.stubs_found == 2
        assert report.stubs_annealed == 1
        assert report.stubs_empty == 1
        assert report.success

    def test_report_repr(self):
        _, report = Annealer().anneal_source("x = 1")
        assert "✅" in repr(report)


class TestEndToEnd:
    """Full .octo → .py pipeline."""

    def test_planner_octo_exists(self):
        """The planner .octo file should be scannable."""
        from pathlib import Path
        octo_path = Path(__file__).parent.parent / "octo" / "planner_agent.octo"
        if not octo_path.exists():
            pytest.skip("planner_agent.octo not found")

        source = octo_path.read_text()
        stubs = scan(source)
        assert len(stubs) > 0
        assert all(s.phase == StubPhase.PSEUDO for s in stubs)

    def test_planner_anneals_cleanly(self):
        """The planner should anneal without errors."""
        from pathlib import Path
        octo_path = Path(__file__).parent.parent / "octo" / "planner_agent.octo"
        if not octo_path.exists():
            pytest.skip("planner_agent.octo not found")

        source = octo_path.read_text()
        output, report = Annealer().anneal_source(source)
        assert report.success
        assert report.stubs_annealed == 5
        assert '#>> STUB' not in output
        # It should be valid Python — compile check
        compile(output, "planner_agent.py", "exec")
