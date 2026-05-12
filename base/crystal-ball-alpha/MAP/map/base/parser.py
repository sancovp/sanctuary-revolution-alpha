"""MAP parser — tokenizer + recursive descent.

Tokenizes `{}|~@#` as structural, everything else as atoms.
Handles pipe-delimited morph syntax: {morph | params | body}
"""

import re
from fractions import Fraction
from .types import Atom, Cell, NIL, make_list

class ParseError(Exception):
    """Parse error with optional source position (line:col)."""
    def __init__(self, msg, line=None, col=None):
        self.line = line
        self.col = col
        if line is not None and col is not None:
            super().__init__(f"{msg} [line {line}, col {col}]")
        else:
            super().__init__(msg)


def _offset_to_line_col(source, offset):
    """Convert a byte offset into (line, col) — both 1-based."""
    line = source[:offset].count('\n') + 1
    last_nl = source.rfind('\n', 0, offset)
    col = offset - last_nl  # works even when last_nl is -1
    return line, col

# --- Tokenizer ---

TOKEN_RE = re.compile(r"""
    (\#[^\n]*)           |  # comment (discarded)
    ([{}|~@])            |  # structural chars
    ("(?:[^"\\]|\\.)*")  |  # string literal (double-quoted)
    (-?\d+/\d+)          |  # fraction literal
    (-?\d+\.?\d*)        |  # number
    (:[A-Za-z_][\w-]*)   |  # keyword
    ([^\s{}|~@\#"]+)        # symbol
""", re.VERBOSE)

def tokenize(source):
    """Yield tokens from MAP source. Comments discarded."""
    for m in TOKEN_RE.finditer(source):
        comment, struct, string, frac, num, kw, sym = m.groups()
        if comment:
            continue
        if struct:
            yield ('STRUCT', struct, m.start())
        elif string:
            # Strip quotes, unescape backslashes
            yield ('STR', string[1:-1].replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\'), m.start())
        elif frac:
            yield ('NUM', frac, m.start())
        elif num:
            yield ('NUM', num, m.start())
        elif kw:
            yield ('KW', kw, m.start())
        elif sym:
            yield ('SYM', sym, m.start())

# --- Parser ---

class Parser:
    def __init__(self, tokens, source=''):
        self.tokens = list(tokens)
        self.pos = 0
        self.source = source

    def _lc(self, offset):
        """Return (line, col) for a byte offset, or (None, None) if unavailable."""
        if self.source and offset is not None:
            return _offset_to_line_col(self.source, offset)
        return None, None

    def peek(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def advance(self):
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def expect(self, kind, val=None):
        tok = self.peek()
        if tok is None:
            raise ParseError(f"Unexpected EOF, expected {kind} {val}")
        if tok[0] != kind or (val is not None and tok[1] != val):
            line, col = self._lc(tok[2])
            raise ParseError(f"Expected {kind} {val}, got {tok}", line, col)
        return self.advance()

    def parse_expr(self):
        tok = self.peek()
        if tok is None:
            raise ParseError("Unexpected EOF")

        kind, val, offset = tok

        if kind == 'STRUCT' and val == '~':
            # Quote: ~expr -> {QUOTE expr}
            self.advance()
            inner = self.parse_expr()
            return Cell(Atom('QUOTE'), Cell(inner, NIL))

        if kind == 'STRUCT' and val == '@':
            # Eval/unquote: @expr -> {EVAL expr}
            self.advance()
            inner = self.parse_expr()
            return Cell(Atom('EVAL'), Cell(inner, NIL))

        if kind == 'STRUCT' and val == '{':
            return self.parse_list()

        if kind == 'STR':
            self.advance()
            return Atom('"' + val)  # prefix with " to mark as string literal

        if kind == 'NUM':
            self.advance()
            if '/' in val:
                return Atom(Fraction(val))
            elif '.' in val:
                return Atom(Fraction(val))
            else:
                return Atom(Fraction(int(val)))

        if kind == 'KW':
            self.advance()
            return Atom(val)  # keywords keep their colon prefix

        if kind == 'SYM':
            self.advance()
            return Atom(val.upper())

        line, col = self._lc(offset)
        raise ParseError(f"Unexpected token: {tok}", line, col)

    def parse_list(self):
        """Parse { ... } with optional pipe sections for morph syntax."""
        open_tok = self.expect('STRUCT', '{')
        elements = []
        pipe_sections = []
        current_section = []

        while True:
            tok = self.peek()
            if tok is None:
                line, col = self._lc(open_tok[2])
                raise ParseError("Unclosed {", line, col)
            if tok[0] == 'STRUCT' and tok[1] == '}':
                self.advance()
                break
            if tok[0] == 'STRUCT' and tok[1] == '|':
                self.advance()
                pipe_sections.append(current_section)
                current_section = []
                continue
            current_section.append(self.parse_expr())

        if pipe_sections:
            # Pipe syntax: first section is pre-pipe, middle sections, last is body
            pipe_sections.append(current_section)
            # {morph | x y | body} => pipe_sections = [[morph], [x, y], [body]]
            all_parts = []
            for section in pipe_sections:
                all_parts.append(section)
            return self._build_pipe_form(all_parts)
        else:
            return _list_to_cells(current_section)

    def _build_pipe_form(self, sections):
        """Convert pipe-delimited sections to cell structure.

        {morph | x y | body} -> Cell(MORPH, Cell(Cell(X, Cell(Y, NIL)), Cell(body, NIL)))
        {when | cond | then | else} -> Cell(WHEN, Cell(cond, Cell(then, Cell(else, NIL))))
        {loop | init | cond | step | body} -> similar
        """
        if not sections or not sections[0]:
            raise ParseError("Empty pipe form")

        head = sections[0]
        if len(head) == 1:
            tag = head[0]
        else:
            tag = _list_to_cells(head)

        rest = sections[1:]

        # For def: {def NAME | params | body} — name is in first section with DEF
        if len(head) == 2 and isinstance(head[0], Atom) and head[0].val == 'DEF':
            name = head[1]
            if len(rest) < 2:
                raise ParseError("def needs | params | body")
            params = _list_to_cells(rest[0]) if rest[0] else NIL
            body_exprs = rest[1]
            if len(body_exprs) == 1:
                body = body_exprs[0]
            else:
                body = Cell(Atom('SEQ'), _list_to_cells(body_exprs) if body_exprs else NIL)
            return Cell(Atom('DEF'), Cell(name, Cell(params, Cell(body, NIL))))

        # For morph/macro: params section becomes a sub-list, body stays as-is
        if isinstance(tag, Atom) and tag.val in ('MORPH', 'MACRO'):
            if len(rest) < 2:
                raise ParseError(f"{tag.val.lower()} needs | params | body")
            params = _list_to_cells(rest[0]) if rest[0] else NIL
            # Body might have multiple exprs — wrap in SEQ if so
            body_exprs = rest[1]
            if len(body_exprs) == 1:
                body = body_exprs[0]
            else:
                body = Cell(Atom('SEQ'), _list_to_cells(body_exprs) if body_exprs else NIL)
            return Cell(tag, Cell(params, Cell(body, NIL)))

        # For when: {when | cond | then | else}
        if isinstance(tag, Atom) and tag.val == 'WHEN':
            parts = []
            for section in rest:
                if len(section) == 1:
                    parts.append(section[0])
                else:
                    parts.append(Cell(Atom('SEQ'), _list_to_cells(section) if section else NIL))
            return Cell(tag, _list_to_cells(parts) if parts else NIL)

        # Generic: each pipe section becomes one element
        parts = [tag]
        for section in rest:
            if len(section) == 1:
                parts.append(section[0])
            elif section:
                parts.append(_list_to_cells(section))
            else:
                parts.append(NIL)
        return _list_to_cells(parts)


def _list_to_cells(items):
    """Convert Python list to Cell chain."""
    result = NIL
    for item in reversed(items):
        result = Cell(item, result)
    return result


def parse(source):
    """Parse a MAP source string. Returns list of top-level expressions."""
    tokens = list(tokenize(source))
    parser = Parser(tokens, source)
    exprs = []
    while parser.peek() is not None:
        exprs.append(parser.parse_expr())
    return exprs


def parse_one(source):
    """Parse a single expression."""
    exprs = parse(source)
    if len(exprs) != 1:
        raise ParseError(f"Expected 1 expression, got {len(exprs)}")
    return exprs[0]
