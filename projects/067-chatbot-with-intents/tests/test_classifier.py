import math

import pytest

from intentbot.classifier import NaiveBayesClassifier, cross_validate

DATA = [
    ("i love this movie", "pos"),
    ("what a great film", "pos"),
    ("great acting and story", "pos"),
    ("love it", "pos"),
    ("i hate this movie", "neg"),
    ("what a terrible film", "neg"),
    ("awful acting and story", "neg"),
    ("hate it", "neg"),
]


def test_predicts_obvious_cases():
    clf = NaiveBayesClassifier().fit(DATA)
    assert clf.predict("great love")[0] == "pos"
    assert clf.predict("terrible hate")[0] == "neg"


def test_probabilities_sum_to_one():
    clf = NaiveBayesClassifier().fit(DATA)
    probs = clf.predict_proba("great story but awful acting")
    assert math.isclose(sum(probs.values()), 1.0)
    assert set(probs) == {"pos", "neg"}


def test_log_score_matches_hand_computation():
    clf = NaiveBayesClassifier(alpha=1.0, featurizer=str.split).fit(
        [("a a b", "x"), ("b c", "y")]
    )
    # vocab {a,b,c}; x: a=2,b=1 total 3; y: b=1,c=1 total 2
    expected_x = math.log(0.5) + math.log((2 + 1) / (3 + 3))
    expected_y = math.log(0.5) + math.log((0 + 1) / (2 + 3))
    scores = clf.log_scores("a")
    assert math.isclose(scores["x"], expected_x)
    assert math.isclose(scores["y"], expected_y)


def test_unknown_words_fall_back_to_prior():
    clf = NaiveBayesClassifier(featurizer=str.split).fit([("a", "x"), ("b", "x"), ("c", "y")])
    probs = clf.predict_proba("zzz")
    assert math.isclose(probs["x"], 2 / 3)
    assert clf.known_fraction("zzz") == 0.0
    assert clf.known_fraction("a zzz") == 0.5


def test_long_input_does_not_underflow():
    clf = NaiveBayesClassifier().fit(DATA)
    label, p = clf.predict("great " * 2000)
    assert label == "pos" and 0 < p <= 1


def test_untrained_raises():
    with pytest.raises(RuntimeError):
        NaiveBayesClassifier().predict("hi")


def test_invalid_alpha():
    with pytest.raises(ValueError):
        NaiveBayesClassifier(alpha=0)


def test_round_trip_serialisation(tmp_path):
    clf = NaiveBayesClassifier(alpha=0.5).fit(DATA)
    path = tmp_path / "model.json"
    clf.save(path)
    loaded = NaiveBayesClassifier.load(path)
    for text in ("great film", "awful story", "unknown words here"):
        assert loaded.predict_proba(text) == pytest.approx(clf.predict_proba(text))


def test_incremental_fit():
    clf = NaiveBayesClassifier().fit(DATA[:4]).fit(DATA[4:])
    assert clf.classes == ["neg", "pos"]


def test_cross_validate_on_separable_data():
    assert cross_validate(DATA, k=4) >= 0.75
    with pytest.raises(ValueError):
        cross_validate(DATA, k=1)
