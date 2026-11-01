//! Random character passwords.

use crate::charset::{pool, CharClass, CharsetSpec};
use crate::entropy;
use crate::rng::{RandomSource, RngError};
use std::fmt;

/// Hard cap on length to keep memory and output sane.
pub const MAX_LENGTH: usize = 4096;

#[derive(Debug, Clone)]
pub struct PasswordConfig {
    pub length: usize,
    pub charset: CharsetSpec,
    /// Require at least one character from every enabled class.
    pub require_each_class: bool,
}

impl Default for PasswordConfig {
    fn default() -> Self {
        Self {
            length: 20,
            charset: CharsetSpec::default(),
            require_each_class: true,
        }
    }
}

#[derive(Debug)]
pub enum PasswordError {
    EmptyCharset,
    InvalidLength(usize),
    /// Fewer positions than required classes.
    TooShortForClasses {
        length: usize,
        classes: usize,
    },
    Rng(RngError),
}

impl fmt::Display for PasswordError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            PasswordError::EmptyCharset => {
                write!(
                    f,
                    "no characters left to choose from; enable a class or relax --exclude"
                )
            }
            PasswordError::InvalidLength(n) => {
                write!(f, "length must be between 1 and {MAX_LENGTH} (got {n})")
            }
            PasswordError::TooShortForClasses { length, classes } => write!(
                f,
                "length {length} cannot contain one character from each of {classes} classes; \
                 increase --length or pass --no-require"
            ),
            PasswordError::Rng(e) => write!(f, "{e}"),
        }
    }
}

impl std::error::Error for PasswordError {}

impl From<RngError> for PasswordError {
    fn from(e: RngError) -> Self {
        PasswordError::Rng(e)
    }
}

/// A validated generator: the expensive set-up (building the pool, checking
/// constraints) is done once and reused for every password in a batch.
#[derive(Debug, Clone)]
pub struct PasswordGenerator {
    length: usize,
    classes: Vec<CharClass>,
    pool: Vec<char>,
    require_each_class: bool,
}

impl PasswordGenerator {
    pub fn new(config: &PasswordConfig) -> Result<Self, PasswordError> {
        if config.length == 0 || config.length > MAX_LENGTH {
            return Err(PasswordError::InvalidLength(config.length));
        }
        let classes = config.charset.classes();
        let pool = pool(&classes);
        if pool.is_empty() {
            return Err(PasswordError::EmptyCharset);
        }
        if config.require_each_class && config.length < classes.len() {
            return Err(PasswordError::TooShortForClasses {
                length: config.length,
                classes: classes.len(),
            });
        }
        Ok(Self {
            length: config.length,
            classes,
            pool,
            require_each_class: config.require_each_class,
        })
    }

    /// Generates one password.
    ///
    /// When every class is required we use **rejection sampling**: draw a
    /// fully uniform string from the pool and retry if a class is missing.
    /// This yields a *uniform* distribution over all valid strings.
    ///
    /// The tempting alternative — "place one char from each class, fill the
    /// rest, then shuffle" — is subtly biased: it over-weights strings with
    /// few members of the small classes. Rejection is simple and exact, and
    /// for realistic lengths almost every attempt succeeds.
    pub fn generate<R: RandomSource + ?Sized>(&self, rng: &mut R) -> Result<String, PasswordError> {
        loop {
            let mut candidate = String::with_capacity(self.length);
            for _ in 0..self.length {
                candidate.push(*rng.choose(&self.pool)?);
            }
            if !self.require_each_class || self.has_every_class(&candidate) {
                return Ok(candidate);
            }
        }
    }

    fn has_every_class(&self, s: &str) -> bool {
        self.classes
            .iter()
            .all(|class| s.chars().any(|c| class.chars.contains(&c)))
    }

    /// Exact entropy of this generator's output distribution, in bits.
    pub fn entropy_bits(&self) -> f64 {
        if self.require_each_class {
            let sizes: Vec<usize> = self.classes.iter().map(|c| c.chars.len()).collect();
            entropy::constrained_bits(self.pool.len(), &sizes, self.length)
        } else {
            entropy::uniform_bits(self.pool.len(), self.length)
        }
    }

    pub fn pool_size(&self) -> usize {
        self.pool.len()
    }

    pub fn classes(&self) -> &[CharClass] {
        &self.classes
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::rng::SeededRng;

    #[test]
    fn respects_length_and_pool() {
        let gen = PasswordGenerator::new(&PasswordConfig::default()).unwrap();
        let mut rng = SeededRng::new(3);
        for _ in 0..200 {
            let pw = gen.generate(&mut rng).unwrap();
            assert_eq!(pw.chars().count(), 20);
            assert!(pw.chars().all(|c| c.is_ascii_graphic()));
        }
    }

    #[test]
    fn every_class_present_when_required() {
        let config = PasswordConfig {
            length: 4,
            ..Default::default()
        };
        let gen = PasswordGenerator::new(&config).unwrap();
        let mut rng = SeededRng::new(11);
        for _ in 0..500 {
            let pw = gen.generate(&mut rng).unwrap();
            assert!(pw.chars().any(|c| c.is_ascii_lowercase()), "{pw}");
            assert!(pw.chars().any(|c| c.is_ascii_uppercase()), "{pw}");
            assert!(pw.chars().any(|c| c.is_ascii_digit()), "{pw}");
            assert!(pw.chars().any(|c| c.is_ascii_punctuation()), "{pw}");
        }
    }

    #[test]
    fn rejects_bad_configs() {
        let zero = PasswordConfig {
            length: 0,
            ..Default::default()
        };
        assert!(matches!(
            PasswordGenerator::new(&zero),
            Err(PasswordError::InvalidLength(0))
        ));

        let short = PasswordConfig {
            length: 3,
            ..Default::default()
        };
        assert!(matches!(
            PasswordGenerator::new(&short),
            Err(PasswordError::TooShortForClasses { .. })
        ));

        let empty = PasswordConfig {
            charset: CharsetSpec {
                lower: false,
                upper: false,
                digits: false,
                symbols: false,
                ..Default::default()
            },
            ..Default::default()
        };
        assert!(matches!(
            PasswordGenerator::new(&empty),
            Err(PasswordError::EmptyCharset)
        ));
    }

    #[test]
    fn pin_style_digits_only() {
        let config = PasswordConfig {
            length: 6,
            charset: CharsetSpec {
                lower: false,
                upper: false,
                symbols: false,
                ..Default::default()
            },
            ..Default::default()
        };
        let gen = PasswordGenerator::new(&config).unwrap();
        let pw = gen.generate(&mut SeededRng::new(5)).unwrap();
        assert!(pw.chars().all(|c| c.is_ascii_digit()));
        // 10^6 possibilities → log2(10^6) ≈ 19.93 bits
        assert!((gen.entropy_bits() - 19.931568569324174).abs() < 1e-9);
    }

    #[test]
    fn rejection_sampling_is_uniform_over_valid_strings() {
        // Pool {a, B} with both classes required, length 3.
        // Valid strings: all 8 except "aaa" and "BBB" → 6, each p = 1/6.
        let config = PasswordConfig {
            length: 3,
            charset: CharsetSpec {
                digits: false,
                symbols: false,
                exclude: "bcdefghijklmnopqrstuvwxyzACDEFGHIJKLMNOPQRSTUVWXYZ".into(),
                ..Default::default()
            },
            require_each_class: true,
        };
        let gen = PasswordGenerator::new(&config).unwrap();
        assert_eq!(gen.pool_size(), 2);
        let mut rng = SeededRng::new(99);
        let mut counts = std::collections::HashMap::new();
        let n = 60_000;
        for _ in 0..n {
            *counts
                .entry(gen.generate(&mut rng).unwrap())
                .or_insert(0u32) += 1;
        }
        assert_eq!(counts.len(), 6);
        for (pw, c) in &counts {
            let share = *c as f64 / n as f64;
            assert!((share - 1.0 / 6.0).abs() < 0.01, "{pw}: {share}");
        }
        assert!((gen.entropy_bits() - 6f64.log2()).abs() < 1e-9);
    }
}
