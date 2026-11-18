/**
 * Adaptive function sampling.
 *
 * Naively evaluating f at one point per pixel works for smooth curves but
 * fails in two ways:
 *   1. Sharp features (sin(1/x) near 0, narrow peaks) are under-sampled and
 *      look jagged.
 *   2. Discontinuities (tan(x), 1/x, floor(x)) get joined by a vertical line,
 *      a classic plotting bug.
 *
 * This sampler starts from a uniform grid and recursively bisects any interval
 * where the curve's midpoint deviates from the straight chord by more than a
 * pixel tolerance (a simple form of adaptive refinement). If an interval keeps
 * changing a lot even at maximum depth, we treat it as a discontinuity and
 * break the polyline there instead of joining it.
 *
 * Output: an array of segments, each an array of [x, y] world points. Points
 * where f is NaN/±Infinity also split segments (e.g. sqrt(x) for x < 0).
 */

const DEFAULTS = {
  samplesPerPixel: 0.5, // initial grid density
  maxDepth: 8,          // max bisection levels per grid interval
  tolerancePx: 0.5,     // acceptable chord error in pixels
};

export function sample(fn, viewport, options = {}) {
  const { samplesPerPixel, maxDepth, tolerancePx } = { ...DEFAULTS, ...options };
  const n = Math.max(2, Math.ceil(viewport.width * samplesPerPixel));
  const { xMin, xMax } = viewport;
  const dx = (xMax - xMin) / n;
  // Pixel <-> world scale factors so tolerances are measured on screen.
  const pxPerY = viewport.height / viewport.ySpan;
  const tolY = tolerancePx / pxPerY;
  const safe = (x) => {
    const y = fn(x);
    return Number.isFinite(y) ? y : NaN;
  };

  const segments = [];
  let current = [];
  const flush = () => {
    if (current.length > 0) segments.push(current);
    current = [];
  };
  const emit = (x, y) => {
    if (Number.isNaN(y)) {
      flush();
    } else {
      current.push([x, y]);
    }
  };

  /**
   * Jump detection by bisection: repeatedly keep the half-interval that holds
   * the larger change in y, shrinking it down to floating-point resolution.
   * For a continuous function the change vanishes as the interval shrinks
   * (|Δy| ≈ |f'|·Δx → 0); across a jump (floor) or pole (tan, 1/x) it does not.
   */
  function isJump(a, ya, b, yb) {
    for (let i = 0; i < 60; i++) {
      const m = (a + b) / 2;
      if (m <= a || m >= b) break; // reached floating-point resolution
      const ym = safe(m);
      if (Number.isNaN(ym)) return true; // pole hit exactly
      if (Math.abs(ym - ya) > Math.abs(yb - ym)) {
        b = m; yb = ym;
      } else {
        a = m; ya = ym;
      }
    }
    return Math.abs(yb - ya) > tolY;
  }

  // Refine the open interval (x0, x1); endpoints already handled by caller.
  function refine(x0, y0, x1, y1, depth) {
    const xm = (x0 + x1) / 2;
    const ym = safe(xm);
    const finite0 = !Number.isNaN(y0);
    const finite1 = !Number.isNaN(y1);
    const finiteM = !Number.isNaN(ym);

    if (depth >= maxDepth) {
      // At the resolution limit but still not converged: either the curve is
      // just very steep here, or it genuinely jumps. Tell them apart.
      if (finite0 && finite1 && finiteM && Math.abs(ym - (y0 + y1) / 2) > tolY
          && isJump(x0, y0, x1, y1)) {
        emit(xm, NaN); // break the polyline at the discontinuity
        return;
      }
      emit(xm, ym);
      return;
    }

    let needsSplit;
    if (finite0 !== finite1 || finite0 !== finiteM) {
      // Domain boundary somewhere inside (e.g. sqrt(x) near 0): refine to find it.
      needsSplit = true;
    } else if (!finite0) {
      needsSplit = false; // entirely undefined here
    } else {
      const chordMid = (y0 + y1) / 2;
      needsSplit = Math.abs(ym - chordMid) > tolY;
    }

    if (needsSplit) {
      refine(x0, y0, xm, ym, depth + 1);
      emit(xm, ym);
      refine(xm, ym, x1, y1, depth + 1);
    }
    // else: the chord is a good enough approximation; emit nothing extra.
  }

  let xPrev = xMin;
  let yPrev = safe(xPrev);
  emit(xPrev, yPrev);
  for (let i = 1; i <= n; i++) {
    const x = i === n ? xMax : xMin + i * dx;
    const y = safe(x);
    refine(xPrev, yPrev, x, y, 0);
    emit(x, y);
    xPrev = x;
    yPrev = y;
  }
  flush();
  return segments;
}

/** Total point count across segments (useful for stats and tests). */
export const pointCount = (segments) => segments.reduce((s, seg) => s + seg.length, 0);
