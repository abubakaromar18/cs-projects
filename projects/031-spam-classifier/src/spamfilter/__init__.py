"""spamfilter - a from-scratch multinomial Naive Bayes SMS spam classifier."""

from .dataset import Message, load_tsv, stratified_split, k_fold
from .metrics import Report, evaluate
from .model import NaiveBayes
from .text import tokenize

__all__ = [
    "Message", "load_tsv", "stratified_split", "k_fold",
    "Report", "evaluate", "NaiveBayes", "tokenize",
]
__version__ = "1.0.0"
