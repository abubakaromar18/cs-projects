import pytest

from spamfilter.dataset import Message, k_fold, parse_lines, stratified_split


def test_parse_lines_ok():
    msgs = parse_lines(["ham\thello there\n", "\n", "SPAM\tfree stuff\r\n"])
    assert msgs == [Message("ham", "hello there"), Message("spam", "free stuff")]


@pytest.mark.parametrize("bad", ["eggs\thello", "no tab here"])
def test_parse_lines_bad(bad):
    with pytest.raises(ValueError, match="line 1"):
        parse_lines([bad])


def test_sample_loads(sample):
    assert len(sample) == 85
    assert sum(m.label == "spam" for m in sample) == 30


def test_stratified_split_preserves_ratio(sample):
    train, test = stratified_split(sample, 0.2, seed=1)
    assert len(train) + len(test) == len(sample)
    assert sum(m.label == "spam" for m in test) == 6     # 20% of 30
    assert sum(m.label == "ham" for m in test) == 11     # 20% of 55
    assert not set(train) & set(test)


def test_split_is_deterministic(sample):
    assert stratified_split(sample, seed=3) == stratified_split(sample, seed=3)


def test_split_bad_ratio(sample):
    with pytest.raises(ValueError):
        stratified_split(sample, 1.0)


def test_k_fold_partitions(sample):
    seen = []
    for train, test in k_fold(sample, 5):
        assert len(train) + len(test) == len(sample)
        assert any(m.label == "spam" for m in test)
        seen.extend(test)
    assert sorted(seen, key=repr) == sorted(sample, key=repr)


def test_k_fold_bad_k(sample):
    with pytest.raises(ValueError):
        list(k_fold(sample, 1))
