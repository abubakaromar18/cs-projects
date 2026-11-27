/**
 * US QWERTY layout model. Each physical key has an unshifted and a shifted
 * character; we map any typed character back to the physical key that
 * produces it so the heatmap aggregates "A" and "a" onto the same key.
 */
export interface KeyDef {
  /** Stable id: the unshifted character, or a name like "space". */
  id: string;
  base: string;
  shifted: string;
  /** Relative width in key units (1 = normal key). */
  width: number;
}

const k = (base: string, shifted: string, width = 1): KeyDef => ({ id: base, base, shifted, width });

export const QWERTY_ROWS: readonly (readonly KeyDef[])[] = [
  [k("`", "~"), k("1", "!"), k("2", "@"), k("3", "#"), k("4", "$"), k("5", "%"), k("6", "^"),
   k("7", "&"), k("8", "*"), k("9", "("), k("0", ")"), k("-", "_"), k("=", "+")],
  [k("q", "Q"), k("w", "W"), k("e", "E"), k("r", "R"), k("t", "T"), k("y", "Y"), k("u", "U"),
   k("i", "I"), k("o", "O"), k("p", "P"), k("[", "{"), k("]", "}"), k("\\", "|")],
  [k("a", "A"), k("s", "S"), k("d", "D"), k("f", "F"), k("g", "G"), k("h", "H"), k("j", "J"),
   k("k", "K"), k("l", "L"), k(";", ":"), k("'", "\"")],
  [k("z", "Z"), k("x", "X"), k("c", "C"), k("v", "V"), k("b", "B"), k("n", "N"), k("m", "M"),
   k(",", "<"), k(".", ">"), k("/", "?")],
  [{ id: "space", base: " ", shifted: " ", width: 6 }],
];

/** Character → physical key id, built once from the layout. */
const CHAR_TO_KEY: ReadonlyMap<string, { id: string; shift: boolean }> = (() => {
  const m = new Map<string, { id: string; shift: boolean }>();
  for (const row of QWERTY_ROWS) {
    for (const key of row) {
      m.set(key.base, { id: key.id, shift: false });
      if (key.shifted !== key.base) m.set(key.shifted, { id: key.id, shift: true });
    }
  }
  return m;
})();

/** Physical key id for a character, or undefined if not on the layout. */
export function keyIdFor(ch: string): string | undefined {
  return CHAR_TO_KEY.get(ch)?.id;
}

/** Whether producing this character requires Shift on US QWERTY. */
export function needsShift(ch: string): boolean {
  return CHAR_TO_KEY.get(ch)?.shift ?? false;
}

export function allKeys(): KeyDef[] {
  return QWERTY_ROWS.flat();
}
