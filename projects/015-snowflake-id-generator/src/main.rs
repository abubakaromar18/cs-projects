//! `snowflake` command-line tool: generate, decode and benchmark IDs.

use std::process::ExitCode;
use std::sync::Arc;
use std::time::Instant;

use snowflake_id::layout::{DEFAULT_EPOCH_MS, MAX_NODE_ID};
use snowflake_id::timefmt::rfc3339_utc;
use snowflake_id::{Config, Generator, SnowflakeId, SystemClock};

const USAGE: &str = "\
snowflake — time-ordered 64-bit unique IDs

USAGE:
    snowflake gen    [-n COUNT] [--node ID] [--epoch MS] [--base62]
    snowflake decode [--epoch MS] ID...
    snowflake bench  [-n COUNT] [--threads T] [--node ID]
    snowflake help

OPTIONS:
    -n COUNT      How many IDs to generate (default: 1 for gen, 1000000 for bench)
    --node ID     Node id 0..=1023 (default: 1)
    --epoch MS    Custom epoch in Unix ms (default: 2020-01-01T00:00:00Z)
    --base62      Print IDs in compact base-62 instead of decimal
    --threads T   Worker threads sharing one generator (default: 4)

Decode accepts decimal IDs or base-62 IDs prefixed with 'b62:'.";

/// Parsed command-line options shared by all subcommands.
struct Opts {
    count: Option<usize>,
    node: u16,
    epoch: u64,
    base62: bool,
    threads: usize,
    positional: Vec<String>,
}

fn parse_opts(args: &[String]) -> Result<Opts, String> {
    let mut o = Opts {
        count: None,
        node: 1,
        epoch: DEFAULT_EPOCH_MS,
        base62: false,
        threads: 4,
        positional: vec![],
    };
    let mut it = args.iter();
    while let Some(arg) = it.next() {
        let mut value = |name: &str| it.next().ok_or_else(|| format!("{name} needs a value"));
        match arg.as_str() {
            "-n" => o.count = Some(value("-n")?.parse().map_err(|e| format!("-n: {e}"))?),
            "--node" => {
                o.node = value("--node")?
                    .parse()
                    .map_err(|e| format!("--node: {e}"))?
            }
            "--epoch" => {
                o.epoch = value("--epoch")?
                    .parse()
                    .map_err(|e| format!("--epoch: {e}"))?
            }
            "--threads" => {
                o.threads = value("--threads")?
                    .parse()
                    .map_err(|e| format!("--threads: {e}"))?;
                if o.threads == 0 {
                    return Err("--threads must be at least 1".into());
                }
            }
            "--base62" => o.base62 = true,
            s if s.starts_with('-') => return Err(format!("unknown option {s}")),
            s => o.positional.push(s.to_string()),
        }
    }
    if o.node > MAX_NODE_ID {
        return Err(format!("--node must be 0..={MAX_NODE_ID}"));
    }
    Ok(o)
}

fn cmd_gen(o: &Opts) -> Result<(), String> {
    let gen = Generator::with_clock(Config::new(o.node).epoch_ms(o.epoch), SystemClock)
        .map_err(|e| e.to_string())?;
    for _ in 0..o.count.unwrap_or(1) {
        let id = gen.next_id().map_err(|e| e.to_string())?;
        if o.base62 {
            println!("{}", id.to_base62());
        } else {
            println!("{id}");
        }
    }
    Ok(())
}

fn cmd_decode(o: &Opts) -> Result<(), String> {
    if o.positional.is_empty() {
        return Err("decode needs at least one ID".into());
    }
    for s in &o.positional {
        let id = match s.strip_prefix("b62:") {
            Some(enc) => SnowflakeId::from_base62(enc)
                .ok_or_else(|| format!("invalid base-62 id {enc:?}"))?,
            None => s.parse::<SnowflakeId>().map_err(|e| e.to_string())?,
        };
        let p = id.parts();
        println!("id        {id}  (b62:{})", id.to_base62());
        println!(
            "  time    {}  (+{} ms since epoch)",
            rfc3339_utc(id.unix_millis(o.epoch)),
            p.timestamp
        );
        println!("  node    {}", p.node_id);
        println!("  seq     {}", p.sequence);
        println!("  binary  {:064b}", id.as_u64());
    }
    Ok(())
}

fn cmd_bench(o: &Opts) -> Result<(), String> {
    let total = o.count.unwrap_or(1_000_000);
    let gen = Arc::new(Generator::new(o.node).map_err(|e| e.to_string())?);
    let per_thread = total / o.threads;
    let start = Instant::now();

    let handles: Vec<_> = (0..o.threads)
        .map(|_| {
            let gen = Arc::clone(&gen);
            std::thread::spawn(move || gen.take(per_thread))
        })
        .collect();
    let mut all = Vec::with_capacity(per_thread * o.threads);
    for h in handles {
        all.extend(
            h.join()
                .map_err(|_| "worker panicked")?
                .map_err(|e| e.to_string())?,
        );
    }
    let elapsed = start.elapsed();

    let n = all.len();
    all.sort_unstable();
    all.dedup();
    let rate = n as f64 / elapsed.as_secs_f64();
    println!(
        "generated {n} IDs on {} threads in {:.3?}",
        o.threads, elapsed
    );
    println!(
        "throughput {:.2} M ids/s (theoretical max 4.096 M/s per node)",
        rate / 1e6
    );
    println!("duplicates {}", n - all.len());
    if n != all.len() {
        return Err("duplicate IDs detected!".into());
    }
    Ok(())
}

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let Some((cmd, rest)) = args.split_first() else {
        eprintln!("{USAGE}");
        return ExitCode::from(2);
    };
    let result = parse_opts(rest).and_then(|o| match cmd.as_str() {
        "gen" => cmd_gen(&o),
        "decode" => cmd_decode(&o),
        "bench" => cmd_bench(&o),
        "help" | "-h" | "--help" => {
            println!("{USAGE}");
            Ok(())
        }
        other => Err(format!("unknown command {other:?}\n\n{USAGE}")),
    });
    match result {
        Ok(()) => ExitCode::SUCCESS,
        Err(e) => {
            eprintln!("error: {e}");
            ExitCode::FAILURE
        }
    }
}
