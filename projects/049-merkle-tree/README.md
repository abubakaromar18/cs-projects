# 049 · Merkle Tree

A dependency-free Go implementation of a **Merkle (hash) tree** with
**inclusion proofs** and verification, plus a small CLI. A Merkle tree lets you
commit to an ordered set of data blocks with a single fixed-size *root* hash,
then later prove that a specific block belonged to that set by revealing only
`O(log n)` sibling hashes — never the whole data set.

This is the structure behind Git's object model, Certificate Transparency
logs, blockchains, and peer-to-peer file transfer. It is a **defensive /
educational** project: it builds and verifies tamper-evidence, and targets
nothing but local input.

```
$ printf 'alpha\nbravo\ncharlie\ndelta\n' | ./bin/merkle root
d1e4...  (the 32-byte SHA-256 root, as hex)

$ printf 'alpha\nbravo\ncharlie\ndelta\n' > data.txt
$ ./bin/merkle verify -i 2 -root <that-hex> data.txt
OK: block is included in the committed root

$ sed 's/charlie/CHARLIE/' data.txt | ./bin/merkle verify -i 2 -root <that-hex>
FAIL: block does not match the root
```

## What it does

Each **line** of the input file (or stdin) is one data block.

- `merkle root [file]` — print the Merkle root as hex.
- `merkle prove -i N [file]` — print a JSON inclusion proof for line `N`
  (0-based); the root is echoed on stderr.
- `merkle verify -i N -root HEX [file]` — recompute the root from the block at
  line `N` and its proof, and report whether it matches `HEX`. A proof file can
  be supplied with `-proof`; otherwise it is recomputed from the input.

## Key CS concepts it demonstrates

- **Merkle / hash trees.** Parents are the hash of their children, so the root
  is a compact commitment to every leaf. Changing, reordering, adding or
  removing any block changes the root.
- **Logarithmic inclusion proofs.** Proving membership needs only the sibling
  hash at each level — `⌈log₂ n⌉` hashes — not the whole set. `Verify` needs
  just the block, the proof, and the trusted root.
- **Domain separation for second-preimage resistance.** Leaves are hashed with
  a `0x00` prefix and interior nodes with `0x01`, following RFC 6962
  (Certificate Transparency). Without this, an attacker could pass an interior
  node off as a leaf.
- **The duplicate-leaf pitfall.** Odd nodes are *promoted* unchanged rather
  than duplicated, avoiding the CVE-2012-2459 ambiguity where two different
  leaf sets hash to the same root.
- **Pluggable hashing & dependency injection.** The hash function is an
  injected `func() hash.Hash` (defaulting to SHA-256), and the CLI's `run` is
  split from `main` so tests drive it with in-memory streams.

## Build, run, test

Requires Go 1.22+.

```
make build      # compiles to ./bin/merkle
make test       # runs all tests
make cover      # per-function coverage report
make vet        # go vet
make run ARGS="root data.txt"
```

The `internal/merkle` package has 100% statement coverage, including trees of
every size from 1 to 17 leaves (exercising the odd-node promotion path).

## Example: a proof

```
$ printf 'a\nb\nc\nd\n' | ./bin/merkle prove -i 0
{
  "index": 0,
  "steps": [
    { "hash": "<H(leaf b)>",        "right": true },
    { "hash": "<H(interior c,d)>",  "right": true }
  ]
}
```

`right: true` means the sibling is on the right, so the running hash is the
left operand at that level. Verification folds the block up the tree:
`leaf(a) → interior(·, Hb) → interior(·, Hcd)` and checks it equals the root.

## Possible extensions

- **Merkle audit between two roots** (consistency proofs), as CT logs use to
  prove an append-only log was never rewritten.
- **Sparse Merkle trees** for key/value commitments with non-membership
  proofs.
- A **streaming builder** that hashes blocks as they arrive instead of holding
  every leaf in memory.
- Swap SHA-256 for BLAKE3 or SHA-3 via the existing `HashFunc` seam and
  benchmark.
