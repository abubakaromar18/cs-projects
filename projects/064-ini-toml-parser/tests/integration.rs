//! End-to-end tests for the public API and the error messages users see.

use confparse::{parse_ini, parse_toml, ErrorKind, Value};

fn get<'a>(t: &'a confparse::Table, path: &str) -> &'a Value {
    let mut cur: Option<&Value> = None;
    for (n, seg) in path.split('.').enumerate() {
        cur = Some(if n == 0 { &t[seg] } else { &cur.unwrap().as_table().unwrap()[seg] });
    }
    cur.unwrap()
}

#[test]
fn parses_example_toml() {
    let src = include_str!("../examples/app.toml");
    let doc = parse_toml(src).expect("example parses");
    assert_eq!(get(&doc, "title").as_str(), Some("Demo service"));
    assert_eq!(get(&doc, "server.port").as_integer(), Some(8080));
    assert_eq!(get(&doc, "server.timeout").as_float(), Some(2.5));
    assert_eq!(get(&doc, "server.tls.enabled").as_bool(), Some(true));
    assert_eq!(get(&doc, "server.tls.cert").as_str(), Some(r"C:\certs\server.pem"));
    assert_eq!(get(&doc, "database.pool.max").as_integer(), Some(10));
    let tags = get(&doc, "server.tags").as_array().unwrap();
    assert_eq!(tags.len(), 2);
    let plugins = get(&doc, "plugins").as_array().unwrap();
    assert_eq!(plugins.len(), 2);
    let second = plugins[1].as_table().unwrap();
    assert_eq!(second["name"].as_str(), Some("metrics"));
    assert_eq!(second["motd"].as_str(), Some("Welcome to the demo service!"));
}

#[test]
fn parses_example_ini() {
    let doc = parse_ini(include_str!("../examples/legacy.ini")).unwrap();
    assert_eq!(get(&doc, "app_name").as_str(), Some("Legacy App"));
    assert_eq!(get(&doc, "paths.home").as_str(), Some("/var/lib/legacy"));
    let paths = doc["paths"].as_table().unwrap();
    assert_eq!(paths["log file"].as_str(), Some("/var/log/legacy.log"));
    let net = doc["network"].as_table().unwrap();
    assert_eq!(net["host"].as_str(), Some("localhost"));
    assert_eq!(net["url"].as_str(), Some("http://example.local/#anchor"));
    assert_eq!(net["greeting"].as_str(), Some("  padded value  "));
}

#[test]
fn dotted_and_quoted_keys() {
    let doc = parse_toml("a.b.c = 1\n\"key with space\" = 'x'\na . d = 2\n").unwrap();
    assert_eq!(get(&doc, "a.b.c").as_integer(), Some(1));
    assert_eq!(get(&doc, "a.d").as_integer(), Some(2));
    assert_eq!(doc["key with space"].as_str(), Some("x"));
}

#[test]
fn string_escapes() {
    let doc = parse_toml(r#"s = "tab\tnl\nq\"u\u00e9\U0001F600""#).unwrap();
    assert_eq!(doc["s"].as_str(), Some("tab\tnl\nq\"u\u{e9}\u{1F600}"));
}

#[test]
fn multiline_strings() {
    let doc = parse_toml("a = \"\"\"\nline1\nline2\"\"\"\nb = '''\nraw \\n'''\n").unwrap();
    assert_eq!(doc["a"].as_str(), Some("line1\nline2"));
    assert_eq!(doc["b"].as_str(), Some("raw \\n"));
}

#[test]
fn nested_arrays_and_crlf() {
    let doc = parse_toml("x = [\r\n  [1, 2], # c\r\n  [\"a\"],\r\n]\r\ny = 1\r\n").unwrap();
    let x = doc["x"].as_array().unwrap();
    assert_eq!(x[0].as_array().unwrap().len(), 2);
    assert_eq!(doc["y"].as_integer(), Some(1));
}

#[test]
fn special_floats() {
    let doc = parse_toml("a = inf\nb = -inf\nc = nan\n").unwrap();
    assert_eq!(doc["a"].as_float(), Some(f64::INFINITY));
    assert_eq!(doc["b"].as_float(), Some(f64::NEG_INFINITY));
    assert!(doc["c"].as_float().unwrap().is_nan());
}

// ---------------------------------------------------------------- errors

#[test]
fn duplicate_key_points_at_second_definition() {
    let err = parse_toml(include_str!("../examples/broken.toml")).unwrap_err();
    assert_eq!(err.kind, ErrorKind::DuplicateKey("port".into()));
    assert_eq!((err.pos.line, err.pos.col), (4, 1));
    assert_eq!(err.note.as_deref(), Some("first defined on line 3"));
    let rendered = err.render("broken.toml");
    assert_eq!(
        rendered,
        "error: duplicate key `port`\n  --> broken.toml:4:1\n  |\n4 | port = 8080\n  | ^\n  = note: first defined on line 3"
    );
}

#[test]
fn unquoted_string_gets_hint() {
    let err = parse_toml("name = hello\n").unwrap_err();
    assert_eq!((err.pos.line, err.pos.col), (1, 8));
    assert!(err.note.unwrap().contains("\"hello\""));
}

#[test]
fn missing_equals() {
    let err = parse_toml("[a]\nkey value\n").unwrap_err();
    assert_eq!(err.kind, ErrorKind::UnexpectedChar { found: 'v', expected: "`=` after the key" });
    assert_eq!((err.pos.line, err.pos.col), (2, 5));
}

#[test]
fn unterminated_string_points_at_opening_quote() {
    let err = parse_toml("a = 1\nb = \"oops\n").unwrap_err();
    assert_eq!(err.kind, ErrorKind::NewlineInString);
    let err = parse_toml("b = \"oops").unwrap_err();
    assert_eq!(err.kind, ErrorKind::UnterminatedString);
    assert_eq!(err.pos.col, 5);
}

#[test]
fn invalid_escape() {
    let err = parse_toml(r#"p = "C:\path""#).unwrap_err();
    assert_eq!(err.kind, ErrorKind::InvalidEscape('p'));
    assert_eq!(err.pos.col, 8);
}

#[test]
fn table_redefined() {
    let err = parse_toml("[a]\nx = 1\n[b]\n[a]\n").unwrap_err();
    assert_eq!(err.kind, ErrorKind::TableRedefined("a".into()));
    assert_eq!(err.pos.line, 4);
    assert_eq!(err.note.as_deref(), Some("first defined on line 1"));
}

#[test]
fn value_used_as_table() {
    let err = parse_toml("a = 1\n[a.b]\n").unwrap_err();
    assert_eq!(err.kind, ErrorKind::NotATable { key: "a".into(), found: "integer" });
    let err = parse_toml("a = 1\na.b = 2\n").unwrap_err();
    assert!(matches!(err.kind, ErrorKind::NotATable { .. }));
}

#[test]
fn trailing_garbage_after_value() {
    let err = parse_toml("a = 1 2\n").unwrap_err();
    assert_eq!(err.kind, ErrorKind::UnexpectedChar { found: '2', expected: "end of line" });
    assert_eq!(err.pos.col, 7);
}

#[test]
fn unclosed_array_and_inline_table() {
    let err = parse_toml("a = [1, 2\n").unwrap_err();
    assert!(matches!(err.kind, ErrorKind::UnexpectedEof { .. }));
    let err = parse_toml("t = { a = 1\nb = 2 }\n").unwrap_err();
    assert_eq!(err.note.as_deref(), Some("inline tables must fit on one line"));
}

#[test]
fn integer_overflow() {
    let err = parse_toml("big = 99999999999999999999\n").unwrap_err();
    assert!(matches!(err.kind, ErrorKind::IntegerOverflow(_)));
}

#[test]
fn array_of_tables_conflicts() {
    let err = parse_toml("a = [1]\n[[a]]\n").unwrap_err();
    assert!(matches!(err.kind, ErrorKind::NotATable { .. }));
    // Keys are scoped per array element, so repeating them across elements is fine.
    let doc = parse_toml("[[p]]\nn = 1\n[[p]]\nn = 2\n").unwrap();
    assert_eq!(doc["p"].as_array().unwrap().len(), 2);
    let err = parse_toml("[[p]]\nn = 1\nn = 2\n").unwrap_err();
    assert_eq!(err.kind, ErrorKind::DuplicateKey("n".into()));
}

#[test]
fn ini_errors() {
    let err = parse_ini("[s]\na = 1\na = 2\n").unwrap_err();
    assert_eq!(err.kind, ErrorKind::DuplicateKey("a".into()));
    assert_eq!(err.note.as_deref(), Some("first defined on line 2"));
    let err = parse_ini("[s]\njust a line\n").unwrap_err();
    assert!(matches!(err.kind, ErrorKind::UnexpectedChar { .. } | ErrorKind::UnexpectedEof { .. }));
    let err = parse_ini("[unclosed\n").unwrap_err();
    assert_eq!(err.pos.col, 10);
    let err = parse_ini("[s]\n[s]\n").unwrap_err();
    assert_eq!(err.kind, ErrorKind::TableRedefined("s".into()));
}

#[test]
fn caret_accounts_for_tabs() {
    let err = parse_toml("\tx = @\n").unwrap_err();
    let rendered = err.render("t.toml");
    assert!(rendered.contains("1 |     x = @\n  |         ^"), "{rendered}");
}
