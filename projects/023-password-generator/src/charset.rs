//! Character classes and the alphabet a password is drawn from.

/// Lowercase ASCII letters.
pub const LOWER: &str = "abcdefghijklmnopqrstuvwxyz";
/// Uppercase ASCII letters.
pub const UPPER: &str = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
/// Decimal digits.
pub const DIGITS: &str = "0123456789";
/// Printable ASCII punctuation (32 symbols; space excluded on purpose).
pub const SYMBOLS: &str = "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~";
/// Glyphs that are easily confused when read aloud or written down.
pub const AMBIGUOUS: &str = "Il1|O0o`'\"";

/// One class of characters, e.g. "digits".
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CharClass {
    pub name: &'static str,
    pub chars: Vec<char>,
}

impl CharClass {
    /// Builds a class from `source`, dropping anything in `exclude`.
    /// Duplicate characters are removed so they cannot skew the distribution.
    pub fn new(name: &'static str, source: &str, exclude: &str) -> Self {
        let mut chars: Vec<char> = Vec::new();
        for c in source.chars() {
            if !exclude.contains(c) && !chars.contains(&c) {
                chars.push(c);
            }
        }
        Self { name, chars }
    }

    pub fn is_empty(&self) -> bool {
        self.chars.is_empty()
    }
}

/// Which built-in classes to include, plus user tweaks.
#[derive(Debug, Clone)]
pub struct CharsetSpec {
    pub lower: bool,
    pub upper: bool,
    pub digits: bool,
    pub symbols: bool,
    /// Drop look-alike glyphs such as `l`, `1`, `O`, `0`.
    pub no_ambiguous: bool,
    /// Additional characters the user never wants to see.
    pub exclude: String,
    /// Extra characters forming their own class.
    pub custom: String,
}

impl Default for CharsetSpec {
    fn default() -> Self {
        Self {
            lower: true,
            upper: true,
            digits: true,
            symbols: true,
            no_ambiguous: false,
            exclude: String::new(),
            custom: String::new(),
        }
    }
}

impl CharsetSpec {
    /// Resolves the spec into concrete, non-empty character classes.
    pub fn classes(&self) -> Vec<CharClass> {
        let mut exclude = self.exclude.clone();
        if self.no_ambiguous {
            exclude.push_str(AMBIGUOUS);
        }
        let mut out = Vec::new();
        let wanted = [
            (self.lower, "lowercase", LOWER),
            (self.upper, "uppercase", UPPER),
            (self.digits, "digits", DIGITS),
            (self.symbols, "symbols", SYMBOLS),
        ];
        for (enabled, name, src) in wanted {
            if enabled {
                out.push(CharClass::new(name, src, &exclude));
            }
        }
        if !self.custom.is_empty() {
            // Custom chars that already appear in another class would be
            // double-counted in the pool, so strip them here.
            let mut ex = exclude.clone();
            for class in &out {
                ex.extend(class.chars.iter());
            }
            out.push(CharClass::new("custom", &self.custom, &ex));
        }
        out.retain(|c| !c.is_empty());
        out
    }
}

/// The union of all classes — the alphabet each "free" position draws from.
pub fn pool(classes: &[CharClass]) -> Vec<char> {
    let mut all: Vec<char> = Vec::new();
    for class in classes {
        for &c in &class.chars {
            if !all.contains(&c) {
                all.push(c);
            }
        }
    }
    all
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn default_pool_is_all_printable_ascii_but_space() {
        let p = pool(&CharsetSpec::default().classes());
        assert_eq!(p.len(), 26 + 26 + 10 + 32);
        assert_eq!(p.len(), 94);
    }

    #[test]
    fn no_ambiguous_removes_lookalikes() {
        let spec = CharsetSpec {
            no_ambiguous: true,
            ..Default::default()
        };
        let p = pool(&spec.classes());
        for c in AMBIGUOUS.chars() {
            assert!(!p.contains(&c), "{c:?} should be excluded");
        }
    }

    #[test]
    fn exclude_and_empty_classes_are_dropped() {
        let spec = CharsetSpec {
            lower: false,
            upper: false,
            symbols: false,
            exclude: DIGITS.to_string(),
            custom: "xyz".into(),
            ..Default::default()
        };
        let classes = spec.classes();
        assert_eq!(classes.len(), 1);
        assert_eq!(classes[0].name, "custom");
        assert_eq!(classes[0].chars, vec!['x', 'y', 'z']);
    }

    #[test]
    fn custom_chars_overlapping_builtins_are_deduplicated() {
        let spec = CharsetSpec {
            custom: "aé".into(),
            ..Default::default()
        };
        let classes = spec.classes();
        let custom = classes.iter().find(|c| c.name == "custom").unwrap();
        assert_eq!(custom.chars, vec!['é']);
    }
}
