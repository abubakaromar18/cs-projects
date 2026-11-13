//! Breakout front-end: window, input, rendering and particles via macroquad.
//!
//! All gameplay rules live in the `breakout` library crate; this file only
//! translates input into [`Input`], calls [`Game::update`], and draws the
//! resulting state. The world is a fixed 800×600 space that is letter-boxed
//! to fit whatever size the window is.

use breakout::game::{self, Game, GameEvent, Input, Phase, BALL_R, WORLD_H, WORLD_W};
use breakout::level::BrickKind;
use breakout::powerup::{PowerUpKind, CAPSULE_H, CAPSULE_W};
use macroquad::prelude::*;

fn window_conf() -> Conf {
    Conf {
        window_title: "Breakout".to_owned(),
        window_width: WORLD_W as i32,
        window_height: WORLD_H as i32,
        window_resizable: true,
        high_dpi: true,
        ..Default::default()
    }
}

/// Maps world coordinates to screen coordinates, preserving aspect ratio.
struct View {
    scale: f32,
    ox: f32,
    oy: f32,
}

impl View {
    fn current() -> Self {
        let scale = (screen_width() / WORLD_W).min(screen_height() / WORLD_H);
        View {
            scale,
            ox: (screen_width() - WORLD_W * scale) / 2.0,
            oy: (screen_height() - WORLD_H * scale) / 2.0,
        }
    }
    fn x(&self, x: f32) -> f32 {
        self.ox + x * self.scale
    }
    fn y(&self, y: f32) -> f32 {
        self.oy + y * self.scale
    }
    fn s(&self, v: f32) -> f32 {
        v * self.scale
    }
    fn to_world_x(&self, sx: f32) -> f32 {
        (sx - self.ox) / self.scale
    }
    fn rect(&self, x: f32, y: f32, w: f32, h: f32, c: Color) {
        draw_rectangle(self.x(x), self.y(y), self.s(w), self.s(h), c);
    }
    fn text(&self, t: &str, x: f32, y: f32, size: f32, c: Color) {
        draw_text(t, self.x(x), self.y(y), self.s(size), c);
    }
    fn text_centered(&self, t: &str, y: f32, size: f32, c: Color) {
        let dims = measure_text(t, None, self.s(size) as u16, 1.0);
        draw_text(t, self.x(WORLD_W / 2.0) - dims.width / 2.0, self.y(y), self.s(size), c);
    }
}

/// Short-lived debris spawned when bricks break. Purely cosmetic.
struct Particle {
    pos: Vec2,
    vel: Vec2,
    life: f32,
    color: Color,
}

const BG: Color = Color::new(0.06, 0.07, 0.11, 1.0);
const ROW_COLORS: [Color; 3] = [
    Color::new(0.36, 0.78, 0.98, 1.0), // 1 hp
    Color::new(0.98, 0.72, 0.25, 1.0), // 2 hp
    Color::new(0.95, 0.35, 0.45, 1.0), // 3 hp
];
const STEEL: Color = Color::new(0.55, 0.58, 0.64, 1.0);

fn brick_color(hp: u8, max_hp: u8, kind: BrickKind) -> Color {
    if kind == BrickKind::Steel {
        return STEEL;
    }
    let base = ROW_COLORS[(max_hp.clamp(1, 3) - 1) as usize];
    // Damaged bricks fade toward the background so hits are visible.
    let t = 0.45 + 0.55 * hp as f32 / max_hp as f32;
    Color::new(base.r * t, base.g * t, base.b * t, 1.0)
}

fn powerup_color(kind: PowerUpKind) -> Color {
    match kind {
        PowerUpKind::Expand => Color::new(0.35, 0.85, 0.45, 1.0),
        PowerUpKind::MultiBall => Color::new(0.70, 0.50, 0.98, 1.0),
        PowerUpKind::Slow => Color::new(0.35, 0.70, 0.98, 1.0),
        PowerUpKind::Sticky => Color::new(0.98, 0.85, 0.30, 1.0),
        PowerUpKind::ExtraLife => Color::new(0.98, 0.40, 0.55, 1.0),
    }
}

fn spawn_burst(particles: &mut Vec<Particle>, at: breakout::physics::Vec2, color: Color) {
    for i in 0..12 {
        let a = i as f32 / 12.0 * std::f32::consts::TAU + rand::gen_range(-0.2, 0.2);
        let speed = rand::gen_range(60.0, 220.0);
        particles.push(Particle {
            pos: vec2(at.x, at.y),
            vel: vec2(a.cos(), a.sin()) * speed,
            life: rand::gen_range(0.3, 0.7),
            color,
        });
    }
}

fn read_input(view: &View, last_mouse: &mut (f32, f32), mouse_mode: &mut bool) -> Input {
    let mut dir = 0.0;
    if is_key_down(KeyCode::Left) || is_key_down(KeyCode::A) {
        dir -= 1.0;
        *mouse_mode = false;
    }
    if is_key_down(KeyCode::Right) || is_key_down(KeyCode::D) {
        dir += 1.0;
        *mouse_mode = false;
    }
    // Switch to mouse steering as soon as the mouse moves.
    let m = mouse_position();
    if (m.0 - last_mouse.0).abs() > 0.5 {
        *mouse_mode = true;
    }
    *last_mouse = m;

    Input {
        move_dir: dir,
        target_x: mouse_mode.then(|| view.to_world_x(m.0)),
        launch: is_key_pressed(KeyCode::Space)
            || is_key_pressed(KeyCode::Up)
            || is_mouse_button_pressed(MouseButton::Left),
    }
}

#[macroquad::main(window_conf)]
async fn main() {
    let seed = (macroquad::miniquad::date::now() * 1000.0) as u64;
    rand::srand(seed);
    let mut game = Game::new(seed);
    let mut high_score = 0u32;
    let mut paused = false;
    let mut particles: Vec<Particle> = Vec::new();
    let mut shake = 0.0f32;
    let mut last_mouse = mouse_position();
    let mut mouse_mode = false;

    loop {
        let dt = get_frame_time();
        let view = View::current();

        // ---- input & simulation -------------------------------------------
        if is_key_pressed(KeyCode::Escape) {
            break;
        }
        if is_key_pressed(KeyCode::P) && game.phase != Phase::GameOver {
            paused = !paused;
        }
        if game.phase == Phase::GameOver
            && (is_key_pressed(KeyCode::R) || is_key_pressed(KeyCode::Enter))
        {
            game = Game::new(seed.wrapping_add(game.score as u64));
        }

        let input = read_input(&view, &mut last_mouse, &mut mouse_mode);
        if !paused {
            game.update(dt, input);
        }
        high_score = high_score.max(game.score);

        for ev in &game.events {
            match ev {
                GameEvent::BrickDestroyed { at, .. } => spawn_burst(&mut particles, *at, ROW_COLORS[1]),
                GameEvent::BrickHit { at } => spawn_burst(&mut particles, *at, WHITE),
                GameEvent::LifeLost => shake = 0.35,
                _ => {}
            }
        }
        particles.retain_mut(|p| {
            p.life -= dt;
            p.vel.y += 400.0 * dt;
            p.pos += p.vel * dt;
            p.life > 0.0
        });
        shake = (shake - dt).max(0.0);

        // ---- rendering ----------------------------------------------------
        clear_background(BLACK);
        let jitter = if shake > 0.0 { rand::gen_range(-4.0, 4.0) * shake } else { 0.0 };
        let view = View { ox: view.ox + jitter, ..view };
        view.rect(0.0, 0.0, WORLD_W, WORLD_H, BG);

        for b in &game.bricks {
            let r = b.rect;
            view.rect(r.x, r.y, r.w, r.h, brick_color(b.hp, b.max_hp, b.kind));
            view.rect(r.x, r.y, r.w, 3.0, Color::new(1.0, 1.0, 1.0, 0.18)); // highlight
        }

        for c in &game.capsules {
            let r = c.rect();
            let col = powerup_color(c.kind);
            draw_rectangle(view.x(r.x), view.y(r.y), view.s(CAPSULE_W), view.s(CAPSULE_H), col);
            view.text(c.kind.label(), r.x + CAPSULE_W / 2.0 - 5.0, r.y + CAPSULE_H - 2.0, 16.0, BG);
        }

        for p in &particles {
            let a = (p.life / 0.7).clamp(0.0, 1.0);
            view.rect(p.pos.x, p.pos.y, 3.0, 3.0, Color::new(p.color.r, p.color.g, p.color.b, a));
        }

        let pr = game.paddle.rect();
        let paddle_col = if game.effects.is_active(PowerUpKind::Sticky) {
            powerup_color(PowerUpKind::Sticky)
        } else {
            Color::new(0.90, 0.92, 0.96, 1.0)
        };
        view.rect(pr.x, pr.y, pr.w, pr.h, paddle_col);

        for b in &game.balls {
            draw_circle(view.x(b.pos.x), view.y(b.pos.y), view.s(BALL_R), WHITE);
        }

        // HUD
        let hud = Color::new(0.85, 0.88, 0.95, 1.0);
        view.text(&format!("SCORE {}", game.score), 16.0, 34.0, 26.0, hud);
        view.text_centered(&format!("LEVEL {}", game.level + 1), 34.0, 26.0, hud);
        view.text(&format!("LIVES {}", game.lives), WORLD_W - 120.0, 34.0, 26.0, hud);
        view.text(&format!("BEST {high_score}"), 16.0, WORLD_H - 12.0, 18.0, GRAY);

        let mut fx_x = WORLD_W - 16.0;
        for (kind, t) in [
            (PowerUpKind::Expand, game.effects.expand),
            (PowerUpKind::Slow, game.effects.slow),
            (PowerUpKind::Sticky, game.effects.sticky),
        ] {
            if t > 0.0 {
                fx_x -= 70.0;
                view.text(&format!("{} {:>2.0}s", kind.label(), t.ceil()), fx_x, WORLD_H - 12.0, 18.0, powerup_color(kind));
            }
        }

        let any_stuck = game.balls.iter().any(|b| b.stuck.is_some());
        match game.phase {
            Phase::GameOver => {
                view.rect(0.0, 0.0, WORLD_W, WORLD_H, Color::new(0.0, 0.0, 0.0, 0.6));
                view.text_centered("GAME OVER", 280.0, 64.0, WHITE);
                view.text_centered(&format!("Final score {}", game.score), 330.0, 28.0, hud);
                view.text_centered("Press R to play again", 370.0, 22.0, GRAY);
            }
            Phase::LevelCleared { .. } => {
                view.text_centered("LEVEL CLEAR!", 300.0, 56.0, ROW_COLORS[1]);
                view.text_centered(&format!("+{} bonus", game::LEVEL_CLEAR_BONUS), 340.0, 24.0, hud);
            }
            Phase::Playing if paused => view.text_centered("PAUSED", 320.0, 56.0, WHITE),
            Phase::Playing if any_stuck && game.score == 0 => {
                view.text_centered("Space / click to launch", 420.0, 24.0, GRAY);
                view.text_centered("Arrows, A/D or mouse to move  -  P pause", 450.0, 18.0, GRAY);
            }
            Phase::Playing => {}
        }

        next_frame().await;
    }
}
