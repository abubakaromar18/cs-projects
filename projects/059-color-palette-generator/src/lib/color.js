/**
 * Color math: conversions between hex / RGB / HSL and the WCAG 2.x
 * contrast model. Everything here is pure and framework-free so it can be
 * unit-tested in Node.
 *
 * Conventions:
 *   RGB  -> { r, g, b } with each channel an integer 0..255
 *   HSL  -> { h, s, l } with h in [0, 360), s and l in [0, 100]
 *   hex  -> "#rrggbb" (lower-case, always 6 digits)
 */

const clamp = (x, lo, hi) => Math.min(hi, Math.max(lo, x));

/** Normalise an angle into [0, 360). */
export const wrapHue = (h) => ((h % 360) + 360) % 360;

/**
 * Parse "#abc", "abc", "#aabbcc" or "aabbcc" into RGB.
 * Returns null for anything that isn't a valid hex color.
 */
export function hexToRgb(hex) {
  if (typeof hex !== 'string') return null;
  let s = hex.trim().replace(/^#/, '');
  if (/^[0-9a-f]{3}$/i.test(s)) s = s.split('').map((c) => c + c).join('');
  if (!/^[0-9a-f]{6}$/i.test(s)) return null;
  const n = parseInt(s, 16);
  return { r: (n >> 16) & 255, g: (n >> 8) & 255, b: n & 255 };
}

export function rgbToHex({ r, g, b }) {
  const part = (v) => clamp(Math.round(v), 0, 255).toString(16).padStart(2, '0');
  return `#${part(r)}${part(g)}${part(b)}`;
}

/** Canonical form of any accepted hex string, or null. */
export function normalizeHex(hex) {
  const rgb = hexToRgb(hex);
  return rgb ? rgbToHex(rgb) : null;
}

/**
 * RGB -> HSL. Standard hexcone model: lightness is the midpoint of the
 * max/min channel; saturation is the chroma scaled by how far lightness
 * is from the extremes.
 */
export function rgbToHsl({ r, g, b }) {
  const rn = r / 255, gn = g / 255, bn = b / 255;
  const max = Math.max(rn, gn, bn);
  const min = Math.min(rn, gn, bn);
  const l = (max + min) / 2;
  const d = max - min;
  let h = 0, s = 0;
  if (d !== 0) {
    s = d / (1 - Math.abs(2 * l - 1));
    switch (max) {
      case rn: h = ((gn - bn) / d) % 6; break;
      case gn: h = (bn - rn) / d + 2; break;
      default: h = (rn - gn) / d + 4;
    }
    h *= 60;
  }
  return { h: wrapHue(h), s: s * 100, l: l * 100 };
}

/** HSL -> RGB (inverse of the above). */
export function hslToRgb({ h, s, l }) {
  const sn = clamp(s, 0, 100) / 100;
  const ln = clamp(l, 0, 100) / 100;
  const c = (1 - Math.abs(2 * ln - 1)) * sn;
  const hp = wrapHue(h) / 60;
  const x = c * (1 - Math.abs((hp % 2) - 1));
  let rgb;
  if (hp < 1) rgb = [c, x, 0];
  else if (hp < 2) rgb = [x, c, 0];
  else if (hp < 3) rgb = [0, c, x];
  else if (hp < 4) rgb = [0, x, c];
  else if (hp < 5) rgb = [x, 0, c];
  else rgb = [c, 0, x];
  const m = ln - c / 2;
  const [r, g, b] = rgb.map((v) => Math.round((v + m) * 255));
  return { r, g, b };
}

export const hexToHsl = (hex) => rgbToHsl(hexToRgb(hex));
export const hslToHex = (hsl) => rgbToHex(hslToRgb(hsl));

/**
 * WCAG relative luminance. Channels are first linearised from sRGB's
 * gamma-encoded values, then weighted by how sensitive the eye is to each.
 */
export function relativeLuminance({ r, g, b }) {
  const lin = (v) => {
    const c = v / 255;
    return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
}

/** WCAG contrast ratio between two hex colors, in [1, 21]. */
export function contrastRatio(hexA, hexB) {
  const la = relativeLuminance(hexToRgb(hexA));
  const lb = relativeLuminance(hexToRgb(hexB));
  const [hi, lo] = la > lb ? [la, lb] : [lb, la];
  return (hi + 0.05) / (lo + 0.05);
}

/**
 * Classify a contrast ratio against WCAG 2.x success criteria.
 *   AAA       >= 7    normal text (enhanced)
 *   AA        >= 4.5  normal text
 *   AA Large  >= 3    large text (>= 18pt, or 14pt bold) and UI components
 *   Fail      < 3
 */
export function wcagRating(ratio) {
  if (ratio >= 7) return 'AAA';
  if (ratio >= 4.5) return 'AA';
  if (ratio >= 3) return 'AA Large';
  return 'Fail';
}

/** Whichever of black or white reads better on top of `hex`. */
export function bestTextColor(hex) {
  return contrastRatio(hex, '#000000') >= contrastRatio(hex, '#ffffff')
    ? '#000000'
    : '#ffffff';
}

/**
 * Adjust only the lightness of `hex` until it reaches `target` contrast
 * against `against`, keeping hue and saturation. Binary-searches lightness
 * in the direction (darker or lighter) that can actually reach the target,
 * returning the closest-to-original color that passes. Returns null if
 * neither direction can get there.
 */
export function ensureContrast(hex, against, target = 4.5) {
  if (contrastRatio(hex, against) >= target) return normalizeHex(hex);
  const hsl = hexToHsl(hex);
  const candidates = [];
  for (const extreme of [0, 100]) {
    const end = hslToHex({ ...hsl, l: extreme });
    if (contrastRatio(end, against) < target) continue;
    // lo = known failing lightness, hi = known passing lightness
    let lo = hsl.l, hi = extreme;
    for (let i = 0; i < 20; i++) {
      const mid = (lo + hi) / 2;
      if (contrastRatio(hslToHex({ ...hsl, l: mid }), against) >= target) hi = mid;
      else lo = mid;
    }
    candidates.push({ hex: hslToHex({ ...hsl, l: hi }), dist: Math.abs(hi - hsl.l) });
  }
  if (candidates.length === 0) return null;
  candidates.sort((a, b) => a.dist - b.dist);
  return candidates[0].hex;
}
