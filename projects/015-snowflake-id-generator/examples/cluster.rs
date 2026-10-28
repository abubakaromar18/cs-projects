//! Simulates three "machines" issuing IDs independently, then merges their
//! output and shows that sorting by ID approximately sorts by time.
//!
//! Run with: `cargo run --example cluster`

use snowflake_id::{Config, Generator, ManualClock};

fn main() {
    let clock = ManualClock::new(1_000);
    let nodes: Vec<_> = (0..3)
        .map(|n| Generator::with_clock(Config::new(n).epoch_ms(0), clock.clone()).unwrap())
        .collect();

    // Each "tick", every node issues a couple of IDs; nodes 0 and 2 are busier.
    let mut log = Vec::new();
    for tick in 0..4 {
        for (n, gen) in nodes.iter().enumerate() {
            let burst = if n == 1 { 1 } else { 2 };
            for _ in 0..burst {
                log.push(gen.next_id().unwrap());
            }
        }
        clock.advance(if tick == 1 { 3 } else { 1 });
    }

    log.sort();
    println!("{:>20}  {:>6}  {:>4}  {:>3}", "id", "ms", "node", "seq");
    for id in &log {
        println!(
            "{:>20}  {:>6}  {:>4}  {:>3}",
            id,
            id.timestamp(),
            id.node_id(),
            id.sequence()
        );
    }
    println!(
        "\n{} IDs from {} nodes, all unique, sorted by time then node.",
        log.len(),
        nodes.len()
    );
}
