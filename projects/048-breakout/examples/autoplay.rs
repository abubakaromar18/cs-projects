//! Headless demo: an autopilot plays 60 simulated seconds and prints a log.
//!
//!     cargo run --example autoplay [seed]
//!
//! Useful for checking game balance without opening a window.

use breakout::game::{Game, GameEvent, Input};

fn main() {
    let seed = std::env::args().nth(1).and_then(|s| s.parse().ok()).unwrap_or(5);
    let mut g = Game::new(seed);
    let dt = 1.0 / 120.0;

    for frame in 0..(120 * 60) {
        // Track the ball, hitting it slightly left of centre so it angles away.
        let target = g.balls.first().map(|b| b.pos.x - 25.0);
        g.update(dt, Input { target_x: target, launch: true, move_dir: 0.0 });

        for ev in &g.events {
            match ev {
                GameEvent::PowerUpCaught(k) => println!("[{:5.1}s] caught {k:?}", frame as f32 * dt),
                GameEvent::LevelCleared => println!("[{:5.1}s] level {} cleared!", frame as f32 * dt, g.level + 1),
                GameEvent::LifeLost => println!("[{:5.1}s] life lost", frame as f32 * dt),
                _ => {}
            }
        }
        if frame % (120 * 10) == 0 {
            println!(
                "[{:5.1}s] score {:>5}  lives {}  balls {}  bricks left {}",
                frame as f32 * dt, g.score, g.lives, g.balls.len(), g.breakable_remaining()
            );
        }
    }
    println!("final score {} on level {}", g.score, g.level + 1);
}
