import { describe, it, expect } from 'vitest';
import {
  HARMONIES, MAX_SIZE, MIN_SIZE, generatePalette, initialPalette, harmonyColors,
  addSwatch, removeSwatch, toggleLock, setColor, moveSwatch, encodePalette, decodePalette,
} from '../src/lib/palette.js';
import { hexToHsl } from '../src/lib/color.js';
import { mulberry32 } from '../src/lib/random.js';

const hueDist = (a, b) => { const d = Math.abs(a - b) % 360; return Math.min(d, 360 - d); };

describe('seeded RNG', () => {
  it('is deterministic and in [0,1)', () => {
    const a = mulberry32(42), b = mulberry32(42);
    for (let i = 0; i < 100; i++) {
      const x = a();
      expect(x).toBe(b());
      expect(x).toBeGreaterThanOrEqual(0);
      expect(x).toBeLessThan(1);
    }
    expect(mulberry32(1)()).not.toBe(mulberry32(2)());
  });
});

describe('generation', () => {
  it('produces valid hex colors for every harmony', () => {
    for (const mode of Object.keys(HARMONIES)) {
      const p = initialPalette(5, mode, mulberry32(7));
      expect(p).toHaveLength(5);
      for (const s of p) expect(s.hex).toMatch(/^#[0-9a-f]{6}$/);
    }
  });
  it('same seed => same palette', () => {
    expect(initialPalette(5, 'triadic', mulberry32(99))).toEqual(initialPalette(5, 'triadic', mulberry32(99)));
  });
  it('keeps locked swatches in place', () => {
    const rng = mulberry32(3);
    let p = initialPalette(5, 'analogous', rng);
    p = toggleLock(p, 2);
    const kept = p[2].hex;
    for (let i = 0; i < 20; i++) {
      p = generatePalette(p, 'analogous', rng);
      expect(p[2]).toEqual({ hex: kept, locked: true });
    }
  });
  it('uses the locked color as the harmony base (complementary)', () => {
    const rng = mulberry32(11);
    let p = setColor(initialPalette(5, 'complementary', rng), 0, '#e03131');
    p = toggleLock(p, 0);
    p = generatePalette(p, 'complementary', rng);
    const base = hexToHsl('#e03131').h;
    // Slot 1 should be roughly opposite the base hue.
    expect(hueDist(hexToHsl(p[1].hex).h, base + 180)).toBeLessThan(20);
  });
  it('monochromatic keeps hue and spreads lightness', () => {
    const base = { h: 200, s: 60, l: 50 };
    const cols = harmonyColors('monochromatic', base, 5, mulberry32(5)).map(hexToHsl);
    for (const c of cols) expect(hueDist(c.h, 200)).toBeLessThan(12);
    for (let i = 1; i < cols.length; i++) expect(cols[i].l).toBeLessThan(cols[i - 1].l);
  });
});

describe('editing operations are immutable and bounded', () => {
  const rng = mulberry32(1);
  const p = initialPalette(5, 'analogous', rng);

  it('add/remove respect limits', () => {
    expect(addSwatch(p, 'analogous', rng)).toHaveLength(6);
    let big = p;
    for (let i = 0; i < 20; i++) big = addSwatch(big, 'analogous', rng);
    expect(big).toHaveLength(MAX_SIZE);
    let small = p;
    for (let i = 0; i < 20; i++) small = removeSwatch(small, 0);
    expect(small).toHaveLength(MIN_SIZE);
    expect(p).toHaveLength(5);
  });
  it('setColor validates input', () => {
    expect(setColor(p, 0, '#ABC')[0].hex).toBe('#aabbcc');
    expect(setColor(p, 0, 'zzz')).toBe(p);
  });
  it('moveSwatch reorders', () => {
    const moved = moveSwatch(p, 0, 4);
    expect(moved[4]).toEqual(p[0]);
    expect(moved[0]).toEqual(p[1]);
    expect(moveSwatch(p, 0, -1)).toBe(p);
  });
});

describe('URL encoding', () => {
  it('round-trips with locks', () => {
    const p = [
      { hex: '#112233', locked: false },
      { hex: '#aabbcc', locked: true },
      { hex: '#ffffff', locked: false },
    ];
    const s = encodePalette(p);
    expect(s).toBe('112233-!aabbcc-ffffff');
    expect(decodePalette(s)).toEqual(p);
    expect(decodePalette('#' + s)).toEqual(p);
  });
  it('rejects malformed hashes', () => {
    for (const bad of ['', 'abc', '112233', '112233-xyz', '112233-abc', '!-112233', null]) {
      expect(decodePalette(bad)).toBeNull();
    }
    expect(decodePalette(Array(11).fill('000000').join('-'))).toBeNull();
  });
});
