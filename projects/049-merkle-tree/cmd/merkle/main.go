// Command merkle builds a Merkle tree over the lines of a file (or stdin) and
// can emit the root, produce an inclusion proof for a line, or verify one.
//
//	merkle root       data.txt            # print the Merkle root
//	merkle prove -i 3 data.txt            # print a proof for line 3 (0-based)
//	merkle verify -i 3 -root <hex> data.txt
//
// Each input line is treated as one data block. This mirrors how real systems
// (Git trees, CT logs) commit to a set of records with one small root hash.
package main

import (
	"bufio"
	"encoding/hex"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"os"

	"github.com/abubakaromar18/cs-projects/projects/049-merkle-tree/internal/merkle"
)

func main() {
	os.Exit(run(os.Args[1:], os.Stdin, os.Stdout, os.Stderr))
}

func run(args []string, stdin io.Reader, stdout, stderr io.Writer) int {
	if len(args) == 0 {
		usage(stderr)
		return 2
	}
	cmd, rest := args[0], args[1:]

	switch cmd {
	case "root":
		return cmdRoot(rest, stdin, stdout, stderr)
	case "prove":
		return cmdProve(rest, stdin, stdout, stderr)
	case "verify":
		return cmdVerify(rest, stdin, stdout, stderr)
	case "-h", "--help", "help":
		usage(stdout)
		return 0
	default:
		fmt.Fprintf(stderr, "merkle: unknown command %q\n", cmd)
		usage(stderr)
		return 2
	}
}

func usage(w io.Writer) {
	fmt.Fprint(w, `merkle - build and verify Merkle inclusion proofs

usage:
  merkle root [file]                      print the Merkle root (hex)
  merkle prove -i N [file]                print a JSON proof for line N
  merkle verify -i N -root HEX [file]     verify a block against a root

Each line of the input is one data block. With no file, input is read from
stdin. Line indexes are 0-based.
`)
}

// readBlocks splits the named file (or stdin when name is "" or "-") into one
// block per line, stripping the trailing newline.
func readBlocks(name string, stdin io.Reader) ([][]byte, error) {
	var r io.Reader
	if name == "" || name == "-" {
		r = stdin
	} else {
		f, err := os.Open(name)
		if err != nil {
			return nil, err
		}
		defer f.Close()
		r = f
	}
	var blocks [][]byte
	sc := bufio.NewScanner(r)
	sc.Buffer(make([]byte, 0, 64*1024), 16*1024*1024)
	for sc.Scan() {
		// Copy: Scanner reuses its buffer across calls.
		blocks = append(blocks, append([]byte(nil), sc.Bytes()...))
	}
	return blocks, sc.Err()
}

func fileArg(fs *flag.FlagSet) string {
	if fs.NArg() > 0 {
		return fs.Arg(0)
	}
	return ""
}

func cmdRoot(args []string, stdin io.Reader, stdout, stderr io.Writer) int {
	fs := flag.NewFlagSet("root", flag.ContinueOnError)
	fs.SetOutput(stderr)
	if err := fs.Parse(args); err != nil {
		return 2
	}
	blocks, err := readBlocks(fileArg(fs), stdin)
	if err != nil {
		fmt.Fprintf(stderr, "merkle: %v\n", err)
		return 1
	}
	t := merkle.New(blocks, nil)
	fmt.Fprintf(stdout, "%s\n", hex.EncodeToString(t.Root()))
	return 0
}

// proofJSON is the on-the-wire shape of a proof, with hashes as hex so it is
// human-readable and pipe-friendly.
type proofJSON struct {
	Index int        `json:"index"`
	Steps []stepJSON `json:"steps"`
}

type stepJSON struct {
	Hash  string `json:"hash"`
	Right bool   `json:"right"`
}

func cmdProve(args []string, stdin io.Reader, stdout, stderr io.Writer) int {
	fs := flag.NewFlagSet("prove", flag.ContinueOnError)
	fs.SetOutput(stderr)
	idx := fs.Int("i", -1, "0-based line index to prove")
	if err := fs.Parse(args); err != nil {
		return 2
	}
	if *idx < 0 {
		fmt.Fprintln(stderr, "merkle: prove requires -i N (N >= 0)")
		return 2
	}
	blocks, err := readBlocks(fileArg(fs), stdin)
	if err != nil {
		fmt.Fprintf(stderr, "merkle: %v\n", err)
		return 1
	}
	t := merkle.New(blocks, nil)
	p, err := t.Prove(*idx)
	if err != nil {
		fmt.Fprintf(stderr, "merkle: %v\n", err)
		return 1
	}
	out := proofJSON{Index: p.Index}
	for _, s := range p.Steps {
		out.Steps = append(out.Steps, stepJSON{Hash: hex.EncodeToString(s.Hash), Right: s.Right})
	}
	enc := json.NewEncoder(stdout)
	enc.SetIndent("", "  ")
	if err := enc.Encode(out); err != nil {
		fmt.Fprintf(stderr, "merkle: %v\n", err)
		return 1
	}
	fmt.Fprintf(stderr, "root: %s\n", hex.EncodeToString(t.Root()))
	return 0
}

func cmdVerify(args []string, stdin io.Reader, stdout, stderr io.Writer) int {
	fs := flag.NewFlagSet("verify", flag.ContinueOnError)
	fs.SetOutput(stderr)
	idx := fs.Int("i", -1, "0-based line index being verified")
	rootHex := fs.String("root", "", "expected Merkle root (hex)")
	proofPath := fs.String("proof", "", "proof JSON file (default: recompute from input)")
	if err := fs.Parse(args); err != nil {
		return 2
	}
	if *idx < 0 || *rootHex == "" {
		fmt.Fprintln(stderr, "merkle: verify requires -i N and -root HEX")
		return 2
	}
	root, err := hex.DecodeString(*rootHex)
	if err != nil {
		fmt.Fprintf(stderr, "merkle: bad -root hex: %v\n", err)
		return 2
	}
	blocks, err := readBlocks(fileArg(fs), stdin)
	if err != nil {
		fmt.Fprintf(stderr, "merkle: %v\n", err)
		return 1
	}
	if *idx >= len(blocks) {
		fmt.Fprintln(stderr, "merkle: index out of range for input")
		return 1
	}
	block := blocks[*idx]

	var proof merkle.Proof
	if *proofPath != "" {
		proof, err = loadProof(*proofPath)
		if err != nil {
			fmt.Fprintf(stderr, "merkle: %v\n", err)
			return 1
		}
	} else {
		t := merkle.New(blocks, nil)
		proof, err = t.Prove(*idx)
		if err != nil {
			fmt.Fprintf(stderr, "merkle: %v\n", err)
			return 1
		}
	}

	if merkle.Verify(root, block, proof, nil) {
		fmt.Fprintln(stdout, "OK: block is included in the committed root")
		return 0
	}
	fmt.Fprintln(stdout, "FAIL: block does not match the root")
	return 1
}

func loadProof(path string) (merkle.Proof, error) {
	f, err := os.Open(path)
	if err != nil {
		return merkle.Proof{}, err
	}
	defer f.Close()
	var pj proofJSON
	if err := json.NewDecoder(f).Decode(&pj); err != nil {
		return merkle.Proof{}, err
	}
	p := merkle.Proof{Index: pj.Index}
	for _, s := range pj.Steps {
		h, err := hex.DecodeString(s.Hash)
		if err != nil {
			return merkle.Proof{}, errors.New("proof contains invalid hex hash")
		}
		p.Steps = append(p.Steps, merkle.ProofStep{Hash: h, Right: s.Right})
	}
	return p, nil
}
