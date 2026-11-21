//! A hand-written recursive-descent parser for TOML (a practical subset) and classic INI.
//!
//! The parser works directly on a `Vec<char>` with a cursor; there is no separate
//! lexer because TOML's lexical rules are context-sensitive (e.g. `1979` is an
//! integer as a value but a bare key on the left of `=`). Every error records the
//! character index where it happened, which is mapped back to line/column at the end.

use std::collections::{HashMap, HashSet};

use crate::error::{ErrorKind, ParseError, Pos};
use crate::value::{Table, Value};

/// Which syntax to accept.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Dialect {
    /// TOML: typed values, dotted keys, nested tables, arrays of tables.
    Toml,
    /// INI: `[section]` headers, `key = value` or `key: value`, `;`/`#` comments,
    /// values are always strings. Sections are one level deep.
    Ini,
}

/// Internal error: kind + character index (+ optional note).
struct Fail {
    kind: ErrorKind,
    at: usize,
    note: Option<String>,
}

type PResult<T> = Result<T, Fail>;

fn fail<T>(kind: ErrorKind, at: usize) -> PResult<T> {
    Err(Fail { kind, at, note: None })
}

pub struct Parser {
    chars: Vec<char>,
    i: usize,
    dialect: Dialect,
    root: Table,
    /// Path of the table that `key = value` lines currently write into.
    current: Vec<String>,
    /// Identity string of `current` (includes array-of-table indices) for bookkeeping.
    current_ident: String,
    /// Tables opened explicitly with `[header]`, mapped to the line they were defined on.
    defined_tables: HashMap<String, usize>,
    /// Paths created with `[[header]]` (so we know which arrays may be appended to).
    table_arrays: HashSet<String>,
    /// Every assigned key (by identity) to the line of its first definition.
    key_lines: HashMap<String, usize>,
}

impl Parser {
    pub fn new(src: &str, dialect: Dialect) -> Self {
        Parser {
            chars: src.chars().collect(),
            i: 0,
            dialect,
            root: Table::new(),
            current: Vec::new(),
            current_ident: String::new(),
            defined_tables: HashMap::new(),
            table_arrays: HashSet::new(),
            key_lines: HashMap::new(),
        }
    }

    /// Parse the whole document into a root table.
    pub fn parse(mut self) -> Result<Table, ParseError> {
        // Tolerate a UTF-8 byte-order mark.
        if self.peek() == Some('\u{feff}') {
            self.i += 1;
        }
        match self.document() {
            Ok(()) => Ok(self.root),
            Err(f) => Err(self.to_error(f)),
        }
    }

    // ------------------------------------------------------------------
    // Cursor helpers
    // ------------------------------------------------------------------

    fn peek(&self) -> Option<char> {
        self.chars.get(self.i).copied()
    }

    fn peek_at(&self, n: usize) -> Option<char> {
        self.chars.get(self.i + n).copied()
    }

    fn bump(&mut self) -> Option<char> {
        let c = self.peek();
        if c.is_some() {
            self.i += 1;
        }
        c
    }

    fn starts_with(&self, s: &str) -> bool {
        s.chars().enumerate().all(|(n, c)| self.peek_at(n) == Some(c))
    }

    fn eat(&mut self, c: char) -> bool {
        if self.peek() == Some(c) {
            self.i += 1;
            true
        } else {
            false
        }
    }

    fn expect(&mut self, c: char, expected: &'static str) -> PResult<()> {
        match self.peek() {
            Some(x) if x == c => {
                self.i += 1;
                Ok(())
            }
            Some(found) => fail(ErrorKind::UnexpectedChar { found, expected }, self.i),
            None => fail(ErrorKind::UnexpectedEof { expected }, self.i),
        }
    }

    /// Skip spaces and tabs (not newlines).
    fn skip_ws(&mut self) {
        while matches!(self.peek(), Some(' ' | '\t')) {
            self.i += 1;
        }
    }

    fn is_comment_start(&self, c: char) -> bool {
        c == '#' || (self.dialect == Dialect::Ini && c == ';')
    }

    fn skip_comment(&mut self) {
        if let Some(c) = self.peek() {
            if self.is_comment_start(c) {
                while !matches!(self.peek(), None | Some('\n')) {
                    self.i += 1;
                }
            }
        }
    }

    /// Consume a newline (`\n` or `\r\n`). Returns false if none present.
    fn eat_newline(&mut self) -> bool {
        if self.starts_with("\r\n") {
            self.i += 2;
            true
        } else {
            self.eat('\n')
        }
    }

    /// Skip whitespace, comments and newlines (used inside arrays).
    fn skip_ws_comments_newlines(&mut self) {
        loop {
            self.skip_ws();
            self.skip_comment();
            if !self.eat_newline() {
                break;
            }
        }
    }

    /// After a statement, only whitespace and a comment may precede the newline.
    fn end_of_line(&mut self) -> PResult<()> {
        self.skip_ws();
        self.skip_comment();
        if self.peek().is_none() || self.eat_newline() {
            return Ok(());
        }
        let found = self.peek().unwrap();
        fail(ErrorKind::UnexpectedChar { found, expected: "end of line" }, self.i)
    }

    fn line_of(&self, idx: usize) -> usize {
        1 + self.chars[..idx.min(self.chars.len())].iter().filter(|&&c| c == '\n').count()
    }

    /// Convert an internal failure into a public `ParseError` with line/column info.
    fn to_error(&self, f: Fail) -> ParseError {
        let at = f.at.min(self.chars.len());
        let line_start = self.chars[..at].iter().rposition(|&c| c == '\n').map_or(0, |p| p + 1);
        let line_end = self.chars[at..]
            .iter()
            .position(|&c| c == '\n')
            .map_or(self.chars.len(), |p| at + p);
        let line_text: String = self.chars[line_start..line_end]
            .iter()
            .collect::<String>()
            .trim_end_matches('\r')
            .to_string();
        ParseError {
            kind: f.kind,
            pos: Pos { line: self.line_of(at), col: at - line_start + 1 },
            line_text,
            note: f.note,
        }
    }

    // ------------------------------------------------------------------
    // Document structure
    // ------------------------------------------------------------------

    fn document(&mut self) -> PResult<()> {
        loop {
            self.skip_ws();
            match self.peek() {
                None => return Ok(()),
                Some('\n') | Some('\r') => {
                    if !self.eat_newline() {
                        return fail(
                            ErrorKind::UnexpectedChar { found: '\r', expected: "a newline after `\\r`" },
                            self.i,
                        );
                    }
                }
                Some(c) if self.is_comment_start(c) => self.skip_comment(),
                Some('[') => {
                    match self.dialect {
                        Dialect::Toml => self.toml_header()?,
                        Dialect::Ini => self.ini_header()?,
                    }
                    self.end_of_line()?;
                }
                Some(_) => {
                    match self.dialect {
                        Dialect::Toml => self.toml_keyval_line()?,
                        Dialect::Ini => self.ini_keyval_line()?,
                    }
                }
            }
        }
    }

    // ------------------------------------------------------------------
    // INI
    // ------------------------------------------------------------------

    fn ini_header(&mut self) -> PResult<()> {
        let open = self.i;
        self.bump(); // '['
        let start = self.i;
        while !matches!(self.peek(), None | Some(']' | '\n')) {
            self.i += 1;
        }
        let name: String = self.chars[start..self.i].iter().collect::<String>().trim().to_string();
        if self.peek() != Some(']') {
            return match self.peek() {
                None => fail(ErrorKind::UnexpectedEof { expected: "`]` to close the section header" }, self.i),
                Some(found) => fail(ErrorKind::UnexpectedChar { found, expected: "`]` to close the section header" }, self.i),
            };
        }
        self.bump();
        if name.is_empty() {
            return fail(ErrorKind::EmptyKey, open + 1);
        }
        let line = self.line_of(open);
        if let Some(&first) = self.defined_tables.get(&name) {
            return Err(Fail {
                kind: ErrorKind::TableRedefined(name),
                at: open,
                note: Some(format!("first defined on line {first}")),
            });
        }
        if let Some(existing) = self.root.get(&name) {
            if !matches!(existing, Value::Table(_)) {
                return Err(Fail {
                    kind: ErrorKind::NotATable { key: name.clone(), found: existing.type_name() },
                    at: open,
                    note: self.key_lines.get(&name).map(|l| format!("`{name}` was set on line {l}")),
                });
            }
        }
        self.defined_tables.insert(name.clone(), line);
        self.root.entry(name.clone()).or_insert_with(|| Value::Table(Table::new()));
        self.current = vec![name.clone()];
        self.current_ident = name;
        Ok(())
    }

    fn ini_keyval_line(&mut self) -> PResult<()> {
        let key_start = self.i;
        while !matches!(self.peek(), None | Some('=' | ':' | '\n')) {
            self.i += 1;
        }
        let key: String = self.chars[key_start..self.i].iter().collect::<String>().trim().to_string();
        if key.is_empty() {
            return fail(ErrorKind::EmptyKey, key_start);
        }
        match self.peek() {
            Some('=' | ':') => {
                self.bump();
            }
            Some(found) => {
                return fail(ErrorKind::UnexpectedChar { found, expected: "`=` or `:` after the key" }, self.i)
            }
            None => return fail(ErrorKind::UnexpectedEof { expected: "`=` or `:` after the key" }, self.i),
        }
        self.skip_ws();

        // A quoted value keeps everything inside the quotes verbatim.
        let value = if matches!(self.peek(), Some('"' | '\'')) {
            let q = self.bump().unwrap();
            let start = self.i;
            while !matches!(self.peek(), None | Some('\n')) && self.peek() != Some(q) {
                self.i += 1;
            }
            if self.peek() != Some(q) {
                return fail(ErrorKind::UnterminatedString, start - 1);
            }
            let s: String = self.chars[start..self.i].iter().collect();
            self.bump();
            self.end_of_line()?;
            s
        } else {
            // Unquoted: rest of the line, with an inline comment stripped only when
            // the comment marker follows whitespace (so `url = a#b` keeps its `#`).
            let start = self.i;
            while !matches!(self.peek(), None | Some('\n')) {
                let c = self.peek().unwrap();
                if self.is_comment_start(c) && matches!(self.chars.get(self.i.wrapping_sub(1)), Some(' ' | '\t')) {
                    break;
                }
                self.i += 1;
            }
            let s: String = self.chars[start..self.i].iter().collect::<String>().trim().to_string();
            self.skip_comment();
            self.eat_newline();
            s
        };

        let ident = if self.current_ident.is_empty() { key.clone() } else { format!("{}\u{0}{key}", self.current_ident) };
        let line = self.line_of(key_start);
        if let Some(&first) = self.key_lines.get(&ident) {
            return Err(Fail {
                kind: ErrorKind::DuplicateKey(key),
                at: key_start,
                note: Some(format!("first defined on line {first}")),
            });
        }
        // A root-level key may not collide with a section name.
        if self.current.is_empty() && self.root.contains_key(&key) {
            return Err(Fail { kind: ErrorKind::DuplicateKey(key), at: key_start, note: None });
        }
        self.key_lines.insert(ident, line);
        let table = match self.current.first() {
            None => &mut self.root,
            Some(sec) => match self.root.get_mut(sec) {
                Some(Value::Table(t)) => t,
                _ => unreachable!("section table exists"),
            },
        };
        table.insert(key, Value::String(value));
        Ok(())
    }

    // ------------------------------------------------------------------
    // TOML: keys and headers
    // ------------------------------------------------------------------

    fn is_bare_key_char(c: char) -> bool {
        c.is_ascii_alphanumeric() || c == '_' || c == '-'
    }

    /// Parse a single key segment: bare, "basic" or 'literal'.
    fn simple_key(&mut self) -> PResult<String> {
        match self.peek() {
            Some('"') => self.basic_string(),
            Some('\'') => self.literal_string(),
            Some(c) if Self::is_bare_key_char(c) => {
                let start = self.i;
                while matches!(self.peek(), Some(c) if Self::is_bare_key_char(c)) {
                    self.i += 1;
                }
                Ok(self.chars[start..self.i].iter().collect())
            }
            Some(found) => fail(ErrorKind::UnexpectedChar { found, expected: "a key (letters, digits, `_`, `-`, or a quoted string)" }, self.i),
            None => fail(ErrorKind::UnexpectedEof { expected: "a key" }, self.i),
        }
    }

    /// Parse `a.b."c d"` into segments.
    fn dotted_key(&mut self) -> PResult<Vec<String>> {
        let mut parts = vec![self.simple_key()?];
        loop {
            let save = self.i;
            self.skip_ws();
            if self.eat('.') {
                self.skip_ws();
                parts.push(self.simple_key()?);
            } else {
                self.i = save;
                return Ok(parts);
            }
        }
    }

    /// Walk (and create) tables along `segs`, starting at `table`.
    /// `ident` accumulates a unique identity string including array-of-table indices.
    fn descend<'t>(
        mut table: &'t mut Table,
        segs: &[String],
        ident: &mut String,
        table_arrays: &HashSet<String>,
    ) -> Result<&'t mut Table, ErrorKind> {
        for seg in segs {
            if !ident.is_empty() {
                ident.push('\u{0}');
            }
            ident.push_str(seg);
            let entry = table.entry(seg.clone()).or_insert_with(|| Value::Table(Table::new()));
            let is_table_array = matches!(entry, Value::Array(_)) && table_arrays.contains(ident.as_str());
            if !is_table_array && !matches!(entry, Value::Table(_)) {
                return Err(ErrorKind::NotATable { key: seg.clone(), found: entry.type_name() });
            }
            table = match entry {
                Value::Table(t) => t,
                Value::Array(items) => {
                    let idx = items.len() - 1;
                    ident.push_str(&format!("[{idx}]"));
                    match items.last_mut() {
                        Some(Value::Table(t)) => t,
                        _ => unreachable!("arrays of tables only hold tables"),
                    }
                }
                _ => unreachable!("checked above"),
            };
        }
        Ok(table)
    }

    fn toml_header(&mut self) -> PResult<()> {
        let open = self.i;
        self.bump(); // '['
        let is_array = self.eat('[');
        self.skip_ws();
        let key_at = self.i;
        let path = self.dotted_key()?;
        self.skip_ws();
        self.expect(']', if is_array { "`]]` to close the header" } else { "`]` to close the header" })?;
        if is_array {
            self.expect(']', "`]]` to close the header")?;
        }
        let line = self.line_of(open);
        let display = path.join(".");
        let (last, parents) = path.split_last().unwrap();

        let mut ident = String::new();
        let parent = Self::descend(&mut self.root, parents, &mut ident, &self.table_arrays)
            .map_err(|kind| Fail { kind, at: key_at, note: None })?;
        if !ident.is_empty() {
            ident.push('\u{0}');
        }
        ident.push_str(last);

        if is_array {
            match parent.get_mut(last) {
                None => {
                    parent.insert(last.clone(), Value::Array(vec![Value::Table(Table::new())]));
                    self.table_arrays.insert(ident.clone());
                }
                Some(Value::Array(items)) if self.table_arrays.contains(&ident) => {
                    items.push(Value::Table(Table::new()));
                }
                Some(other) => {
                    return Err(Fail {
                        kind: ErrorKind::NotATable { key: display, found: other.type_name() },
                        at: key_at,
                        note: Some("`[[name]]` can only append to an array of tables".into()),
                    })
                }
            }
            let n = parent.get(last).and_then(Value::as_array).map_or(0, Vec::len);
            ident.push_str(&format!("[{}]", n - 1));
        } else {
            match parent.get(last) {
                Some(Value::Table(_)) | None => {}
                Some(other) => {
                    return Err(Fail {
                        kind: ErrorKind::NotATable { key: display, found: other.type_name() },
                        at: key_at,
                        note: self.key_lines.get(&ident).map(|l| format!("value assigned on line {l}")),
                    })
                }
            }
            if let Some(&first) = self.defined_tables.get(&ident) {
                return Err(Fail {
                    kind: ErrorKind::TableRedefined(display),
                    at: open,
                    note: Some(format!("first defined on line {first}")),
                });
            }
            parent.entry(last.clone()).or_insert_with(|| Value::Table(Table::new()));
            self.defined_tables.insert(ident.clone(), line);
        }
        self.current = path;
        self.current_ident = ident;
        Ok(())
    }

    fn toml_keyval_line(&mut self) -> PResult<()> {
        let key_at = self.i;
        let key = self.dotted_key()?;
        self.skip_ws();
        if self.peek() != Some('=') {
            return match self.peek() {
                Some(found) => fail(ErrorKind::UnexpectedChar { found, expected: "`=` after the key" }, self.i),
                None => fail(ErrorKind::UnexpectedEof { expected: "`=` after the key" }, self.i),
            };
        }
        self.bump();
        self.skip_ws();
        let value = self.value()?;
        self.end_of_line()?;

        // Navigate to the current table, then through the dotted key's parents.
        let line = self.line_of(key_at);
        let mut ident = String::new();
        let current = self.current.clone();
        let (last, parents) = key.split_last().unwrap();
        let mut segs = current;
        segs.extend_from_slice(parents);
        // Rebuild ident the same way headers did so array indices match.
        let table = Self::descend(&mut self.root, &segs, &mut ident, &self.table_arrays)
            .map_err(|kind| Fail { kind, at: key_at, note: None })?;
        if !ident.is_empty() {
            ident.push('\u{0}');
        }
        ident.push_str(last);
        if table.contains_key(last) {
            return Err(Fail {
                kind: ErrorKind::DuplicateKey(key.join(".")),
                at: key_at,
                note: self.key_lines.get(&ident).map(|l| format!("first defined on line {l}"))
                    .or_else(|| Some("this name is already used by a table".into())),
            });
        }
        table.insert(last.clone(), value);
        self.key_lines.insert(ident, line);
        Ok(())
    }

    // ------------------------------------------------------------------
    // TOML: values
    // ------------------------------------------------------------------

    fn value(&mut self) -> PResult<Value> {
        match self.peek() {
            None => fail(ErrorKind::UnexpectedEof { expected: "a value" }, self.i),
            Some('"') => {
                if self.starts_with("\"\"\"") {
                    self.ml_basic_string().map(Value::String)
                } else {
                    self.basic_string().map(Value::String)
                }
            }
            Some('\'') => {
                if self.starts_with("'''") {
                    self.ml_literal_string().map(Value::String)
                } else {
                    self.literal_string().map(Value::String)
                }
            }
            Some('[') => self.array(),
            Some('{') => self.inline_table(),
            Some(c) if c.is_ascii_digit() || c == '+' || c == '-' || c.is_ascii_alphabetic() => self.scalar(),
            Some(found) => fail(
                ErrorKind::UnexpectedChar { found, expected: "a value (string, number, boolean, array or inline table)" },
                self.i,
            ),
        }
    }

    /// Booleans, integers and floats share one token shape; classify after reading.
    fn scalar(&mut self) -> PResult<Value> {
        let start = self.i;
        while matches!(self.peek(), Some(c) if c.is_ascii_alphanumeric() || matches!(c, '_' | '+' | '-' | '.')) {
            self.i += 1;
        }
        let tok: String = self.chars[start..self.i].iter().collect();
        match tok.as_str() {
            "true" => return Ok(Value::Boolean(true)),
            "false" => return Ok(Value::Boolean(false)),
            "inf" | "+inf" => return Ok(Value::Float(f64::INFINITY)),
            "-inf" => return Ok(Value::Float(f64::NEG_INFINITY)),
            "nan" | "+nan" | "-nan" => return Ok(Value::Float(f64::NAN)),
            _ => {}
        }
        if tok.chars().next().is_some_and(|c| c.is_ascii_alphabetic()) {
            return Err(Fail {
                kind: ErrorKind::UnexpectedChar { found: tok.chars().next().unwrap(), expected: "a value" },
                at: start,
                note: Some(format!("strings must be quoted, e.g. \"{tok}\"")),
            });
        }
        parse_number(&tok).map_err(|kind| Fail { kind, at: start, note: None })
    }

    fn array(&mut self) -> PResult<Value> {
        self.bump(); // '['
        let mut items = Vec::new();
        loop {
            self.skip_ws_comments_newlines();
            if self.eat(']') {
                return Ok(Value::Array(items));
            }
            items.push(self.value()?);
            self.skip_ws_comments_newlines();
            match self.peek() {
                Some(',') => {
                    self.bump();
                }
                Some(']') => {
                    self.bump();
                    return Ok(Value::Array(items));
                }
                Some(found) => return fail(ErrorKind::UnexpectedChar { found, expected: "`,` or `]` in array" }, self.i),
                None => return fail(ErrorKind::UnexpectedEof { expected: "`]` to close the array" }, self.i),
            }
        }
    }

    fn inline_table(&mut self) -> PResult<Value> {
        self.bump(); // '{'
        let mut table = Table::new();
        let no_tables = HashSet::new();
        self.skip_ws();
        if self.eat('}') {
            return Ok(Value::Table(table));
        }
        loop {
            self.skip_ws();
            let key_at = self.i;
            let key = self.dotted_key()?;
            self.skip_ws();
            self.expect('=', "`=` after the key")?;
            self.skip_ws();
            let v = self.value()?;
            let (last, parents) = key.split_last().unwrap();
            let mut ident = String::new();
            let t = Self::descend(&mut table, parents, &mut ident, &no_tables)
                .map_err(|kind| Fail { kind, at: key_at, note: None })?;
            if t.insert(last.clone(), v).is_some() {
                return fail(ErrorKind::DuplicateKey(key.join(".")), key_at);
            }
            self.skip_ws();
            match self.peek() {
                Some(',') => {
                    self.bump();
                }
                Some('}') => {
                    self.bump();
                    return Ok(Value::Table(table));
                }
                Some(found) => {
                    return Err(Fail {
                        kind: ErrorKind::UnexpectedChar { found, expected: "`,` or `}` in inline table" },
                        at: self.i,
                        note: (found == '\n').then(|| "inline tables must fit on one line".to_string()),
                    })
                }
                None => return fail(ErrorKind::UnexpectedEof { expected: "`}` to close the inline table" }, self.i),
            }
        }
    }

    // ------------------------------------------------------------------
    // TOML: strings
    // ------------------------------------------------------------------

    /// Parse the escape after a backslash (cursor is on the char after `\`).
    fn escape(&mut self, out: &mut String) -> PResult<()> {
        let at = self.i - 1;
        let c = match self.bump() {
            Some(c) => c,
            None => return fail(ErrorKind::UnterminatedString, at),
        };
        let ch = match c {
            'b' => '\u{8}',
            't' => '\t',
            'n' => '\n',
            'f' => '\u{c}',
            'r' => '\r',
            'e' => '\u{1b}',
            '"' => '"',
            '\\' => '\\',
            'u' | 'U' => {
                let len = if c == 'u' { 4 } else { 8 };
                let hex: String = (0..len).filter_map(|_| self.bump()).collect();
                let code = (hex.len() == len)
                    .then(|| u32::from_str_radix(&hex, 16).ok())
                    .flatten()
                    .and_then(char::from_u32);
                match code {
                    Some(ch) => ch,
                    None => return fail(ErrorKind::InvalidUnicodeEscape, at),
                }
            }
            other => return fail(ErrorKind::InvalidEscape(other), at),
        };
        out.push(ch);
        Ok(())
    }

    fn basic_string(&mut self) -> PResult<String> {
        let open = self.i;
        self.bump(); // '"'
        let mut s = String::new();
        loop {
            match self.bump() {
                None => return fail(ErrorKind::UnterminatedString, open),
                Some('"') => return Ok(s),
                Some('\n') | Some('\r') => return fail(ErrorKind::NewlineInString, self.i - 1),
                Some('\\') => self.escape(&mut s)?,
                Some(c) => s.push(c),
            }
        }
    }

    fn literal_string(&mut self) -> PResult<String> {
        let open = self.i;
        self.bump(); // '\''
        let start = self.i;
        loop {
            match self.bump() {
                None => return fail(ErrorKind::UnterminatedString, open),
                Some('\'') => return Ok(self.chars[start..self.i - 1].iter().collect()),
                Some('\n') | Some('\r') => return fail(ErrorKind::NewlineInString, self.i - 1),
                Some(_) => {}
            }
        }
    }

    fn ml_basic_string(&mut self) -> PResult<String> {
        let open = self.i;
        self.i += 3;
        self.eat_newline(); // a newline right after the opening quotes is trimmed
        let mut s = String::new();
        loop {
            if self.starts_with("\"\"\"") {
                self.i += 3;
                // Up to two extra quotes directly before the delimiter belong to the string.
                for _ in 0..2 {
                    if self.eat('"') {
                        s.push('"');
                    }
                }
                return Ok(s);
            }
            match self.bump() {
                None => return fail(ErrorKind::UnterminatedString, open),
                Some('\\') => {
                    // "Line ending backslash": skip the newline and following whitespace.
                    let save = self.i;
                    self.skip_ws();
                    if self.eat_newline() {
                        while matches!(self.peek(), Some(' ' | '\t' | '\n' | '\r')) {
                            self.i += 1;
                        }
                    } else {
                        self.i = save;
                        self.escape(&mut s)?;
                    }
                }
                Some('\r') if self.peek() == Some('\n') => {}
                Some(c) => s.push(c),
            }
        }
    }

    fn ml_literal_string(&mut self) -> PResult<String> {
        let open = self.i;
        self.i += 3;
        self.eat_newline();
        let mut s = String::new();
        loop {
            if self.starts_with("'''") {
                self.i += 3;
                for _ in 0..2 {
                    if self.eat('\'') {
                        s.push('\'');
                    }
                }
                return Ok(s);
            }
            match self.bump() {
                None => return fail(ErrorKind::UnterminatedString, open),
                Some('\r') if self.peek() == Some('\n') => {}
                Some(c) => s.push(c),
            }
        }
    }
}

/// Classify and parse a numeric token (integer or float), validating TOML rules.
pub(crate) fn parse_number(tok: &str) -> Result<Value, ErrorKind> {
    let bad = || ErrorKind::InvalidNumber(tok.to_string());

    // Underscores must sit between two digits.
    let chars: Vec<char> = tok.chars().collect();
    for (n, &c) in chars.iter().enumerate() {
        if c == '_' {
            let ok = n > 0
                && n + 1 < chars.len()
                && chars[n - 1].is_ascii_hexdigit()
                && chars[n + 1].is_ascii_hexdigit();
            if !ok {
                return Err(bad());
            }
        }
    }
    let clean: String = tok.chars().filter(|&c| c != '_').collect();

    // Prefixed integers: 0x / 0o / 0b (no sign allowed).
    for (prefix, radix) in [("0x", 16), ("0o", 8), ("0b", 2)] {
        if let Some(digits) = clean.strip_prefix(prefix) {
            if digits.is_empty() || !digits.chars().all(|c| c.is_digit(radix)) {
                return Err(bad());
            }
            return u64::from_str_radix(digits, radix)
                .ok()
                .and_then(|u| i64::try_from(u).ok())
                .map(Value::Integer)
                .ok_or_else(|| ErrorKind::IntegerOverflow(tok.to_string()));
        }
    }

    let (sign, body) = match clean.strip_prefix(['+', '-']) {
        Some(rest) => (&clean[..1], rest),
        None => ("", clean.as_str()),
    };
    if body.is_empty() {
        return Err(bad());
    }

    let is_float = body.contains(['.', 'e', 'E']);
    // Split into integer part / fraction / exponent and validate each piece.
    let (mantissa, exponent) = match body.find(['e', 'E']) {
        Some(p) => (&body[..p], Some(&body[p + 1..])),
        None => (body, None),
    };
    let (int_part, frac) = match mantissa.find('.') {
        Some(p) => (&mantissa[..p], Some(&mantissa[p + 1..])),
        None => (mantissa, None),
    };
    let all_digits = |s: &str| !s.is_empty() && s.chars().all(|c| c.is_ascii_digit());
    if !all_digits(int_part) || (int_part.len() > 1 && int_part.starts_with('0')) {
        return Err(bad());
    }
    if let Some(f) = frac {
        if !all_digits(f) {
            return Err(bad());
        }
    }
    if let Some(e) = exponent {
        if !all_digits(e.strip_prefix(['+', '-']).unwrap_or(e)) {
            return Err(bad());
        }
    }

    if is_float {
        format!("{sign}{body}").parse::<f64>().map(Value::Float).map_err(|_| bad())
    } else {
        format!("{sign}{body}")
            .parse::<i64>()
            .map(Value::Integer)
            .map_err(|_| ErrorKind::IntegerOverflow(tok.to_string()))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn numbers() {
        assert_eq!(parse_number("42"), Ok(Value::Integer(42)));
        assert_eq!(parse_number("-17"), Ok(Value::Integer(-17)));
        assert_eq!(parse_number("1_000_000"), Ok(Value::Integer(1_000_000)));
        assert_eq!(parse_number("0xff"), Ok(Value::Integer(255)));
        assert_eq!(parse_number("0o17"), Ok(Value::Integer(15)));
        assert_eq!(parse_number("0b101"), Ok(Value::Integer(5)));
        assert_eq!(parse_number("3.25"), Ok(Value::Float(3.25)));
        assert_eq!(parse_number("-1e3"), Ok(Value::Float(-1000.0)));
        assert_eq!(parse_number("6.02E+23"), Ok(Value::Float(6.02e23)));
    }

    #[test]
    fn bad_numbers() {
        for tok in ["01", "1__0", "_1", "1_", "1.", ".5", "1e", "0xg", "0x", "+", "1.2.3"] {
            assert!(matches!(parse_number(tok), Err(ErrorKind::InvalidNumber(_))), "{tok}");
        }
        assert!(matches!(parse_number("9223372036854775808"), Err(ErrorKind::IntegerOverflow(_))));
        assert_eq!(parse_number("-9223372036854775808"), Ok(Value::Integer(i64::MIN)));
    }
}
