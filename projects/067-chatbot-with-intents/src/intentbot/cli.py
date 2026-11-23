"""Command-line interface: interactive chat, one-shot queries and evaluation."""

from __future__ import annotations

import argparse
import sys

from .bot import ChatBot, load_spec, training_examples
from .classifier import cross_validate


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="intentbot", description="Hybrid rule + Naive Bayes chatbot")
    p.add_argument("--intents", help="path to a custom intents.json")
    p.add_argument("--threshold", type=float, default=0.45, help="min classifier probability (default 0.45)")
    p.add_argument("--debug", action="store_true", help="show intent, source and confidence for each reply")
    p.add_argument("--eval", action="store_true", help="print k-fold cross-validated classifier accuracy and exit")
    p.add_argument("-k", type=int, default=5, help="folds for --eval (default 5)")
    p.add_argument("-m", "--message", action="append", help="send a message non-interactively (repeatable)")
    args = p.parse_args(argv)

    spec = load_spec(args.intents)

    if args.eval:
        examples = training_examples(spec)
        acc = cross_validate(examples, k=args.k, alpha=0.3)
        print(f"{len(examples)} examples, {len({lbl for _, lbl in examples})} classifier intents")
        print(f"{args.k}-fold cross-validated accuracy: {acc:.1%}")
        return 0

    bot = ChatBot(spec, threshold=args.threshold)

    def say(msg: str) -> str:
        reply = bot.respond(msg)
        line = f"bot> {reply.text}"
        if args.debug:
            line += f"   [{reply.intent} via {reply.source}, p={reply.confidence:.2f}]"
        print(line)
        return reply.intent

    if args.message:
        for msg in args.message:
            print(f"you> {msg}")
            say(msg)
        return 0

    print("IntentBot ready. Type 'bye' to leave.")
    while True:
        try:
            msg = input("you> ")
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if say(msg) == "goodbye":
            return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
