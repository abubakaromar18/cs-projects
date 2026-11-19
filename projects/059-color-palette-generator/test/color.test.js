import { describe, it, expect } from 'vitest';
import {
  hexToRgb, rgbToHex, normalizeHex, rgbToHsl, hslToRgb, hexToHsl, hslToHex,
  relativeLuminance, contrastRatio, wcagRating, bestTextColor, ensureContrast, wrapHue,
} from '../src/lib/color.js';

describe('hex parsing', () => {
  it('parses 6- and 3-digit hex, with or without #', () => {
    expect(hexToRgb('#ff8000')).toEqual({ r: 255, g: 128, b: 0 });
    expect(hexToRgb('0f0')).toEqual({ r: 0, g: 255, b: 0 });
    expect(hexToRgb('#ABC')).toEqual({ r: 170, g: 187, b: 204 });
  });
  it('rejects invalid input', () => {
    for (const bad of ['', '#12', '#12345', 'ggg', '#1234567', null, 42]) {
      expect(hexToRgb(bad)).toBeNull();
    }
  });
  it('formats and normalises', () => {
    expect(rgbToHex({ r: 1, g: 2, b: 255 })).toBe('#0102ff');
    expect(rgbToHex({ r: -5, g: 300, b: 12.6 })).toBe('#00ff0d');
    expect(normalizeHex(' #ABC ')).toBe('#aabbcc');
    expect(normalizeHex('nope')).toBeNull();
  });
});

describe('HSL conversion', () => {
  it('converts primaries correctly', () => {
    expect(hexToHsl('#ff0000')).toEqual({ h: 0, s: 100, l: 50 });
    expect(hexToHsl('#00ff00').h).toBeCloseTo(120);
    expect(hexToHsl('#0000ff').h).toBeCloseTo(240);
    expect(hexToHsl('#808080')).toMatchObject({ s: 0 });
  });
  it('round-trips every 7th RGB value within rounding', () => {
    for (let r = 0; r < 256; r += 37)
      for (let g = 0; g < 256; g += 41)
        for (let b = 0; b < 256; b += 43) {
          const back = hslToRgb(rgbToHsl({ r, g, b }));
          expect(Math.abs(back.r - r)).toBeLessThanOrEqual(1);
          expect(Math.abs(back.g - g)).toBeLessThanOrEqual(1);
          expect(Math.abs(back.b - b)).toBeLessThanOrEqual(1);
        }
  });
  it('wraps hue', () => {
    expect(wrapHue(-30)).toBe(330);
    expect(wrapHue(725)).toBe(5);
    expect(hslToHex({ h: 360, s: 100, l: 50 })).toBe('#ff0000');
  });
});

describe('WCAG contrast', () => {
  it('luminance of black and white', () => {
    expect(relativeLuminance({ r: 0, g: 0, b: 0 })).toBe(0);
    expect(relativeLuminance({ r: 255, g: 255, b: 255 })).toBeCloseTo(1);
  });
  it('black on white is 21:1 and symmetric', () => {
    expect(contrastRatio('#000', '#fff')).toBeCloseTo(21);
    expect(contrastRatio('#fff', '#000')).toBeCloseTo(21);
    expect(contrastRatio('#3b5bdb', '#3b5bdb')).toBeCloseTo(1);
  });
  it('matches known reference values', () => {
    // #767676 on white is the classic "just passes AA" grey (≈4.54).
    expect(contrastRatio('#767676', '#ffffff')).toBeCloseTo(4.54, 2);
    expect(contrastRatio('#777777', '#ffffff')).toBeLessThan(4.5);
  });
  it('rates ratios', () => {
    expect(wcagRating(21)).toBe('AAA');
    expect(wcagRating(7)).toBe('AAA');
    expect(wcagRating(5)).toBe('AA');
    expect(wcagRating(3.2)).toBe('AA Large');
    expect(wcagRating(1.5)).toBe('Fail');
  });
  it('picks a readable text color', () => {
    expect(bestTextColor('#ffff00')).toBe('#000000');
    expect(bestTextColor('#1e1e64')).toBe('#ffffff');
  });
});

describe('ensureContrast', () => {
  it('returns the color unchanged if it already passes', () => {
    expect(ensureContrast('#000000', '#ffffff')).toBe('#000000');
  });
  it('nudges lightness until AA is met, keeping hue', () => {
    const fixed = ensureContrast('#8899ff', '#ffffff', 4.5);
    expect(contrastRatio(fixed, '#ffffff')).toBeGreaterThanOrEqual(4.5);
    expect(Math.abs(hexToHsl(fixed).h - hexToHsl('#8899ff').h)).toBeLessThan(3);
    // It should be the minimal change, not just jump to black.
    expect(contrastRatio(fixed, '#ffffff')).toBeLessThan(5);
  });
  it('can go lighter on a dark background', () => {
    const fixed = ensureContrast('#333366', '#000000', 7);
    expect(contrastRatio(fixed, '#000000')).toBeGreaterThanOrEqual(7);
    expect(hexToHsl(fixed).l).toBeGreaterThan(hexToHsl('#333366').l);
  });
  it('returns null when the target is unreachable', () => {
    // No color reaches 15:1 against mid grey.
    expect(ensureContrast('#808080', '#777777', 15)).toBeNull();
  });
});
