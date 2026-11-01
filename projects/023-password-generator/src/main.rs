//! CLI entry point: parse args, build a generator, print secrets to stdout.
//! Diagnostics (entropy, warnings) go to stderr so `passgen | pbcopy` and
//! similar pipelines receive only the secret.

use passgen::cli::{self, Command, Common};
use passgen::entropy::{crack_time, Strength};
use passgen::passphrase::{parse_wordlist, PassphraseGenerator};
use passgen::password::PasswordGenerator;
use passgen::rng::{OsRng, RandomSource, SeededRng};
use std::io::{self, BufWriter, Write};
use std::process::ExitCode;

/// Assumed attacker speed for the crack-time estimate: 10^11 guesses/s,
/// roughly a GPU rig against a fast, unsalted hash.
const GUESSES_PER_SEC: f64 = 1e11;

fn main() -> ExitCode {
    match run(std::env::args().skip(1)) {
        Ok(()) => ExitCode::SUCCESS,
        Err(msg) => {
            eprintln!("error: {msg}");
            ExitCode::from(2)
        }
    }
}

fn run(args: impl Iterator<Item = String>) -> Result<(), String> {
    match cli::parse(args)? {
        Command::Help => {
            print!("{}", cli::USAGE);
            Ok(())
        }
        Command::Version => {
            println!("passgen {}", env!("CARGO_PKG_VERSION"));
            Ok(())
        }
        Command::Password(config, common) => {
            let gen = PasswordGenerator::new(&config).map_err(|e| e.to_string())?;
            emit(&common, gen.entropy_bits(), |rng| {
                gen.generate(rng).map_err(|e| e.to_string())
            })?;
            if common.show_entropy {
                let names: Vec<_> = gen.classes().iter().map(|c| c.name).collect();
                eprintln!(
                    "pool: {} chars from [{}]",
                    gen.pool_size(),
                    names.join(", ")
                );
            }
            Ok(())
        }
        Command::Phrase {
            config,
            wordlist,
            common,
        } => {
            let gen = match wordlist {
                Some(path) => {
                    let text = std::fs::read_to_string(&path)
                        .map_err(|e| format!("cannot read wordlist '{path}': {e}"))?;
                    PassphraseGenerator::new(parse_wordlist(&text), config)
                }
                None => PassphraseGenerator::with_default_list(config),
            }
            .map_err(|e| e.to_string())?;
            emit(&common, gen.entropy_bits(), |rng| {
                gen.generate(rng).map_err(|e| e.to_string())
            })?;
            if common.show_entropy {
                eprintln!("wordlist: {} words", gen.wordlist_len());
            }
            Ok(())
        }
    }
}

/// Generates `common.count` secrets with the right RNG and prints them.
fn emit<F>(common: &Common, bits: f64, mut make: F) -> Result<(), String>
where
    F: FnMut(&mut dyn DynRng) -> Result<String, String>,
{
    let mut rng: Box<dyn DynRng> = match common.seed {
        Some(seed) => {
            eprintln!("warning: --seed makes output predictable; never use it for real secrets");
            Box::new(SeededRng::new(seed))
        }
        None => Box::new(OsRng),
    };
    let stdout = io::stdout();
    let mut out = BufWriter::new(stdout.lock());
    for _ in 0..common.count {
        let secret = make(rng.as_mut())?;
        writeln!(out, "{secret}").map_err(|e| e.to_string())?;
    }
    out.flush().map_err(|e| e.to_string())?;

    if common.show_entropy {
        eprintln!(
            "entropy: {bits:.1} bits ({}) — brute force at 1e11 guesses/s: {}",
            Strength::from_bits(bits).label(),
            crack_time(bits, GUESSES_PER_SEC)
        );
    }
    Ok(())
}

/// Object-safe shim so we can pick the RNG at runtime. `RandomSource` has
/// generic methods, so it can't be a trait object directly; instead we box a
/// type that forwards `next_u32` and get the default methods for free.
trait DynRng {
    fn next_u32_dyn(&mut self) -> Result<u32, passgen::rng::RngError>;
}

impl<T: RandomSource> DynRng for T {
    fn next_u32_dyn(&mut self) -> Result<u32, passgen::rng::RngError> {
        self.next_u32()
    }
}

impl RandomSource for dyn DynRng + '_ {
    fn next_u32(&mut self) -> Result<u32, passgen::rng::RngError> {
        self.next_u32_dyn()
    }
}
