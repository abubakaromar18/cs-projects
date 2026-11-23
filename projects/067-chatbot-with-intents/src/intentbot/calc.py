"""A safe arithmetic evaluator for the "math" intent.

Never call eval() on user input. Instead parse with Python's ast module
and walk only the node types we explicitly allow.
"""

from __future__ import annotations

import ast
import operator

_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}

MAX_EXPONENT = 100  # stops "9**9**9" from eating the CPU


class CalcError(ValueError):
    pass


def evaluate(expr: str) -> float | int:
    expr = expr.replace("^", "**").replace("x", "*").replace("×", "*").replace("÷", "/")
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as e:
        raise CalcError(f"can't parse {expr!r}") from e
    return _eval(tree.body)


def _eval(node: ast.AST) -> float | int:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        return node.value
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
        return _UNARY[type(node.op)](_eval(node.operand))
    if isinstance(node, ast.BinOp) and type(node.op) in _BINOPS:
        left, right = _eval(node.left), _eval(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > MAX_EXPONENT:
            raise CalcError("exponent too large")
        try:
            return _BINOPS[type(node.op)](left, right)
        except ZeroDivisionError as e:
            raise CalcError("division by zero") from e
    raise CalcError(f"unsupported expression element: {type(node).__name__}")
