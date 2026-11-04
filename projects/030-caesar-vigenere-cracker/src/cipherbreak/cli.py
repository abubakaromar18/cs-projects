"""Command-line interface.

    cipherbreak encrypt  caesar   -k 3      "attack at dawn"
    cipherbreak decrypt  vigenere -k LEMON  -f secret.txt
    cipherbreak analyze  -f secret.txt
    cipherbreak crack-caesar   -f secret.txt --top 3
    cipherbreak crack-vigenere -f secret.txt --explain
"""

from __future__ import annotations

import argparse
import sys

from . import ciphers
from .crack import crack_caesar, crack_vigenere
from .stats import (ENGLISH_IOC, ENGLISH_PROB, RANDOM_IOC, chi_squared, friedman_estimate,
                    index_of_coincidence, letter_counts)


def _read_text(args: argparse.Namespace) -> str:
    if args.file:
        with open(args.file, encoding="utf-8") as fh:
            return fh.read()
    if args.text is not None:
        return args.text
    return sys.stdin.read()


def _add_input(p: argparse.ArgumentParser) -> None:
    p.add_argument("text", nargs="?", help="input text (default: stdin)")
    p.add_argument("-f", "--file", help="read input from a file")


def _transform(args: argparse.Namespace, encrypt: bool) -> str:
    text = _read_text(args)
    if args.cipher == "caesar":
        try:
            shift = int(args.key)
        except ValueError:
            raise SystemExit("caesar key must be an integer shift") from None
        return ciphers.caesar_encrypt(text, shift) if encrypt else ciphers.caesar_decrypt(text, shift)
    fn = ciphers.vigenere_encrypt if encrypt else ciphers.vigenere_decrypt
    try:
        return fn(text, args.key)
    except ValueError as e:
        raise SystemExit(str(e)) from None


def _bar(value: float, scale: float, width: int = 30) -> str:
    return "#" * max(0, round(value / scale * width)) if scale else ""


def cmd_analyze(args: argparse.Namespace) -> None:
    text = _read_text(args)
    counts = letter_counts(text)
    n = sum(counts.values())
    if n == 0:
        raise SystemExit("no letters to analyze")
    top = max(counts.values()) / n
    print(f"letters: {n}")
    print(f"index of coincidence: {index_of_coincidence(text):.4f} "
          f"(English ~{ENGLISH_IOC:.4f}, random ~{RANDOM_IOC:.4f})")
    print(f"chi-squared vs English: {chi_squared(text):.1f}")
    print(f"Friedman key-length estimate: {friedman_estimate(text):.1f}\n")
    print("ltr  observed  english")
    for ch, c in counts.items():
        obs = c / n
        print(f" {ch}   {obs * 100:5.1f}%   {ENGLISH_PROB[ch] * 100:5.1f}%  {_bar(obs, top)}")


def cmd_crack_caesar(args: argparse.Namespace) -> None:
    for c in crack_caesar(_read_text(args))[: args.top]:
        if args.top > 1:
            print(f"--- shift {c.shift:2d}  chi2 {c.chi2:8.1f}")
        print(c.plaintext.rstrip("\n"))


def cmd_crack_vigenere(args: argparse.Namespace) -> None:
    res = crack_vigenere(_read_text(args), max_key_len=args.max_key_len, key_len=args.key_len)
    if args.explain:
        print("key length  mean column IoC   kasiski hits")
        for k, ioc in sorted(res.key_length_ranking)[: args.max_key_len]:
            mark = " <-" if k == len(res.key) else ""
            print(f"   {k:3d}        {ioc:.4f}  {_bar(ioc, ENGLISH_IOC, 20):20s} {res.kasiski.get(k, 0):4d}{mark}")
        print()
    print(f"key: {res.key}")
    if not res.looks_english:
        print("warning: result does not look like English; try --key-len or more ciphertext",
              file=sys.stderr)
    print(res.plaintext.rstrip("\n"))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="cipherbreak", description="Classical ciphers and frequency-analysis crackers")
    sub = p.add_subparsers(dest="cmd", required=True)

    for name, encrypt in (("encrypt", True), ("decrypt", False)):
        sp = sub.add_parser(name, help=f"{name} with a known key")
        sp.add_argument("cipher", choices=["caesar", "vigenere"])
        sp.add_argument("-k", "--key", required=True, help="integer shift (caesar) or keyword (vigenere)")
        _add_input(sp)
        sp.set_defaults(func=lambda a, e=encrypt: print(_transform(a, e), end="" if a.file or a.text is None else "\n"))

    sp = sub.add_parser("analyze", help="letter frequencies, IoC and chi-squared")
    _add_input(sp)
    sp.set_defaults(func=cmd_analyze)

    sp = sub.add_parser("crack-caesar", help="brute-force all 26 shifts, ranked by chi-squared")
    _add_input(sp)
    sp.add_argument("--top", type=int, default=1, help="show the N best candidates")
    sp.set_defaults(func=cmd_crack_caesar)

    sp = sub.add_parser("crack-vigenere", help="recover a Vigenere key via IoC + Kasiski + chi-squared")
    _add_input(sp)
    sp.add_argument("--max-key-len", type=int, default=20)
    sp.add_argument("--key-len", type=int, help="skip key-length estimation")
    sp.add_argument("--explain", action="store_true", help="show the key-length analysis table")
    sp.set_defaults(func=cmd_crack_vigenere)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    args.func(args)
    return 0
