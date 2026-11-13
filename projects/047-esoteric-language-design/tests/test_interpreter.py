import io

import pytest

from pebble import Interpreter, PebbleRuntimeError, run_source


def stack_after(src, stdin=""):
    interp = Interpreter(stdout=io.StringIO(), stdin=io.StringIO(stdin), max_steps=100_000)
    interp.run(src)
    return interp.stack


@pytest.mark.parametrize(
    "src, expected",
    [
        ("7 3 +", [10]),
        ("7 3 -", [4]),
        ("7 3 *", [21]),
        ("7 2 /", [3]),
        ("0 7 - 2 /", [-4]),   # floor division
        ("7 3 %", [1]),
        ("3 3 =", [1]),
        ("2 3 <", [1]),
        ("2 3 >", [0]),
        ("0 !", [1]),
        ("5 !", [0]),
    ],
)
def test_arithmetic_and_comparison(src, expected):
    assert stack_after(src) == expected


@pytest.mark.parametrize(
    "src, expected",
    [
        ("1 :", [1, 1]),
        ("1 2 $", [1]),
        ("1 2 \\", [2, 1]),
        ("1 2 3 @", [2, 3, 1]),
        ("1 2 ^", [1, 2, 1]),
    ],
)
def test_stack_shuffles(src, expected):
    assert stack_after(src) == expected


def test_big_integers_do_not_overflow():
    assert stack_after("2 2 * : * : * : * : * : *") == [2**64]


def test_string_layout_is_zero_terminated_first_char_on_top():
    assert stack_after('"ab"') == [0, ord("b"), ord("a")]


def test_registers_default_to_zero_and_store_pops():
    assert stack_after("q 42 ~q q q") == [0, 42, 42]


def test_while_peeks_and_if_pops():
    assert stack_after("3 [ 1 - ]") == [0]
    assert stack_after("9 1 { 5 } 0 { 6 }") == [9, 5]


def test_output_ops():
    assert run_source("72 , 105 , 32, 42 .") == "Hi 42"


def test_read_char_and_eof():
    assert stack_after("? ? ?", stdin="ab") == [97, 98, -1]


def test_read_number_skips_whitespace_and_handles_negative():
    assert stack_after("& & &", stdin="  12\n-7 ") == [12, -7, -1]


def test_read_number_rejects_garbage():
    with pytest.raises(PebbleRuntimeError, match="expected a number"):
        stack_after("&", stdin="xyz")


def test_words_and_recursion():
    # countdown printer: C ( n -- ) prints n..1
    src = "(C : { : . 32, 1 - C 0 } $) 5 C"
    assert run_source(src) == "5 4 3 2 1 "


def test_forward_call_before_definition():
    assert run_source("D (D 9 .)") == "9"


@pytest.mark.parametrize(
    "src, fragment",
    [
        ("+", "stack underflow"),
        ("1 +", "needs 2"),
        ("1 0 /", "division by zero"),
        ("1 0 %", "modulo by zero"),
        ("[ ]", "empty stack"),
        ("0 1 - ,", "not a valid character"),
        ("(R R) R", "call depth limit"),
        ("1 [ ]", "step limit"),
    ],
)
def test_runtime_errors(src, fragment):
    with pytest.raises(PebbleRuntimeError, match=fragment):
        stack_after(src)


def test_runtime_error_has_position():
    with pytest.raises(PebbleRuntimeError) as exc:
        stack_after("1 2\n 3 / 0 /")
    assert (exc.value.line, exc.value.col) == (2, 8)


def test_interpreter_state_persists_across_runs():
    interp = Interpreter(stdout=io.StringIO(), stdin=io.StringIO())
    interp.run("(A 1 +) 5 ~x")
    interp.run("x A")
    assert interp.stack == [6]
