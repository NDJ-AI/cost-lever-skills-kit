"""Reference solution for the expression evaluator fixture.

NOT part of the task the agent sees. Used only to validate that the test suite
is achievable (a correct implementation makes every test pass). The runner must
copy only `calc/`, `tests/`, and `TASK.md` into an executor's working directory
-- never this `solution/` folder.

Recursive-descent parser:
    expression := term (('+' | '-') term)*
    term       := factor (('*' | '/') factor)*
    factor     := '-' factor | '(' expression ')' | number
"""


def _tokenize(expr):
    tokens = []
    i, n = 0, len(expr)
    while i < n:
        c = expr[i]
        if c.isspace():
            i += 1
            continue
        if c in "+-*/()":
            tokens.append(c)
            i += 1
            continue
        if c.isdigit() or c == ".":
            j = i
            while j < n and (expr[j].isdigit() or expr[j] == "."):
                j += 1
            piece = expr[i:j]
            try:
                tokens.append(float(piece))
            except ValueError:
                raise ValueError(f"invalid number: {piece!r}")
            i = j
            continue
        raise ValueError(f"unexpected character: {c!r}")
    return tokens


class _Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def _peek(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def _advance(self):
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def parse(self):
        if not self.tokens:
            raise ValueError("empty expression")
        value = self.expression()
        if self.pos != len(self.tokens):
            raise ValueError("unexpected trailing input")
        return value

    def expression(self):
        value = self.term()
        while self._peek() in ("+", "-"):
            op = self._advance()
            rhs = self.term()
            value = value + rhs if op == "+" else value - rhs
        return value

    def term(self):
        value = self.factor()
        while self._peek() in ("*", "/"):
            op = self._advance()
            rhs = self.factor()
            value = value * rhs if op == "*" else value / rhs
        return value

    def factor(self):
        tok = self._peek()
        if tok is None:
            raise ValueError("unexpected end of expression")
        if tok == "-":
            self._advance()
            return -self.factor()
        if tok == "(":
            self._advance()
            value = self.expression()
            if self._peek() != ")":
                raise ValueError("unbalanced parentheses")
            self._advance()
            return value
        if isinstance(tok, float):
            self._advance()
            return tok
        raise ValueError(f"unexpected token: {tok!r}")


def evaluate(expr: str) -> float:
    return float(_Parser(_tokenize(expr)).parse())
