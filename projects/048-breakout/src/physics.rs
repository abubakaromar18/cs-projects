//! Minimal 2D math and collision primitives.
//!
//! The game logic deliberately uses its own tiny vector type instead of
//! macroquad's so that every rule of the game can be unit-tested headlessly,
//! without a window or a GPU.

use std::ops::{Add, AddAssign, Mul, Neg, Sub};

/// A 2D vector in world units. The world uses screen convention: +y is down.
#[derive(Debug, Clone, Copy, PartialEq, Default)]
pub struct Vec2 {
    pub x: f32,
    pub y: f32,
}

impl Vec2 {
    pub const ZERO: Vec2 = Vec2 { x: 0.0, y: 0.0 };

    pub const fn new(x: f32, y: f32) -> Self {
        Vec2 { x, y }
    }

    pub fn dot(self, o: Vec2) -> f32 {
        self.x * o.x + self.y * o.y
    }

    pub fn length(self) -> f32 {
        self.dot(self).sqrt()
    }

    /// Unit vector in the same direction, or zero for a zero vector.
    pub fn normalize_or_zero(self) -> Vec2 {
        let len = self.length();
        if len > f32::EPSILON {
            self * (1.0 / len)
        } else {
            Vec2::ZERO
        }
    }

    /// Reflect this vector about a surface with unit normal `n`:
    /// r = v - 2 (v·n) n
    pub fn reflect(self, n: Vec2) -> Vec2 {
        self - n * (2.0 * self.dot(n))
    }

    /// Rotate counter-clockwise (in math convention) by `radians`.
    pub fn rotate(self, radians: f32) -> Vec2 {
        let (s, c) = radians.sin_cos();
        Vec2::new(self.x * c - self.y * s, self.x * s + self.y * c)
    }
}

impl Add for Vec2 {
    type Output = Vec2;
    fn add(self, o: Vec2) -> Vec2 {
        Vec2::new(self.x + o.x, self.y + o.y)
    }
}
impl AddAssign for Vec2 {
    fn add_assign(&mut self, o: Vec2) {
        self.x += o.x;
        self.y += o.y;
    }
}
impl Sub for Vec2 {
    type Output = Vec2;
    fn sub(self, o: Vec2) -> Vec2 {
        Vec2::new(self.x - o.x, self.y - o.y)
    }
}
impl Mul<f32> for Vec2 {
    type Output = Vec2;
    fn mul(self, k: f32) -> Vec2 {
        Vec2::new(self.x * k, self.y * k)
    }
}
impl Neg for Vec2 {
    type Output = Vec2;
    fn neg(self) -> Vec2 {
        Vec2::new(-self.x, -self.y)
    }
}

/// Axis-aligned rectangle described by its top-left corner and size.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Rect {
    pub x: f32,
    pub y: f32,
    pub w: f32,
    pub h: f32,
}

impl Rect {
    pub const fn new(x: f32, y: f32, w: f32, h: f32) -> Self {
        Rect { x, y, w, h }
    }

    pub fn center(&self) -> Vec2 {
        Vec2::new(self.x + self.w / 2.0, self.y + self.h / 2.0)
    }

    pub fn overlaps(&self, o: &Rect) -> bool {
        self.x < o.x + o.w && o.x < self.x + self.w && self.y < o.y + o.h && o.y < self.y + self.h
    }

    /// The point inside (or on the edge of) the rectangle closest to `p`.
    pub fn closest_point(&self, p: Vec2) -> Vec2 {
        Vec2::new(p.x.clamp(self.x, self.x + self.w), p.y.clamp(self.y, self.y + self.h))
    }
}

/// Result of a circle-vs-rectangle overlap test.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Contact {
    /// Unit normal pointing from the rectangle toward the circle.
    pub normal: Vec2,
    /// How far the circle must move along `normal` to stop overlapping.
    pub depth: f32,
}

/// Circle vs. axis-aligned rectangle collision.
///
/// Works by finding the closest point on the rectangle to the circle's
/// center. If that point is within `radius`, the shapes overlap and the
/// vector between them gives the contact normal. When the center is already
/// inside the rectangle (deep penetration) we fall back to pushing out along
/// the axis of least penetration.
pub fn circle_rect(center: Vec2, radius: f32, rect: &Rect) -> Option<Contact> {
    let closest = rect.closest_point(center);
    let delta = center - closest;
    let dist_sq = delta.dot(delta);

    if dist_sq > radius * radius {
        return None;
    }

    if dist_sq > f32::EPSILON {
        let dist = dist_sq.sqrt();
        return Some(Contact { normal: delta * (1.0 / dist), depth: radius - dist });
    }

    // Center is inside the rectangle: choose the nearest face.
    let left = center.x - rect.x;
    let right = rect.x + rect.w - center.x;
    let top = center.y - rect.y;
    let bottom = rect.y + rect.h - center.y;
    let min = left.min(right).min(top).min(bottom);
    let normal = if min == left {
        Vec2::new(-1.0, 0.0)
    } else if min == right {
        Vec2::new(1.0, 0.0)
    } else if min == top {
        Vec2::new(0.0, -1.0)
    } else {
        Vec2::new(0.0, 1.0)
    };
    Some(Contact { normal, depth: min + radius })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn reflect_off_floor_flips_y() {
        let v = Vec2::new(3.0, 4.0).reflect(Vec2::new(0.0, -1.0));
        assert_eq!(v, Vec2::new(3.0, -4.0));
    }

    #[test]
    fn circle_misses_rect() {
        let r = Rect::new(0.0, 0.0, 10.0, 10.0);
        assert!(circle_rect(Vec2::new(20.0, 5.0), 5.0, &r).is_none());
    }

    #[test]
    fn circle_touching_side_has_horizontal_normal() {
        let r = Rect::new(0.0, 0.0, 10.0, 10.0);
        let c = circle_rect(Vec2::new(13.0, 5.0), 5.0, &r).unwrap();
        assert_eq!(c.normal, Vec2::new(1.0, 0.0));
        assert!((c.depth - 2.0).abs() < 1e-5);
    }

    #[test]
    fn deep_penetration_uses_nearest_face() {
        let r = Rect::new(0.0, 0.0, 100.0, 10.0);
        let c = circle_rect(Vec2::new(50.0, 2.0), 3.0, &r).unwrap();
        assert_eq!(c.normal, Vec2::new(0.0, -1.0));
    }
}
