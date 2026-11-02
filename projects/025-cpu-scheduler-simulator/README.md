# CPU Scheduler Simulator

A discrete-event simulator for the classic uniprocessor CPU scheduling
algorithms. Give it a workload of processes (arrival time + CPU burst) and it
produces the exact timeline each scheduler would follow, draws it as a Gantt
chart (ASCII in the terminal, SVG to a file), and computes the standard
metrics so you can compare policies side by side.

Algorithms:

| Name | Flag | Preemptive | Idea |
|------|------|------------|------|
| First-Come, First-Served | `fcfs` | no | run jobs in arrival order |
| Shortest Job First | `sjf` | no | when the CPU frees up, run the shortest ready job |
| Shortest Remaining Time First | `srtf` | yes | SJF, but re-decide at every arrival |
| Round Robin | `rr` | yes | FIFO queue, each job gets at most `q` units per turn |
| Multi-Level Feedback Queue | `mlfq` | yes | priority queues that *learn* which jobs are short |

Pure Python standard library; no dependencies.

```
$ cpusched run examples/classic.csv -a rr -q 2
== RR (q=2) ==

+----+----+----+----+----+----+----+----+----+----+----+----+------+
| P1 | P2 | P3 | P1 | P4 | P2 | P3 | P1 | P4 | P3 | P1 | P4 |  P3  |
+----+----+----+----+----+----+----+----+----+----+----+----+------+
0    2    4    6    8    10   12   14   16   18   20   22   23     26

PID  Arrival  Burst  Start  Finish  Turnaround  Waiting  Response
---  -------  -----  -----  ------  ----------  -------  --------
 P1        0      8      0      22          22       14         0
 P2        1      4      2      12          11        7         1
 P3        2      9      4      26          24       15         2
 P4        3      5      8      23          20       15         5
---  -------  -----  -----  ------  ----------  -------  --------
avg                                      19.25    12.75      2.00

makespan=26  CPU utilization=100.0%  throughput=0.154/unit  context switches=12
```

## Key CS concepts

- **Discrete-event simulation.** There is no clock ticking one unit at a
  time. The simulator jumps straight to the next *event* (an arrival, a
  completion, a quantum expiry or a priority boost) and makes a scheduling
  decision there. That's how real OS simulators and network simulators work.
- **Preemptive vs. non-preemptive scheduling.** SJF and SRTF use the same
  rule; the only difference is whether an arrival can interrupt the running
  job. On the textbook workload that one change drops average waiting time
  from 7.75 to 6.50.
- **The trade-off between turnaround and response time.** SRTF is optimal
  for average waiting time but needs to know the future. Round Robin and MLFQ
  give the best *response* time (how soon a job first gets the CPU) and pay
  for it in turnaround and context switches.
- **The convoy effect.** In `examples/convoy.csv` one 30-unit job arrives
  just ahead of four 2-unit jobs. Under FCFS the short jobs wait behind it
  (average wait 24.4); every preemptive policy cuts that to under 5.
- **MLFQ, following OSTEP chapter 8.** New jobs start at the top. A job that
  uses up its allotment at a level gets demoted. A periodic **priority boost**
  moves everything back to the top so long jobs can't **starve**. With only
  CPU-bound jobs, MLFQ ends up approximating SJF without knowing burst
  lengths.
- **Data structures.** SJF and SRTF use a binary heap (`heapq`) keyed on
  `(burst, arrival, input order)`. RR and MLFQ use `collections.deque` as
  FIFO ready queues.
- **Invariants as a test oracle.** `summarize()` checks every schedule as it
  computes metrics: no overlapping slices, no process runs before it
  arrives, and each process gets exactly its burst. Property tests run every
  algorithm on hundreds of random workloads and also check facts from
  scheduling theory: SRTF never loses on average waiting time, and every
  algorithm here is work-conserving, so they all have the same makespan.

### Metric definitions

| Metric | Formula |
|--------|---------|
| turnaround | completion − arrival |
| waiting | turnaround − burst |
| response | first time on CPU − arrival |
| CPU utilization | busy time / makespan |
| throughput | processes / makespan |
| context switches | changes from one process to a different one (idle gaps ignored) |

## Project layout

```
src/cpusched/
  models.py      Process, Slice, Schedule (timeline with slice merging)
  algorithms.py  fcfs, sjf, srtf, round_robin, mlfq
  metrics.py     per-process stats, averages, schedule validation
  gantt.py       ASCII and SVG Gantt charts
  workload.py    CSV parsing and random workload generation
  cli.py         `cpusched run | compare | random`
tests/           unit tests, property tests, CLI/IO tests (pytest)
examples/        classic.csv, convoy.csv, staggered.csv
```

## Build, run, test

Requires Python 3.10+.

```bash
make dev                      # pip install -e '.[dev]'  (installs pytest)
make test                     # python -m pytest   -> 468 tests
make demo                     # RR and MLFQ on the sample workload
make compare                  # all algorithms side by side

# without installing:
PYTHONPATH=src python3 -m cpusched run examples/classic.csv -a srtf
```

### CLI

```
cpusched run WORKLOAD -a {fcfs,sjf,srtf,rr,mlfq} [-q QUANTUM]
             [--quanta 2,4,0] [--boost N] [--scale N] [--svg chart.svg]
cpusched compare WORKLOAD [-q QUANTUM] [--quanta ...] [--boost N] [--gantt]
cpusched random N [--seed S] > workload.csv
```

`--quanta` gives the MLFQ allotment for each level, top first, and `0`
means unlimited (FCFS) for the bottom level. Workload files are CSV,
`pid,arrival,burst`, with optional header and `#` comments.

### Example: comparing policies on the convoy workload

```
$ cpusched compare examples/convoy.csv -q 2 --boost 10
Algorithm               Avg turnaround  Avg waiting  Avg response  Switches  Makespan
----------------------  --------------  -----------  ------------  --------  --------
FCFS                             32.00        24.40         24.40         4        38
SJF                              32.00        24.40         24.40         4        38
SRTF                             10.40         2.80          1.20         5        38
RR (q=2)                         12.00         4.40          2.80         6        38
MLFQ (2/4/∞, boost=10)           11.20         3.60          2.00         5        38
```

SJF doesn't help here. When the CPU first becomes free at t=0, the long job
is the only one that has arrived, so non-preemptive SJF has to start it.

### Example: watching MLFQ demote jobs

`@n` is the queue level the slice ran from:

```
$ cpusched run examples/classic.csv -a mlfq --quanta 2,4,0
+------+------+------+------+--------+------+--------+------+------+------+
| P1@0 | P2@0 | P3@0 | P4@0 |  P1@1  | P2@1 |  P3@1  | P4@1 | P1@2 | P3@2 |
+------+------+------+------+--------+------+--------+------+------+------+
0      2      4      6      8        12     14       18     21     23     26
```

### Library use

```python
from cpusched import Process, mlfq, summarize, ascii_gantt

jobs = [Process("A", 0, 10), Process("B", 3, 1)]
sched = mlfq(jobs, quanta=(2, 4, None), boost=20)
print(ascii_gantt(sched, show_levels=True))
print(summarize(sched).avg_response)
```

## Modelling choices

- Times are integers. Context switches cost nothing.
- Ties go to the earlier arrival, then to input order, so every run gives
  the same result.
- In Round Robin, a job that arrives at the exact moment a quantum expires
  goes into the queue *ahead of* the preempted job (the usual textbook
  convention).
- In MLFQ, a job preempted by a higher-priority arrival goes back to the
  *front* of its queue and keeps the allotment it has already used.

## Possible extensions

- I/O bursts (CPU–I/O–CPU job profiles), so MLFQ's reward for interactive
  jobs that give up the CPU early actually shows.
- A non-zero context-switch cost, then plot average waiting time against
  the RR quantum to find the sweet spot.
- Priority scheduling with aging, lottery/stride scheduling, or a toy
  Linux CFS (red-black tree keyed on virtual runtime).
- Multiprocessor scheduling with per-CPU queues and work stealing.
- An interactive HTML visualiser that animates the timeline.
