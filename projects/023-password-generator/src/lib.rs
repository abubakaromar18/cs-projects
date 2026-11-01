//! # passgen
//!
//! A small library (plus CLI) for generating secrets correctly:
//!
//! * [`rng`] — OS CSPRNG access and **unbiased** sampling (rejection
//!   sampling, Fisher–Yates).
//! * [`charset`] — character classes, look-alike filtering, exclusions.
//! * [`password`] — random-character passwords, uniform even when every
//!   class is required.
//! * [`passphrase`] — diceware-style word passphrases.
//! * [`entropy`] — exact entropy (with inclusion–exclusion for class
//!   constraints) and strength ratings.
//! * [`cli`] — dependency-free argument parsing.

pub mod charset;
pub mod cli;
pub mod entropy;
pub mod passphrase;
pub mod password;
pub mod rng;

pub use passphrase::{PassphraseConfig, PassphraseGenerator};
pub use password::{PasswordConfig, PasswordGenerator};
pub use rng::{OsRng, RandomSource, SeededRng};
