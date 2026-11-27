# File Organizer

A command-line tool that sorts a messy folder (think `~/Downloads`) into tidy
sub-folders by **file type**, by **modification date**, or both. Every run can
be previewed with `--dry-run` and reversed with `fileorg undo`.

```
Downloads/                     Downloads/
├── photo.JPG                  ├── Archives/archive.zip
├── notes.txt         ──►      ├── Audio/song.mp3
├── report.pdf                 ├── Code/script.py
├── song.mp3                   ├── Documents/notes.txt
├── script.py                  ├── Documents/report.pdf
├── archive.zip                ├── Images/photo.JPG
└── mystery.xyz                └── Other/mystery.xyz
```

## Features

- Three grouping modes: `type` (`Images/`), `date` (`2026/11/`), `type-date` (`Images/2026/11/`)
- Dry run that prints the exact plan the real run would execute
- Undo journal (`.fileorg-journal.json`) — undo the latest run, then the one before, and so on
- Never overwrites: name clashes become `photo (1).JPG`, `photo (2).JPG`, …
- Recursive mode that flattens nested folders and removes the empty ones it leaves behind
- Idempotent: running it twice does nothing the second time
- Custom categories from a JSON rules file
- Skips hidden files (unless `--include-hidden`) and symlinks
- No third-party dependencies

## CS concepts demonstrated

| Concept | Where |
| --- | --- |
| **Separating pure logic from side effects** — planning is a pure function of the directory listing; only the executor touches disk. That is why dry run can be trusted. | `planner.py` vs `executor.py` |
| **Inverted index / hash lookup** — category→extensions config is inverted into an extension→category dict for O(1) classification, with conflict detection. | `rules.Rules` |
| **Iterative tree traversal** — explicit stack instead of recursion, sorted for determinism, with pruning of destination folders. | `planner._iter_files` |
| **Write-ahead journaling** — each move is recorded right after it succeeds, and the journal is written atomically (temp file + rename), so an interrupted run can still be undone. | `executor.apply_plan` |
| **Inverse operations / undo stack** — the journal is a stack of runs; undo pops the latest and replays its moves in reverse. Moves that cannot be reversed stay on the stack. | `executor.undo` |
| **Collision resolution** — deterministic suffixing that accounts for both existing files and destinations already claimed earlier in the same plan. | `planner.unique_name` |
| **Idempotence and TOCTOU safety** — re-checks destinations at execution time, so a file created after planning is never clobbered. | `executor.apply_plan` |

## Project layout

```
076-file-organizer/
├── pyproject.toml
├── Makefile
├── src/fileorg/
│   ├── rules.py      # extension parsing + classification
│   ├── planner.py    # directory walk → list of Move(src, dst)
│   ├── executor.py   # perform moves, journal, undo
│   └── cli.py        # argparse front end
└── tests/            # pytest suite (35 tests)
```

## Build, run, test

Requires Python 3.10+.

```bash
make install            # pip install -e ".[dev]"
make test               # python -m pytest
make demo               # builds a throwaway folder in /tmp and dry-runs it

# without installing:
PYTHONPATH=src python -m fileorg organize ~/Downloads --dry-run
```

## Usage

```bash
fileorg organize DIR [--by type|date|type-date] [--dry-run] [--recursive]
                     [--include-hidden] [--rules FILE] [--quiet]
fileorg undo DIR
```

Example session:

```
$ fileorg organize ~/Downloads --dry-run
  archive.zip  ->  Archives/archive.zip
  mystery.xyz  ->  Other/mystery.xyz
  notes.txt  ->  Documents/notes.txt
  photo.JPG  ->  Images/photo.JPG
  report.pdf  ->  Documents/report.pdf
  script.py  ->  Code/script.py
  song.mp3  ->  Audio/song.mp3
Dry run: would move 7 file(s) (Archives: 1, Audio: 1, Code: 1, Documents: 2, Images: 1, Other: 1).

$ fileorg organize ~/Downloads -q
Moved 7 file(s) (Archives: 1, Audio: 1, Code: 1, Documents: 2, Images: 1, Other: 1).
Undo with: fileorg undo /home/me/Downloads

$ fileorg undo ~/Downloads
Restored 7 file(s).
```

### Custom rules

```json
{
  "Photos": ["jpg", "jpeg", "png", "heic"],
  "Books": ["epub", "mobi", "pdf"],
  "_fallback": "Misc"
}
```

```bash
fileorg organize ~/Downloads --rules my-rules.json
```

An extension may only belong to one category; the loader rejects duplicates.

## Test results

```
$ python -m pytest
...................................                                      [100%]
35 passed
```

Tests cover extension parsing (including `.tar.gz` and dotfiles), every mode,
collision numbering, recursion and pruning, determinism, symlink skipping,
dry-run purity, undo of multiple runs, and the never-overwrite guarantees.

## Possible extensions

- Use EXIF "date taken" for photos instead of file mtime
- Detect type by content (magic bytes) rather than extension
- Duplicate detection by hashing file contents
- Watch mode that organizes new files as they arrive (`watchdog`)
- Glob/regex rules (e.g. `Screenshot*` → `Screenshots/`) with priorities
- A TOML config file and per-folder rule overrides
