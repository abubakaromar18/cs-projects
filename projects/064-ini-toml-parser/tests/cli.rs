//! Tests that run the compiled `confparse` binary.

use std::process::Command;

fn bin() -> Command {
    Command::new(env!("CARGO_BIN_EXE_confparse"))
}

#[test]
fn prints_json() {
    let out = bin().arg("examples/app.toml").output().unwrap();
    assert!(out.status.success());
    let s = String::from_utf8(out.stdout).unwrap();
    assert!(s.contains("\"port\": 8080"));
}

#[test]
fn get_path() {
    let out = bin().args(["--get", "server.host", "examples/app.toml"]).output().unwrap();
    assert_eq!(String::from_utf8(out.stdout).unwrap(), "127.0.0.1\n");
    let out = bin().args(["--get", "network.host", "examples/legacy.ini"]).output().unwrap();
    assert_eq!(String::from_utf8(out.stdout).unwrap(), "localhost\n");
}

#[test]
fn reports_errors_with_exit_code() {
    let out = bin().arg("examples/broken.toml").output().unwrap();
    assert_eq!(out.status.code(), Some(1));
    let err = String::from_utf8(out.stderr).unwrap();
    assert!(err.contains("duplicate key `port`"));
    assert!(err.contains("examples/broken.toml:4:1"));
}

#[test]
fn bad_usage() {
    let out = bin().output().unwrap();
    assert_eq!(out.status.code(), Some(2));
}
