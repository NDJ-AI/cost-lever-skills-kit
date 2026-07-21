"""Test suite for the arithmetic expression evaluator.

This is the objective scorer's ground truth: a config's output "passes" when
`pytest` exits 0 against this file. Do not edit as part of the task.
"""

import pytest

from calc.evaluator import evaluate


# --- Basic arithmetic --------------------------------------------------------

def test_single_number():
    assert evaluate("42") == 42.0


def test_decimal_number():
    assert evaluate("3.5") == 3.5


def test_simple_addition():
    assert evaluate("2 + 3") == 5.0


def test_simple_subtraction():
    assert evaluate("10 - 4") == 6.0


def test_simple_multiplication():
    assert evaluate("6 * 7") == 42.0


def test_division_returns_float():
    assert evaluate("7 / 2") == 3.5


def test_return_type_is_float():
    assert isinstance(evaluate("2 + 2"), float)


# --- Precedence --------------------------------------------------------------

def test_multiplication_before_addition():
    assert evaluate("2 + 3 * 4") == 14.0


def test_addition_then_multiplication():
    assert evaluate("3 * 4 + 2") == 14.0


def test_division_before_subtraction():
    assert evaluate("20 - 8 / 4") == 18.0


# --- Associativity (left-to-right) -------------------------------------------

def test_left_associative_subtraction():
    assert evaluate("10 - 2 - 3") == 5.0


def test_left_associative_division():
    assert evaluate("8 / 4 / 2") == 1.0


# --- Parentheses -------------------------------------------------------------

def test_parentheses_override_precedence():
    assert evaluate("(2 + 3) * 4") == 20.0


def test_nested_parentheses():
    assert evaluate("((1 + 2) * (3 + 4))") == 21.0


def test_parentheses_deeply_nested():
    assert evaluate("2 * (3 + (4 - 1))") == 12.0


# --- Unary minus -------------------------------------------------------------

def test_unary_minus_number():
    assert evaluate("-5") == -5.0


def test_unary_minus_after_operator():
    assert evaluate("2 * -3") == -6.0


def test_subtract_negative():
    assert evaluate("3 - -2") == 5.0


def test_unary_minus_on_group():
    assert evaluate("-(2 + 3)") == -5.0


def test_unary_minus_in_expression():
    assert evaluate("10 + -4 * 2") == 2.0


# --- Whitespace --------------------------------------------------------------

def test_no_whitespace():
    assert evaluate("2+3*4") == 14.0


def test_extra_whitespace():
    assert evaluate("   2   +    3   ") == 5.0


# --- Mixed / integration -----------------------------------------------------

def test_complex_expression():
    assert evaluate("3 + 4 * 2 / (1 - 5)") == pytest.approx(1.0)


def test_all_operators():
    assert evaluate("2 * 3 + 8 / 4 - 1") == 7.0


def test_fractional_result():
    assert evaluate("1 / 3") == pytest.approx(1 / 3)


# --- Error handling ----------------------------------------------------------

def test_division_by_zero():
    with pytest.raises(ZeroDivisionError):
        evaluate("1 / 0")


def test_division_by_zero_in_subexpression():
    with pytest.raises(ZeroDivisionError):
        evaluate("5 / (3 - 3)")


def test_empty_string_raises():
    with pytest.raises(ValueError):
        evaluate("")


def test_whitespace_only_raises():
    with pytest.raises(ValueError):
        evaluate("   ")


def test_trailing_operator_raises():
    with pytest.raises(ValueError):
        evaluate("2 +")


def test_leading_binary_operator_raises():
    with pytest.raises(ValueError):
        evaluate("* 5")


def test_unbalanced_open_paren_raises():
    with pytest.raises(ValueError):
        evaluate("(2 + 3")


def test_unbalanced_close_paren_raises():
    with pytest.raises(ValueError):
        evaluate("2 + 3)")


def test_unknown_operator_raises():
    with pytest.raises(ValueError):
        evaluate("2 ** 3")


def test_unknown_characters_raise():
    with pytest.raises(ValueError):
        evaluate("abc")


def test_missing_operator_raises():
    with pytest.raises(ValueError):
        evaluate("2 3")
