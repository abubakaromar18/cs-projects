//! Bit layout of a Snowflake ID.
//!
//! ```text
//!  63  62                                      22 21          12 11           0
//! +---+------------------------------------------+--------------+--------------+
//! | 0 |   timestamp: ms since custom epoch (41)  | node id (10) | sequence (12)|
//! +---+------------------------------------------+--------------+--------------+
//! ```
//!
//! * The sign bit is always 0 so IDs stay positive when stored as `i64`
//!   (e.g. in SQL `BIGINT` columns or Java `long`s).
//! * 41 bits of milliseconds cover ~69.7 years past the epoch.
//! * 10 bits of node id allow 1024 independent generators with no coordination.
//! * 12 bits of sequence allow 4096 IDs per node per millisecond.
//!
//! Because the timestamp occupies the most significant bits, sorting IDs
//! numerically sorts them (roughly) by creation time.

/// Number of bits used for the per-millisecond sequence counter.
pub const SEQUENCE_BITS: u32 = 12;
/// Number of bits used for the node (machine/worker) identifier.
pub const NODE_BITS: u32 = 10;
/// Number of bits used for the timestamp.
pub const TIMESTAMP_BITS: u32 = 41;

/// Largest sequence value inside one millisecond (4095).
pub const MAX_SEQUENCE: u64 = (1 << SEQUENCE_BITS) - 1;
/// Largest valid node id (1023).
pub const MAX_NODE_ID: u16 = ((1u32 << NODE_BITS) - 1) as u16;
/// Largest timestamp offset representable (~69.7 years in ms).
pub const MAX_TIMESTAMP: u64 = (1 << TIMESTAMP_BITS) - 1;

/// Shift to place the node id above the sequence.
pub const NODE_SHIFT: u32 = SEQUENCE_BITS;
/// Shift to place the timestamp above node id + sequence.
pub const TIMESTAMP_SHIFT: u32 = SEQUENCE_BITS + NODE_BITS;

/// Default custom epoch: 2020-01-01T00:00:00Z in Unix milliseconds.
///
/// Using a recent epoch instead of 1970 "spends" none of the 41-bit range on
/// the past, so IDs stay valid until ~2089.
pub const DEFAULT_EPOCH_MS: u64 = 1_577_836_800_000;

// Compile-time check that the three fields exactly fill 63 bits.
const _: () = assert!(TIMESTAMP_BITS + NODE_BITS + SEQUENCE_BITS == 63);
