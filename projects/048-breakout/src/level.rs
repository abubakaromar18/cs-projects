//! Brick layouts and the brick grid.
//!
//! Levels are written as ASCII art so they are easy to read and edit:
//!
//! * `.` – empty cell
//! * `1`-`3` – breakable brick with that many hit points
//! * `#` – indestructible steel brick (does not count toward clearing)

use crate::physics::Rect;

pub const COLS: usize = 12;
pub const BRICK_W: f32 = 60.0;
pub const BRICK_H: f32 = 22.0;
pub const BRICK_GAP: f32 = 4.0;
pub const GRID_TOP: f32 = 70.0;

/// Built-in levels. Play cycles through them, getting faster each lap.
pub const LAYOUTS: &[&[&str]] = &[
    &[
        "333333333333",
        "222222222222",
        "222222222222",
        "111111111111",
        "111111111111",
    ],
    &[
        "3..........3",
        "23........32",
        "123......321",
        ".123....321.",
        "..12####21..",
        "...111111...",
    ],
    &[
        "#2#2#2#2#2#2",
        "111111111111",
        "3.3.3.3.3.3.",
        ".2.2.2.2.2.2",
        "111111111111",
        "2#2#2#2#2#2#",
    ],
];

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum BrickKind {
    Normal,
    Steel,
}

#[derive(Debug, Clone, PartialEq)]
pub struct Brick {
    pub rect: Rect,
    pub hp: u8,
    pub max_hp: u8,
    pub kind: BrickKind,
}

impl Brick {
    pub fn is_breakable(&self) -> bool {
        self.kind == BrickKind::Normal
    }

    /// Points awarded when this brick is destroyed. Tougher bricks pay more.
    pub fn points(&self) -> u32 {
        50 * self.max_hp as u32
    }
}

/// Left edge of the grid, chosen so the grid is centred in a world of `world_w`.
fn grid_left(world_w: f32) -> f32 {
    let total = COLS as f32 * BRICK_W + (COLS as f32 - 1.0) * BRICK_GAP;
    (world_w - total) / 2.0
}

/// Parse an ASCII layout into bricks positioned in world space.
pub fn parse_layout(rows: &[&str], world_w: f32) -> Result<Vec<Brick>, String> {
    let left = grid_left(world_w);
    let mut bricks = Vec::new();
    for (r, row) in rows.iter().enumerate() {
        if row.chars().count() != COLS {
            return Err(format!("row {r} has {} columns, expected {COLS}", row.chars().count()));
        }
        for (c, ch) in row.chars().enumerate() {
            let (hp, kind) = match ch {
                '.' => continue,
                '1'..='3' => (ch as u8 - b'0', BrickKind::Normal),
                '#' => (u8::MAX, BrickKind::Steel),
                other => return Err(format!("unknown brick '{other}' at row {r}, col {c}")),
            };
            let x = left + c as f32 * (BRICK_W + BRICK_GAP);
            let y = GRID_TOP + r as f32 * (BRICK_H + BRICK_GAP);
            bricks.push(Brick { rect: Rect::new(x, y, BRICK_W, BRICK_H), hp, max_hp: hp, kind });
        }
    }
    Ok(bricks)
}

/// Build the bricks for level `index` (0-based; wraps around the built-ins).
pub fn build_level(index: usize, world_w: f32) -> Vec<Brick> {
    parse_layout(LAYOUTS[index % LAYOUTS.len()], world_w).expect("built-in layouts are valid")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn all_builtin_layouts_parse() {
        for (i, l) in LAYOUTS.iter().enumerate() {
            let bricks = parse_layout(l, 800.0).unwrap_or_else(|e| panic!("level {i}: {e}"));
            assert!(bricks.iter().any(Brick::is_breakable));
        }
    }

    #[test]
    fn rejects_bad_rows() {
        assert!(parse_layout(&["111"], 800.0).is_err());
        assert!(parse_layout(&["11111111111x"], 800.0).is_err());
    }

    #[test]
    fn grid_fits_inside_world() {
        let bricks = build_level(0, 800.0);
        for b in &bricks {
            assert!(b.rect.x >= 0.0 && b.rect.x + b.rect.w <= 800.0);
        }
    }
}
