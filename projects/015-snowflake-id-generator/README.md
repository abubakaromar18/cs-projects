# Snowflake ID Generator

A **lock-free, thread-safe generator of unique, time-ordered 64-bit IDs** in Rust, using the
layout Twitter introduced with Snowflake. Any number of machines can mint IDs at the same time
with **no coordination** beyond each having its own node id, and the IDs sort roughly by
creation time. Zero external dependencies.

```text
 63  62                                      22 21          12 11           0
+---+------------------------------------------+--------------+--------------+
| 0 |   timestamp: ms since custom epoch (41)  | node id (10) | sequence (12)|
+---+------------------------------------------+--------------+--------------+
```

- 41 bits of milliseconds ≈ 69.7 years past the epoch (default epoch 2020-01-01, so valid until ~2089)
- 10 bits of node id → 1024 independent generators
- 12 bits of sequence → 4096 IDs per node per millisecond (≈ 4.1 M/s)
- Sign bit is always 0, so IDs fit a SQL `BIGINT` / Java `long`

## Features

- `Generator::next_id()` is **lock-free**: all state lives in one `AtomicU64`, updated by compare-and-swap
- Handles **sequence exhaustion** (waits for the next millisecond) and **clocks moving backwards**
  (strict error by default, or a configurable tolerance that keeps IDs monotonic)
- `SnowflakeId` type: pack/unpack fields, `Ord`, `Display`/`FromStr`, `as_i64`, compact **base-62** encoding
- Pluggable `Clock` trait with a `ManualClock` for deterministic tests (including time travel)
- `snowflake` CLI to generate, decode and benchmark IDs
- Dependency-free RFC 3339 date formatting (Hinnant's days→civil algorithm)

## CS concepts

| Concept | Where |
|---|---|
| **Bit packing** with shifts and masks; compile-time layout check | `src/layout.rs`, `src/id.rs` |
| **Lock-free concurrency**: CAS retry loop on a packed `AtomicU64`, `Acquire`/`Release` ordering | `src/generator.rs: next_id` |
| Distributed **uniqueness without coordination** (space partitioned by node id) | `tests/concurrency.rs: different_nodes_never_collide` |
| **Clock skew** and monotonicity; a small logical clock to ride out NTP corrections | `Config::max_backward_ms` |
| Dependency injection for **testable time** | `src/clock.rs: Clock`, `ManualClock` |
| Base conversion (base-62) with overflow checking | `SnowflakeId::to_base62` / `from_base62` |
| Calendar arithmetic without a date library | `src/timefmt.rs` |

### Why the CAS loop is correct

The state word is `(last_timestamp << 12) | last_sequence`. Every successful CAS replaces it with
a strictly **larger** value — either a later timestamp with sequence 0 or the same timestamp with
sequence + 1. Since the word only ever grows, no `(timestamp, sequence)` pair can be handed out
twice, and the node id makes the pair globally unique. A thread that loses the race just retries
with the newer value; nobody ever blocks while holding a lock.

## Build, run, test

Requires a Rust toolchain (1.70+).

```bash
cargo test                          # 15 unit + 4 integration + 1 doc test
cargo run --release -- gen -n 3 --node 42
cargo run --release -- decode 903096938902233088
cargo run --release -- bench -n 2000000 --threads 4
cargo run --example cluster         # three simulated machines, merged and sorted
cargo clippy --all-targets          # lint-clean
```

## Example output

```text
$ snowflake gen -n 3 --node 42
903096938893844480
903096938893844481
903096938893844482

$ snowflake decode 903096938902233088
id        903096938902233088  (b62:14iC035NHQu)
  time    2026-10-28T01:44:48.964Z  (+215315088964 ms since epoch)
  node    42
  seq     0
  binary  0000110010001000011100011110000110010001000000101010000000000000

$ snowflake bench -n 2000000 --threads 4
generated 2000000 IDs on 4 threads in 492.424ms
throughput 4.06 M ids/s (theoretical max 4.096 M/s per node)
duplicates 0
```

The benchmark runs right up against the 4096-per-millisecond ceiling: past that point the
generator waits for the clock, which is the design working as intended.

### Library usage

```rust
use snowflake_id::{Config, Generator, SnowflakeId};

let gen = Generator::new(42)?;                  // system clock, default epoch
let id = gen.next_id()?;
println!("{id} made by node {} at +{} ms", id.node_id(), id.timestamp());

// Tolerate up to 5 ms of backwards clock adjustment:
let tolerant = Generator::with_clock(Config::new(7).max_backward_ms(5), snowflake_id::SystemClock)?;

let back: SnowflakeId = id.to_string().parse()?;
assert_eq!(SnowflakeId::from_base62(&id.to_base62()), Some(back));
```

## Project layout

```text
src/layout.rs      bit widths, shifts, limits, default epoch
src/id.rs          SnowflakeId value type (pack/unpack, parse, base-62)
src/clock.rs       Clock trait, SystemClock, ManualClock
src/generator.rs   lock-free Generator, Config, Error
src/timefmt.rs     Unix ms → RFC 3339 UTC
src/main.rs        `snowflake` CLI
tests/             multi-threaded uniqueness and multi-node tests
examples/cluster.rs  simulated three-node cluster
```

## Possible extensions

- Configurable bit layout (e.g. 5-bit datacenter + 5-bit worker, or Sonyflake's 10 ms ticks)
- Lease node ids automatically from etcd/ZooKeeper/Redis instead of configuring them by hand
- Persist the last timestamp to disk so a restarted process can detect a clock that went backwards while it was down
- An HTTP or gRPC ID service with batching, and a comparison with UUIDv7 and ULID
- Criterion benchmarks comparing the CAS loop with a `Mutex` implementation
