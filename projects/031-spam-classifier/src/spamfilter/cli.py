"""Command-line interface: ``spamfilter {train,eval,cv,predict,explain,top}``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .dataset import k_fold, load_tsv, stratified_split
from .metrics import Report, evaluate
from .model import NaiveBayes

DEFAULT_DATA = Path(__file__).resolve().parents[2] / "data" / "sample_sms.tsv"


def _data_arg(p: argparse.ArgumentParser) -> None:
    p.add_argument("-d", "--data", default=str(DEFAULT_DATA),
                   help="TSV file of 'ham|spam<TAB>text' lines (default: bundled sample)")


def _model_or_train(args) -> NaiveBayes:
    if args.model:
        return NaiveBayes.load(args.model)
    return NaiveBayes(alpha=args.alpha).fit(load_tsv(args.data))


def cmd_train(args) -> int:
    data = load_tsv(args.data)
    model = NaiveBayes(alpha=args.alpha).fit(data)
    model.save(args.out)
    print(f"trained on {len(data)} messages "
          f"({model.class_docs['spam']} spam, {model.class_docs['ham']} ham), "
          f"vocabulary {len(model.vocab)} -> {args.out}")
    return 0


def cmd_eval(args) -> int:
    train, test = stratified_split(load_tsv(args.data), args.test_ratio, args.seed)
    model = NaiveBayes(alpha=args.alpha).fit(train)
    print(f"train {len(train)} / test {len(test)}  (alpha={args.alpha}, threshold={args.threshold})")
    print(evaluate(model, test, args.threshold).format())
    return 0


def cmd_cv(args) -> int:
    data = load_tsv(args.data)
    total = Report()
    for i, (train, test) in enumerate(k_fold(data, args.k, args.seed), 1):
        r = evaluate(NaiveBayes(alpha=args.alpha).fit(train), test, args.threshold)
        total = total + r
        print(f"fold {i}: acc {r.accuracy:.3f}  prec {r.precision:.3f}  "
              f"rec {r.recall:.3f}  f1 {r.f1:.3f}")
    print(f"\npooled over {args.k} folds:\n{total.format()}")
    return 0


def cmd_predict(args) -> int:
    model = _model_or_train(args)
    texts = args.text or [line.rstrip("\n") for line in sys.stdin if line.strip()]
    for text in texts:
        p = model.predict_proba(text)["spam"]
        label = "spam" if p >= args.threshold else "ham"
        print(f"{label:4s}  {p:6.3f}  {text}")
    return 0


def cmd_explain(args) -> int:
    model = _model_or_train(args)
    p = model.predict_proba(args.text)["spam"]
    print(f"P(spam) = {p:.4f}\n\ntoken            log-ratio  (+ spam / - ham)")
    for tok, w in model.explain(args.text):
        bar = ("+" if w > 0 else "-") * min(20, round(abs(w) * 4))
        print(f"{tok:16s} {w:+8.3f}  {bar}")
    return 0


def cmd_top(args) -> int:
    model = _model_or_train(args)
    for c, o in (("spam", "ham"), ("ham", "spam")):
        print(f"most {c}-indicative tokens:")
        for t, w in model.top_tokens(c, o, args.n):
            print(f"  {t:16s} {w:+.3f}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="spamfilter",
                                 description="Naive Bayes SMS spam classifier")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p, model=False):
        _data_arg(p)
        p.add_argument("-a", "--alpha", type=float, default=1.0, help="Laplace smoothing (default 1)")
        p.add_argument("-t", "--threshold", type=float, default=0.5,
                       help="P(spam) needed to label spam (default 0.5)")
        if model:
            p.add_argument("-m", "--model", help="saved model JSON (otherwise train on --data)")

    p = sub.add_parser("train", help="train and save a model")
    common(p); p.add_argument("-o", "--out", default="model.json"); p.set_defaults(fn=cmd_train)

    p = sub.add_parser("eval", help="hold-out evaluation")
    common(p)
    p.add_argument("--test-ratio", type=float, default=0.25)
    p.add_argument("--seed", type=int, default=0)
    p.set_defaults(fn=cmd_eval)

    p = sub.add_parser("cv", help="stratified k-fold cross-validation")
    common(p)
    p.add_argument("-k", type=int, default=5)
    p.add_argument("--seed", type=int, default=0)
    p.set_defaults(fn=cmd_cv)

    p = sub.add_parser("predict", help="classify messages (args or stdin)")
    common(p, model=True); p.add_argument("text", nargs="*"); p.set_defaults(fn=cmd_predict)

    p = sub.add_parser("explain", help="show which tokens drove a prediction")
    common(p, model=True); p.add_argument("text"); p.set_defaults(fn=cmd_explain)

    p = sub.add_parser("top", help="most indicative tokens per class")
    common(p, model=True); p.add_argument("-n", type=int, default=10); p.set_defaults(fn=cmd_top)
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.fn(args)
    except (OSError, ValueError, RuntimeError) as e:
        print(f"spamfilter: error: {e}", file=sys.stderr)
        return 1
