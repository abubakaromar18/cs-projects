"""A calculator built on a hand-written lexer and recursive descent parser."""

from .errors import CalcError, EvalError, LexError, ParseError
from .evaluator import Evaluator, evaluate
from .parser import parse

__all__ = ["CalcError", "EvalError", "LexError", "ParseError", "Evaluator", "evaluate", "parse"]
__version__ = "1.0.0"
