import pytest

from pebble import PebbleSyntaxError, parse
from pebble import ast


def test_nested_blocks_build_a_tree():
    prog = parse("1 [ { 2 } ]")
    push, loop = prog.body
    assert isinstance(push, ast.Push) and push.value == 1
    assert isinstance(loop, ast.While)
    (cond,) = loop.body
    assert isinstance(cond, ast.If)
    assert cond.body[0].value == 2


def test_definitions_are_collected_and_hoisted():
    prog = parse("F (F 1)")
    assert [type(n) for n in prog.body] == [ast.Call]
    assert set(prog.words) == {"F"}


def test_dump_outline():
    out = ast.dump(parse('1 [ "x" , ]').body)
    assert out.splitlines() == ["Push 1", "While", "  PushString 'x'", "  Op ,"]


@pytest.mark.parametrize(
    "src, fragment",
    [
        ("[ 1", "never closed"),
        ("{ 1", "never closed"),
        ("(F 1", "never closed"),
        ("1 ]", "nothing to close"),
        ("}", "nothing to close"),
        ("[ (F 1) ]", "only allowed at top level"),
        ("(F 1) (F 2)", "defined twice"),
        ("G", "undefined word G"),
        ("(F G)", "undefined word G"),
    ],
)
def test_parse_errors(src, fragment):
    with pytest.raises(PebbleSyntaxError, match=fragment):
        parse(src)


def test_error_reports_position():
    with pytest.raises(PebbleSyntaxError) as exc:
        parse("1\n  [ 2")
    assert (exc.value.line, exc.value.col) == (2, 3)
