# 043 · Trie Autocomplete

Prefix search with frequency ranking. Train a trie on any text, then ask it for
the most popular completions of a prefix — the core of a search-box or
keyboard autocomplete. Pure Python, no dependencies.

## What it does

- Stores words with frequencies in a **prefix tree** (case-insensitive by default).
- `suggest(prefix, k)` returns the top-k completions, by frequency then alphabetically.
- Trains from text files (tokenizer handles apostrophes, hyphens, Unicode letters).
- Insert, remove (with branch pruning), list by prefix, tab-style longest-common-prefix.
- Persists to JSON with atomic writes; an interactive REPL learns from your picks.

## CS concepts

| Concept | Where |
|---|---|
| Trie / prefix tree — O(m) lookup for a prefix of length m | `trie.py` `_find` |
| Subtree aggregates: each node caches `best`, the max frequency below it | `_Node.best`, `insert`, `remove` |
| Best-first (branch-and-bound) search with a heap for top-k | `Trie.suggest` |
| Maintaining aggregates under deletion (bottom-up recompute + pruning) | `Trie.remove` |
| Iterative DFS producing lexicographic order | `words_with_prefix` |
| Property testing against a brute-force oracle | `tests/test_trie.py` |
| Atomic file replacement (`mkstemp` + `os.replace`) | `storage.py` |

**Why the `best` cache?** A naive top-k collects *every* word under the prefix
and sorts — O(n log n) for a short prefix like `"t"`. With `best` cached, the
search pushes subtrees onto a max-heap keyed by their best frequency. When a
finished word reaches the top of the heap, nothing left can beat it, so the
search stops after k words while only expanding the branches that matter.

## Layout

```
src/trie_autocomplete/
  trie.py      # Trie and node, ranking search
  corpus.py    # tokenizer + training from text
  storage.py   # JSON save/load
  cli.py       # argparse CLI and REPL
tests/         # pytest suite (31 tests)
data/sample.txt
```

## Build, run, test

```bash
make dev                      # pip install -e '.[dev]'
make test                     # python -m pytest
make demo                     # REPL over the sample corpus
make run ARGS="--corpus data/sample.txt suggest th -k 6"
```

After `make install`, the `autocomplete` command is on your PATH:

```bash
autocomplete train notes/*.txt          # builds words.trie.json
autocomplete suggest pro -k 5
autocomplete add kubernetes --freq 10
autocomplete remove teh
autocomplete list tra
autocomplete stats
autocomplete repl                       # '+word' records a pick, '-word' removes, ':q' quits
```

`--db PATH` chooses the store (default `words.trie.json`); `--corpus FILE`
builds a throwaway in-memory trie instead (read-only).

## Example output

```
$ autocomplete --corpus data/sample.txt suggest th -k 6
  1. the    20
  2. that   2
  3. they   2
  4. think  2
  5. th     1
  6. them   1

$ autocomplete --corpus data/sample.txt stats
words: 123
nodes: 412
chars stored: 702
prefix sharing: 41.5% of characters saved

$ autocomplete repl
> transp
  [tab → transport]
  ...
> +transport
  recorded 'transport' (now 3)
```

### As a library

```python
from trie_autocomplete import Trie, train

t = Trie()
t.insert("the", 50); t.insert("this", 20); t.insert("that", 20)
t.suggest("th", 2)            # [('the', 50), ('that', 20)]
t.longest_common_prefix("t")  # 'th'

with open("book.txt") as f:
    big = train(f)
```

## Possible extensions

- Fuzzy matching: suggest within edit distance 1–2 (Levenshtein automaton over the trie).
- Radix / Patricia tree to compress single-child chains and cut node count.
- Per-node cached top-k lists for O(m) query time at the cost of memory.
- Recency decay (exponentially weighted frequencies) so recent picks rank higher.
- Phrase / next-word suggestions from bigram counts.
- A tiny HTTP endpoint or web UI with debounced keystroke queries.
