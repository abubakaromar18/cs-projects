"""Fail the release if the git tag doesn't match the version in pyproject.toml.

Usage: python scripts/check_version.py v1.2.3
"""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

SEMVER_TAG = re.compile(r"^v(\d+\.\d+\.\d+(?:[-.]?(?:a|b|rc)\d+)?)$")


def project_version(pyproject: Path) -> str:
    with pyproject.open("rb") as fh:
        return tomllib.load(fh)["project"]["version"]


def check(tag: str, version: str) -> str | None:
    """Return an error message, or None if ``tag`` is a valid tag for ``version``."""
    match = SEMVER_TAG.match(tag)
    if not match:
        return f"tag {tag!r} is not of the form vMAJOR.MINOR.PATCH"
    if match.group(1) != version:
        return f"tag {tag!r} does not match pyproject version {version!r}"
    return None


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    root = Path(__file__).resolve().parent.parent
    error = check(argv[1], project_version(root / "pyproject.toml"))
    if error:
        print(f"::error::{error}")  # GitHub Actions annotation syntax
        return 1
    print(f"tag {argv[1]} matches package version")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
