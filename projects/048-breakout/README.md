# Breakout

The arcade classic in Rust with [macroquad](https://macroquad.rs): aim with the paddle, smash
multi-hit bricks, dodge indestructible steel, and grab falling power-ups. Three hand-made
levels cycle forever, each lap a little faster.

## Features

- **Paddle physics with aim:** where the ball hits the paddle sets its outgoing angle (up to 60°
  from vertical), and the ball keeps its speed.
- **Bricks:** 1–3 hit points (color fades as they take damage) and steel bricks that can't be
  broken. Tougher bricks are worth more points.
- **Power-ups:** 18% of destroyed bricks drop a capsule:

  | Capsule | Effect |
  |---|---|
  | `W` Expand | Paddle 50% wider for 12 s |
  | `M` Multi-ball | Every ball splits into three (max 12 balls) |
  | `S` Slow | All balls at 65% speed for 8 s |
  | `C` Catch | Ball sticks to the paddle for 10 s. Launch again to release |
  | `+` Extra life | +1 life (max 9) |

- The ball speeds up with each brick, then resets for the next level. Clearing a level is
  worth a 1000-point bonus.
- Particles, screen shake when you lose a life, pausing, a best-score counter for the session,
  and a resizable letter-boxed window.

## Controls

| Key | Action |
|---|---|
| ← / → or A / D, or the mouse | Move the paddle |
| Space / ↑ / left click | Launch the ball (or release a caught ball) |
| P | Pause |
| R / Enter | Restart after game over |
| Esc | Quit |

## CS concepts demonstrated

- **Separating the simulation from the renderer.** `src/lib.rs` holds all the game rules and has
  no graphics dependency. `src/main.rs` only turns input into an `Input` struct and draws the
  state. That's why every rule can be unit-tested without a window.
- **Circle-vs-AABB collision.** The game finds the closest point on the rectangle to the ball's
  center. The vector from that point to the center gives the contact normal and how deep the
  ball has gone in. If the center is already inside, the ball is pushed out along the axis of
  least penetration.
- **Vector reflection,** `r = v − 2(v·n)n`, for walls, bricks, and the sides of the paddle.
- **Continuous-collision substitute (sub-stepping).** Each frame is split into steps of at most
  4 world units, which is smaller than the ball's radius. Even a ball at top speed with a long
  frame can't tunnel through a thin brick (this is tested).
- **Contact resolution order.** Only the deepest brick contact is handled in each sub-step.
  This avoids the classic bug where touching two bricks at once reflects the ball twice and
  sends it straight through them.
- **Gameplay invariants.** A minimum vertical speed component stops near-horizontal "forever"
  bounces. The frame time is clamped to 0.1 s so a hitch can't break the physics.
- **State machine:** `Playing → LevelCleared{timer} → Playing … → GameOver`.
- **Event queue:** `update` emits `GameEvent`s. The front end uses them for particles and screen
  shake, and the tests use them for assertions.
- **Deterministic PRNG:** xorshift64* with weighted choice of power-ups. The same seed and
  inputs always replay the same game.
- **Data-driven levels:** levels are written as ASCII art and parsed and checked at load time.

## Project layout

```
src/
  physics.rs   Vec2, Rect, circle/rect collision, reflection
  level.rs     ASCII layouts → bricks
  powerup.rs   capsule kinds, weighted drops, timed effects
  rng.rs       xorshift64* PRNG
  game.rs      Game state machine and all rules
  lib.rs       library root (headless, testable)
  main.rs      macroquad window, input, rendering, particles
tests/
  gameplay.rs  24 integration tests driving Game with synthetic input
examples/
  autoplay.rs  headless autopilot demo
```

## Build, run, test

You need Rust 1.80 or newer (`rustup` is the easiest way to get it). On Linux, the game needs the
usual X11/GL libraries at runtime (for example, `libgl1` and `libx11-6`). Nothing extra is needed
just to build or test.

```bash
cargo run --release          # play
cargo test                   # 12 unit + 24 integration tests, all headless
cargo run --example autoplay # watch an autopilot play 60 simulated seconds
cargo clippy --all-targets   # lint (clean)
```

Example `autoplay` output:

```
[  0.0s] score     0  lives 3  balls 1  bricks left 60
[ 10.0s] score   250  lives 3  balls 1  bricks left 55
[ 11.2s] caught MultiBall
[ 20.0s] score   550  lives 3  balls 1  bricks left 50
...
final score 2250 on level 1
```

## Adding a level

Add another entry to `LAYOUTS` in `src/level.rs`. Each row must be 12 characters: `.` for empty,
`1`–`3` for hit points, and `#` for steel. A unit test checks that every built-in layout parses.

## Possible extensions

- Sound effects through `macroquad::audio`, triggered from the existing `GameEvent`s
- A laser power-up (the paddle fires shots up), and bricks that drop a chosen power-up
- A high-score table saved to disk, and a level editor that writes the ASCII format
- A fixed-timestep accumulator for frame-rate-independent replays, plus input recording
- A WebAssembly build (`cargo build --target wasm32-unknown-unknown` with macroquad's JS loader)
