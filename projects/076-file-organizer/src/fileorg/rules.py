"""Classification rules: map a file extension to a category folder name."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

# Category -> extensions (lowercase, without the dot).
DEFAULT_RULES: dict[str, list[str]] = {
    "Images": ["jpg", "jpeg", "png", "gif", "bmp", "svg", "webp", "heic", "tiff", "ico"],
    "Documents": ["pdf", "doc", "docx", "odt", "rtf", "txt", "md", "tex", "epub"],
    "Spreadsheets": ["xls", "xlsx", "ods", "csv", "tsv"],
    "Presentations": ["ppt", "pptx", "odp", "key"],
    "Audio": ["mp3", "wav", "flac", "aac", "ogg", "m4a"],
    "Video": ["mp4", "mkv", "mov", "avi", "webm", "wmv"],
    "Archives": ["zip", "tar", "gz", "tgz", "bz2", "xz", "7z", "rar"],
    "Code": ["py", "js", "ts", "java", "c", "h", "cpp", "go", "rs", "rb", "sh", "html", "css", "json", "yaml", "yml", "toml"],
    "Installers": ["exe", "msi", "dmg", "pkg", "deb", "rpm", "apk"],
}

OTHER = "Other"

# Multi-part extensions that should be recognised as a whole.
COMPOUND_EXTENSIONS = ("tar.gz", "tar.bz2", "tar.xz")


def extension_of(name: str) -> str:
    """Return the lowercase extension of ``name`` without the leading dot.

    Compound extensions like ``.tar.gz`` are returned whole. Dotfiles such as
    ``.bashrc`` have no extension.
    """
    lower = name.lower()
    for compound in COMPOUND_EXTENSIONS:
        if lower.endswith("." + compound) and len(lower) > len(compound) + 1:
            return compound
    stem, dot, ext = lower.rpartition(".")
    if not dot or not stem:  # no dot at all, or a dotfile like ".bashrc"
        return ""
    return ext


@dataclass
class Rules:
    """An inverted index from extension to category for O(1) lookup."""

    categories: Mapping[str, list[str]] = field(default_factory=lambda: DEFAULT_RULES)
    fallback: str = OTHER

    def __post_init__(self) -> None:
        self._index: dict[str, str] = {}
        for category, exts in self.categories.items():
            for ext in exts:
                key = ext.lower().lstrip(".")
                if key in self._index and self._index[key] != category:
                    raise ValueError(
                        f"extension '.{key}' is listed under both "
                        f"'{self._index[key]}' and '{category}'"
                    )
                self._index[key] = category

    def classify(self, name: str) -> str:
        ext = extension_of(name)
        if ext in self._index:
            return self._index[ext]
        # A compound like "tar.gz" may only be configured as "gz".
        if "." in ext:
            last = ext.rsplit(".", 1)[1]
            if last in self._index:
                return self._index[last]
        return self.fallback

    @property
    def folder_names(self) -> set[str]:
        return set(self.categories) | {self.fallback}


def load_rules(path: str | Path | None) -> Rules:
    """Load rules from a JSON file, or return the defaults when ``path`` is None.

    The file maps category names to lists of extensions, e.g.
    ``{"Photos": ["jpg", "png"], "Books": ["epub"]}``. An optional
    ``"_fallback"`` key renames the catch-all folder.
    """
    if path is None:
        return Rules()
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("rules file must contain a JSON object")
    fallback = data.pop("_fallback", OTHER)
    for category, exts in data.items():
        if not isinstance(exts, list) or not all(isinstance(e, str) for e in exts):
            raise ValueError(f"category '{category}' must map to a list of strings")
    return Rules(categories=data, fallback=fallback)
