/**
 * Export a palette to formats designers and developers actually paste
 * into their projects. Each exporter is a pure function: hex[] -> string.
 */
import { hexToHsl, hexToRgb } from './color.js';

/** Default token names: color-1, color-2, ... */
export const tokenNames = (n, prefix = 'color') =>
  Array.from({ length: n }, (_, i) => `${prefix}-${i + 1}`);

export function toCss(hexes, prefix = 'color') {
  const names = tokenNames(hexes.length, prefix);
  const lines = hexes.map((h, i) => `  --${names[i]}: ${h};`);
  return `:root {\n${lines.join('\n')}\n}\n`;
}

export function toScss(hexes, prefix = 'color') {
  const names = tokenNames(hexes.length, prefix);
  return hexes.map((h, i) => `$${names[i]}: ${h};`).join('\n') + '\n';
}

export function toJson(hexes) {
  const data = hexes.map((hex) => {
    const { r, g, b } = hexToRgb(hex);
    const { h, s, l } = hexToHsl(hex);
    return { hex, rgb: [r, g, b], hsl: [Math.round(h), Math.round(s), Math.round(l)] };
  });
  return JSON.stringify(data, null, 2) + '\n';
}

/** A snippet for tailwind.config.js `theme.extend.colors`. */
export function toTailwind(hexes, name = 'palette') {
  const steps = hexes.map((h, i) => `    ${(i + 1) * 100}: '${h}',`);
  return `colors: {\n  ${name}: {\n${steps.join('\n')}\n  },\n},\n`;
}

/** A simple SVG strip, handy for dropping into docs or design tools. */
export function toSvg(hexes, swatch = 100, height = 100) {
  const rects = hexes
    .map((h, i) => `  <rect x="${i * swatch}" y="0" width="${swatch}" height="${height}" fill="${h}"/>`)
    .join('\n');
  const w = hexes.length * swatch;
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${height}" viewBox="0 0 ${w} ${height}">\n${rects}\n</svg>\n`;
}

export const EXPORTERS = {
  css: { label: 'CSS variables', ext: 'css', mime: 'text/css', fn: toCss },
  scss: { label: 'SCSS', ext: 'scss', mime: 'text/x-scss', fn: toScss },
  json: { label: 'JSON', ext: 'json', mime: 'application/json', fn: toJson },
  tailwind: { label: 'Tailwind', ext: 'js', mime: 'text/javascript', fn: toTailwind },
  svg: { label: 'SVG', ext: 'svg', mime: 'image/svg+xml', fn: toSvg },
};
