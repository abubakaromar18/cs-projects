import pytest

from spamfilter import Message, Report, evaluate


def test_report_math():
    r = Report(tp=8, fp=2, tn=85, fn=5)
    assert r.total == 100
    assert r.accuracy == pytest.approx(0.93)
    assert r.precision == pytest.approx(0.8)
    assert r.recall == pytest.approx(8 / 13)
    assert r.f1 == pytest.approx(2 * 0.8 * (8 / 13) / (0.8 + 8 / 13))


def test_empty_report_is_safe():
    r = Report()
    assert (r.accuracy, r.precision, r.recall, r.f1) == (0, 0, 0, 0)


def test_add():
    assert Report(1, 2, 3, 4) + Report(1, 1, 1, 1) == Report(2, 3, 4, 5)


class Always:
    def __init__(self, label): self.label = label
    def predict(self, text, threshold=0.5): return self.label


def test_evaluate_counts():
    data = [Message("spam", "a"), Message("ham", "b"), Message("ham", "c")]
    assert evaluate(Always("ham"), data) == Report(tp=0, fp=0, tn=2, fn=1)
    assert evaluate(Always("spam"), data) == Report(tp=1, fp=2, tn=0, fn=0)


def test_format_contains_matrix():
    assert "actual spam" in Report(1, 0, 1, 0).format()
