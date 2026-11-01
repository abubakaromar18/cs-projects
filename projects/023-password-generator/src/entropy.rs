//! Entropy accounting.
//!
//! Entropy here means the base-2 logarithm of the number of equally likely
//! outputs the generator could have produced. It measures the generator,
//! not a particular string — that is the only honest way to rate a password
//! that was chosen uniformly at random.

/// Bits of entropy for `length` independent uniform picks from `pool_size`.
pub fn uniform_bits(pool_size: usize, length: usize) -> f64 {
    if pool_size <= 1 || length == 0 {
        return 0.0;
    }
    length as f64 * (pool_size as f64).log2()
}

/// Probability that a uniformly random string of `length` characters drawn
/// from a pool of `pool_size` contains **at least one** character from every
/// class, where `class_sizes` are the sizes of disjoint classes partitioning
/// the pool.
///
/// Computed by inclusion–exclusion over the set of classes that are
/// *missing*:
///
/// ```text
/// P = Σ_{S ⊆ classes} (-1)^|S| · (1 − |∪S| / N)^L
/// ```
///
/// Working with probabilities (rather than raw counts like N^L, which
/// overflow quickly) keeps everything comfortably inside an `f64`.
pub fn all_classes_probability(pool_size: usize, class_sizes: &[usize], length: usize) -> f64 {
    let n = pool_size as f64;
    let k = class_sizes.len();
    assert!(k < 32, "too many classes for subset enumeration");
    let mut p = 0.0;
    for mask in 0u32..(1 << k) {
        let missing: usize = (0..k)
            .filter(|i| mask & (1 << i) != 0)
            .map(|i| class_sizes[i])
            .sum();
        let sign = if mask.count_ones() % 2 == 0 {
            1.0
        } else {
            -1.0
        };
        p += sign * (1.0 - missing as f64 / n).powi(length as i32);
    }
    p.clamp(0.0, 1.0)
}

/// Exact entropy when the generator samples uniformly from strings that
/// contain every class (what [`crate::password`] does via rejection):
/// `log2(N^L · P) = L·log2(N) + log2(P)`.
pub fn constrained_bits(pool_size: usize, class_sizes: &[usize], length: usize) -> f64 {
    let p = all_classes_probability(pool_size, class_sizes, length);
    if p == 0.0 {
        return 0.0;
    }
    (uniform_bits(pool_size, length) + p.log2()).max(0.0)
}

/// Coarse human-readable rating for a number of bits.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum Strength {
    VeryWeak,
    Weak,
    Reasonable,
    Strong,
    VeryStrong,
}

impl Strength {
    /// Thresholds loosely follow common guidance: < 40 bits is crackable
    /// offline in hours to days; ≥ 128 bits is beyond brute force.
    pub fn from_bits(bits: f64) -> Self {
        match bits {
            b if b < 28.0 => Strength::VeryWeak,
            b if b < 40.0 => Strength::Weak,
            b if b < 60.0 => Strength::Reasonable,
            b if b < 128.0 => Strength::Strong,
            _ => Strength::VeryStrong,
        }
    }

    pub fn label(self) -> &'static str {
        match self {
            Strength::VeryWeak => "very weak",
            Strength::Weak => "weak",
            Strength::Reasonable => "reasonable",
            Strength::Strong => "strong",
            Strength::VeryStrong => "very strong",
        }
    }
}

/// Rough time to exhaust half the keyspace at `guesses_per_sec`,
/// formatted for humans.
pub fn crack_time(bits: f64, guesses_per_sec: f64) -> String {
    let seconds = 2f64.powf(bits - 1.0) / guesses_per_sec;
    const UNITS: [(&str, f64); 6] = [
        ("years", 365.25 * 86400.0),
        ("days", 86400.0),
        ("hours", 3600.0),
        ("minutes", 60.0),
        ("seconds", 1.0),
        ("seconds", 0.0),
    ];
    if seconds > 1e12 * UNITS[0].1 {
        return "longer than the age of the universe".into();
    }
    for (name, size) in UNITS {
        if size > 0.0 && seconds >= size {
            return format!("~{:.1} {}", seconds / size, name);
        }
    }
    "less than a second".into()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn close(a: f64, b: f64) -> bool {
        (a - b).abs() < 1e-9
    }

    #[test]
    fn uniform_bits_basics() {
        assert!(close(uniform_bits(2, 10), 10.0));
        assert!(close(uniform_bits(16, 4), 16.0));
        assert_eq!(uniform_bits(1, 100), 0.0);
        assert_eq!(uniform_bits(94, 0), 0.0);
    }

    #[test]
    fn all_classes_probability_matches_brute_force() {
        // Pool {a,b,c} split into classes {a} and {b,c}; length 2.
        // Strings: 9 total; valid = those with an 'a' and a 'b'/'c' = 4.
        let p = all_classes_probability(3, &[1, 2], 2);
        assert!(close(p, 4.0 / 9.0), "p = {p}");
    }

    #[test]
    fn impossible_when_shorter_than_class_count() {
        let p = all_classes_probability(94, &[26, 26, 10, 32], 3);
        assert!(close(p, 0.0), "p = {p}");
        assert_eq!(constrained_bits(94, &[26, 26, 10, 32], 3), 0.0);
    }

    #[test]
    fn constraint_costs_little_entropy_for_long_passwords() {
        let classes = [26, 26, 10, 32];
        let free = uniform_bits(94, 20);
        let constrained = constrained_bits(94, &classes, 20);
        assert!(constrained < free);
        assert!(free - constrained < 0.5, "lost {} bits", free - constrained);
    }

    #[test]
    fn strength_thresholds() {
        assert_eq!(Strength::from_bits(10.0), Strength::VeryWeak);
        assert_eq!(Strength::from_bits(39.9), Strength::Weak);
        assert_eq!(Strength::from_bits(50.0), Strength::Reasonable);
        assert_eq!(Strength::from_bits(80.0), Strength::Strong);
        assert_eq!(Strength::from_bits(200.0), Strength::VeryStrong);
    }

    #[test]
    fn crack_time_formats() {
        assert_eq!(crack_time(1.0, 1e10), "less than a second");
        assert!(
            crack_time(60.0, 1e10).contains("years") || crack_time(60.0, 1e10).contains("days")
        );
        assert_eq!(
            crack_time(256.0, 1e10),
            "longer than the age of the universe"
        );
    }
}
