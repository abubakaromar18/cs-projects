//! Headless gameplay tests: drive `Game` directly with synthetic input.

use breakout::game::*;
use breakout::level::{Brick, BrickKind};
use breakout::physics::{Rect, Vec2};
use breakout::powerup::{Capsule, PowerUpKind};

const DT: f32 = 1.0 / 120.0;
const IDLE: Input = Input { move_dir: 0.0, target_x: None, launch: false };
const LAUNCH: Input = Input { move_dir: 0.0, target_x: None, launch: true };

/// A game with no bricks except a far-away steel one, so the level
/// isn't instantly "cleared" (steel doesn't count, so add one normal brick
/// in a corner the ball won't reach in short tests).
fn empty_game() -> Game {
    let mut g = Game::new(1);
    g.bricks = vec![brick(0.0, 40.0, 1, BrickKind::Normal)];
    g
}

fn brick(x: f32, y: f32, hp: u8, kind: BrickKind) -> Brick {
    Brick { rect: Rect::new(x, y, 60.0, 22.0), hp, max_hp: hp, kind }
}

fn free_ball(pos: Vec2, vel: Vec2) -> Ball {
    Ball { pos, vel, stuck: None }
}

fn run(g: &mut Game, secs: f32, input: Input) -> Vec<GameEvent> {
    let mut all = Vec::new();
    let steps = (secs / DT).round() as usize;
    for _ in 0..steps {
        g.update(DT, input);
        all.append(&mut g.events);
    }
    all
}

#[test]
fn ball_starts_on_paddle_and_follows_it() {
    let mut g = Game::new(1);
    assert_eq!(g.balls.len(), 1);
    assert!(g.balls[0].stuck.is_some());
    run(&mut g, 0.3, Input { move_dir: 1.0, ..IDLE });
    assert!(g.paddle.x > WORLD_W / 2.0);
    assert!((g.balls[0].pos.x - g.paddle.x).abs() < 1e-3);
    assert!((g.balls[0].pos.y - (PADDLE_Y - BALL_R)).abs() < 1e-3);
}

#[test]
fn launch_from_centre_goes_straight_up_at_level_speed() {
    let mut g = Game::new(1);
    g.update(DT, LAUNCH);
    let b = &g.balls[0];
    assert!(b.stuck.is_none());
    assert!(b.vel.y < 0.0);
    assert!(b.vel.x.abs() < 1e-3);
    assert!((b.speed() - g.level_speed()).abs() < 1e-2);
}

#[test]
fn paddle_is_clamped_to_world() {
    let mut g = Game::new(1);
    g.update(DT, Input { target_x: Some(-500.0), ..IDLE });
    assert_eq!(g.paddle.x, PADDLE_W / 2.0);
    g.update(DT, Input { target_x: Some(5000.0), ..IDLE });
    assert_eq!(g.paddle.x, WORLD_W - PADDLE_W / 2.0);
}

#[test]
fn bounce_angle_depends_on_hit_position() {
    let centre = bounce_velocity(0.0, 400.0);
    assert!(centre.x.abs() < 1e-3 && centre.y < 0.0);

    let right = bounce_velocity(1.0, 400.0);
    let angle = right.x.atan2(-right.y);
    assert!((angle - MAX_BOUNCE_ANGLE).abs() < 1e-4);
    assert!((right.length() - 400.0).abs() < 1e-2, "speed preserved");

    let left = bounce_velocity(-0.5, 400.0);
    assert!(left.x < 0.0);
    // Offsets beyond the paddle edge are clamped.
    assert_eq!(bounce_velocity(3.0, 400.0), right);
}

#[test]
fn ball_hitting_paddle_edge_deflects_sideways() {
    let mut g = empty_game();
    let px = g.paddle.x;
    g.balls = vec![free_ball(Vec2::new(px + PADDLE_W / 2.0 - 2.0, PADDLE_Y - 30.0), Vec2::new(0.0, 400.0))];
    let ev = run(&mut g, 0.1, IDLE);
    assert!(ev.contains(&GameEvent::PaddleHit));
    assert!(g.balls[0].vel.y < 0.0 && g.balls[0].vel.x > 0.0);
}

#[test]
fn walls_reflect_the_ball() {
    let mut g = empty_game();
    g.balls = vec![free_ball(Vec2::new(20.0, 300.0), Vec2::new(-300.0, -200.0))];
    let ev = run(&mut g, 0.1, IDLE);
    assert!(ev.contains(&GameEvent::WallHit));
    assert!(g.balls[0].vel.x > 0.0);
    assert!(g.balls[0].pos.x >= BALL_R);
}

#[test]
fn ball_never_goes_near_horizontal_after_wall_hit() {
    let mut g = empty_game();
    g.balls = vec![free_ball(Vec2::new(20.0, 300.0), Vec2::new(-400.0, -1.0))];
    run(&mut g, 0.1, IDLE);
    let b = &g.balls[0];
    assert!(b.vel.y.abs() >= b.speed() * MIN_VERTICAL_RATIO - 1e-3);
}

#[test]
fn destroying_a_brick_scores_and_removes_it() {
    let mut g = Game::new(1);
    g.bricks = vec![brick(370.0, 200.0, 1, BrickKind::Normal), brick(0.0, 40.0, 1, BrickKind::Normal)];
    g.balls = vec![free_ball(Vec2::new(400.0, 300.0), Vec2::new(0.0, -400.0))];
    let ev = run(&mut g, 0.4, IDLE);
    assert!(ev.iter().any(|e| matches!(e, GameEvent::BrickDestroyed { points: 50, .. })));
    assert_eq!(g.score, 50);
    assert_eq!(g.bricks.len(), 1);
    assert!(g.balls[0].vel.y > 0.0, "ball bounced back down");
}

#[test]
fn tough_bricks_take_multiple_hits() {
    let mut g = Game::new(1);
    g.bricks = vec![brick(370.0, 200.0, 3, BrickKind::Normal), brick(0.0, 40.0, 1, BrickKind::Normal)];
    g.balls = vec![free_ball(Vec2::new(400.0, 300.0), Vec2::new(0.0, -400.0))];
    let ev = run(&mut g, 0.4, IDLE);
    assert!(ev.iter().any(|e| matches!(e, GameEvent::BrickHit { .. })));
    assert_eq!(g.bricks[0].hp, 2);
    assert_eq!(g.score, 0);
}

#[test]
fn steel_is_indestructible_and_ignored_for_clearing() {
    let mut g = Game::new(1);
    g.bricks = vec![brick(370.0, 200.0, u8::MAX, BrickKind::Steel)];
    // Only steel left: the level counts as cleared.
    g.update(DT, IDLE);
    assert!(matches!(g.phase, Phase::LevelCleared { .. }));

    let mut g = Game::new(1);
    g.bricks = vec![brick(370.0, 200.0, u8::MAX, BrickKind::Steel), brick(0.0, 40.0, 1, BrickKind::Normal)];
    g.balls = vec![free_ball(Vec2::new(400.0, 300.0), Vec2::new(0.0, -400.0))];
    let ev = run(&mut g, 0.4, IDLE);
    assert!(ev.contains(&GameEvent::SteelHit));
    assert_eq!(g.bricks.len(), 2);
}

#[test]
fn fast_ball_does_not_tunnel_through_brick() {
    let mut g = Game::new(1);
    // A thin brick and a ball fast enough to cross it many times per frame
    // without sub-stepping.
    g.bricks = vec![
        Brick { rect: Rect::new(380.0, 200.0, 40.0, 4.0), hp: 1, max_hp: 1, kind: BrickKind::Normal },
        brick(0.0, 40.0, 1, BrickKind::Normal),
    ];
    g.balls = vec![free_ball(Vec2::new(400.0, 260.0), Vec2::new(0.0, -MAX_BALL_SPEED))];
    g.update(0.1, IDLE); // one big frame (max allowed dt)
    assert_eq!(g.bricks.len(), 1, "brick should have been hit");
}

#[test]
fn bricks_speed_up_the_ball() {
    let mut g = Game::new(1);
    g.bricks = vec![brick(370.0, 200.0, 1, BrickKind::Normal), brick(0.0, 40.0, 1, BrickKind::Normal)];
    g.balls = vec![free_ball(Vec2::new(400.0, 300.0), Vec2::new(0.0, -400.0))];
    run(&mut g, 0.4, IDLE);
    assert!((g.balls[0].speed() - (400.0 + SPEEDUP_PER_BRICK)).abs() < 1e-2);
}

#[test]
fn losing_the_ball_costs_a_life_and_respawns() {
    let mut g = empty_game();
    g.balls = vec![free_ball(Vec2::new(30.0, 580.0), Vec2::new(0.0, 400.0))];
    let ev = run(&mut g, 0.2, IDLE);
    assert!(ev.contains(&GameEvent::BallLost));
    assert!(ev.contains(&GameEvent::LifeLost));
    assert_eq!(g.lives, START_LIVES - 1);
    assert_eq!(g.balls.len(), 1);
    assert!(g.balls[0].stuck.is_some());
}

#[test]
fn losing_one_of_several_balls_is_free() {
    let mut g = empty_game();
    g.balls = vec![
        free_ball(Vec2::new(30.0, 580.0), Vec2::new(0.0, 400.0)),
        free_ball(Vec2::new(400.0, 300.0), Vec2::new(0.0, -100.0)),
    ];
    let ev = run(&mut g, 0.2, IDLE);
    assert!(ev.contains(&GameEvent::BallLost));
    assert!(!ev.contains(&GameEvent::LifeLost));
    assert_eq!(g.lives, START_LIVES);
}

#[test]
fn game_over_after_last_life() {
    let mut g = empty_game();
    g.lives = 1;
    g.balls = vec![free_ball(Vec2::new(30.0, 590.0), Vec2::new(0.0, 400.0))];
    let ev = run(&mut g, 0.2, IDLE);
    assert!(ev.contains(&GameEvent::GameOver));
    assert_eq!(g.phase, Phase::GameOver);
    // Updates are inert after game over.
    let score = g.score;
    run(&mut g, 1.0, LAUNCH);
    assert_eq!(g.score, score);
}

#[test]
fn clearing_a_level_awards_bonus_and_loads_next() {
    let mut g = Game::new(1);
    g.bricks = vec![brick(370.0, 200.0, 1, BrickKind::Normal)];
    g.balls = vec![free_ball(Vec2::new(400.0, 300.0), Vec2::new(0.0, -400.0))];
    let ev = run(&mut g, 0.4, IDLE);
    assert!(ev.contains(&GameEvent::LevelCleared));
    assert_eq!(g.score, 50 + LEVEL_CLEAR_BONUS);

    let ev = run(&mut g, LEVEL_TRANSITION_SECS + 0.1, IDLE);
    assert!(ev.contains(&GameEvent::LevelStarted(1)));
    assert_eq!(g.level, 1);
    assert_eq!(g.phase, Phase::Playing);
    assert!(g.breakable_remaining() > 0);
    assert!(g.level_speed() > BASE_BALL_SPEED);
}

#[test]
fn catching_capsule_applies_expand() {
    let mut g = empty_game();
    let at = Vec2::new(g.paddle.x, PADDLE_Y - 20.0);
    g.capsules.push(Capsule::new(at, PowerUpKind::Expand));
    let ev = run(&mut g, 0.3, IDLE);
    assert!(ev.contains(&GameEvent::PowerUpCaught(PowerUpKind::Expand)));
    assert!(g.capsules.is_empty());
    assert!((g.paddle.width - PADDLE_W * EXPAND_FACTOR).abs() < 1e-3);

    run(&mut g, 13.0, IDLE); // effect lasts 12 s
    assert!((g.paddle.width - PADDLE_W).abs() < 1e-3);
}

#[test]
fn missed_capsule_falls_away() {
    let mut g = empty_game();
    g.capsules.push(Capsule::new(Vec2::new(20.0, 500.0), PowerUpKind::ExtraLife));
    run(&mut g, 1.0, IDLE);
    assert!(g.capsules.is_empty());
    assert_eq!(g.lives, START_LIVES);
}

#[test]
fn multiball_triples_balls() {
    let mut g = empty_game();
    g.balls = vec![free_ball(Vec2::new(400.0, 300.0), Vec2::new(0.0, -400.0))];
    g.apply_powerup(PowerUpKind::MultiBall);
    assert_eq!(g.balls.len(), 3);
    for b in &g.balls {
        assert!((b.speed() - 400.0).abs() < 1e-2);
    }
    // Capped at MAX_BALLS.
    for _ in 0..5 {
        g.apply_powerup(PowerUpKind::MultiBall);
    }
    assert_eq!(g.balls.len(), MAX_BALLS);
}

#[test]
fn extra_life_is_capped() {
    let mut g = empty_game();
    for _ in 0..20 {
        g.apply_powerup(PowerUpKind::ExtraLife);
    }
    assert_eq!(g.lives, MAX_LIVES);
}

#[test]
fn slow_reduces_ball_travel() {
    let mut normal = empty_game();
    normal.balls = vec![free_ball(Vec2::new(400.0, 400.0), Vec2::new(0.0, -300.0))];
    let mut slow = normal.clone();
    slow.apply_powerup(PowerUpKind::Slow);

    run(&mut normal, 0.2, IDLE);
    run(&mut slow, 0.2, IDLE);
    let d_normal = 400.0 - normal.balls[0].pos.y;
    let d_slow = 400.0 - slow.balls[0].pos.y;
    assert!((d_slow / d_normal - SLOW_FACTOR).abs() < 0.02);
}

#[test]
fn sticky_paddle_catches_and_relaunches() {
    let mut g = empty_game();
    g.apply_powerup(PowerUpKind::Sticky);
    let px = g.paddle.x;
    g.balls = vec![free_ball(Vec2::new(px + 20.0, PADDLE_Y - 30.0), Vec2::new(0.0, 400.0))];
    run(&mut g, 0.2, IDLE);
    let off = g.balls[0].stuck.expect("ball should be held");
    assert!((off - 20.0).abs() < 1.0);

    g.update(DT, LAUNCH);
    let b = &g.balls[0];
    assert!(b.stuck.is_none() && b.vel.y < 0.0 && b.vel.x > 0.0);
}

#[test]
fn simulation_is_deterministic_for_a_seed() {
    let play = |seed| {
        let mut g = Game::new(seed);
        run(&mut g, 0.01, LAUNCH);
        // Track the ball with the paddle so the game runs for a while.
        for _ in 0..3000 {
            let tx = g.balls.first().map(|b| b.pos.x);
            g.update(DT, Input { target_x: tx, launch: true, ..IDLE });
        }
        (g.score, g.lives, g.bricks.len(), g.level)
    };
    assert_eq!(play(99), play(99));
}

#[test]
fn autopilot_makes_progress() {
    // A paddle that tracks the first ball (hitting it slightly off-centre so
    // it travels at an angle) should clear bricks without losing lives:
    // a coarse end-to-end sanity check of the whole rule set.
    let mut g = Game::new(5);
    for _ in 0..(120 * 60) {
        let tx = g.balls.first().map(|b| b.pos.x - 25.0);
        g.update(DT, Input { target_x: tx, launch: true, ..IDLE });
    }
    assert!(g.score > 1000, "score was {}", g.score);
    assert_eq!(g.lives, START_LIVES);
}
