//! The lock-free ID generator.
//!
//! # How it stays unique without a lock
//!
//! All mutable state — the last timestamp used and the sequence within it —
//! is packed into a single `AtomicU64`:
//!
//! ```text
//! state = (last_timestamp << 12) | last_sequence
//! ```
//!
//! Each call reads the state, computes the successor, and publishes it with a
//! compare-and-swap (CAS). If another thread won the race, the CAS fails and we
//! simply retry with the fresh state. Because the successor is always strictly
//! greater than the state it replaced, every successful CAS hands out a
//! distinct (timestamp, sequence) pair, and therefore a distinct ID.
//!
//! # Clock problems
//!
//! * **Sequence exhausted** (more than 4096 IDs in one millisecond): wait until
//!   the clock ticks past that millisecond, then retry.
//! * **Clock moved backwards** (e.g. an NTP correction): if the jump is within
//!   `max_backward_ms`, keep issuing IDs on the *last* timestamp (a tiny
//!   logical clock) so IDs stay monotonic; otherwise return an error rather
//!   than risk duplicates.

use std::fmt;
use std::sync::atomic::{AtomicU64, Ordering};

use crate::clock::{Clock, SystemClock};
use crate::id::SnowflakeId;
use crate::layout::*;

/// Sentinel meaning "no ID issued yet".
const EMPTY: u64 = u64::MAX;

/// Things that can go wrong when creating or using a generator.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Error {
    /// Node id does not fit in 10 bits.
    InvalidNodeId(u16),
    /// The configured epoch is in the future relative to the clock.
    ClockBeforeEpoch { now_ms: u64, epoch_ms: u64 },
    /// The clock went backwards by more than the configured tolerance.
    ClockMovedBackwards { behind_ms: u64, tolerance_ms: u64 },
    /// 41 bits of milliseconds since the epoch have run out (~69 years).
    TimestampOverflow,
}

impl fmt::Display for Error {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Error::InvalidNodeId(n) => write!(f, "node id {n} out of range 0..={MAX_NODE_ID}"),
            Error::ClockBeforeEpoch { now_ms, epoch_ms } => {
                write!(f, "clock ({now_ms} ms) is before the epoch ({epoch_ms} ms)")
            }
            Error::ClockMovedBackwards { behind_ms, tolerance_ms } => write!(
                f,
                "clock moved backwards by {behind_ms} ms (tolerance {tolerance_ms} ms); refusing to generate"
            ),
            Error::TimestampOverflow => write!(f, "timestamp no longer fits in {TIMESTAMP_BITS} bits"),
        }
    }
}

impl std::error::Error for Error {}

/// Generator settings.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Config {
    /// This generator's node id, `0..=1023`. Must be unique per running generator.
    pub node_id: u16,
    /// Custom epoch in Unix milliseconds.
    pub epoch_ms: u64,
    /// How far (ms) the clock may jump backwards before `next_id` errors.
    /// `0` is the classic, strict Snowflake behaviour.
    pub max_backward_ms: u64,
}

impl Config {
    /// Default settings for the given node id.
    pub fn new(node_id: u16) -> Self {
        Self {
            node_id,
            epoch_ms: DEFAULT_EPOCH_MS,
            max_backward_ms: 0,
        }
    }

    /// Builder-style setter for the epoch.
    pub fn epoch_ms(mut self, epoch_ms: u64) -> Self {
        self.epoch_ms = epoch_ms;
        self
    }

    /// Builder-style setter for the backwards-clock tolerance.
    pub fn max_backward_ms(mut self, ms: u64) -> Self {
        self.max_backward_ms = ms;
        self
    }
}

/// A thread-safe Snowflake generator. Share it with `Arc` across threads.
#[derive(Debug)]
pub struct Generator<C: Clock = SystemClock> {
    config: Config,
    clock: C,
    state: AtomicU64,
}

impl Generator<SystemClock> {
    /// A generator on the system clock with default settings.
    pub fn new(node_id: u16) -> Result<Self, Error> {
        Self::with_clock(Config::new(node_id), SystemClock)
    }
}

impl<C: Clock> Generator<C> {
    /// A generator with explicit settings and time source.
    pub fn with_clock(config: Config, clock: C) -> Result<Self, Error> {
        if config.node_id > MAX_NODE_ID {
            return Err(Error::InvalidNodeId(config.node_id));
        }
        Ok(Self {
            config,
            clock,
            state: AtomicU64::new(EMPTY),
        })
    }

    /// This generator's configuration.
    pub fn config(&self) -> &Config {
        &self.config
    }

    /// Produces the next unique ID.
    pub fn next_id(&self) -> Result<SnowflakeId, Error> {
        let mut current = self.state.load(Ordering::Acquire);
        loop {
            let now = self.elapsed_ms()?;

            let (ts, seq) = if current == EMPTY {
                (now, 0)
            } else {
                let last_ts = current >> SEQUENCE_BITS;
                let last_seq = current & MAX_SEQUENCE;
                if now > last_ts {
                    // A new millisecond: restart the sequence.
                    (now, 0)
                } else {
                    // Same millisecond, or the clock went backwards.
                    let behind = last_ts - now;
                    if behind > self.config.max_backward_ms {
                        return Err(Error::ClockMovedBackwards {
                            behind_ms: behind,
                            tolerance_ms: self.config.max_backward_ms,
                        });
                    }
                    if last_seq < MAX_SEQUENCE {
                        (last_ts, last_seq + 1)
                    } else {
                        // 4096 IDs already issued for last_ts: wait it out.
                        self.clock.wait_past(self.config.epoch_ms + last_ts);
                        current = self.state.load(Ordering::Acquire);
                        continue;
                    }
                }
            };

            let next = (ts << SEQUENCE_BITS) | seq;
            match self.state.compare_exchange_weak(
                current,
                next,
                Ordering::AcqRel,
                Ordering::Acquire,
            ) {
                Ok(_) => {
                    let id = SnowflakeId::from_parts(ts, self.config.node_id, seq as u16)
                        .expect("fields validated above");
                    return Ok(id);
                }
                // Lost the race (or spurious failure): retry with the newer state.
                Err(actual) => current = actual,
            }
        }
    }

    /// Generates `n` IDs in order.
    pub fn take(&self, n: usize) -> Result<Vec<SnowflakeId>, Error> {
        (0..n).map(|_| self.next_id()).collect()
    }

    /// Milliseconds since the custom epoch, validated against the layout.
    fn elapsed_ms(&self) -> Result<u64, Error> {
        let now_ms = self.clock.now_millis();
        let elapsed = now_ms
            .checked_sub(self.config.epoch_ms)
            .ok_or(Error::ClockBeforeEpoch {
                now_ms,
                epoch_ms: self.config.epoch_ms,
            })?;
        if elapsed > MAX_TIMESTAMP {
            return Err(Error::TimestampOverflow);
        }
        Ok(elapsed)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::clock::ManualClock;

    const EPOCH: u64 = 1_000_000;

    fn gen_at(start: u64, cfg: Config) -> (Generator<ManualClock>, ManualClock) {
        let clock = ManualClock::new(start);
        (
            Generator::with_clock(cfg.epoch_ms(EPOCH), clock.clone()).unwrap(),
            clock,
        )
    }

    #[test]
    fn rejects_bad_node_id() {
        assert_eq!(
            Generator::new(1024).unwrap_err(),
            Error::InvalidNodeId(1024)
        );
        assert!(Generator::new(1023).is_ok());
    }

    #[test]
    fn sequence_increments_within_a_millisecond() {
        let (g, _) = gen_at(EPOCH + 50, Config::new(3));
        let ids = g.take(3).unwrap();
        for (i, id) in ids.iter().enumerate() {
            assert_eq!(id.timestamp(), 50);
            assert_eq!(id.node_id(), 3);
            assert_eq!(id.sequence() as usize, i);
        }
    }

    #[test]
    fn sequence_resets_on_new_millisecond() {
        let (g, clock) = gen_at(EPOCH + 5, Config::new(0));
        g.take(10).unwrap();
        clock.advance(1);
        let id = g.next_id().unwrap();
        assert_eq!((id.timestamp(), id.sequence()), (6, 0));
    }

    #[test]
    fn sequence_overflow_rolls_into_next_millisecond() {
        let (g, clock) = gen_at(EPOCH + 7, Config::new(1));
        let ids = g.take(4097).unwrap();
        assert_eq!(ids[4095].parts().sequence, 4095);
        assert_eq!(ids[4095].timestamp(), 7);
        // The 4097th ID forced the clock to tick.
        assert_eq!((ids[4096].timestamp(), ids[4096].sequence()), (8, 0));
        assert_eq!(clock.now_millis(), EPOCH + 8);
        assert!(ids.windows(2).all(|w| w[0] < w[1]));
    }

    #[test]
    fn strict_mode_errors_when_clock_goes_backwards() {
        let (g, clock) = gen_at(EPOCH + 100, Config::new(0));
        g.next_id().unwrap();
        clock.set(EPOCH + 97);
        assert_eq!(
            g.next_id().unwrap_err(),
            Error::ClockMovedBackwards {
                behind_ms: 3,
                tolerance_ms: 0
            }
        );
        // Recovers once the clock catches up.
        clock.set(EPOCH + 101);
        assert_eq!(g.next_id().unwrap().timestamp(), 101);
    }

    #[test]
    fn tolerant_mode_keeps_ids_monotonic_through_small_regressions() {
        let (g, clock) = gen_at(EPOCH + 100, Config::new(0).max_backward_ms(5));
        let a = g.next_id().unwrap();
        clock.set(EPOCH + 97);
        let b = g.next_id().unwrap();
        assert!(b > a);
        assert_eq!(
            (b.timestamp(), b.sequence()),
            (100, 1),
            "reuses last timestamp"
        );
        clock.set(EPOCH + 90);
        assert!(matches!(
            g.next_id(),
            Err(Error::ClockMovedBackwards { behind_ms: 10, .. })
        ));
    }

    #[test]
    fn clock_before_epoch_is_an_error() {
        let (g, _) = gen_at(EPOCH - 1, Config::new(0));
        assert!(matches!(g.next_id(), Err(Error::ClockBeforeEpoch { .. })));
    }

    #[test]
    fn timestamp_overflow_is_detected() {
        let (g, _) = gen_at(EPOCH + MAX_TIMESTAMP + 1, Config::new(0));
        assert_eq!(g.next_id().unwrap_err(), Error::TimestampOverflow);
        let (g, _) = gen_at(EPOCH + MAX_TIMESTAMP, Config::new(0));
        assert!(g.next_id().is_ok());
    }
}
