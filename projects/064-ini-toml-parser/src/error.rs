//! Parse errors that point at the exact line and column, rustc-style.

use std::fmt;

/// A 1-based source position.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Pos {
    pub line: usize,
    pub col: usize,
}

/// What went wrong. Kept as an enum so callers (and tests) can match on it.
#[derive(Debug, Clone, PartialEq)]
pub enum ErrorKind {
    UnexpectedChar { found: char, expected: &'static str },
    UnexpectedEof { expected: &'static str },
    UnterminatedString,
    InvalidEscape(char),
    InvalidUnicodeEscape,
    NewlineInString,
    InvalidNumber(String),
    IntegerOverflow(String),
    DuplicateKey(String),
    TableRedefined(String),
    NotATable { key: String, found: &'static str },
    EmptyKey,
}

impl fmt::Display for ErrorKind {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        use ErrorKind::*;
        match self {
            UnexpectedChar { found, expected } => {
                write!(f, "unexpected {}, expected {expected}", describe(*found))
            }
            UnexpectedEof { expected } => write!(f, "unexpected end of input, expected {expected}"),
            UnterminatedString => write!(f, "unterminated string"),
            InvalidEscape(c) => write!(f, "invalid escape sequence `\\{c}`"),
            InvalidUnicodeEscape => write!(f, "invalid unicode escape (expected \\uXXXX or \\UXXXXXXXX)"),
            NewlineInString => write!(f, "newline in single-line string (use \"\"\" for multi-line)"),
            InvalidNumber(s) => write!(f, "invalid number `{s}`"),
            IntegerOverflow(s) => write!(f, "integer `{s}` does not fit in 64 bits"),
            DuplicateKey(k) => write!(f, "duplicate key `{k}`"),
            TableRedefined(k) => write!(f, "table `[{k}]` is defined more than once"),
            NotATable { key, found } => {
                write!(f, "cannot use `{key}` as a table, it is already a {found}")
            }
            EmptyKey => write!(f, "expected a key name"),
        }
    }
}

fn describe(c: char) -> String {
    match c {
        '\n' => "end of line".to_string(),
        '\t' => "tab".to_string(),
        c => format!("character `{c}`"),
    }
}

/// A parse error plus enough context to render a helpful message.
#[derive(Debug, Clone, PartialEq)]
pub struct ParseError {
    pub kind: ErrorKind,
    pub pos: Pos,
    /// The full text of the offending line (without the newline).
    pub line_text: String,
    /// An optional hint, e.g. "first defined on line 3".
    pub note: Option<String>,
}

impl ParseError {
    /// Render with a filename header, e.g. `error: ... --> app.toml:3:7`.
    pub fn render(&self, filename: &str) -> String {
        let num = self.pos.line.to_string();
        let gutter = " ".repeat(num.len());
        // Expand tabs so the caret lines up with what the terminal shows.
        let shown: String = self.line_text.replace('\t', "    ");
        let caret_offset: usize = self
            .line_text
            .chars()
            .take(self.pos.col.saturating_sub(1))
            .map(|c| if c == '\t' { 4 } else { 1 })
            .sum();
        let mut s = format!(
            "error: {}\n{gutter} --> {filename}:{}:{}\n{gutter} |\n{num} | {shown}\n{gutter} | {}^",
            self.kind,
            self.pos.line,
            self.pos.col,
            " ".repeat(caret_offset)
        );
        if let Some(note) = &self.note {
            s.push_str(&format!("\n{gutter} = note: {note}"));
        }
        s
    }
}

impl fmt::Display for ParseError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{} at line {}, column {}", self.kind, self.pos.line, self.pos.col)
    }
}

impl std::error::Error for ParseError {}
