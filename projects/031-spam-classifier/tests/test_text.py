from spamfilter.text import tokenize


def test_lowercases_and_drops_stopwords():
    assert tokenize("The Cat and the hat") == ["cat", "hat"]


def test_placeholders():
    toks = tokenize("Win £500 now! Call 0800 555 0199 or visit http://x.example/claim")
    assert "__money__" in toks
    assert "__phone__" in toks
    assert "__url__" in toks
    assert "500" not in " ".join(toks)


def test_short_numbers_and_email():
    toks = tokenize("Text 80086 or mail prizes@win.example")
    assert "__num__" in toks and "__email__" in toks


def test_caps_counted():
    assert tokenize("URGENT FREE offer").count("__caps__") == 2
    assert "__caps__" not in tokenize("OK I am in")  # under 3 letters


def test_contractions_kept_together():
    assert "don't" in tokenize("I don't know")


def test_bigrams():
    toks = tokenize("claim cash prize", bigrams=True)
    assert "claim_cash" in toks and "cash_prize" in toks


def test_custom_stopwords():
    assert tokenize("the cat", stopwords=frozenset()) == ["the", "cat"]
