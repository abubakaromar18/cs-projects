from pathlib import Path

import pytest

from spamfilter import NaiveBayes, load_tsv

SAMPLE = Path(__file__).resolve().parents[1] / "data" / "sample_sms.tsv"


@pytest.fixture(scope="session")
def sample():
    return load_tsv(SAMPLE)


@pytest.fixture(scope="session")
def model(sample):
    return NaiveBayes().fit(sample)
