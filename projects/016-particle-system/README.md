# 016 · Particle System

An interactive fireworks show on an HTML5 canvas, written in vanilla JavaScript with no dependencies. Rockets climb to where you click and burst into peony, ring, heart, willow or spiral patterns. Every spark is pushed by composable forces (gravity, gusting wind, air drag, point attractors, repulsors and vortices) that you can tune live.

**Level:** Starter · **Area:** Graphics & Simulation

## Features

- Click to launch a rocket that peaks at the cursor and explodes at the top of its arc.
- Five shell patterns, including a heart drawn from a parametric curve.
- **Shift+click** adds an attractor, **Alt+click** a repulsor, **Ctrl/⌘+click** a vortex.
- Live sliders for gravity, wind, drag and trail persistence. Auto-show and a "Finale" button.
- HUD showing the live particle count, FPS and number of bursts.

## CS concepts demonstrated

| Concept | Where |
|---|---|
| **Newtonian particle dynamics.** Forces are summed (superposition) and `a = F/m`. | `src/particle.js`, `src/forces.js` |
| **Semi-implicit (symplectic) Euler integration.** It updates velocity first, which is more stable than explicit Euler. | `ParticleSystem.step` |
| **Fixed timestep with accumulator.** Physics is frame-rate independent and deterministic, with a cap that prevents the "spiral of death". | `ParticleSystem.advance` |
| **Object pooling.** A free-list stack gives O(1) acquire/release with no GC churn, and spawns past capacity are dropped. | `ParticlePool` |
| **Strategy pattern.** Each force is a small object with `apply()`, so a new behaviour doesn't touch the integrator. | `src/forces.js` |
| **Gravitational softening.** `F ∝ 1/(r²+ε²)` avoids singularities near attractors. | `attractor()` |
| **Projectile kinematics.** Launch speed `v = √(2gh)` and fuse `t = v/g` hit a target apex. | `launchSpeedFor`, `launch` |
| **Seeded PRNG (Mulberry32).** Shows are reproducible and tests are deterministic. | `src/vec.js` |
| **Additive blending and afterglow.** Uses `globalCompositeOperation='lighter'` and translucent clears. | `src/renderer.js` |
| **Separation of simulation and rendering.** The physics runs headless in Node, and only `app.js` and `renderer.js` touch the DOM. | project layout |

## Project structure

```
016-particle-system/
├── index.html          # canvas + control panel
├── styles.css
├── src/
│   ├── vec.js          # math helpers, Mulberry32 PRNG, HSL colours
│   ├── particle.js     # Particle state + ParticlePool (free-list)
│   ├── forces.js       # gravity, wind, drag, attractor, vortex
│   ├── fireworks.js    # pure burst-pattern generators + launch kinematics
│   ├── system.js       # ParticleSystem: forces, integrator, lifecycle, clock
│   ├── renderer.js     # Canvas 2D drawing (additive glow, trails)
│   └── app.js          # browser wiring: input, UI, main loop
└── test/
    ├── physics.test.js
    └── fireworks.test.js
```

## Run

ES modules need to be served over HTTP, not opened as `file://`:

```bash
npm start                 # serves on http://localhost:5173 (via npx serve)
# or
python3 -m http.server 5173
```

Then open <http://localhost:5173>.

## Test

The simulation core has no DOM dependencies, so it's tested directly with Node's built-in runner (Node ≥ 18, no install needed):

```bash
npm test
```

The 25 tests cover:

- Free fall against the closed-form semi-implicit Euler solution.
- Exponential drag decay.
- Mass-independence of gravity.
- Attractor, repulsor, radius and softening behaviour, plus vortex perpendicularity.
- Pool capacity and recycling.
- Trail bounds and lifecycle culling.
- Fixed-step accounting.
- **Frame-rate independence.** The same show at 30 fps and 60 fps ends in identical positions.
- Rockets reaching their target apex.
- Pattern geometry, such as heart symmetry and ring speed.
- A full 10-second show that drains to zero particles.

```
# tests 25
# pass 25
# fail 0
```

## Example: headless use

```js
import { ParticleSystem } from './src/system.js';
import { attractor } from './src/forces.js';

const sky = new ParticleSystem({ width: 800, height: 600, seed: 42 });
sky.addForce(attractor(400, 300, 2e6));
sky.launch(400, 150, { pattern: 'heart', hue: 340 });

for (let i = 0; i < 240; i++) sky.step();     // 2 s at 120 Hz
console.log(sky.pool.liveCount, sky.stats);   // e.g. 120 { spawned: 121, dropped: 0, explosions: 1 }
```

## Possible extensions

- Verlet or RK4 integrators, with an energy-drift comparison.
- Particle–particle interactions using a spatial hash grid or Barnes–Hut tree.
- Multi-stage shells (crossettes) where sparks are themselves small rockets.
- A WebGL renderer that draws instanced points to handle 100k+ particles.
- Collision with the ground and buildings, with restitution.
- Web Audio "boom" synced to the `onExplode` hook, delayed by distance and the speed of sound.
- Recording a seeded show and exporting it as a GIF or WebM.
