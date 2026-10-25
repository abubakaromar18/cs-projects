"""Command-line interface.

The password is read with :func:`getpass.getpass` (no echo) or from stdin, so
it never appears in shell history or ``ps`` output. Passing it as an argument
is intentionally not supported.
"""

from __future__ import annotations

import argparse
import getpass
import json
import sys
from pathlib import Path

from .breach import pwned_count
from .scoring import Result, check

BAR = ("█" * 1, "█" * 2, "█" * 3, "█" * 4, "█" * 5)


def render(r: Result) -> str:
    d = r.to_dict()
    lines = [
        f"Strength : {BAR[r.score]:<5} {r.score}/4 ({r.label})",
        f"Length   : {r.length}",
        f"Entropy  : {d['effective_entropy_bits']} bits effective "
        f"(naive charset estimate: {d['naive_entropy_bits']} bits)",
        f"Crack    : {d['crack_time_online']} online (100/s), "
        f"{d['crack_time_offline']} offline (10^10/s)",
        f"Breached : {'YES' if r.breached else 'not found'}"
        + (f" (seen {r.pwned_count:,} times in HIBP)" if r.pwned_count else ""),
    ]
    if r.entropy.matches:
        lines.append("Patterns : " + ", ".join(f"{m.kind} '{m.token}'" for m in r.entropy.matches))
    for tip in r.feedback:
        lines.append(f"  - {tip}")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="pwcheck", description=__doc__.splitlines()[0])
    p.add_argument("--stdin", action="store_true",
                   help="read one password per line from stdin instead of prompting")
    p.add_argument("--breach-list", type=Path,
                   help="extra breach list (plaintext or SHA-1 hex, one per line)")
    p.add_argument("--online", action="store_true",
                   help="also query Have I Been Pwned via k-anonymity (sends 5 hash chars only)")
    p.add_argument("--json", action="store_true", help="emit JSON")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.stdin:
        passwords = [line.rstrip("\n") for line in sys.stdin if line.rstrip("\n")]
    else:
        passwords = [getpass.getpass("Password: ")]

    worst = 4
    for pw in passwords:
        count = None
        if args.online:
            try:
                count = pwned_count(pw)
            except OSError as exc:
                print(f"warning: HIBP lookup failed: {exc}", file=sys.stderr)
        result = check(pw, args.breach_list, count)
        worst = min(worst, result.score)
        print(json.dumps(result.to_dict()) if args.json else render(result))
        if not args.json and len(passwords) > 1:
            print()
    # Non-zero exit if anything scored below "strong" — handy in scripts.
    return 0 if worst >= 3 else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
