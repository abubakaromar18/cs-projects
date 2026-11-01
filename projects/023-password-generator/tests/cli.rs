//! End-to-end tests that run the compiled `passgen` binary.

use std::process::{Command, Output};

fn passgen(args: &[&str]) -> Output {
    Command::new(env!("CARGO_BIN_EXE_passgen"))
        .args(args)
        .output()
        .expect("failed to run passgen")
}

fn stdout_lines(out: &Output) -> Vec<String> {
    String::from_utf8_lossy(&out.stdout)
        .lines()
        .map(str::to_string)
        .collect()
}

#[test]
fn default_prints_one_20_char_password() {
    let out = passgen(&[]);
    assert!(out.status.success());
    let lines = stdout_lines(&out);
    assert_eq!(lines.len(), 1);
    assert_eq!(lines[0].chars().count(), 20);
    assert!(out.stderr.is_empty(), "stderr should be clean by default");
}

#[test]
fn count_and_uniqueness() {
    let out = passgen(&["-n", "50", "-l", "16"]);
    let lines = stdout_lines(&out);
    assert_eq!(lines.len(), 50);
    let unique: std::collections::HashSet<_> = lines.iter().collect();
    assert_eq!(unique.len(), 50, "CSPRNG output should not repeat");
}

#[test]
fn seed_is_reproducible_and_warns() {
    let a = passgen(&["--seed", "1234", "-n", "3"]);
    let b = passgen(&["--seed", "1234", "-n", "3"]);
    assert_eq!(a.stdout, b.stdout);
    assert!(String::from_utf8_lossy(&a.stderr).contains("predictable"));
}

#[test]
fn entropy_report_goes_to_stderr() {
    let out = passgen(&["phrase", "-w", "5", "-e"]);
    assert!(out.status.success());
    let err = String::from_utf8_lossy(&out.stderr);
    assert!(err.contains("entropy: 51.3 bits"), "{err}");
    let lines = stdout_lines(&out);
    assert_eq!(lines.len(), 1);
    assert_eq!(lines[0].split('-').count(), 5);
}

#[test]
fn custom_wordlist_file() {
    let dir = std::env::temp_dir().join(format!("passgen-test-{}", std::process::id()));
    std::fs::create_dir_all(&dir).unwrap();
    let path = dir.join("words.txt");
    std::fs::write(&path, "red\ngreen\nblue\n").unwrap();
    let out = passgen(&[
        "phrase",
        "--wordlist",
        path.to_str().unwrap(),
        "-w",
        "8",
        "-s",
        "_",
    ]);
    assert!(out.status.success());
    let line = &stdout_lines(&out)[0];
    for word in line.split('_') {
        assert!(["red", "green", "blue"].contains(&word), "{line}");
    }
    std::fs::remove_dir_all(dir).ok();
}

#[test]
fn bad_input_exits_with_code_2() {
    let out = passgen(&["-l", "2"]);
    assert_eq!(out.status.code(), Some(2));
    assert!(String::from_utf8_lossy(&out.stderr).contains("cannot contain one character"));

    let out = passgen(&["--bogus"]);
    assert_eq!(out.status.code(), Some(2));
}

#[test]
fn help_lists_both_modes() {
    let out = passgen(&["--help"]);
    let text = String::from_utf8_lossy(&out.stdout);
    assert!(text.contains("passgen phrase"));
    assert!(text.contains("--no-ambiguous"));
}
