# Producer-Consumer Simulator

A terminal simulation of the classic **bounded-buffer (producer-consumer) problem** in Java.
Producer threads make items and consumer threads process them, sharing a fixed-size ring
buffer synchronized with **counting semaphores**. Every put, take, and wait is printed with a
live picture of the buffer, so you can watch it fill, block, drain, and shut down.

```
Producer-Consumer: 2 producer(s) x 3 item(s), 1 consumer(s), buffer of 3

   20.0 ms  C1  waits for an item   [····· ····· ·····]  0/3  H0 T0  EMPTY
   44.8 ms  P2  put P2#1            [P2#1  ····· ·····]  1/3  H0 T1
   57.7 ms  P1  put P1#1            [····· P1#1  ·····]  1/3  H1 T2
   74.9 ms  C1  took P2#1           [····· P1#1  ·····]  1/3  H1 T2
   83.8 ms  P2  put P2#2            [····· P1#1  P2#2 ]  2/3  H1 T0
   97.5 ms  P1  put P1#2            [P1#2  P1#1  P2#2 ]  3/3  H1 T1  FULL
  101.5 ms  C1  took P1#1           [P1#2  ····· P2#2 ]  2/3  H2 T1
  ...
  174.6 ms  C1  took P2#3           [STOP  ····· P1#3 ]  2/3  H2 T1
  211.1 ms  C1  took P1#3           [STOP  ····· ·····]  1/3  H0 T1
  244.5 ms  C1  finished            [····· ····· ·····]  0/3  H1 T1  EMPTY

Summary
  elapsed            244.9 ms
  produced/consumed  6 / 6
  throughput         24.5 items/s
  peak occupancy     3 / 3
  producer blocks    0  (buffer full)
  consumer blocks    1  (buffer empty)
  per consumer       C1=6
  integrity          OK (every item consumed exactly once)
```

`H` and `T` are the ring's head (next slot to take from) and tail (next slot to put into).
Notice how `T` wraps from 2 back to 0, and the `STOP` poison pill that ends the consumer.

## CS concepts

- **Bounded buffer with three semaphores** (`BoundedBuffer`): `emptySlots` (starts at
  capacity), `filledSlots` (starts at 0), and a binary `mutex`. Producers do
  `P(empty); P(mutex); insert; V(mutex); V(full)` and consumers do the mirror image.
- **Why acquisition order matters**: taking `mutex` before `emptySlots` deadlocks. A
  producer would sleep on a full buffer while holding the lock that consumers need.
- **Circular buffer** indexing with `head`, `tail`, and modular arithmetic.
- **Fair semaphores**: FIFO wake-ups prevent starvation and keep the trace readable.
- **Poison-pill shutdown**: after producers finish, one sentinel per consumer is queued.
  FIFO order guarantees each pill arrives after all real work.
- **Lock-free statistics** with `AtomicInteger`/`AtomicIntegerArray`. The simulation also
  verifies its own integrity: no item is lost or consumed twice.
- **Throughput vs. buffer size**: compare runs with different capacities and speeds to see
  how a buffer smooths out bursts but can't fix a long-term rate mismatch.

## Project layout

```
src/main/java/dev/csprojects/prodcons/
  BoundedBuffer.java   semaphore-based ring buffer (put/take/offer/poll/snapshot)
  Item.java            work item + POISON sentinel
  Event.java           immutable trace event with a buffer snapshot
  Simulation.java      producer/consumer threads, poison-pill shutdown
  Stats.java           thread-safe counters and summary
  Visualizer.java      renders events and the ring buffer (optional ANSI color)
  Config.java          CLI flag parsing and validation
  Main.java            entry point
src/test/java/...      JUnit 5 tests
```

## Build, run, test

Requires JDK 17+ and Maven 3.8+.

```bash
mvn package                      # compile, test, build the jar
java -jar target/producer-consumer-simulator-1.0.0.jar
mvn test                         # tests only

# or with make
make test
make run ARGS="-b 2 -p 3 -c 1 --consume-delay 120"
```

### Options

| Flag | Meaning | Default |
|------|---------|---------|
| `-b, --capacity N` | buffer slots | 5 |
| `-p, --producers N` | producer threads | 2 |
| `-c, --consumers N` | consumer threads | 2 |
| `-n, --items N` | items per producer | 8 |
| `--produce-delay MS` | mean time to make an item (±50% jitter) | 40 |
| `--consume-delay MS` | mean time to process an item (±50% jitter) | 60 |
| `--seed N` | jitter seed | 42 |
| `--no-color` | plain output | off |
| `-q, --quiet` | summary only | off |

Experiments to try:

- `-b 1`: a buffer of one forces producers and consumers into lockstep.
- `-p 4 -c 1 --consume-delay 100`: watch the buffer sit `FULL` and producer blocks climb.
- `-p 1 -c 4 --produce-delay 100`: consumers spend most of their time waiting.

## Tests

The tests cover FIFO order and ring wrap-around, timeouts, blocking `put` when full and
blocking `take` when empty, a stress test (8 threads, 8,000 items, no loss or duplication,
occupancy never above capacity), end-to-end simulation integrity, event ordering, CLI
parsing, and rendering.

Note: this project was built in a sandbox that could not reach Maven Central. There, the test
sources were compiled with `javac` and run against a minimal stand-in for the JUnit 5
assertions API: all 20 tests passed. On a normal machine, `mvn test` runs them with real JUnit 5.

## Possible extensions

- Swap the semaphores for `ReentrantLock` + two `Condition`s, or a monitor
  (`synchronized`/`wait`/`notifyAll`), and compare.
- Add a deliberately broken mode (wrong acquire order, missing mutex) that shows the
  deadlock or race it causes.
- Priority items, multiple buffers in a pipeline, or a dynamically resizable buffer.
- A Swing/JavaFX or web front end that animates the ring.
- Sweep capacities and plot throughput and blocking counts.
