/**
 * Passage generation: random word streams, with optional punctuation,
 * numbers, and a "focus" mode that biases toward words containing the
 * user's weakest keys (adaptive practice).
 */
import { COMMON_WORDS } from "./words.js";
import { pick, randInt, type Rng } from "./random.js";

export interface PassageOptions {
  /** Number of words to generate. */
  words: number;
  /** Capitalise sentence starts and sprinkle , . ? ! */
  punctuation?: boolean;
  /** Occasionally insert numbers. */
  numbers?: boolean;
  /** Keys (lowercase characters) to favour; see focusWeight. */
  focusKeys?: readonly string[];
  /** Probability that a word is drawn from the focus pool (0–1). */
  focusWeight?: number;
  /** Custom vocabulary (defaults to COMMON_WORDS). */
  vocabulary?: readonly string[];
}

export function generatePassage(opts: PassageOptions, rng: Rng): string {
  if (!Number.isInteger(opts.words) || opts.words < 1) {
    throw new RangeError("words must be a positive integer");
  }
  const vocab = opts.vocabulary ?? COMMON_WORDS;
  const focusPool = buildFocusPool(vocab, opts.focusKeys ?? []);
  const focusWeight = opts.focusWeight ?? 0.6;

  const out: string[] = [];
  let sentenceStart = true;
  let prev = "";
  for (let i = 0; i < opts.words; i++) {
    let w: string;
    if (opts.numbers && rng() < 0.08) {
      w = String(randInt(rng, 1000));
    } else {
      const pool = focusPool.length > 0 && rng() < focusWeight ? focusPool : vocab;
      // Avoid immediate repeats ("the the") which feel like bugs to users.
      do { w = pick(rng, pool); } while (w === prev && pool.length > 1);
    }
    prev = w;

    if (opts.punctuation) {
      if (sentenceStart) w = capitalise(w);
      sentenceStart = false;
      const last = i === opts.words - 1;
      const r = rng();
      if (last) { w += "."; }
      else if (r < 0.07) { w += "."; sentenceStart = true; }
      else if (r < 0.10) { w += "?"; sentenceStart = true; }
      else if (r < 0.12) { w += "!"; sentenceStart = true; }
      else if (r < 0.20) { w += ","; }
    }
    out.push(w);
  }
  return out.join(" ");
}

/** Words that contain at least one of the focus keys, ranked by how many. */
export function buildFocusPool(vocab: readonly string[], keys: readonly string[]): string[] {
  if (keys.length === 0) return [];
  const set = new Set(keys.map((k) => k.toLowerCase()));
  const scored = vocab
    .map((w) => ({ w, n: [...w].filter((c) => set.has(c)).length }))
    .filter((x) => x.n > 0);
  // Duplicate words proportionally to their hit count so words with several
  // weak keys come up more often.
  return scored.flatMap(({ w, n }) => Array<string>(n).fill(w));
}

function capitalise(w: string): string {
  return w.length ? w[0]!.toUpperCase() + w.slice(1) : w;
}
