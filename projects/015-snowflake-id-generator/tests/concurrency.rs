//! Integration tests: uniqueness and ordering under real concurrency, and
//! independence of multiple nodes.

use std::collections::HashSet;
use std::sync::{Arc, Barrier};
use std::thread;

use snowflake_id::{Config, Generator, ManualClock, SnowflakeId};

/// Many threads hammer one generator; every ID must be unique and each
/// thread's own sequence must be strictly increasing.
#[test]
fn concurrent_generation_is_unique_and_per_thread_monotonic() {
    const THREADS: usize = 8;
    const PER_THREAD: usize = 25_000;

    let gen = Arc::new(Generator::new(7).unwrap());
    let barrier = Arc::new(Barrier::new(THREADS));
    let handles: Vec<_> = (0..THREADS)
        .map(|_| {
            let (gen, barrier) = (Arc::clone(&gen), Arc::clone(&barrier));
            thread::spawn(move || {
                barrier.wait(); // maximise contention
                gen.take(PER_THREAD).unwrap()
            })
        })
        .collect();

    let mut seen = HashSet::with_capacity(THREADS * PER_THREAD);
    for h in handles {
        let ids = h.join().unwrap();
        assert!(
            ids.windows(2).all(|w| w[0] < w[1]),
            "per-thread order violated"
        );
        for id in ids {
            assert_eq!(id.node_id(), 7);
            assert!(seen.insert(id), "duplicate id {id}");
        }
    }
    assert_eq!(seen.len(), THREADS * PER_THREAD);
}

/// Concurrency with a frozen manual clock forces every thread through the
/// sequence-overflow path many times.
#[test]
fn concurrent_overflow_path_is_unique() {
    let clock = ManualClock::new(10_000);
    let gen = Arc::new(Generator::with_clock(Config::new(1).epoch_ms(0), clock).unwrap());
    let handles: Vec<_> = (0..4)
        .map(|_| {
            let gen = Arc::clone(&gen);
            thread::spawn(move || gen.take(10_000).unwrap())
        })
        .collect();
    let all: Vec<SnowflakeId> = handles
        .into_iter()
        .flat_map(|h| h.join().unwrap())
        .collect();
    let unique: HashSet<_> = all.iter().copied().collect();
    assert_eq!(unique.len(), 40_000);
    // 40 000 IDs / 4096 per ms ⇒ the clock had to tick at least 9 times.
    let max_ts = all.iter().map(|id| id.timestamp()).max().unwrap();
    assert!(max_ts >= 10_000 + 9);
}

/// Two nodes sharing the same clock never collide: the node bits differ.
#[test]
fn different_nodes_never_collide() {
    let clock = ManualClock::new(5_000);
    let a = Generator::with_clock(Config::new(1).epoch_ms(0), clock.clone()).unwrap();
    let b = Generator::with_clock(Config::new(2).epoch_ms(0), clock.clone()).unwrap();
    let mut set = HashSet::new();
    for _ in 0..1_000 {
        assert!(set.insert(a.next_id().unwrap()));
        assert!(set.insert(b.next_id().unwrap()));
        clock.advance(1);
    }
}

/// IDs from the real clock decode back to roughly "now".
#[test]
fn ids_decode_to_current_time() {
    let gen = Generator::new(0).unwrap();
    let before = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_millis() as u64;
    let id = gen.next_id().unwrap();
    let decoded = id.unix_millis(gen.config().epoch_ms);
    assert!(
        decoded >= before && decoded <= before + 1_000,
        "{decoded} vs {before}"
    );
}
