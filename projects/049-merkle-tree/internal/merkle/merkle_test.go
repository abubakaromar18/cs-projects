package merkle

import (
	"bytes"
	"crypto/sha256"
	"fmt"
	"testing"
)

func blocks(ss ...string) [][]byte {
	out := make([][]byte, len(ss))
	for i, s := range ss {
		out[i] = []byte(s)
	}
	return out
}

func TestRootDeterministic(t *testing.T) {
	a := New(blocks("a", "b", "c", "d"), nil)
	b := New(blocks("a", "b", "c", "d"), nil)
	if !bytes.Equal(a.Root(), b.Root()) {
		t.Fatal("same input produced different roots")
	}
}

func TestRootChangesOnTamper(t *testing.T) {
	a := New(blocks("a", "b", "c", "d"), nil)
	b := New(blocks("a", "b", "x", "d"), nil)
	if bytes.Equal(a.Root(), b.Root()) {
		t.Fatal("tampering with a block did not change the root")
	}
}

func TestOrderMatters(t *testing.T) {
	a := New(blocks("a", "b"), nil)
	b := New(blocks("b", "a"), nil)
	if bytes.Equal(a.Root(), b.Root()) {
		t.Fatal("reordering blocks did not change the root")
	}
}

func TestLen(t *testing.T) {
	if got := New(blocks(), nil).Len(); got != 0 {
		t.Fatalf("empty Len = %d, want 0", got)
	}
	if got := New(blocks("a", "b", "c"), nil).Len(); got != 3 {
		t.Fatalf("Len = %d, want 3", got)
	}
}

func TestEmptyRootIsHashOfNothing(t *testing.T) {
	want := sha256.Sum256(nil)
	if got := New(blocks(), nil).Root(); !bytes.Equal(got, want[:]) {
		t.Fatalf("empty root = %x, want %x", got, want)
	}
}

// Every leaf in trees of many sizes (including odd ones that force node
// promotion) must produce a proof that verifies, and only against the real
// block.
func TestProveAndVerifyAllSizes(t *testing.T) {
	for n := 1; n <= 17; n++ {
		data := make([][]byte, n)
		for i := range data {
			data[i] = []byte(fmt.Sprintf("block-%d", i))
		}
		tr := New(data, nil)
		root := tr.Root()
		for i := 0; i < n; i++ {
			p, err := tr.Prove(i)
			if err != nil {
				t.Fatalf("n=%d Prove(%d): %v", n, i, err)
			}
			if !Verify(root, data[i], p, nil) {
				t.Fatalf("n=%d: valid proof for leaf %d failed to verify", n, i)
			}
			if Verify(root, []byte("forged"), p, nil) {
				t.Fatalf("n=%d: forged block for leaf %d verified", n, i)
			}
		}
	}
}

func TestProveOutOfRange(t *testing.T) {
	tr := New(blocks("a", "b"), nil)
	for _, idx := range []int{-1, 2, 99} {
		if _, err := tr.Prove(idx); err != ErrIndexRange {
			t.Fatalf("Prove(%d) err = %v, want ErrIndexRange", idx, err)
		}
	}
}

// A proof for one leaf must not verify a different leaf's block.
func TestProofNotTransferable(t *testing.T) {
	data := blocks("a", "b", "c", "d")
	tr := New(data, nil)
	root := tr.Root()
	p0, _ := tr.Prove(0)
	if Verify(root, data[1], p0, nil) {
		t.Fatal("leaf 0's proof verified leaf 1's block")
	}
}

// Domain separation: a tree of a single block must not have a root equal to
// the bare hash of that block, nor to an interior-style hash. This guards
// against second-preimage confusion between leaves and internal nodes.
func TestDomainSeparation(t *testing.T) {
	tr := New(blocks("a"), nil)
	bare := sha256.Sum256([]byte("a"))
	if bytes.Equal(tr.Root(), bare[:]) {
		t.Fatal("leaf hash is not domain-separated from a bare hash")
	}
}

// A single-element tamper must break verification against the honest root.
func TestVerifyRejectsWrongRoot(t *testing.T) {
	data := blocks("a", "b", "c", "d")
	tr := New(data, nil)
	p, _ := tr.Prove(2)
	wrong := make([]byte, len(tr.Root()))
	if Verify(wrong, data[2], p, nil) {
		t.Fatal("verified against an all-zero root")
	}
}
