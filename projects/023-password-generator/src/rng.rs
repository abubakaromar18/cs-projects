//! Random number sources and *unbiased* sampling helpers.
//!
//! The hard part of a password generator is not producing random bytes —
//! the OS does that for us — but turning those bytes into a uniformly
//! distributed choice among `n` items. The naive `byte % n` is **biased**
//! whenever `n` does not divide 256 (or 2^32): low values come up slightly
//! more often. We use *rejection sampling* to eliminate that bias.

use std::fmt;

/// Error raised when the operating system cannot provide randomness.
#[derive(Debug)]
pub struct RngError(String);

impl fmt::Display for RngError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "random source failure: {}", self.0)
    }
}

impl std::error::Error for RngError {}

/// A source of uniformly random 32-bit words.
///
/// Abstracting over the source lets production code use the OS CSPRNG
/// while tests use a seeded, reproducible generator.
pub trait RandomSource {
    fn next_u32(&mut self) -> Result<u32, RngError>;

    /// Returns a uniformly distributed integer in `0..bound`.
    ///
    /// Uses rejection sampling ("Lemire-free" simple variant): we discard
    /// values from the top partial bucket of the 2^32 range so every residue
    /// class mod `bound` has exactly the same number of pre-images.
    ///
    /// # Panics
    /// Panics if `bound == 0`.
    fn below(&mut self, bound: u32) -> Result<u32, RngError> {
        assert!(bound > 0, "bound must be positive");
        // Largest multiple of `bound` that fits in u32's range (2^32).
        // Values >= `zone` would make some residues over-represented.
        let zone = u32::MAX - (u32::MAX - bound + 1) % bound;
        loop {
            let x = self.next_u32()?;
            if x <= zone {
                return Ok(x % bound);
            }
        }
    }

    /// Picks a uniformly random element of a non-empty slice.
    fn choose<'a, T>(&mut self, items: &'a [T]) -> Result<&'a T, RngError> {
        let idx = self.below(items.len() as u32)? as usize;
        Ok(&items[idx])
    }

    /// In-place Fisher–Yates shuffle: every permutation is equally likely
    /// (given an unbiased `below`).
    fn shuffle<T>(&mut self, items: &mut [T]) -> Result<(), RngError> {
        for i in (1..items.len()).rev() {
            let j = self.below((i + 1) as u32)? as usize;
            items.swap(i, j);
        }
        Ok(())
    }
}

/// Cryptographically secure randomness from the operating system.
#[derive(Debug, Default, Clone, Copy)]
pub struct OsRng;

impl RandomSource for OsRng {
    fn next_u32(&mut self) -> Result<u32, RngError> {
        let mut buf = [0u8; 4];
        getrandom::getrandom(&mut buf).map_err(|e| RngError(e.to_string()))?;
        Ok(u32::from_le_bytes(buf))
    }
}

/// Deterministic xorshift64* generator.
///
/// **Not** cryptographically secure — used only for reproducible tests and
/// the `--seed` debugging flag (which the CLI marks as insecure).
#[derive(Debug, Clone)]
pub struct SeededRng {
    state: u64,
}

impl SeededRng {
    pub fn new(seed: u64) -> Self {
        // xorshift must never have an all-zero state.
        Self {
            state: if seed == 0 {
                0x9E37_79B9_7F4A_7C15
            } else {
                seed
            },
        }
    }
}

impl RandomSource for SeededRng {
    fn next_u32(&mut self) -> Result<u32, RngError> {
        let mut x = self.state;
        x ^= x >> 12;
        x ^= x << 25;
        x ^= x >> 27;
        self.state = x;
        Ok((x.wrapping_mul(0x2545_F491_4F6C_DD1D) >> 32) as u32)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// A source that replays a fixed script, to test rejection logic exactly.
    struct Scripted(Vec<u32>);
    impl RandomSource for Scripted {
        fn next_u32(&mut self) -> Result<u32, RngError> {
            Ok(self.0.remove(0))
        }
    }

    #[test]
    fn below_rejects_values_in_partial_bucket() {
        // For bound = 3, 2^32 mod 3 = 1, so exactly one value (u32::MAX)
        // must be rejected. The next value (7) is accepted: 7 % 3 = 1.
        let mut rng = Scripted(vec![u32::MAX, 7]);
        assert_eq!(rng.below(3).unwrap(), 1);
    }

    #[test]
    fn below_power_of_two_never_rejects() {
        let mut rng = Scripted(vec![u32::MAX]);
        assert_eq!(rng.below(256).unwrap(), 255);
    }

    #[test]
    fn below_stays_in_range() {
        let mut rng = SeededRng::new(42);
        for bound in [1u32, 2, 3, 7, 10, 62, 94, 1000] {
            for _ in 0..500 {
                assert!(rng.below(bound).unwrap() < bound);
            }
        }
    }

    #[test]
    fn below_is_roughly_uniform() {
        // Chi-squared goodness-of-fit over 10 buckets. With 9 degrees of
        // freedom the 99.9th percentile is ~27.9; a fixed seed keeps it stable.
        let mut rng = SeededRng::new(7);
        let n = 100_000;
        let mut counts = [0u32; 10];
        for _ in 0..n {
            counts[rng.below(10).unwrap() as usize] += 1;
        }
        let expected = n as f64 / 10.0;
        let chi2: f64 = counts
            .iter()
            .map(|&c| (c as f64 - expected).powi(2) / expected)
            .sum();
        assert!(chi2 < 27.9, "chi2 = {chi2}, counts = {counts:?}");
    }

    #[test]
    fn shuffle_is_a_permutation() {
        let mut rng = SeededRng::new(1);
        let mut v: Vec<u32> = (0..50).collect();
        rng.shuffle(&mut v).unwrap();
        let mut sorted = v.clone();
        sorted.sort();
        assert_eq!(sorted, (0..50).collect::<Vec<_>>());
        assert_ne!(v, sorted, "50 elements should virtually never stay sorted");
    }

    #[test]
    fn os_rng_produces_varied_output() {
        let mut rng = OsRng;
        let a: Vec<u32> = (0..8).map(|_| rng.next_u32().unwrap()).collect();
        let b: Vec<u32> = (0..8).map(|_| rng.next_u32().unwrap()).collect();
        assert_ne!(a, b);
    }
}
