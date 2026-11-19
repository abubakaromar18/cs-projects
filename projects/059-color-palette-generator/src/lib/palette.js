/**
 * Palette generation based on color-harmony rules from color theory.
 *
 * A palette is an array of swatches: { hex, locked }. Generating a new
 * palette re-rolls only the unlocked swatches. When at least one swatch is
 * locked, the first locked color becomes the "base" so new colors stay in
 * harmony with what the user chose to keep.
 */
import { hexToHsl, hslToHex, normalizeHex, wrapHue } from './color.js';
import { between } from './random.js';

/**
 * Each harmony returns a list of hue offsets (degrees from the base hue).
 * Offsets repeat cyclically if the palette is longer than the list.
 */
export const HARMONIES = {
  analogous: { label: 'Analogous', offsets: [0, 30, -30, 60, -60] },
  complementary: { label: 'Complementary', offsets: [0, 180, 0, 180, 0] },
  'split-complementary': { label: 'Split complementary', offsets: [0, 150, 210, 0, 180] },
  triadic: { label: 'Triadic', offsets: [0, 120, 240, 0, 120] },
  tetradic: { label: 'Tetradic', offsets: [0, 90, 180, 270, 0] },
  monochromatic: { label: 'Monochromatic', offsets: [0, 0, 0, 0, 0] },
  random: { label: 'Random', offsets: null },
};

export const MIN_SIZE = 2;
export const MAX_SIZE = 10;

/**
 * Lightness values spread evenly across a usable range so a palette has
 * visual rhythm (light → dark) instead of five mid-tones. Shuffled
 * slightly by the RNG so repeated rolls don't look identical.
 */
function lightnessLadder(n, rng) {
  const lo = 18, hi = 88;
  const jitter = between(rng, -4, 4);
  if (n === 1) return [50 + jitter];
  return Array.from({ length: n }, (_, i) => hi - (i * (hi - lo)) / (n - 1) + jitter);
}

/**
 * Produce `size` target colors for the given harmony and base HSL.
 * Pure given `rng`.
 */
export function harmonyColors(mode, base, size, rng) {
  const harmony = HARMONIES[mode] ?? HARMONIES.analogous;
  const lights = lightnessLadder(size, rng);
  return Array.from({ length: size }, (_, i) => {
    if (!harmony.offsets) {
      return hslToHex({
        h: between(rng, 0, 360),
        s: between(rng, 35, 90),
        l: between(rng, 20, 85),
      });
    }
    const offset = harmony.offsets[i % harmony.offsets.length];
    const h = wrapHue(base.h + offset + between(rng, -6, 6));
    const s = Math.min(95, Math.max(20, base.s + between(rng, -15, 15)));
    return hslToHex({ h, s, l: lights[i] });
  });
}

/** A random but pleasant base color (avoids greys and near-black/white). */
export function randomBase(rng) {
  return { h: between(rng, 0, 360), s: between(rng, 45, 85), l: between(rng, 40, 65) };
}

/**
 * Create the next palette. Locked swatches are kept verbatim and in place;
 * unlocked slots receive fresh harmony colors.
 */
export function generatePalette(previous, mode, rng) {
  const size = previous.length;
  const anchor = previous.find((s) => s.locked);
  const base = anchor ? hexToHsl(anchor.hex) : randomBase(rng);
  const fresh = harmonyColors(mode, base, size, rng);
  return previous.map((sw, i) => (sw.locked ? { ...sw } : { hex: fresh[i], locked: false }));
}

/** Start a new palette of a given size with nothing locked. */
export function initialPalette(size, mode, rng) {
  const blank = Array.from({ length: size }, () => ({ hex: '#000000', locked: false }));
  return generatePalette(blank, mode, rng);
}

/** Add a swatch (up to MAX_SIZE), choosing a color that fits the harmony. */
export function addSwatch(palette, mode, rng) {
  if (palette.length >= MAX_SIZE) return palette;
  const anchor = palette.find((s) => s.locked) ?? palette[0];
  const base = anchor ? hexToHsl(anchor.hex) : randomBase(rng);
  const colors = harmonyColors(mode, base, palette.length + 1, rng);
  return [...palette, { hex: colors[palette.length], locked: false }];
}

export function removeSwatch(palette, index) {
  if (palette.length <= MIN_SIZE) return palette;
  return palette.filter((_, i) => i !== index);
}

export function toggleLock(palette, index) {
  return palette.map((s, i) => (i === index ? { ...s, locked: !s.locked } : s));
}

export function setColor(palette, index, hex) {
  const norm = normalizeHex(hex);
  if (!norm) return palette;
  return palette.map((s, i) => (i === index ? { ...s, hex: norm } : s));
}

/** Move the swatch at `from` to position `to` (for drag/arrow reordering). */
export function moveSwatch(palette, from, to) {
  if (to < 0 || to >= palette.length || from === to) return palette;
  const next = palette.slice();
  const [item] = next.splice(from, 1);
  next.splice(to, 0, item);
  return next;
}

/**
 * Serialise to a short URL-hash string so palettes can be bookmarked or
 * shared: "1e3a5f-!f2c14e-..." where "!" marks a locked swatch.
 */
export function encodePalette(palette) {
  return palette.map((s) => (s.locked ? '!' : '') + s.hex.slice(1)).join('-');
}

/** Inverse of encodePalette. Returns null on any malformed input. */
export function decodePalette(str) {
  if (typeof str !== 'string' || !str) return null;
  const parts = str.replace(/^#/, '').split('-');
  if (parts.length < MIN_SIZE || parts.length > MAX_SIZE) return null;
  const out = [];
  for (const part of parts) {
    const locked = part.startsWith('!');
    const hex = normalizeHex(locked ? part.slice(1) : part);
    if (!hex || (locked ? part.length - 1 : part.length) !== 6) return null;
    out.push({ hex, locked });
  }
  return out;
}
