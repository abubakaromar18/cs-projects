//! Power-ups: capsules that drop from destroyed bricks and modify play.

use crate::physics::{Rect, Vec2};
use crate::rng::Rng;

pub const CAPSULE_W: f32 = 36.0;
pub const CAPSULE_H: f32 = 14.0;
pub const FALL_SPEED: f32 = 160.0;
/// Probability that a destroyed brick drops a capsule.
pub const DROP_CHANCE: f32 = 0.18;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum PowerUpKind {
    /// Paddle grows 50% wider for a while.
    Expand,
    /// Every ball in play splits into three.
    MultiBall,
    /// All balls move at 65% speed for a while.
    Slow,
    /// Ball sticks to the paddle on contact; launch again to release.
    Sticky,
    /// One extra life.
    ExtraLife,
}

impl PowerUpKind {
    pub const ALL: [PowerUpKind; 5] = [
        PowerUpKind::Expand,
        PowerUpKind::MultiBall,
        PowerUpKind::Slow,
        PowerUpKind::Sticky,
        PowerUpKind::ExtraLife,
    ];

    /// Relative drop weights: extra lives are rare, utility drops are common.
    fn weight(self) -> u32 {
        match self {
            PowerUpKind::Expand => 5,
            PowerUpKind::MultiBall => 4,
            PowerUpKind::Slow => 4,
            PowerUpKind::Sticky => 3,
            PowerUpKind::ExtraLife => 1,
        }
    }

    /// Duration in seconds for timed effects; `None` for instant effects.
    pub fn duration(self) -> Option<f32> {
        match self {
            PowerUpKind::Expand => Some(12.0),
            PowerUpKind::Slow => Some(8.0),
            PowerUpKind::Sticky => Some(10.0),
            PowerUpKind::MultiBall | PowerUpKind::ExtraLife => None,
        }
    }

    pub fn label(self) -> &'static str {
        match self {
            PowerUpKind::Expand => "W",
            PowerUpKind::MultiBall => "M",
            PowerUpKind::Slow => "S",
            PowerUpKind::Sticky => "C",
            PowerUpKind::ExtraLife => "+",
        }
    }

    /// Weighted random choice among all kinds.
    pub fn random(rng: &mut Rng) -> PowerUpKind {
        let total: u32 = Self::ALL.iter().map(|k| k.weight()).sum();
        let mut roll = rng.below(total);
        for k in Self::ALL {
            if roll < k.weight() {
                return k;
            }
            roll -= k.weight();
        }
        unreachable!("roll is always below the total weight")
    }
}

/// A falling capsule waiting to be caught by the paddle.
#[derive(Debug, Clone, PartialEq)]
pub struct Capsule {
    pub pos: Vec2,
    pub kind: PowerUpKind,
}

impl Capsule {
    /// Spawn a capsule centred at `center`.
    pub fn new(center: Vec2, kind: PowerUpKind) -> Self {
        Capsule { pos: Vec2::new(center.x - CAPSULE_W / 2.0, center.y - CAPSULE_H / 2.0), kind }
    }

    pub fn rect(&self) -> Rect {
        Rect::new(self.pos.x, self.pos.y, CAPSULE_W, CAPSULE_H)
    }

    pub fn update(&mut self, dt: f32) {
        self.pos.y += FALL_SPEED * dt;
    }
}

/// Remaining time on each timed effect (0 = inactive).
#[derive(Debug, Clone, Default, PartialEq)]
pub struct ActiveEffects {
    pub expand: f32,
    pub slow: f32,
    pub sticky: f32,
}

impl ActiveEffects {
    /// Start or refresh a timed effect. Catching the same power-up again
    /// resets its timer rather than stacking.
    pub fn activate(&mut self, kind: PowerUpKind) {
        if let Some(d) = kind.duration() {
            match kind {
                PowerUpKind::Expand => self.expand = d,
                PowerUpKind::Slow => self.slow = d,
                PowerUpKind::Sticky => self.sticky = d,
                _ => {}
            }
        }
    }

    pub fn tick(&mut self, dt: f32) {
        for t in [&mut self.expand, &mut self.slow, &mut self.sticky] {
            *t = (*t - dt).max(0.0);
        }
    }

    pub fn is_active(&self, kind: PowerUpKind) -> bool {
        match kind {
            PowerUpKind::Expand => self.expand > 0.0,
            PowerUpKind::Slow => self.slow > 0.0,
            PowerUpKind::Sticky => self.sticky > 0.0,
            _ => false,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn random_produces_every_kind() {
        let mut rng = Rng::new(1);
        let mut seen = std::collections::HashSet::new();
        for _ in 0..2_000 {
            seen.insert(PowerUpKind::random(&mut rng));
        }
        assert_eq!(seen.len(), PowerUpKind::ALL.len());
    }

    #[test]
    fn effects_expire() {
        let mut fx = ActiveEffects::default();
        fx.activate(PowerUpKind::Slow);
        assert!(fx.is_active(PowerUpKind::Slow));
        fx.tick(100.0);
        assert!(!fx.is_active(PowerUpKind::Slow));
    }

    #[test]
    fn instant_effects_have_no_timer() {
        let mut fx = ActiveEffects::default();
        fx.activate(PowerUpKind::ExtraLife);
        assert_eq!(fx, ActiveEffects::default());
    }
}
