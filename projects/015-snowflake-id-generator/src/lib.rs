//! # snowflake_id
//!
//! Unique, time-ordered 64-bit IDs in the style of Twitter's Snowflake, with
//! no coordination between machines beyond assigning each a node id.
//!
//! ```
//! use snowflake_id::{Generator, SnowflakeId};
//!
//! let gen = Generator::new(42).unwrap();
//! let a = gen.next_id().unwrap();
//! let b = gen.next_id().unwrap();
//! assert!(a < b);                     // later IDs sort after earlier ones
//! assert_eq!(a.node_id(), 42);        // every ID records who made it
//!
//! let parsed: SnowflakeId = a.to_string().parse().unwrap();
//! assert_eq!(parsed, a);
//! ```

pub mod clock;
pub mod generator;
pub mod id;
pub mod layout;
pub mod timefmt;

pub use clock::{Clock, ManualClock, SystemClock};
pub use generator::{Config, Error, Generator};
pub use id::{ParseIdError, Parts, SnowflakeId};
