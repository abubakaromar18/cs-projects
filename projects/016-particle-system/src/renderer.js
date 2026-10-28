/**
 * Canvas 2D renderer.
 *
 * Draws with `globalCompositeOperation = 'lighter'` (additive blending):
 * overlapping sparks add their light together, which is how glowing
 * fireworks look. Instead of clearing each frame we paint a translucent
 * black rectangle, leaving faint motion-blur afterglow.
 */
import { KIND } from './particle.js';
import { hsl } from './vec.js';

export class Renderer {
  /** @param {CanvasRenderingContext2D} ctx */
  constructor(ctx) {
    this.ctx = ctx;
    this.fade = 0.22; // 0 = infinite trails, 1 = hard clear
  }

  draw(system) {
    const { ctx } = this;
    const { width, height } = system;

    ctx.globalCompositeOperation = 'source-over';
    ctx.fillStyle = `rgba(5, 6, 15, ${this.fade})`;
    ctx.fillRect(0, 0, width, height);

    ctx.globalCompositeOperation = 'lighter';
    ctx.lineCap = 'round';

    for (const p of system.pool.items) {
      if (!p.alive) continue;
      const v = p.kind === KIND.ROCKET ? 1 : p.vitality;
      // Sparks flicker as they die out.
      const flicker = v < 0.3 ? 0.5 + Math.random() * 0.5 : 1;
      const alpha = v * flicker;
      const light = 50 + 30 * v;
      const color = hsl(p.hue, 100, light, alpha);

      // Trail: a polyline through recorded history, thinning toward the tail.
      const h = p.history;
      if (h.length >= 2) {
        ctx.strokeStyle = hsl(p.hue, 100, light, alpha * 0.45);
        ctx.lineWidth = p.size * 0.8;
        ctx.beginPath();
        ctx.moveTo(h[0], h[1]);
        for (let i = 2; i < h.length; i += 2) ctx.lineTo(h[i], h[i + 1]);
        ctx.lineTo(p.x, p.y);
        ctx.stroke();
      }

      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.size * (0.5 + 0.5 * v), 0, Math.PI * 2);
      ctx.fill();
    }

    ctx.globalCompositeOperation = 'source-over';
  }

  /** Mark active point forces so the user can see what is pulling the sparks. */
  drawForces(system) {
    const { ctx } = this;
    for (const f of system.forces) {
      if (!f.enabled || f.x === undefined) continue;
      const repel = f.strength < 0;
      ctx.strokeStyle = f.name === 'vortex' ? 'rgba(120,200,255,0.6)'
        : repel ? 'rgba(255,120,120,0.6)' : 'rgba(160,255,160,0.6)';
      ctx.lineWidth = 1.5;
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      ctx.arc(f.x, f.y, 14, 0, Math.PI * 2);
      ctx.stroke();
      ctx.setLineDash([]);
    }
  }
}
