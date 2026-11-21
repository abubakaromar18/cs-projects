//! `confparse` — a small, dependency-free parser for TOML (practical subset) and INI files
//! that focuses on precise, friendly error messages.
//!
//! ```
//! use confparse::{parse_toml, Value};
//!
//! let doc = parse_toml("[server]\nport = 8080\n").unwrap();
//! assert_eq!(doc["server"].as_table().unwrap()["port"], Value::Integer(8080));
//! ```

pub mod error;
pub mod parser;
pub mod value;

pub use error::{ErrorKind, ParseError, Pos};
pub use parser::Dialect;
pub use value::{Table, Value};

/// Parse a TOML document.
pub fn parse_toml(src: &str) -> Result<Table, ParseError> {
    parser::Parser::new(src, Dialect::Toml).parse()
}

/// Parse a classic INI document (all values are strings).
pub fn parse_ini(src: &str) -> Result<Table, ParseError> {
    parser::Parser::new(src, Dialect::Ini).parse()
}

/// Parse with an explicit dialect.
pub fn parse(src: &str, dialect: Dialect) -> Result<Table, ParseError> {
    parser::Parser::new(src, dialect).parse()
}

/// Guess the dialect from a file name: `.ini`, `.cfg`, `.conf` → INI, otherwise TOML.
pub fn dialect_for_path(path: &str) -> Dialect {
    let lower = path.to_ascii_lowercase();
    if [".ini", ".cfg", ".conf"].iter().any(|ext| lower.ends_with(ext)) {
        Dialect::Ini
    } else {
        Dialect::Toml
    }
}
