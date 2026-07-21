# Task: Implement the arithmetic expression evaluator

Implement the `evaluate` function in `calc/evaluator.py` so that all tests in
`tests/test_evaluator.py` pass.

`evaluate(expr: str) -> float` takes a string containing an arithmetic
expression and returns the result as a float.

## Requirements

The evaluator must support:

- The four binary operators `+`, `-`, `*`, `/`.
- Standard operator precedence: `*` and `/` bind tighter than `+` and `-`.
  So `2 + 3 * 4` is `14.0`, not `20.0`.
- Left-to-right associativity for operators of equal precedence.
  So `10 - 2 - 3` is `5.0`, and `8 / 4 / 2` is `1.0`.
- Parentheses for grouping, including nested parentheses.
  So `(2 + 3) * 4` is `20.0`.
- Unary minus applied to a number or a parenthesized group.
  So `-5` is `-5.0`, `2 * -3` is `-6.0`, and `-(2 + 3)` is `-5.0`.
- Integer and decimal number literals (e.g. `3`, `3.5`, `0.5`).
- Arbitrary whitespace between tokens, which is ignored.
- The return value is always a `float`.

## Error handling

- Division by zero must raise `ZeroDivisionError`.
- Any malformed expression must raise `ValueError`. This includes: an empty or
  whitespace-only string, a trailing operator (`"2 +"`), unbalanced parentheses
  (`"(2 + 3"`), unknown characters or operators (`"2 ** 3"`, `"abc"`), and a
  missing operator between operands (`"2 3"`).

## Constraints

- Pure standard library only. Do **not** use Python's built-in `eval`, `exec`,
  `compile`, `ast`, or any third-party parsing library — implement the parsing
  yourself.
- Do not change the function signature or the test files.

Run the tests with `pytest` from the fixture root.
