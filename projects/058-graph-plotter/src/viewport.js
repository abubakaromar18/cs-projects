/**
 * Viewport: the affine mapping between "world" coordinates (math units) and
 * "screen" coordinates (canvas pixels, y pointing down).
 *
 *   sx = (x - xMin) / (xMax - xMin) * width
 *   sy = (yMax - y) / (yMax - yMin) * height
 *
 * Zooming is done *about a fixed point*: the world point under the cursor
 * stays under the cursor. For a point p and scale factor k, each bound b
 * becomes p + (b - p) * k. Panning just translates both bounds.
 *
 * The viewport is immutable — every operation returns a new instance, which
 * keeps the UI code simple (old state is never accidentally mutated).
 */

export const MIN_SPAN = 1e-9;
export const MAX_SPAN = 1e9;

export class Viewport {
  constructor({ xMin = -10, xMax = 10, yMin = -10, yMax = 10, width = 800, height = 600 } = {}) {
    if (!(xMax > xMin) || !(yMax > yMin)) throw new RangeError('Viewport bounds must satisfy min < max');
    Object.assign(this, { xMin, xMax, yMin, yMax, width, height });
    Object.freeze(this);
  }

  with(changes) {
    return new Viewport({ ...this, ...changes });
  }

  get xSpan() { return this.xMax - this.xMin; }
  get ySpan() { return this.yMax - this.yMin; }

  toScreenX(x) { return ((x - this.xMin) / this.xSpan) * this.width; }
  toScreenY(y) { return ((this.yMax - y) / this.ySpan) * this.height; }
  toWorldX(sx) { return this.xMin + (sx / this.width) * this.xSpan; }
  toWorldY(sy) { return this.yMax - (sy / this.height) * this.ySpan; }

  /** Pan by a screen-space delta (e.g. a mouse drag of dx, dy pixels). */
  panByPixels(dx, dy) {
    const wx = (dx / this.width) * this.xSpan;
    const wy = (dy / this.height) * this.ySpan;
    return this.with({
      xMin: this.xMin - wx, xMax: this.xMax - wx,
      yMin: this.yMin + wy, yMax: this.yMax + wy,
    });
  }

  /**
   * Zoom about a screen point. factor < 1 zooms in, > 1 zooms out.
   * Separate x/y factors allow axis-only zoom (shift/alt + wheel).
   */
  zoomAt(sx, sy, factorX, factorY = factorX) {
    const px = this.toWorldX(sx);
    const py = this.toWorldY(sy);
    const kx = clampFactor(factorX, this.xSpan);
    const ky = clampFactor(factorY, this.ySpan);
    return this.with({
      xMin: px + (this.xMin - px) * kx, xMax: px + (this.xMax - px) * kx,
      yMin: py + (this.yMin - py) * ky, yMax: py + (this.yMax - py) * ky,
    });
  }

  /** Resize the canvas, keeping the centre and the pixels-per-unit scale. */
  resize(width, height) {
    const cx = (this.xMin + this.xMax) / 2;
    const cy = (this.yMin + this.yMax) / 2;
    const hx = (this.xSpan / this.width) * width / 2;
    const hy = (this.ySpan / this.height) * height / 2;
    return new Viewport({ xMin: cx - hx, xMax: cx + hx, yMin: cy - hy, yMax: cy + hy, width, height });
  }

  /** A square-ish default view of half-width `r` that respects the aspect ratio. */
  static centered(width, height, r = 10) {
    const aspect = height / width;
    return new Viewport({ xMin: -r, xMax: r, yMin: -r * aspect, yMax: r * aspect, width, height });
  }
}

// Keep spans inside [MIN_SPAN, MAX_SPAN] so floating point never degenerates.
function clampFactor(k, span) {
  const target = span * k;
  if (target < MIN_SPAN) return MIN_SPAN / span;
  if (target > MAX_SPAN) return MAX_SPAN / span;
  return k;
}
