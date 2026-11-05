# 031 · Spam Classifier

A multinomial **Naive Bayes** SMS spam filter written from scratch in pure
Python (standard library only). It handles the
[UCI SMS Spam Collection](https://archive.ics.uci.edu/dataset/228/sms+spam+collection)
format and comes with a small hand-written sample dataset so it runs offline.
It can train, evaluate, cross-validate, save and load models, and explain
each prediction.

```
$ spamfilter explain "Congratulations! Text WIN to 80086 to claim your FREE £500 prize"
P(spam) = 1.0000

token            log-ratio  (+ spam / - ham)
__caps__           +3.110  ++++++++++++
__money__          +2.704  +++++++++++
claim              +2.497  ++++++++++
prize              +1.878  ++++++++
win                +1.723  +++++++
free               +1.723  +++++++
congratulations    +1.318  +++++
text               +0.912  ++++
__num__            +0.912  ++++
```

## CS concepts

| Concept | Where |
|---|---|
| Bayes' rule & the conditional-independence ("naive") assumption | `model.py` |
| Multinomial event model: word counts per class | `NaiveBayes.partial_fit` |
| Laplace / additive smoothing for unseen words | `NaiveBayes.log_likelihood` |
| Log-space arithmetic and the **log-sum-exp** trick to avoid underflow | `predict_proba` |
| Feature engineering: normalising URLs, phone numbers, money and CAPS to shared tokens | `text.py` |
| Incremental (online) learning: training is only counting | `partial_fit` |
| Interpretability via per-token log-likelihood ratios | `explain`, `top_tokens` |
| Imbalanced-class evaluation: precision, recall, F1, confusion matrix | `metrics.py` |
| Stratified hold-out split and stratified k-fold cross-validation | `dataset.py` |
| Decision thresholds and asymmetric error costs | `--threshold` |

### The model in short

For tokens *w₁…wₙ*:

```
log P(c | w) = log P(c) + Σ log P(wᵢ | c) − log Z
P(w | c)     = (count(w, c) + α) / (total_words(c) + α·|V|)
```

The scores are normalised with log-sum-exp
(`Z = m + log Σ exp(sᶜ − m)`, where *m* is the largest score), so a message
with thousands of tokens still gives a finite probability. Tokens never seen
in training are skipped, since they would add the same constant to every class.

## Layout

```
031-spam-classifier/
├── data/sample_sms.tsv      85 hand-written messages (55 ham / 30 spam), UCI format
├── src/spamfilter/
│   ├── text.py              tokenizer + placeholder normalisation
│   ├── model.py             NaiveBayes (fit, predict_proba, explain, save/load)
│   ├── dataset.py           TSV loader, stratified split, k-fold
│   ├── metrics.py           confusion-matrix Report, evaluate()
│   └── cli.py               train / eval / cv / predict / explain / top
├── tests/                   pytest suite (39 tests)
├── pyproject.toml
└── Makefile
```

## Build, run, test

Requires Python ≥ 3.10. There are no runtime dependencies.

```bash
make test                     # python3 -m pytest
make demo                     # cross-validate, list top tokens, explain a message
make run ARGS="predict 'see you at lunch' 'URGENT! claim your £900 prize now'"

pip install -e '.[dev]'       # optional: installs the `spamfilter` command
spamfilter train -o model.json
spamfilter predict -m model.json "free entry to win cash, text WIN to 80086"
cat messages.txt | spamfilter predict -m model.json      # one message per line
spamfilter eval --test-ratio 0.3 --seed 7
spamfilter cv -k 10 --threshold 0.8
spamfilter top -n 15
```

### Using the full UCI dataset

```bash
make data         # downloads SMSSpamCollection (5,574 messages) into data/
make eval-full    # 10-fold CV on it
```

The downloaded file is git-ignored. Any file of `ham|spam<TAB>text` lines works
with `-d`.

## Example output (bundled sample, 5-fold CV)

```
fold 1: acc 0.882  prec 0.750  rec 1.000  f1 0.857
fold 2: acc 1.000  prec 1.000  rec 1.000  f1 1.000
fold 3: acc 1.000  prec 1.000  rec 1.000  f1 1.000
fold 4: acc 0.941  prec 0.857  rec 1.000  f1 0.923
fold 5: acc 0.824  prec 0.667  rec 1.000  f1 0.800

pooled over 5 folds:
accuracy  : 0.929
precision : 0.833
recall    : 1.000
f1        : 0.909

               predicted
               ham    spam
actual ham      49       6
actual spam      0      30
```

With only about 68 training messages per fold, the errors are easy to read.
"Leaving **now**, traffic looks okay" is flagged because *now* appears almost
only in spam. The class prior (spam is about 35% of this sample, compared with
about 13% in real SMS traffic) also pushes borderline messages towards spam.
More data fixes both. You can also raise `--threshold` to trade a little
recall for fewer false positives, which is usually the right trade for a spam
filter. The full UCI dataset could not be downloaded in the environment where
this project was built, so no full-dataset numbers are given here. Run
`make eval-full` to measure them yourself.

## Possible extensions

- Bigram features (`tokenize(..., bigrams=True)` exists; add a CLI flag) and character n-grams for obfuscations such as "fr33".
- A Bernoulli Naive Bayes variant and a comparison with the multinomial model.
- Complement Naive Bayes, or class-prior overrides for skewed data.
- A precision/recall curve over thresholds, with the cost-optimal threshold chosen automatically.
- TF-IDF weighting, or a from-scratch logistic regression baseline to compare against.
- A `feedback` command that calls `partial_fit` on corrected messages and re-saves the model.
