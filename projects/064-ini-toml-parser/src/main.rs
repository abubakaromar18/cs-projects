//! Command-line front end: parse a config file and print it as JSON, or print
//! a rustc-style error pointing at the problem.

use std::io::Read;
use std::process::ExitCode;

use confparse::{dialect_for_path, parse, Dialect, Value};

const USAGE: &str = "\
usage: confparse [--ini | --toml] [--get KEY.PATH] [--check] <FILE | ->

Parses an INI or TOML file and prints it as JSON.

options:
  --ini, --toml   force a dialect (default: guessed from the file extension)
  --get PATH      print only the value at a dotted path, e.g. server.port
  --check         validate only; print nothing on success
  -h, --help      show this help";

struct Args {
    dialect: Option<Dialect>,
    get: Option<String>,
    check: bool,
    file: String,
}

fn parse_args() -> Result<Args, String> {
    let mut dialect = None;
    let mut get = None;
    let mut check = false;
    let mut file = None;
    let mut it = std::env::args().skip(1);
    while let Some(a) = it.next() {
        match a.as_str() {
            "-h" | "--help" => return Err(String::new()),
            "--ini" => dialect = Some(Dialect::Ini),
            "--toml" => dialect = Some(Dialect::Toml),
            "--check" => check = true,
            "--get" => get = Some(it.next().ok_or("--get needs a key path")?),
            _ if a.starts_with("--") => return Err(format!("unknown option `{a}`")),
            _ if file.is_none() => file = Some(a),
            _ => return Err("only one file may be given".into()),
        }
    }
    Ok(Args { dialect, get, check, file: file.ok_or("missing input file")? })
}

fn main() -> ExitCode {
    let args = match parse_args() {
        Ok(a) => a,
        Err(msg) => {
            if !msg.is_empty() {
                eprintln!("confparse: {msg}\n");
            }
            eprintln!("{USAGE}");
            return ExitCode::from(2);
        }
    };

    let src = if args.file == "-" {
        let mut s = String::new();
        if let Err(e) = std::io::stdin().read_to_string(&mut s) {
            eprintln!("confparse: cannot read stdin: {e}");
            return ExitCode::from(2);
        }
        s
    } else {
        match std::fs::read_to_string(&args.file) {
            Ok(s) => s,
            Err(e) => {
                eprintln!("confparse: cannot read `{}`: {e}", args.file);
                return ExitCode::from(2);
            }
        }
    };

    let dialect = args.dialect.unwrap_or_else(|| dialect_for_path(&args.file));
    let name = if args.file == "-" { "<stdin>" } else { &args.file };
    let doc = match parse(&src, dialect) {
        Ok(t) => Value::Table(t),
        Err(e) => {
            eprintln!("{}", e.render(name));
            return ExitCode::FAILURE;
        }
    };

    if args.check {
        return ExitCode::SUCCESS;
    }
    match &args.get {
        None => println!("{}", doc.to_json()),
        Some(path) => match doc.get_path(path) {
            // Print bare strings without JSON quotes so shell scripts can use them.
            Some(Value::String(s)) => println!("{s}"),
            Some(v) => println!("{}", v.to_json()),
            None => {
                eprintln!("confparse: key `{path}` not found");
                return ExitCode::FAILURE;
            }
        },
    }
    ExitCode::SUCCESS
}
