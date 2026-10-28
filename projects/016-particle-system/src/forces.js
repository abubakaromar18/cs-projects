/**
 * Composable force generators.
 *
 * Each force is an object with `apply(particle, t)` that calls
 * `particle.applyForce(fx, fy)`. The system sums every enabled force each
 * step (superposition), so new behaviours are added by writing a new small
 * object instead of editing the integrator.
 */

/** Uniform gravitational field: F = m·g, independent of position. */
export function gravity(g = 300) {
  return {
    name: 'gravity',
    enabled: true,
    g,
    apply(p) { p.applyForce(0, p.mass * this.g); },
  };
}

/**
 * Wind that gusts over time: a constant base plus a slow sine wave, so the
 * whole sky sways rather than being pushed uniformly.
 */
export function wind(strength = 40, gustPeriod = 4) {
  return {
    name: 'wind',
    enabled: true,
    strength,
    gustPeriod,
    apply(p, t) {
      const gust = 0.5 + 0.5 * Math.sin((2 * Math.PI * t) / this.gustPeriod);
      p.applyForce(this.strength * gust, 0);
    },
  };
}

/**
 * Linear air drag: F = -k·v. Opposes motion and gives sparks their
 * characteristic "slow down and droop" look. Per-particle `drag` scales k.
 */
export function drag(k = 1.2) {
  return {
    name: 'drag',
    enabled: true,
    k,
    apply(p) {
      const c = this.k * p.drag * p.mass;
      p.applyForce(-c * p.vx, -c * p.vy);
    },
  };
}

/**
 * Point attractor (negative strength repels). Uses a softened inverse-square
 * law, F = s·m / (r² + ε²), so particles passing through the centre don't
 * receive an infinite kick — the classic gravitational softening trick from
 * N-body simulation.
 */
export function attractor(x, y, strength = 2e6, softening = 40, radius = Infinity) {
  return {
    name: 'attractor',
    enabled: true,
    x, y, strength, softening, radius,
    apply(p) {
      const dx = this.x - p.x;
      const dy = this.y - p.y;
      const r2 = dx * dx + dy * dy;
      if (r2 > this.radius * this.radius) return;
      const r = Math.sqrt(r2) || 1;
      const mag = (this.strength * p.mass) / (r2 + this.softening * this.softening);
      p.applyForce((mag * dx) / r, (mag * dy) / r);
    },
  };
}

/**
 * Vortex: a tangential force around a point, perpendicular to the radius,
 * falling off with distance. Produces swirling pinwheels.
 */
export function vortex(x, y, strength = 3e4, falloff = 120) {
  return {
    name: 'vortex',
    enabled: true,
    x, y, strength, falloff,
    apply(p) {
      const dx = p.x - this.x;
      const dy = p.y - this.y;
      const r = Math.hypot(dx, dy) || 1;
      const mag = (this.strength * p.mass) / (r + this.falloff);
      // Rotate the radial unit vector by +90°: (dx, dy) -> (-dy, dx).
      p.applyForce((-dy / r) * mag, (dx / r) * mag);
    },
  };
}
