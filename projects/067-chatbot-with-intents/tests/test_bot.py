from datetime import datetime

import pytest

from intentbot.bot import ChatBot, load_spec, training_examples
from intentbot.classifier import cross_validate
from intentbot.cli import main


@pytest.fixture
def bot():
    return ChatBot(seed=0, clock=lambda: datetime(2026, 1, 1, 9, 5))


@pytest.mark.parametrize(
    "text,intent",
    [
        ("hello there", "greeting"),
        ("hi", "greeting"),
        ("thank you so much", "thanks"),
        ("can you tell me a joke", "joke"),
        ("is it going to snow", "weather"),
        ("who made you", "bot_identity"),
        ("what are you able to do", "capabilities"),
        ("how are you doing today", "how_are_you"),
    ],
)
def test_classifier_routes_paraphrases(bot, text, intent):
    reply = bot.respond(text)
    assert reply.intent == intent
    assert reply.source == "classifier"


def test_rules_take_precedence(bot):
    reply = bot.respond("what is 12 * 4")
    assert (reply.intent, reply.source, reply.confidence) == ("math", "rule", 1.0)
    assert reply.text == "12 * 4 = 48"


def test_math_errors_are_reported(bot):
    assert "division by zero" in bot.respond("10 / 0").text


def test_float_results_are_tidied(bot):
    assert bot.respond("calculate 1 / 4").text.endswith("= 0.25")
    assert bot.respond("4 / 2").text.endswith("= 2")


def test_time_uses_injected_clock(bot):
    assert bot.respond("what time is it?").text == "It's 09:05."


def test_name_memory_across_turns(bot):
    assert "don't know your name" in bot.respond("what's my name").text
    assert bot.respond("call me grace").text == "Nice to meet you, Grace!"
    assert bot.respond("do you know my name").text == "You're Grace."
    assert "Grace" in bot.respond("hello").text


def test_gibberish_falls_back(bot):
    reply = bot.respond("flurble quantum zxqv")
    assert reply.intent == "fallback"


def test_empty_message(bot):
    assert bot.respond("   ").intent == "fallback"


def test_rule_only_intents_are_not_trained():
    labels = {lbl for _, lbl in training_examples(load_spec())}
    assert "math" not in labels and "set_name" not in labels


def test_bundled_dataset_quality_bar():
    # Guards against edits to intents.json quietly making the model worse.
    assert cross_validate(training_examples(load_spec()), k=5, alpha=0.3) >= 0.75


def test_custom_spec():
    spec = {
        "intents": {
            "order": {"examples": ["i want pizza", "order a pizza", "get me food"], "responses": ["Ordering!"]},
            "cancel": {"examples": ["cancel my order", "stop the order", "never mind"], "responses": ["Cancelled."]},
        }
    }
    b = ChatBot(spec, seed=1)
    assert b.respond("please order pizza").text == "Ordering!"
    assert b.respond("cancel it").text == "Cancelled."


def test_cli_one_shot(capsys):
    assert main(["-m", "my name is Omar", "-m", "bye", "--debug"]) == 0
    out = capsys.readouterr().out
    assert "Nice to meet you, Omar!" in out
    assert "[goodbye via rule" in out


def test_cli_eval(capsys):
    assert main(["--eval"]) == 0
    assert "cross-validated accuracy" in capsys.readouterr().out
