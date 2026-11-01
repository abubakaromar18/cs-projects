//! Command-line parsing, written by hand (no `clap`) to keep the dependency
//! tree tiny — fewer dependencies is itself a security property for a tool
//! that handles secrets.

use crate::charset::CharsetSpec;
use crate::passphrase::{Case, PassphraseConfig};
use crate::password::PasswordConfig;

pub const USAGE: &str = "\
passgen — secure password & passphrase generator

USAGE:
    passgen [password] [OPTIONS]      random-character passwords (default)
    passgen phrase [OPTIONS]          diceware-style passphrases

COMMON OPTIONS:
    -n, --count <N>          how many to generate              [default: 1]
    -e, --entropy            print entropy & strength to stderr
        --seed <U64>         deterministic INSECURE output (testing only)
    -h, --help               show this help
    -V, --version            show version

PASSWORD OPTIONS:
    -l, --length <N>         number of characters              [default: 20]
        --no-lower           exclude a-z
        --no-upper           exclude A-Z
        --no-digits          exclude 0-9
        --no-symbols         exclude punctuation
        --no-ambiguous       exclude look-alikes  Il1|O0o`'\"
        --exclude <CHARS>    exclude specific characters
        --custom <CHARS>     add an extra character class
        --no-require         don't force one char from each class

PHRASE OPTIONS:
    -w, --words <N>          number of words                   [default: 6]
    -s, --separator <S>      word separator                    [default: -]
        --case <C>           lower | upper | title             [default: lower]
        --digit              append a random digit to one word
        --wordlist <FILE>    use a custom list (one word per line)
";

#[derive(Debug, Clone)]
pub struct Common {
    pub count: usize,
    pub show_entropy: bool,
    pub seed: Option<u64>,
}

impl Default for Common {
    fn default() -> Self {
        Self {
            count: 1,
            show_entropy: false,
            seed: None,
        }
    }
}

#[derive(Debug, Clone)]
pub enum Command {
    Help,
    Version,
    Password(PasswordConfig, Common),
    Phrase {
        config: PassphraseConfig,
        wordlist: Option<String>,
        common: Common,
    },
}

/// Parses arguments (excluding the program name).
pub fn parse<I, S>(args: I) -> Result<Command, String>
where
    I: IntoIterator<Item = S>,
    S: Into<String>,
{
    let mut args: Vec<String> = args.into_iter().map(Into::into).collect();
    if args.iter().any(|a| a == "-h" || a == "--help") {
        return Ok(Command::Help);
    }
    if args.iter().any(|a| a == "-V" || a == "--version") {
        return Ok(Command::Version);
    }

    let mode = match args.first().map(String::as_str) {
        Some("phrase") | Some("passphrase") => {
            args.remove(0);
            "phrase"
        }
        Some("password") | Some("pw") => {
            args.remove(0);
            "password"
        }
        _ => "password",
    };

    let mut it = args.into_iter();
    let mut common = Common::default();
    let mut pw = PasswordConfig::default();
    let mut charset = CharsetSpec::default();
    let mut phrase = PassphraseConfig::default();
    let mut wordlist = None;

    while let Some(arg) = it.next() {
        // Support --flag=value as well as --flag value.
        let (flag, inline) = match arg.split_once('=') {
            Some((f, v)) if f.starts_with("--") => (f.to_string(), Some(v.to_string())),
            _ => (arg.clone(), None),
        };
        let mut value = |name: &str| -> Result<String, String> {
            inline
                .clone()
                .or_else(|| it.next())
                .ok_or_else(|| format!("{name} requires a value"))
        };

        let is_pw = mode == "password";
        match flag.as_str() {
            "-n" | "--count" => common.count = parse_num(&value(&flag)?, &flag)?,
            "-e" | "--entropy" => common.show_entropy = true,
            "--seed" => common.seed = Some(parse_num(&value(&flag)?, &flag)?),

            "-l" | "--length" if is_pw => pw.length = parse_num(&value(&flag)?, &flag)?,
            "--no-lower" if is_pw => charset.lower = false,
            "--no-upper" if is_pw => charset.upper = false,
            "--no-digits" if is_pw => charset.digits = false,
            "--no-symbols" if is_pw => charset.symbols = false,
            "--no-ambiguous" if is_pw => charset.no_ambiguous = true,
            "--exclude" if is_pw => charset.exclude = value(&flag)?,
            "--custom" if is_pw => charset.custom = value(&flag)?,
            "--no-require" if is_pw => pw.require_each_class = false,

            "-w" | "--words" if !is_pw => phrase.words = parse_num(&value(&flag)?, &flag)?,
            "-s" | "--separator" if !is_pw => phrase.separator = value(&flag)?,
            "--case" if !is_pw => {
                phrase.case = match value(&flag)?.to_lowercase().as_str() {
                    "lower" => Case::Lower,
                    "upper" => Case::Upper,
                    "title" => Case::Title,
                    other => return Err(format!("unknown case '{other}' (lower|upper|title)")),
                }
            }
            "--digit" if !is_pw => phrase.add_digit = true,
            "--wordlist" if !is_pw => wordlist = Some(value(&flag)?),

            other => {
                return Err(format!(
                    "unknown option '{other}' for {mode} mode (see --help)"
                ))
            }
        }
    }

    if common.count == 0 {
        return Err("--count must be at least 1".into());
    }

    Ok(if mode == "password" {
        pw.charset = charset;
        Command::Password(pw, common)
    } else {
        Command::Phrase {
            config: phrase,
            wordlist,
            common,
        }
    })
}

fn parse_num<T: std::str::FromStr>(s: &str, flag: &str) -> Result<T, String> {
    s.parse()
        .map_err(|_| format!("{flag}: '{s}' is not a valid non-negative number"))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn defaults_to_password_mode() {
        match parse(Vec::<String>::new()).unwrap() {
            Command::Password(cfg, common) => {
                assert_eq!(cfg.length, 20);
                assert_eq!(common.count, 1);
            }
            other => panic!("unexpected {other:?}"),
        }
    }

    #[test]
    fn password_flags() {
        let cmd = parse(["-l", "32", "--no-symbols", "--exclude=xyz", "-n", "3", "-e"]).unwrap();
        let Command::Password(cfg, common) = cmd else {
            panic!()
        };
        assert_eq!(cfg.length, 32);
        assert!(!cfg.charset.symbols);
        assert_eq!(cfg.charset.exclude, "xyz");
        assert_eq!(common.count, 3);
        assert!(common.show_entropy);
    }

    #[test]
    fn phrase_flags() {
        let cmd = parse(["phrase", "-w", "4", "-s", " ", "--case", "title", "--digit"]).unwrap();
        let Command::Phrase {
            config, wordlist, ..
        } = cmd
        else {
            panic!()
        };
        assert_eq!(config.words, 4);
        assert_eq!(config.separator, " ");
        assert_eq!(config.case, Case::Title);
        assert!(config.add_digit);
        assert!(wordlist.is_none());
    }

    #[test]
    fn mode_specific_flags_are_rejected_elsewhere() {
        assert!(parse(["phrase", "--length", "10"]).is_err());
        assert!(parse(["--words", "4"]).is_err());
    }

    #[test]
    fn errors_are_helpful() {
        assert!(parse(["-l"]).unwrap_err().contains("requires a value"));
        assert!(parse(["-l", "abc"]).unwrap_err().contains("not a valid"));
        assert!(parse(["-n", "0"]).unwrap_err().contains("at least 1"));
        assert!(parse(["phrase", "--case", "sponge"])
            .unwrap_err()
            .contains("unknown case"));
    }

    #[test]
    fn help_and_version_win() {
        assert!(matches!(
            parse(["-l", "5", "--help"]).unwrap(),
            Command::Help
        ));
        assert!(matches!(parse(["-V"]).unwrap(), Command::Version));
    }
}
