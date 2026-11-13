//! Core game state and the fixed rules of Breakout.
//!
//! `Game::update` is a pure state transition: given the elapsed time and the
//! player's input it advances the simulation and records what happened as a
//! list of [`GameEvent`]s. Rendering and audio live in `main.rs` and only
//! *read* this state, which is what lets the whole rule set be tested
//! without opening a window.

use crate::level::{self, Brick};
use crate::physics::{circle_rect, Rect, Vec2};
use crate::powerup::{ActiveEffects, Capsule, PowerUpKind, DROP_CHANCE};
use crate::rng::Rng;

pub const WORLD_W: f32 = 800.0;
pub const WORLD_H: f32 = 600.0;

pub const PADDLE_Y: f32 = 550.0;
pub const PADDLE_H: f32 = 14.0;
pub const PADDLE_W: f32 = 110.0;
pub const PADDLE_SPEED: f32 = 640.0;
pub const EXPAND_FACTOR: f32 = 1.5;

pub const BALL_R: f32 = 7.0;
pub const BASE_BALL_SPEED: f32 = 380.0;
pub const LEVEL_SPEEDUP: f32 = 35.0;
pub const SPEEDUP_PER_BRICK: f32 = 3.0;
pub const MAX_BALL_SPEED: f32 = 760.0;
pub const SLOW_FACTOR: f32 = 0.65;
pub const MAX_BALLS: usize = 12;

/// Largest angle from vertical the paddle can send the ball (60°).
pub const MAX_BOUNCE_ANGLE: f32 = std::f32::consts::FRAC_PI_3;
/// The ball never travels flatter than this fraction of its speed vertically,
/// which prevents frustrating near-horizontal "stuck" trajectories.
pub const MIN_VERTICAL_RATIO: f32 = 0.25;
/// Max distance a ball may travel in one physics sub-step. Keeping this
/// below the ball's radius prevents fast balls tunnelling through bricks.
pub const MAX_SUBSTEP: f32 = 4.0;

pub const START_LIVES: u32 = 3;
pub const MAX_LIVES: u32 = 9;
pub const LEVEL_CLEAR_BONUS: u32 = 1000;
pub const LEVEL_TRANSITION_SECS: f32 = 1.5;

/// What the player is doing this frame.
#[derive(Debug, Clone, Copy, Default, PartialEq)]
pub struct Input {
    /// Keyboard steering in [-1, 1].
    pub move_dir: f32,
    /// Absolute paddle target (e.g. mouse x). Overrides `move_dir` when set.
    pub target_x: Option<f32>,
    /// Launch / release any balls held on the paddle.
    pub launch: bool,
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub enum Phase {
    Playing,
    /// Short pause between levels; counts down to the next layout.
    LevelCleared { remaining: f32 },
    GameOver,
}

/// Things that happened during an update, for sound/particles/tests.
#[derive(Debug, Clone, PartialEq)]
pub enum GameEvent {
    Launched,
    PaddleHit,
    WallHit,
    BrickHit { at: Vec2 },
    BrickDestroyed { at: Vec2, points: u32 },
    SteelHit,
    CapsuleDropped(PowerUpKind),
    PowerUpCaught(PowerUpKind),
    BallLost,
    LifeLost,
    LevelCleared,
    LevelStarted(usize),
    GameOver,
}

#[derive(Debug, Clone, PartialEq)]
pub struct Paddle {
    /// Horizontal centre.
    pub x: f32,
    pub width: f32,
}

impl Paddle {
    pub fn rect(&self) -> Rect {
        Rect::new(self.x - self.width / 2.0, PADDLE_Y, self.width, PADDLE_H)
    }
}

#[derive(Debug, Clone, PartialEq)]
pub struct Ball {
    pub pos: Vec2,
    pub vel: Vec2,
    /// When `Some(offset)`, the ball rides on the paddle at that horizontal
    /// offset from its centre (serving, or caught by the Sticky power-up).
    pub stuck: Option<f32>,
}

impl Ball {
    pub fn speed(&self) -> f32 {
        self.vel.length()
    }

    fn set_speed(&mut self, speed: f32) {
        self.vel = self.vel.normalize_or_zero() * speed;
    }

    /// Nudge the direction so the ball is never close to horizontal.
    fn enforce_min_vertical(&mut self) {
        let speed = self.speed();
        if speed <= 0.0 {
            return;
        }
        let min_vy = speed * MIN_VERTICAL_RATIO;
        if self.vel.y.abs() < min_vy {
            let sign_y = if self.vel.y < 0.0 { -1.0 } else { 1.0 };
            let sign_x = if self.vel.x < 0.0 { -1.0 } else { 1.0 };
            let vx = (speed * speed - min_vy * min_vy).sqrt();
            self.vel = Vec2::new(vx * sign_x, min_vy * sign_y);
        }
    }
}

/// Velocity after leaving the paddle.
///
/// `offset` is where the ball struck, from -1 (left edge) to 1 (right edge).
/// The further from centre, the sharper the angle — this is what gives the
/// player aim. Speed is preserved; only direction changes.
pub fn bounce_velocity(offset: f32, speed: f32) -> Vec2 {
    let angle = offset.clamp(-1.0, 1.0) * MAX_BOUNCE_ANGLE;
    Vec2::new(speed * angle.sin(), -speed * angle.cos())
}

#[derive(Debug, Clone)]
pub struct Game {
    pub paddle: Paddle,
    pub balls: Vec<Ball>,
    pub bricks: Vec<Brick>,
    pub capsules: Vec<Capsule>,
    pub effects: ActiveEffects,
    pub score: u32,
    pub lives: u32,
    /// 0-based level index.
    pub level: usize,
    pub phase: Phase,
    /// Events produced by the most recent `update`.
    pub events: Vec<GameEvent>,
    rng: Rng,
}

impl Game {
    pub fn new(seed: u64) -> Self {
        let mut g = Game {
            paddle: Paddle { x: WORLD_W / 2.0, width: PADDLE_W },
            balls: Vec::new(),
            bricks: Vec::new(),
            capsules: Vec::new(),
            effects: ActiveEffects::default(),
            score: 0,
            lives: START_LIVES,
            level: 0,
            phase: Phase::Playing,
            events: Vec::new(),
            rng: Rng::new(seed),
        };
        g.load_level(0);
        g
    }

    /// Serving speed for the current level.
    pub fn level_speed(&self) -> f32 {
        (BASE_BALL_SPEED + self.level as f32 * LEVEL_SPEEDUP).min(MAX_BALL_SPEED)
    }

    pub fn speed_multiplier(&self) -> f32 {
        if self.effects.is_active(PowerUpKind::Slow) {
            SLOW_FACTOR
        } else {
            1.0
        }
    }

    pub fn breakable_remaining(&self) -> usize {
        self.bricks.iter().filter(|b| b.is_breakable()).count()
    }

    fn load_level(&mut self, index: usize) {
        self.level = index;
        self.bricks = level::build_level(index, WORLD_W);
        self.capsules.clear();
        self.effects = ActiveEffects::default();
        self.paddle = Paddle { x: WORLD_W / 2.0, width: PADDLE_W };
        self.reset_ball();
        self.phase = Phase::Playing;
        self.events.push(GameEvent::LevelStarted(index));
    }

    /// Replace all balls with a single ball resting on the paddle.
    fn reset_ball(&mut self) {
        self.balls = vec![Ball {
            pos: Vec2::new(self.paddle.x, PADDLE_Y - BALL_R),
            vel: Vec2::ZERO,
            stuck: Some(0.0),
        }];
    }

    /// Advance the simulation by `dt` seconds.
    pub fn update(&mut self, dt: f32, input: Input) {
        self.events.clear();
        let dt = dt.clamp(0.0, 0.1); // guard against huge frame hitches

        match self.phase {
            Phase::GameOver => return,
            Phase::LevelCleared { remaining } => {
                let remaining = remaining - dt;
                if remaining <= 0.0 {
                    self.load_level(self.level + 1);
                } else {
                    self.phase = Phase::LevelCleared { remaining };
                }
                return;
            }
            Phase::Playing => {}
        }

        self.effects.tick(dt);
        self.update_paddle(dt, input);
        self.update_stuck_balls(input.launch);
        self.update_free_balls(dt);
        self.update_capsules(dt);
        self.check_ball_loss();

        if self.phase == Phase::Playing && self.breakable_remaining() == 0 {
            self.score += LEVEL_CLEAR_BONUS;
            self.phase = Phase::LevelCleared { remaining: LEVEL_TRANSITION_SECS };
            self.events.push(GameEvent::LevelCleared);
        }
    }

    fn update_paddle(&mut self, dt: f32, input: Input) {
        self.paddle.width = if self.effects.is_active(PowerUpKind::Expand) {
            PADDLE_W * EXPAND_FACTOR
        } else {
            PADDLE_W
        };
        let x = match input.target_x {
            Some(t) => t,
            None => self.paddle.x + input.move_dir.clamp(-1.0, 1.0) * PADDLE_SPEED * dt,
        };
        let half = self.paddle.width / 2.0;
        self.paddle.x = x.clamp(half, WORLD_W - half);
    }

    fn update_stuck_balls(&mut self, launch: bool) {
        let speed = self.level_speed();
        let half = self.paddle.width / 2.0;
        let mut launched = false;
        for ball in &mut self.balls {
            if let Some(offset) = ball.stuck {
                let offset = offset.clamp(-half, half);
                ball.pos = Vec2::new(self.paddle.x + offset, PADDLE_Y - BALL_R);
                if launch {
                    // Keep any speed the ball had built up; serve at level speed otherwise.
                    let s = ball.speed().max(speed);
                    ball.vel = bounce_velocity(offset / half, s);
                    ball.stuck = None;
                    launched = true;
                } else {
                    ball.stuck = Some(offset);
                }
            }
        }
        if launched {
            self.events.push(GameEvent::Launched);
        }
    }

    fn update_free_balls(&mut self, dt: f32) {
        let mult = self.speed_multiplier();
        for i in 0..self.balls.len() {
            if self.balls[i].stuck.is_some() {
                continue;
            }
            // Sub-step so no single step moves farther than MAX_SUBSTEP.
            let distance = self.balls[i].speed() * mult * dt;
            let steps = (distance / MAX_SUBSTEP).ceil().max(1.0) as usize;
            let step_dt = dt / steps as f32;
            for _ in 0..steps {
                let v = self.balls[i].vel;
                self.balls[i].pos += v * (mult * step_dt);
                self.collide_walls(i);
                if self.collide_paddle(i) {
                    break; // ball is now stuck to the paddle
                }
                self.collide_bricks(i);
            }
        }
    }

    fn collide_walls(&mut self, i: usize) {
        let ball = &mut self.balls[i];
        let mut hit = false;
        if ball.pos.x - BALL_R < 0.0 && ball.vel.x < 0.0 {
            ball.pos.x = BALL_R;
            ball.vel.x = -ball.vel.x;
            hit = true;
        } else if ball.pos.x + BALL_R > WORLD_W && ball.vel.x > 0.0 {
            ball.pos.x = WORLD_W - BALL_R;
            ball.vel.x = -ball.vel.x;
            hit = true;
        }
        if ball.pos.y - BALL_R < 0.0 && ball.vel.y < 0.0 {
            ball.pos.y = BALL_R;
            ball.vel.y = -ball.vel.y;
            hit = true;
        }
        if hit {
            ball.enforce_min_vertical();
            self.events.push(GameEvent::WallHit);
        }
    }

    /// Returns true if the ball became stuck to the paddle.
    fn collide_paddle(&mut self, i: usize) -> bool {
        let rect = self.paddle.rect();
        let sticky = self.effects.is_active(PowerUpKind::Sticky);
        let ball = &mut self.balls[i];
        if ball.vel.y <= 0.0 {
            return false; // only catch balls coming down
        }
        let Some(contact) = circle_rect(ball.pos, BALL_R, &rect) else {
            return false;
        };

        let top_hit = ball.pos.y <= rect.y + rect.h / 2.0;
        if top_hit {
            let half = self.paddle.width / 2.0;
            let offset = (ball.pos.x - self.paddle.x).clamp(-half, half);
            ball.pos.y = rect.y - BALL_R;
            self.events.push(GameEvent::PaddleHit);
            if sticky {
                ball.stuck = Some(offset);
                return true;
            }
            ball.vel = bounce_velocity(offset / half, ball.speed());
        } else {
            // Clipped the side of the paddle: plain reflection; the ball is
            // probably lost but it should at least look physical.
            ball.pos += contact.normal * contact.depth;
            if ball.vel.dot(contact.normal) < 0.0 {
                ball.vel = ball.vel.reflect(contact.normal);
            }
        }
        false
    }

    /// Resolve at most one brick collision per sub-step. Handling only the
    /// deepest contact avoids double reflections when the ball touches two
    /// adjacent bricks at once (which would send it straight through them).
    fn collide_bricks(&mut self, i: usize) {
        let pos = self.balls[i].pos;
        let mut best: Option<(usize, crate::physics::Contact)> = None;
        for (bi, b) in self.bricks.iter().enumerate() {
            if let Some(c) = circle_rect(pos, BALL_R, &b.rect) {
                if best.as_ref().is_none_or(|(_, bc)| c.depth > bc.depth) {
                    best = Some((bi, c));
                }
            }
        }
        let Some((bi, contact)) = best else { return };

        let ball = &mut self.balls[i];
        ball.pos += contact.normal * contact.depth;
        if ball.vel.dot(contact.normal) < 0.0 {
            ball.vel = ball.vel.reflect(contact.normal);
        }
        ball.enforce_min_vertical();

        let brick = &mut self.bricks[bi];
        let at = brick.rect.center();
        if !brick.is_breakable() {
            self.events.push(GameEvent::SteelHit);
            return;
        }
        brick.hp -= 1;
        if brick.hp > 0 {
            self.events.push(GameEvent::BrickHit { at });
            return;
        }

        let points = brick.points();
        self.bricks.remove(bi);
        self.score += points;
        self.events.push(GameEvent::BrickDestroyed { at, points });

        // Each destroyed brick makes the ball a little faster.
        let ball = &mut self.balls[i];
        let s = (ball.speed() + SPEEDUP_PER_BRICK).min(MAX_BALL_SPEED);
        ball.set_speed(s);

        if self.rng.next_f32() < DROP_CHANCE {
            let kind = PowerUpKind::random(&mut self.rng);
            self.capsules.push(Capsule::new(at, kind));
            self.events.push(GameEvent::CapsuleDropped(kind));
        }
    }

    fn update_capsules(&mut self, dt: f32) {
        let paddle = self.paddle.rect();
        let mut caught = Vec::new();
        self.capsules.retain_mut(|c| {
            c.update(dt);
            if c.rect().overlaps(&paddle) {
                caught.push(c.kind);
                false
            } else {
                c.pos.y < WORLD_H
            }
        });
        for kind in caught {
            self.apply_powerup(kind);
        }
    }

    /// Apply a power-up's effect immediately.
    pub fn apply_powerup(&mut self, kind: PowerUpKind) {
        self.events.push(GameEvent::PowerUpCaught(kind));
        match kind {
            PowerUpKind::ExtraLife => self.lives = (self.lives + 1).min(MAX_LIVES),
            PowerUpKind::MultiBall => self.split_balls(),
            PowerUpKind::Expand | PowerUpKind::Slow | PowerUpKind::Sticky => {
                self.effects.activate(kind)
            }
        }
    }

    /// Each ball spawns two siblings angled ±20° from its heading.
    fn split_balls(&mut self) {
        let spread = 20f32.to_radians();
        let speed = self.level_speed();
        let mut spawned = Vec::new();
        for b in &self.balls {
            // Held balls split as if they had just been launched straight up.
            let vel = if b.stuck.is_some() { bounce_velocity(0.0, b.speed().max(speed)) } else { b.vel };
            for angle in [-spread, spread] {
                let mut nb = Ball { pos: b.pos, vel: vel.rotate(angle), stuck: None };
                nb.enforce_min_vertical();
                spawned.push(nb);
            }
        }
        for nb in spawned {
            if self.balls.len() >= MAX_BALLS {
                break;
            }
            self.balls.push(nb);
        }
    }

    fn check_ball_loss(&mut self) {
        let before = self.balls.len();
        self.balls.retain(|b| b.pos.y - BALL_R <= WORLD_H);
        for _ in self.balls.len()..before {
            self.events.push(GameEvent::BallLost);
        }
        if !self.balls.is_empty() {
            return;
        }
        self.lives = self.lives.saturating_sub(1);
        self.events.push(GameEvent::LifeLost);
        self.capsules.clear();
        self.effects = ActiveEffects::default();
        if self.lives == 0 {
            self.phase = Phase::GameOver;
            self.events.push(GameEvent::GameOver);
        } else {
            self.reset_ball();
        }
    }
}
