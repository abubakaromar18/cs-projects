# Caesar/Vigenère Cracker

An educational Python toolkit that encrypts with the two most famous classical
ciphers and then **breaks them from ciphertext alone** using frequency analysis.
No dependencies beyond the standard library.

> Classical ciphers offer no real security. This project exists to show *why*,
> and works only on text you give it.

## What it does

| Command | Purpose |
|---|---|
| `encrypt` / `decrypt` | Caesar (integer shift) or Vigenère (keyword), case and punctuation preserved |
| `analyze` | Letter-frequency histogram vs. English, index of coincidence, chi-squared, Friedman estimate |
| `crack-caesar` | Tries all 26 shifts and ranks them by chi-squared |
| `crack-vigenere` | Finds the key length (IoC + Kasiski), then solves each column as a Caesar cipher |

## CS concepts demonstrated

- **Frequency analysis.** Natural language has a lopsided letter distribution
  (E ≈ 12.7%, Z ≈ 0.07%). A substitution cipher relabels letters but keeps that shape.
- **Chi-squared goodness of fit.** `Σ (observed − expected)² / expected` measures how far a
  candidate plaintext is from English. Lowest score wins.
- **Index of coincidence.** The probability that two random letters from a text match.
  English ≈ 0.066 and uniform random ≈ 0.038. Caesar leaves it unchanged; Vigenère pulls it
  toward random, which shows that a polyalphabetic cipher is in use.
- **Kasiski examination.** Repeated n-grams in the ciphertext usually come from the same
  plaintext under the same key offset, so their distances are multiples of the key length.
- **Divide and conquer.** Once the key length *L* is known, taking every *L*-th letter yields
  *L* independent Caesar ciphers, each solved in 26 tries. A key space of 26^L collapses to 26·L.
- **Avoiding the "multiple" trap.** Lengths 2L, 3L, … score as well as L, so the cracker takes
  the *smallest* length whose IoC is close to the best. It then collapses periodic keys
  (`KEYKEY → KEY`).

## Layout

```
src/cipherbreak/
  ciphers.py   Caesar & Vigenère encrypt/decrypt
  stats.py     English frequencies, chi-squared, IoC, Friedman test
  crack.py     Caesar brute force, Kasiski, key-length ranking, Vigenère attack
  cli.py       argparse front end
tests/         85 pytest tests (known vectors, round-trips, every Caesar shift, random Vigenère keys)
examples/      caesar.txt (shift 17) and vigenere.txt (an unknown keyword)
```

## Build, run, test

```bash
make dev            # pip install -e '.[dev]'  (or just have pytest installed)
make test           # python3 -m pytest   ->  85 passed
make demo           # analyze + crack both examples

# run from source without installing
PYTHONPATH=src python3 -m cipherbreak encrypt vigenere -k LEMON "attack at dawn"
# installed
cipherbreak crack-vigenere -f examples/vigenere.txt --explain
echo "Khoor, Zruog!" | cipherbreak crack-caesar
```

## Example output

```
$ cipherbreak crack-vigenere -f examples/vigenere.txt --explain
key length  mean column IoC   kasiski hits
     1        0.0443  ##############          0
     2        0.0438  #############          70
     3        0.0530  ################      142
     ...
     9        0.0701  #####################  139 <-
    ...
    18        0.0692  #####################   60

key: FREQUENCY
The history of secret writing is a long contest between the people who make codes ...
```

Length 9 and its multiple 18 both score near English IoC. The cracker picks 9, and
chi-squared on each of the nine columns recovers `FREQUENCY`.

```
$ cipherbreak crack-caesar -f examples/caesar.txt --top 2
--- shift 17  chi2     23.0
The history of secret writing is a long contest between the people who make codes ...
--- shift  2  chi2    909.2
Iwt wxhidgn du htrgti lgxixcv xh p adcv rdcithi qtilttc iwt etdeat lwd bpzt ...
```

## Limitations

- It needs enough text: about 20+ letters per key character for reliable Vigenère recovery.
  Short messages may need `--key-len`.
- The Friedman estimate is shown for teaching purposes. It is coarse and is not used to pick the key length.
- The cracker assumes English plaintext and the 26-letter ASCII alphabet.

## Possible extensions

- Bigram/quadgram scoring for shorter ciphertexts and for refining key letters with hill-climbing
- Autokey Vigenère, Beaufort, and affine ciphers
- Monoalphabetic substitution cracking with simulated annealing
- Frequency tables for other languages (`--lang fr`)
- A web UI that animates the column split and per-column histograms
