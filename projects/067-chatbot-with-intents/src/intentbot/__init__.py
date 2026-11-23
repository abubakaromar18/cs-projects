"""IntentBot: a hybrid rule-based + Naive Bayes intent chatbot."""

from .bot import ChatBot, Reply
from .classifier import NaiveBayesClassifier, cross_validate
from .rules import Rule, RuleEngine

__all__ = ["ChatBot", "Reply", "NaiveBayesClassifier", "cross_validate", "Rule", "RuleEngine"]
__version__ = "1.0.0"
