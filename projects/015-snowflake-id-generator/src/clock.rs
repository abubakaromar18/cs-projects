//! Time sources.
//!
//! The generator is generic over [`Clock`] so tests can drive time by hand
//! (including making it jump *backwards*) instead of sleeping.

use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Arc;
use std::time::{SystemTime, UNIX_EPOCH};

/// A source of wall-clock milliseconds since the Unix epoch.
pub trait Clock: Send + Sync {
    /// Current Unix time in milliseconds.
    fn now_millis(&self) -> u64;

    /// Block until the clock reads strictly greater than `ms`, returning the
    /// new reading. Called when a millisecond's sequence space is exhausted.
    ///
    /// The default busy-waits with `yield_now`, which is fine because the wait
    /// is at most ~1 ms in the normal case.
    fn wait_past(&self, ms: u64) -> u64 {
        loop {
            let now = self.now_millis();
            if now > ms {
                return now;
            }
            std::thread::yield_now();
        }
    }
}

/// The real system clock.
#[derive(Debug, Default, Clone, Copy)]
pub struct SystemClock;

impl Clock for SystemClock {
    fn now_millis(&self) -> u64 {
        SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("system clock is before 1970")
            .as_millis() as u64
    }
}

/// A manually controlled clock for deterministic tests and simulations.
///
/// Cloning shares the same underlying time, so a test can keep one handle
/// and give another to the generator.
#[derive(Debug, Clone, Default)]
pub struct ManualClock {
    now: Arc<AtomicU64>,
}

impl ManualClock {
    /// Creates a clock frozen at `start_ms`.
    pub fn new(start_ms: u64) -> Self {
        Self {
            now: Arc::new(AtomicU64::new(start_ms)),
        }
    }

    /// Sets the time to an absolute value (may go backwards).
    pub fn set(&self, ms: u64) {
        self.now.store(ms, Ordering::SeqCst);
    }

    /// Moves time forward by `delta_ms`.
    pub fn advance(&self, delta_ms: u64) {
        self.now.fetch_add(delta_ms, Ordering::SeqCst);
    }
}

impl Clock for ManualClock {
    fn now_millis(&self) -> u64 {
        self.now.load(Ordering::SeqCst)
    }

    /// A frozen clock would wait forever, so instead "time passes": the clock
    /// jumps to `ms + 1` if it is not already past it.
    fn wait_past(&self, ms: u64) -> u64 {
        self.now.fetch_max(ms + 1, Ordering::SeqCst).max(ms + 1)
    }
}
