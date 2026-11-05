import math

import pytest

from spamfilter import Message, NaiveBayes

TOY = [
    Message("spam", "free money"),
    Message("spam", "free prize"),
    Message("ham", "lunch money"),
]


def ident(text):
    return text.split()


def test_hand_computed_probabilities():
    nb = NaiveBayes(alpha=1, tokenizer=ident).fit(TOY)
    # vocab = {free, money, prize, lunch} -> |V| = 4
    assert nb.vocab == {"free", "money", "prize", "lunch"}
    assert math.isclose(nb.log_likelihood("free", "spam"), math.log((2 + 1) / (4 + 4)))
    assert math.isclose(nb.log_likelihood("free", "ham"), math.log((0 + 1) / (2 + 4)))
    # P(spam|"free") ∝ 2/3 * 3/8 = 1/4 ; P(ham|"free") ∝ 1/3 * 1/6 = 1/18
    p = nb.predict_proba("free")
    assert math.isclose(p["spam"], (1 / 4) / (1 / 4 + 1 / 18))
    assert math.isclose(sum(p.values()), 1.0)


def test_unknown_tokens_fall_back_to_prior():
    nb = NaiveBayes(tokenizer=ident).fit(TOY)
    assert math.isclose(nb.predict_proba("zzz qqq")["spam"], 2 / 3)


def test_long_input_does_not_underflow():
    nb = NaiveBayes(tokenizer=ident).fit(TOY)
    p = nb.predict_proba("free " * 5000)
    assert p["spam"] == pytest.approx(1.0) and not math.isnan(p["ham"])


def test_threshold_shifts_decision():
    nb = NaiveBayes(tokenizer=ident).fit(TOY)
    p = nb.predict_proba("money")["spam"]
    assert nb.predict("money", threshold=p - 0.01) == "spam"
    assert nb.predict("money", threshold=p + 0.01) == "ham"


def test_partial_fit_equals_fit():
    a = NaiveBayes(tokenizer=ident).fit(TOY)
    b = NaiveBayes(tokenizer=ident).fit(TOY[:1]).partial_fit(TOY[1:])
    assert a.to_dict() == b.to_dict()


def test_refit_resets_state():
    nb = NaiveBayes(tokenizer=ident).fit(TOY)
    nb.fit(TOY)
    assert nb.class_docs["spam"] == 2


def test_unfitted_raises():
    with pytest.raises(RuntimeError):
        NaiveBayes().predict("hi")
    with pytest.raises(RuntimeError):
        NaiveBayes().fit([Message("ham", "only one class")]).predict("hi")


def test_bad_alpha():
    with pytest.raises(ValueError):
        NaiveBayes(alpha=0)


def test_save_load_roundtrip(tmp_path, model):
    path = tmp_path / "m.json"
    model.save(path)
    loaded = NaiveBayes.load(path)
    for text in ["free prize call now", "see you at lunch"]:
        assert loaded.predict_proba(text) == pytest.approx(model.predict_proba(text))


def test_load_rejects_other_json(tmp_path):
    p = tmp_path / "x.json"
    p.write_text('{"hello": 1}')
    with pytest.raises(ValueError):
        NaiveBayes.load(p)


def test_explain_signs(model):
    contrib = dict(model.explain("claim your free prize, see you at lunch"))
    assert contrib["claim"] > 0 and contrib["prize"] > 0
    assert contrib["lunch"] < 0


def test_top_tokens(model):
    spam_top = [t for t, _ in model.top_tokens("spam", "ham", 15)]
    assert "claim" in spam_top and "__money__" in spam_top


def test_classifies_obvious_examples(model):
    assert model.predict("URGENT! You have won a £1000 cash prize, call 09061234567 to claim") == "spam"
    assert model.predict("are you coming to dinner tonight? running late") == "ham"
