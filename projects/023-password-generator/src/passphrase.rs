//! Diceware-style passphrases: several words picked uniformly at random.
//!
//! Security comes from the *size of the list* and the *number of words*,
//! never from the words being obscure. With the bundled 1,234-word list each
//! word adds log2(1234) ≈ 10.27 bits.

use crate::entropy;
use crate::rng::{RandomSource, RngError};
use std::fmt;

/// The bundled list: lowercase, 3–8 letters, de-duplicated, one per line.
pub const DEFAULT_WORDLIST: &str = include_str!("wordlist.txt");

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Case {
    Lower,
    Upper,
    /// Capitalise the first letter of each word.
    Title,
}

#[derive(Debug, Clone)]
pub struct PassphraseConfig {
    pub words: usize,
    pub separator: String,
    pub case: Case,
    /// Append one random digit to a random word (some sites demand digits).
    pub add_digit: bool,
}

impl Default for PassphraseConfig {
    fn default() -> Self {
        Self {
            words: 6,
            separator: "-".into(),
            case: Case::Lower,
            add_digit: false,
        }
    }
}

#[derive(Debug)]
pub enum PassphraseError {
    InvalidWordCount(usize),
    WordlistTooSmall(usize),
    Rng(RngError),
}

impl fmt::Display for PassphraseError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            PassphraseError::InvalidWordCount(n) => {
                write!(f, "word count must be 1..=64 (got {n})")
            }
            PassphraseError::WordlistTooSmall(n) => {
                write!(
                    f,
                    "wordlist must contain at least 2 distinct words (got {n})"
                )
            }
            PassphraseError::Rng(e) => write!(f, "{e}"),
        }
    }
}

impl std::error::Error for PassphraseError {}

impl From<RngError> for PassphraseError {
    fn from(e: RngError) -> Self {
        PassphraseError::Rng(e)
    }
}

/// Parses a wordlist: one word per line, `#` comments and blanks ignored.
/// Also accepts the EFF/diceware format `11111<TAB>word` by taking the last
/// whitespace-separated field. Words are de-duplicated (case-insensitively)
/// because duplicates would silently reduce entropy.
pub fn parse_wordlist(text: &str) -> Vec<String> {
    let mut seen = std::collections::HashSet::new();
    let mut words = Vec::new();
    for line in text.lines() {
        let line = line.trim();
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        if let Some(word) = line.split_whitespace().last() {
            if seen.insert(word.to_lowercase()) {
                words.push(word.to_string());
            }
        }
    }
    words
}

#[derive(Debug, Clone)]
pub struct PassphraseGenerator {
    words: Vec<String>,
    config: PassphraseConfig,
}

impl PassphraseGenerator {
    pub fn new(words: Vec<String>, config: PassphraseConfig) -> Result<Self, PassphraseError> {
        if config.words == 0 || config.words > 64 {
            return Err(PassphraseError::InvalidWordCount(config.words));
        }
        if words.len() < 2 {
            return Err(PassphraseError::WordlistTooSmall(words.len()));
        }
        Ok(Self { words, config })
    }

    pub fn with_default_list(config: PassphraseConfig) -> Result<Self, PassphraseError> {
        Self::new(parse_wordlist(DEFAULT_WORDLIST), config)
    }

    pub fn generate<R: RandomSource + ?Sized>(
        &self,
        rng: &mut R,
    ) -> Result<String, PassphraseError> {
        let mut parts: Vec<String> = Vec::with_capacity(self.config.words);
        for _ in 0..self.config.words {
            let w = rng.choose(&self.words)?;
            parts.push(apply_case(w, self.config.case));
        }
        if self.config.add_digit {
            let idx = rng.below(parts.len() as u32)? as usize;
            let digit = rng.below(10)?;
            parts[idx].push(char::from(b'0' + digit as u8));
        }
        Ok(parts.join(&self.config.separator))
    }

    /// Entropy in bits. Case and separator are fixed choices, so they add
    /// nothing; the optional digit adds log2(words × 10).
    pub fn entropy_bits(&self) -> f64 {
        let mut bits = entropy::uniform_bits(self.words.len(), self.config.words);
        if self.config.add_digit {
            bits += ((self.config.words * 10) as f64).log2();
        }
        bits
    }

    pub fn wordlist_len(&self) -> usize {
        self.words.len()
    }
}

fn apply_case(word: &str, case: Case) -> String {
    match case {
        Case::Lower => word.to_lowercase(),
        Case::Upper => word.to_uppercase(),
        Case::Title => {
            let mut chars = word.chars();
            match chars.next() {
                Some(first) => first
                    .to_uppercase()
                    .chain(chars.flat_map(char::to_lowercase))
                    .collect(),
                None => String::new(),
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::rng::SeededRng;

    #[test]
    fn bundled_list_is_clean() {
        let words = parse_wordlist(DEFAULT_WORDLIST);
        assert_eq!(words.len(), 1234);
        for w in &words {
            assert!((3..=8).contains(&w.len()), "{w}");
            assert!(w.chars().all(|c| c.is_ascii_lowercase()), "{w}");
        }
    }

    #[test]
    fn parses_diceware_format_and_dedupes() {
        let text = "# comment\n11111\tapple\n11112\tbanana\n\n11113\tApple\n";
        assert_eq!(parse_wordlist(text), vec!["apple", "banana"]);
    }

    #[test]
    fn generates_requested_shape() {
        let config = PassphraseConfig {
            words: 5,
            separator: ".".into(),
            case: Case::Title,
            add_digit: false,
        };
        let gen = PassphraseGenerator::with_default_list(config).unwrap();
        let p = gen.generate(&mut SeededRng::new(8)).unwrap();
        let parts: Vec<&str> = p.split('.').collect();
        assert_eq!(parts.len(), 5);
        for part in parts {
            assert!(part.chars().next().unwrap().is_ascii_uppercase(), "{p}");
        }
    }

    #[test]
    fn add_digit_appends_exactly_one_digit() {
        let config = PassphraseConfig {
            add_digit: true,
            ..Default::default()
        };
        let gen = PassphraseGenerator::with_default_list(config).unwrap();
        let mut rng = SeededRng::new(21);
        for _ in 0..100 {
            let p = gen.generate(&mut rng).unwrap();
            assert_eq!(p.chars().filter(char::is_ascii_digit).count(), 1, "{p}");
        }
    }

    #[test]
    fn entropy_math() {
        let gen = PassphraseGenerator::with_default_list(PassphraseConfig::default()).unwrap();
        let expected = 6.0 * 1234f64.log2();
        assert!((gen.entropy_bits() - expected).abs() < 1e-9);
        assert!(gen.entropy_bits() > 60.0);
    }

    #[test]
    fn rejects_bad_input() {
        assert!(matches!(
            PassphraseGenerator::new(vec!["one".into()], PassphraseConfig::default()),
            Err(PassphraseError::WordlistTooSmall(1))
        ));
        let zero = PassphraseConfig {
            words: 0,
            ..Default::default()
        };
        assert!(matches!(
            PassphraseGenerator::with_default_list(zero),
            Err(PassphraseError::InvalidWordCount(0))
        ));
    }
}
