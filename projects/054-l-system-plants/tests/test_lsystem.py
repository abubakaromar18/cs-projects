import math
import xml.etree.ElementTree as ET

import pytest

from lsystem import (PRESETS, GrammarError, LSystem, TurtleConfig, bounds,
                     interpret, parse_rules, to_svg)
from lsystem.cli import main


# ---------- grammar ----------

def test_algae_matches_fibonacci():
    # Lindenmayer's original algae system: lengths follow Fibonacci numbers.
    algae = LSystem("A", {"A": "AB", "B": "A"})
    assert algae.generate(4) == "ABAABABA"
    lengths = [len(algae.generate(n)) for n in range(10)]
    assert lengths == [1, 2, 3, 5, 8, 13, 21, 34, 55, 89]


def test_rewriting_is_parallel_not_sequential():
    # If rewriting were sequential, A->B then B->A would undo itself.
    swap = LSystem("AB", {"A": "B", "B": "A"})
    assert swap.generate(1) == "BA"


def test_symbols_without_rules_are_copied():
    assert LSystem("F+F", {"F": "FF"}).generate(1) == "FF+FF"


def test_zero_iterations_returns_axiom():
    assert LSystem("X", {"X": "F"}).generate(0) == "X"


def test_stochastic_is_reproducible_and_varies_with_seed():
    s = PRESETS["random-shrub"].lsystem()
    assert s.is_stochastic
    assert s.generate(4, seed=1) == s.generate(4, seed=1)
    outputs = {s.generate(4, seed=k) for k in range(10)}
    assert len(outputs) > 1


@pytest.mark.parametrize("axiom,rules", [
    ("", {}),
    ("F]", {}),
    ("F", {"F": "F[+F"}),
    ("F", {"FF": "F"}),
    ("F", {"F": [(0.0, "F")]}),
])
def test_invalid_grammars_rejected(axiom, rules):
    with pytest.raises(GrammarError):
        LSystem(axiom, rules)


def test_max_length_guard():
    with pytest.raises(GrammarError):
        LSystem("F", {"F": "FF"}).generate(30, max_length=1000)


def test_parse_rules():
    assert parse_rules(["F=FF", "X=F[+X]"]) == {"F": "FF", "X": "F[+X]"}
    stoch = parse_rules(["F=0.25:F+|0.75:F-"])
    assert stoch == {"F": [(0.25, "F+"), (0.75, "F-")]}
    with pytest.raises(GrammarError):
        parse_rules(["oops"])


# ---------- turtle ----------

def test_square_closes():
    segs = interpret("F+F+F+F", TurtleConfig(angle=90, step=1, start_heading=0))
    assert len(segs) == 4
    assert math.isclose(segs[-1].x2, 0, abs_tol=1e-9)
    assert math.isclose(segs[-1].y2, 0, abs_tol=1e-9)


def test_brackets_restore_position_and_track_depth():
    segs = interpret("F[+F]F", TurtleConfig(angle=90, step=1))
    trunk1, branch, trunk2 = segs
    assert branch.depth == 1 and trunk1.depth == trunk2.depth == 0
    # After ']' the turtle resumes at the top of the first trunk segment.
    assert (trunk2.x1, trunk2.y1) == pytest.approx((trunk1.x2, trunk1.y2))
    assert trunk2.y2 == pytest.approx(2.0)


def test_move_without_drawing_and_width_decay():
    segs = interpret("FfF!F", TurtleConfig(step=1, start_width=2, width_decay=0.5))
    assert len(segs) == 3
    assert segs[1].y1 == pytest.approx(2.0)
    assert segs[2].width == pytest.approx(1.0)


def test_unbalanced_pop_raises():
    with pytest.raises(ValueError):
        interpret("F]")


def test_bounds():
    segs = interpret("F", TurtleConfig(step=5))
    x0, y0, x1, y1 = bounds(segs)
    assert (y0, y1) == pytest.approx((0, 5))
    assert bounds([]) == (0, 0, 0, 0)


# ---------- render & presets ----------

@pytest.mark.parametrize("name", list(PRESETS))
def test_every_preset_renders_valid_svg(name):
    pr = PRESETS[name]
    segs = interpret(pr.lsystem().generate(min(pr.iterations, 4)), pr.turtle)
    assert segs
    root = ET.fromstring(to_svg(segs, size=400))
    lines = root.findall(".//{http://www.w3.org/2000/svg}line")
    assert len(lines) == len(segs)
    for ln in lines:
        for attr in ("x1", "y1", "x2", "y2"):
            assert -0.01 <= float(ln.get(attr)) <= 400.01


def test_plants_grow_upwards():
    pr = PRESETS["tree"]
    x0, y0, x1, y1 = bounds(interpret(pr.lsystem().generate(4), pr.turtle))
    assert y1 - y0 > 0 and y0 >= -1e-9


# ---------- CLI ----------

def test_cli_list(capsys):
    assert main(["--list"]) == 0
    assert "fern" in capsys.readouterr().out


def test_cli_writes_svg(tmp_path):
    out = tmp_path / "bush.svg"
    assert main(["bush", "-n", "2", "-o", str(out)]) == 0
    assert out.read_text().startswith("<svg")


def test_cli_custom_rules_stats(capsys):
    assert main(["--axiom", "F", "--rule", "F=F+F", "-n", "3", "--stats"]) == 0
    out = capsys.readouterr().out
    assert "length:     15" in out and "segments:   8" in out


def test_cli_errors():
    assert main([]) == 2
    assert main(["--axiom", "F", "--rule", "F=F["]) == 2
