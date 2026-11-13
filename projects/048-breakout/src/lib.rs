//! Breakout game logic, independent of any graphics library.
//!
//! * [`physics`] – vectors, rectangles and circle/AABB collision
//! * [`level`] – ASCII brick layouts
//! * [`powerup`] – falling capsules and timed effects
//! * [`game`] – the state machine that ties it all together
//! * [`rng`] – seedable PRNG for reproducible power-up drops

pub mod game;
pub mod level;
pub mod physics;
pub mod powerup;
pub mod rng;

pub use game::{Game, GameEvent, Input, Phase};
