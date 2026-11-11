"""Command-line interface.

    autocomplete train corpus.txt         # count words, add to the word store
    autocomplete suggest th -k 8          # ranked completions
    autocomplete repl                     # interactive; '+word' records a pick
    autocomplete --corpus data/sample.txt suggest pre   # in-memory, nothing saved
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TextIO

from .corpus import train
from .storage import load, save
from .trie import Trie

DEFAULT_DB = "words.trie.json"


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="autocomplete", description="Trie-based prefix search with frequency ranking.")
    p.add_argument("--db", default=DEFAULT_DB, help=f"word store (default: {DEFAULT_DB})")
    p.add_argument("--corpus", metavar="FILE", help="train an in-memory trie from FILE instead of using --db (read-only)")
    sub = p.add_subparsers(dest="cmd", required=True)

    t = sub.add_parser("train", help="count words in text files and add them")
    t.add_argument("files", nargs="+", type=Path)
    t.add_argument("--min-length", type=int, default=2, help="ignore shorter words (default 2)")

    a = sub.add_parser("add", help="add a word (or bump its frequency)")
    a.add_argument("word")
    a.add_argument("--freq", type=int, default=1)

    r = sub.add_parser("remove", help="delete a word")
    r.add_argument("word")

    s = sub.add_parser("suggest", help="top-k completions of a prefix")
    s.add_argument("prefix")
    s.add_argument("-k", type=int, default=5)

    ls = sub.add_parser("list", help="all words under a prefix, alphabetically")
    ls.add_argument("prefix", nargs="?", default="")

    sub.add_parser("stats", help="size of the store")
    rp = sub.add_parser("repl", help="interactive autocomplete prompt")
    rp.add_argument("-k", type=int, default=5)
    return p


def _print_suggestions(trie: Trie, prefix: str, k: int, out: TextIO) -> None:
    hits = trie.suggest(prefix, k)
    if not hits:
        print(f"  (no words start with {prefix!r})", file=out)
        return
    width = max(len(w) for w, _ in hits)
    for rank, (word, freq) in enumerate(hits, 1):
        print(f"  {rank}. {word:<{width}}  {freq}", file=out)


def repl(trie: Trie, k: int, inp: TextIO, out: TextIO) -> bool:
    """Run the prompt. Returns True if the trie was modified."""
    print("Type a prefix for suggestions. '+word' records a pick, "
          "'-word' removes, ':q' quits.", file=out)
    changed = False
    for raw in inp:
        line = raw.strip()
        if line in (":q", ":quit", ":exit"):
            break
        if not line:
            continue
        if line.startswith("+") and len(line) > 1:
            n = trie.insert(line[1:])
            changed = True
            print(f"  recorded {line[1:].lower()!r} (now {n})", file=out)
        elif line.startswith("-") and len(line) > 1:
            ok = trie.remove(line[1:])
            changed |= ok
            print(f"  {'removed' if ok else 'not found:'} {line[1:]!r}", file=out)
        else:
            lcp = trie.longest_common_prefix(line)
            if lcp != line.lower() and trie.has_prefix(line):
                print(f"  [tab → {lcp}]", file=out)
            _print_suggestions(trie, line, k, out)
    return changed


def main(argv: list[str] | None = None, *, stdin: TextIO | None = None, stdout: TextIO | None = None) -> int:
    stdin = stdin or sys.stdin
    out = stdout or sys.stdout
    args = _build_parser().parse_args(argv)

    try:
        if args.corpus:
            with open(args.corpus, encoding="utf-8") as f:
                trie = train(f, min_length=2)
            persist = False
        else:
            trie = load(args.db)
            persist = True
    except (OSError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    mutating = args.cmd in ("train", "add", "remove")
    if mutating and not persist:
        print("error: --corpus is read-only; use --db for train/add/remove", file=sys.stderr)
        return 2

    try:
        if args.cmd == "train":
            before = len(trie)
            for path in args.files:
                with path.open(encoding="utf-8") as f:
                    train(f, trie, min_length=args.min_length)
            print(f"trained on {len(args.files)} file(s): {len(trie) - before} new words, {len(trie)} total", file=out)
        elif args.cmd == "add":
            n = trie.insert(args.word, args.freq)
            print(f"{args.word.lower()}: {n}", file=out)
        elif args.cmd == "remove":
            if not trie.remove(args.word):
                print(f"not found: {args.word}", file=sys.stderr)
                return 1
            print(f"removed {args.word}", file=out)
        elif args.cmd == "suggest":
            _print_suggestions(trie, args.prefix, args.k, out)
        elif args.cmd == "list":
            for word, freq in trie.words_with_prefix(args.prefix):
                print(f"{word}\t{freq}", file=out)
        elif args.cmd == "stats":
            nodes = trie.node_count()
            chars = sum(len(w) for w in trie)
            print(f"words: {len(trie)}\nnodes: {nodes}\nchars stored: {chars}", file=out)
            if chars:
                print(f"prefix sharing: {1 - (nodes - 1) / chars:.1%} of characters saved", file=out)
        elif args.cmd == "repl":
            if repl(trie, args.k, stdin, out) and persist:
                save(trie, args.db)
            return 0
    except (OSError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    if mutating:
        save(trie, args.db)
    return 0
