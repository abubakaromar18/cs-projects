# 067 · Chatbot With Intents

A small conversational bot that routes every message through a **hybrid
pipeline**: precise regex rules first, a from-scratch **Multinomial Naive
Bayes** intent classifier second, and an honest "I didn't understand"
fallback when neither is confident. Pure Python standard library, no
ML dependencies.

```
message ──► RuleEngine ──match──► intent + slots (confidence 1.0)
               │ no match
               ▼
        NaiveBayesClassifier ──p ≥ threshold & words known──► intent
               │ otherwise
               ▼
            fallback
```

## Key CS concepts

| Concept | Where |
|---|---|
| Multinomial Naive Bayes with Laplace smoothing, log-space scoring | `classifier.py` |
| Numerically stable softmax (subtract the max before `exp`) | `NaiveBayesClassifier.predict_proba` |
| Stratified k-fold cross-validation | `cross_validate` |
| Text normalisation, suffix-stripping stemming, unigram + bigram features | `text.py` |
| Regex rules with priorities and named-group slot extraction | `rules.py` |
| Safe expression evaluation by walking a whitelisted AST (no `eval`) | `calc.py` |
| Out-of-vocabulary detection to avoid confident nonsense | `known_fraction` |
| Dialogue state (remembering the user's name across turns) | `bot.Context` |
| Data-driven design: intents, examples, responses and rules live in JSON | `data/intents.json` |

### Why hybrid?

Rules are perfectly precise and can pull structured data out of a message
(`my name is (?P<name>\w+)`), but nobody can write a rule for every way of
saying "tell me a joke". A statistical classifier generalises to unseen
phrasings but can't extract slots and will happily pick *some* winner for
gibberish. Combining the two, plus a confidence threshold and a
"how many of these words have I ever seen?" check, gives you the strengths
of both.

Intents marked `"rule_only": true` (math, set_name) need slots, so the
classifier is never trained on them.

## Project layout

```
src/intentbot/
  text.py         normalise / tokenise / stem / features
  classifier.py   Naive Bayes + cross-validation + JSON persistence
  rules.py        Rule and RuleEngine
  calc.py         AST-based safe arithmetic
  bot.py          ChatBot: routing, handlers, templates, context
  cli.py          REPL, one-shot (-m) and --eval modes
  data/intents.json
tests/            52 pytest tests
```

## Build, run, test

Requires Python 3.10+.

```bash
make install        # pip install -e ".[dev]"
make test           # python -m pytest
make run            # interactive chat
make eval           # cross-validated accuracy of the bundled dataset
```

Without installing:

```bash
PYTHONPATH=src python -m intentbot --debug
PYTHONPATH=src python -m intentbot -m "hi" -m "what is 3 * 7"
PYTHONPATH=src python -m intentbot --intents my_intents.json
```

## Example session (`--debug`)

```
you> hi
bot> Hello! How can I help?   [greeting via classifier, p=0.74]
you> my name is omar
bot> Nice to meet you, Omar!   [set_name via rule, p=1.00]
you> what is 3 * (4 + 2)
bot> 3 * (4 + 2) = 18   [math via rule, p=1.00]
you> make me laugh
bot> There are 10 kinds of people: those who understand binary and those who don't.   [joke via classifier, p=0.99]
you> whats my name
bot> You're Omar.   [ask_my_name via classifier, p=1.00]
you> is it raining outside
bot> I don't have live weather data, but a window is a great sensor!   [weather via classifier, p=1.00]
you> flibber quantum
bot> Sorry, I didn't catch that. Try asking 'what can you do?'   [fallback via fallback, p=0.12]
you> 1/0
bot> I couldn't compute that: division by zero.   [math via rule, p=1.00]
you> bye
bot> See you later, Omar!   [goodbye via rule, p=1.00]
```

```
$ make eval
195 examples, 10 classifier intents
5-fold cross-validated accuracy: 82.1%
```

## Writing your own intents

```json
{
  "rules": [{"intent": "order", "pattern": "\\border (?P<item>\\w+)", "priority": 5}],
  "intents": {
    "order":  {"examples": ["i want pizza", "get me food"], "responses": ["Ordering {item}!"]},
    "cancel": {"examples": ["cancel my order", "never mind"], "responses": ["Cancelled."]}
  }
}
```

Response templates can use any rule slot plus `{name}` and `{name_suffix}`.
Note that a template referencing a slot (like `{item}`) needs that slot to
exist, so either mark such intents `rule_only` or avoid slot placeholders.

## Possible extensions

- Replace Naive Bayes with logistic regression or a TF-IDF + cosine nearest-neighbour baseline and compare via `--eval`.
- Add a confusion-matrix report to `--eval` to see which intents get mixed up.
- Fuzzy matching (Levenshtein) to tolerate typos like "jok" or "wether".
- Multi-turn flows: a slot-filling state machine ("Which city?" → "Chicago").
- Active learning: log fallback messages so they can be labelled and added as examples.
- A tiny web UI over the same `ChatBot` class.
