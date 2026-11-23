from intentbot.text import features, normalize, stem, tokenize


def test_normalize_expands_contractions_and_accents():
    assert normalize("What's UP, Café?") == "what is up, cafe?"


def test_contractions_only_replace_whole_words():
    assert normalize("shows") == "shows"
    assert normalize("hows it going") == "how is it going"


def test_stem_conflates_inflections():
    assert stem("jokes") == stem("joke") == stem("joking")
    assert stem("forecasts") == stem("forecast")
    assert stem("go") == "go"  # short words untouched


def test_tokenize_drops_stopwords_but_keeps_question_words():
    toks = tokenize("How are you doing today?")
    assert "how" in toks
    assert "are" not in toks and "you" not in toks


def test_features_include_bigrams_from_full_stream():
    f = features("thank you")
    assert "thank" in f
    assert "thank_you" in f
