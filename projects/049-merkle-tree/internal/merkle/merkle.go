// Package merkle implements a binary Merkle (hash) tree over an ordered list
// of data blocks, with inclusion proofs and verification.
//
// A Merkle tree lets you commit to a sequence of blocks with a single
// fixed-size "root" hash, then later prove that a specific block really
// belonged to that commitment by revealing only O(log n) sibling hashes —
// never the whole data set. This is the structure behind Git's object model,
// Certificate Transparency logs, blockchains and peer-to-peer file transfer.
//
// Design notes:
//
//   - Leaves and internal nodes are domain-separated with distinct prefix
//     bytes (0x00 for leaves, 0x01 for interior). Without this a second
//     preimage attack is possible: an attacker could present an internal node
//     pair as if it were a leaf. This is the same fix RFC 6962 (Certificate
//     Transparency) uses.
//   - When a level has an odd number of nodes, the last node is promoted
//     unchanged to the next level (it is not duplicated). Duplicating the last
//     node — as early Bitcoin did — enables the CVE-2012-2459 duplicate-leaf
//     ambiguity, where two different leaf sets yield the same root.
//   - The hash function is pluggable; it defaults to SHA-256.
package merkle

import (
	"bytes"
	"crypto/sha256"
	"errors"
	"hash"
)

// Prefix bytes used for domain separation (see package docs).
const (
	leafPrefix     = 0x00
	interiorPrefix = 0x01
)

// HashFunc returns a fresh hash.Hash. Callers may supply any collision
// resistant function; the zero value of a Tree uses SHA-256.
type HashFunc func() hash.Hash

// Tree is an immutable Merkle tree built from a fixed set of leaves.
type Tree struct {
	newHash HashFunc
	// levels[0] holds the leaf hashes; each subsequent level holds the parent
	// hashes, up to levels[len-1] which holds the single root.
	levels [][][]byte
}

// New builds a Merkle tree over blocks. An empty input yields a tree whose
// root is the hash of the empty string (a well-defined commitment to "no
// data"). The hash function defaults to SHA-256 when fn is nil.
func New(blocks [][]byte, fn HashFunc) *Tree {
	if fn == nil {
		fn = sha256.New
	}
	t := &Tree{newHash: fn}

	leaves := make([][]byte, len(blocks))
	for i, b := range blocks {
		leaves[i] = t.hashLeaf(b)
	}
	if len(leaves) == 0 {
		// Commit to emptiness with H() of no data.
		leaves = [][]byte{t.hashEmpty()}
	}
	t.levels = append(t.levels, leaves)

	for len(t.levels[len(t.levels)-1]) > 1 {
		cur := t.levels[len(t.levels)-1]
		next := make([][]byte, 0, (len(cur)+1)/2)
		for i := 0; i < len(cur); i += 2 {
			if i+1 == len(cur) {
				// Odd node out: promote it unchanged (no duplication).
				next = append(next, cur[i])
				continue
			}
			next = append(next, t.hashInterior(cur[i], cur[i+1]))
		}
		t.levels = append(t.levels, next)
	}
	return t
}

// Root returns a copy of the tree's root hash.
func (t *Tree) Root() []byte {
	top := t.levels[len(t.levels)-1]
	return append([]byte(nil), top[0]...)
}

// Len reports the number of leaves (data blocks) in the tree. For an
// empty-input tree this is 0, even though an empty-commitment leaf exists
// internally.
func (t *Tree) Len() int {
	// Distinguish the real-leaf case from the empty-commitment sentinel.
	if len(t.levels[0]) == 1 && bytes.Equal(t.levels[0][0], t.hashEmpty()) {
		return 0
	}
	return len(t.levels[0])
}

// ProofStep is one sibling hash on the path from a leaf to the root, together
// with which side the sibling sits on.
type ProofStep struct {
	Hash  []byte
	Right bool // true if Hash is the right sibling (our running hash is left)
}

// Proof is an ordered inclusion path, leaf-to-root.
type Proof struct {
	Index int
	Steps []ProofStep
}

// ErrIndexRange is returned when a leaf index is out of bounds.
var ErrIndexRange = errors.New("merkle: leaf index out of range")

// Prove returns an inclusion proof for the leaf at index.
func (t *Tree) Prove(index int) (Proof, error) {
	if index < 0 || index >= t.Len() {
		return Proof{}, ErrIndexRange
	}
	p := Proof{Index: index}
	idx := index
	for level := 0; level < len(t.levels)-1; level++ {
		nodes := t.levels[level]
		if idx%2 == 0 {
			// We are the left child; sibling is to the right, if it exists.
			if idx+1 < len(nodes) {
				p.Steps = append(p.Steps, ProofStep{
					Hash:  append([]byte(nil), nodes[idx+1]...),
					Right: true,
				})
			}
			// else: promoted odd node, no sibling at this level.
		} else {
			// We are the right child; sibling is to the left.
			p.Steps = append(p.Steps, ProofStep{
				Hash:  append([]byte(nil), nodes[idx-1]...),
				Right: false,
			})
		}
		idx /= 2
	}
	return p, nil
}

// Verify recomputes the root from a data block and its proof and reports
// whether it matches root. It reconstructs the leaf hash itself, so a caller
// verifying a proof needs only the block, the proof and the trusted root —
// never the rest of the tree. fn must match the function used to build the
// tree (nil means SHA-256).
func Verify(root, block []byte, p Proof, fn HashFunc) bool {
	if fn == nil {
		fn = sha256.New
	}
	h := &hasher{fn: fn}
	running := h.leaf(block)
	for _, step := range p.Steps {
		if step.Right {
			running = h.interior(running, step.Hash)
		} else {
			running = h.interior(step.Hash, running)
		}
	}
	return bytes.Equal(running, root)
}

// --- internal hashing helpers -------------------------------------------

type hasher struct{ fn HashFunc }

func (h *hasher) leaf(data []byte) []byte {
	hh := h.fn()
	hh.Write([]byte{leafPrefix})
	hh.Write(data)
	return hh.Sum(nil)
}

func (h *hasher) interior(left, right []byte) []byte {
	hh := h.fn()
	hh.Write([]byte{interiorPrefix})
	hh.Write(left)
	hh.Write(right)
	return hh.Sum(nil)
}

func (t *Tree) hashLeaf(data []byte) []byte { return (&hasher{t.newHash}).leaf(data) }
func (t *Tree) hashInterior(l, r []byte) []byte {
	return (&hasher{t.newHash}).interior(l, r)
}
func (t *Tree) hashEmpty() []byte {
	hh := t.newHash()
	return hh.Sum(nil)
}
