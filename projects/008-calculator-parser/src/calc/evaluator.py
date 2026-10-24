"""Tree-walking evaluator.

`Evaluator` holds the variable environment, so a REPL can keep state across
lines (`x = 3`, then `x * 2`). Evaluation is a post-order traversal: children
first, then the operator at the node.
"""

from __future__ import annotations

import math
from typing import Callable

from .ast import Assign, BinaryOp, Call, Factorial, Name, Node, Number, UnaryOp
from .errors import EvalError
from .parser import parse

# name -> (function, min_args, max_args); max_args None means variadic.
Builtin = tuple[Callable[..., float], int, int | None]

BUILTINS: dict[str, Builtin] = {
    "sqrt": (math.sqrt, 1, 1),
    "abs": (abs, 1, 1),
    "sin": (math.sin, 1, 1),
    "cos": (math.cos, 1, 1),
    "tan": (math.tan, 1, 1),
    "asin": (math.asin, 1, 1),
    "acos": (math.acos, 1, 1),
    "atan": (math.atan, 1, 1),
    "ln": (math.log, 1, 1),
    "log": (lambda x, base=10.0: math.log(x, base), 1, 2),
    "exp": (math.exp, 1, 1),
    "floor": (math.floor, 1, 1),
    "ceil": (math.ceil, 1, 1),
    "round": (lambda x, nd=0: round(x, int(nd)), 1, 2),
    "min": (min, 1, None),
    "max": (max, 1, None),
}

CONSTANTS: dict[str, float] = {"pi": math.pi, "e": math.e, "tau": math.tau}

# The REPL stores the last result here, like many desk calculators.
LAST = "ans"


class Evaluator:
    def __init__(self) -> None:
        self.variables: dict[str, float] = {}

    def evaluate(self, source: str) -> float:
        """Parse and evaluate one line; remembers the result as `ans`."""
        tree = parse(source)
        try:
            result = self.eval_node(tree)
        except RecursionError:
            # Long left-associative chains (1+1+1+...) build a deep tree even
            # though the parser handles them with a loop.
            raise EvalError("expression too long to evaluate", 0) from None
        self.variables[LAST] = result
        return result

    def eval_node(self, node: Node) -> float:
        match node:
            case Number(value=v):
                return v

            case Name(ident=name, pos=pos):
                if name in self.variables:
                    return self.variables[name]
                if name in CONSTANTS:
                    return CONSTANTS[name]
                if name in BUILTINS:
                    raise EvalError(f"{name!r} is a function; call it like {name}(x)", pos)
                raise EvalError(f"undefined variable {name!r}", pos)

            case UnaryOp(op=op, operand=x):
                v = self.eval_node(x)
                return -v if op == "-" else v

            case BinaryOp(op=op, left=l, right=r, pos=pos):
                return self._binary(op, self.eval_node(l), self.eval_node(r), pos)

            case Factorial(operand=x, pos=pos):
                v = self.eval_node(x)
                if v < 0 or not float(v).is_integer():
                    raise EvalError("factorial needs a non-negative integer", pos)
                if v > 170:  # 171! overflows a float
                    raise EvalError("factorial argument too large", pos)
                return float(math.factorial(int(v)))

            case Call(func=name, args=args, pos=pos):
                return self._call(name, [self.eval_node(a) for a in args], pos)

            case Assign(target=name, value=value, pos=pos):
                if name in CONSTANTS or name in BUILTINS:
                    raise EvalError(f"cannot assign to built-in {name!r}", pos)
                v = self.eval_node(value)
                self.variables[name] = v
                return v

        raise TypeError(f"unknown node {node!r}")

    @staticmethod
    def _binary(op: str, a: float, b: float, pos: int) -> float:
        try:
            if op == "+":
                return a + b
            if op == "-":
                return a - b
            if op == "*":
                return a * b
            if op == "/":
                return a / b
            if op == "//":
                return float(a // b)
            if op == "%":
                return a % b
            if op == "^":
                result = a ** b
                if isinstance(result, complex):
                    raise EvalError("result is not a real number", pos)
                return float(result)
        except ZeroDivisionError:
            raise EvalError("division by zero", pos) from None
        except OverflowError:
            raise EvalError("number too large", pos) from None
        raise EvalError(f"unknown operator {op!r}", pos)

    @staticmethod
    def _call(name: str, args: list[float], pos: int) -> float:
        if name not in BUILTINS:
            raise EvalError(f"unknown function {name!r}", pos)
        fn, lo, hi = BUILTINS[name]
        if len(args) < lo or (hi is not None and len(args) > hi):
            want = str(lo) if lo == hi else f"{lo}+" if hi is None else f"{lo}-{hi}"
            raise EvalError(f"{name}() takes {want} argument(s), got {len(args)}", pos)
        try:
            return float(fn(*args))
        except (ValueError, OverflowError) as exc:
            raise EvalError(f"{name}(): {exc}", pos) from None


def evaluate(source: str) -> float:
    """Evaluate a single expression with a fresh environment."""
    return Evaluator().evaluate(source)


def format_number(v: float) -> str:
    """Show whole numbers without a trailing .0 and trim float noise."""
    if math.isfinite(v) and v.is_integer() and abs(v) < 1e16:
        return str(int(v))
    return f"{v:.12g}"
