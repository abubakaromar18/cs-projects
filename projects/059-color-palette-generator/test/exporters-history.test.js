import { describe, it, expect } from 'vitest';
import { toCss, toScss, toJson, toTailwind, toSvg, EXPORTERS } from '../src/lib/exporters.js';
import { createHistory, push, undo, redo, canUndo, canRedo } from '../src/lib/history.js';

const hexes = ['#ff0000', '#00ff00'];

describe('exporters', () => {
  it('CSS custom properties', () => {
    expect(toCss(hexes)).toBe(':root {\n  --color-1: #ff0000;\n  --color-2: #00ff00;\n}\n');
  });
  it('SCSS variables', () => {
    expect(toScss(hexes, 'brand')).toBe('$brand-1: #ff0000;\n$brand-2: #00ff00;\n');
  });
  it('JSON includes rgb and hsl', () => {
    const data = JSON.parse(toJson(hexes));
    expect(data[0]).toEqual({ hex: '#ff0000', rgb: [255, 0, 0], hsl: [0, 100, 50] });
    expect(data[1].hsl[0]).toBe(120);
  });
  it('Tailwind snippet uses 100-step keys', () => {
    const out = toTailwind(hexes);
    expect(out).toContain("100: '#ff0000'");
    expect(out).toContain("200: '#00ff00'");
  });
  it('SVG has one rect per color and correct width', () => {
    const svg = toSvg(hexes);
    expect(svg.match(/<rect/g)).toHaveLength(2);
    expect(svg).toContain('width="200"');
  });
  it('every exporter returns a string', () => {
    for (const ex of Object.values(EXPORTERS)) expect(typeof ex.fn(hexes)).toBe('string');
  });
});

describe('undo/redo history', () => {
  it('undoes and redoes in order', () => {
    let h = createHistory('a');
    h = push(h, 'b');
    h = push(h, 'c');
    expect(h.present).toBe('c');
    h = undo(h); expect(h.present).toBe('b');
    h = undo(h); expect(h.present).toBe('a');
    expect(canUndo(h)).toBe(false);
    expect(undo(h)).toBe(h);
    h = redo(h); expect(h.present).toBe('b');
    h = redo(h); expect(h.present).toBe('c');
    expect(canRedo(h)).toBe(false);
  });
  it('pushing after undo discards the redo branch', () => {
    let h = push(push(createHistory(1), 2), 3);
    h = push(undo(h), 99);
    expect(h.present).toBe(99);
    expect(canRedo(h)).toBe(false);
    expect(undo(h).present).toBe(2);
  });
  it('respects the size limit', () => {
    let h = createHistory(0, 3);
    for (let i = 1; i <= 10; i++) h = push(h, i);
    expect(h.past).toEqual([7, 8, 9]);
  });
});
