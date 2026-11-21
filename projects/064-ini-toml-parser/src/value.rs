//! The document model produced by the parser.

use std::collections::BTreeMap;
use std::fmt::Write;

/// A table maps keys to values. `BTreeMap` keeps output deterministic.
pub type Table = BTreeMap<String, Value>;

/// Any value that can appear on the right-hand side of `key = value`.
#[derive(Debug, Clone, PartialEq)]
pub enum Value {
    String(String),
    Integer(i64),
    Float(f64),
    Boolean(bool),
    Array(Vec<Value>),
    Table(Table),
}

impl Value {
    /// Human-readable type name, used in error messages.
    pub fn type_name(&self) -> &'static str {
        match self {
            Value::String(_) => "string",
            Value::Integer(_) => "integer",
            Value::Float(_) => "float",
            Value::Boolean(_) => "boolean",
            Value::Array(_) => "array",
            Value::Table(_) => "table",
        }
    }

    pub fn as_str(&self) -> Option<&str> {
        match self {
            Value::String(s) => Some(s),
            _ => None,
        }
    }

    pub fn as_integer(&self) -> Option<i64> {
        match self {
            Value::Integer(i) => Some(*i),
            _ => None,
        }
    }

    pub fn as_float(&self) -> Option<f64> {
        match self {
            Value::Float(f) => Some(*f),
            _ => None,
        }
    }

    pub fn as_bool(&self) -> Option<bool> {
        match self {
            Value::Boolean(b) => Some(*b),
            _ => None,
        }
    }

    pub fn as_array(&self) -> Option<&Vec<Value>> {
        match self {
            Value::Array(a) => Some(a),
            _ => None,
        }
    }

    pub fn as_table(&self) -> Option<&Table> {
        match self {
            Value::Table(t) => Some(t),
            _ => None,
        }
    }

    /// Look up a dotted path such as `"server.tls.port"`.
    pub fn get_path(&self, path: &str) -> Option<&Value> {
        path.split('.')
            .try_fold(self, |v, key| v.as_table().and_then(|t| t.get(key)))
    }

    /// Serialize to pretty-printed JSON (two-space indent).
    pub fn to_json(&self) -> String {
        let mut out = String::new();
        write_json(self, 0, &mut out);
        out
    }
}

fn write_json(v: &Value, indent: usize, out: &mut String) {
    let pad = |n: usize| "  ".repeat(n);
    match v {
        Value::String(s) => write_json_string(s, out),
        Value::Integer(i) => {
            let _ = write!(out, "{i}");
        }
        Value::Float(f) => {
            // JSON has no NaN/inf; emit them as strings so output stays valid.
            if f.is_finite() {
                let _ = write!(out, "{f:?}");
            } else {
                write_json_string(&f.to_string(), out);
            }
        }
        Value::Boolean(b) => {
            let _ = write!(out, "{b}");
        }
        Value::Array(items) => {
            if items.is_empty() {
                out.push_str("[]");
                return;
            }
            out.push_str("[\n");
            for (i, item) in items.iter().enumerate() {
                out.push_str(&pad(indent + 1));
                write_json(item, indent + 1, out);
                if i + 1 < items.len() {
                    out.push(',');
                }
                out.push('\n');
            }
            out.push_str(&pad(indent));
            out.push(']');
        }
        Value::Table(t) => {
            if t.is_empty() {
                out.push_str("{}");
                return;
            }
            out.push_str("{\n");
            for (i, (k, val)) in t.iter().enumerate() {
                out.push_str(&pad(indent + 1));
                write_json_string(k, out);
                out.push_str(": ");
                write_json(val, indent + 1, out);
                if i + 1 < t.len() {
                    out.push(',');
                }
                out.push('\n');
            }
            out.push_str(&pad(indent));
            out.push('}');
        }
    }
}

fn write_json_string(s: &str, out: &mut String) {
    out.push('"');
    for c in s.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c if (c as u32) < 0x20 => {
                let _ = write!(out, "\\u{:04x}", c as u32);
            }
            c => out.push(c),
        }
    }
    out.push('"');
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn json_escapes_and_nesting() {
        let mut inner = Table::new();
        inner.insert("q".into(), Value::String("a\"b\n".into()));
        let mut root = Table::new();
        root.insert("t".into(), Value::Table(inner));
        root.insert("a".into(), Value::Array(vec![Value::Integer(1), Value::Float(2.5)]));
        let json = Value::Table(root).to_json();
        assert!(json.contains(r#""q": "a\"b\n""#));
        assert!(json.contains("2.5"));
    }

    #[test]
    fn get_path_walks_tables() {
        let mut inner = Table::new();
        inner.insert("port".into(), Value::Integer(80));
        let mut root = Table::new();
        root.insert("server".into(), Value::Table(inner));
        let v = Value::Table(root);
        assert_eq!(v.get_path("server.port"), Some(&Value::Integer(80)));
        assert_eq!(v.get_path("server.nope"), None);
        assert_eq!(v.get_path("server.port.x"), None);
    }
}
