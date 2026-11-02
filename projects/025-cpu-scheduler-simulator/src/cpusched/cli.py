"""Command-line interface.

    cpusched run WORKLOAD -a ALGO [-q N] [--quanta 2,4,0] [--boost N] [--svg FILE]
    cpusched compare WORKLOAD [-q N]
    cpusched random N [--seed S]          # print a random workload as CSV
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .algorithms import fcfs, mlfq, round_robin, sjf, srtf
from .gantt import ascii_gantt, svg_gantt
from .metrics import Summary, summarize
from .models import Process, Schedule
from .workload import load_workload, random_workload


def _parse_quanta(text: str) -> tuple[int | None, ...]:
    try:
        return tuple(int(x) or None for x in text.split(","))
    except ValueError:
        raise argparse.ArgumentTypeError("quanta must be comma-separated integers, e.g. 2,4,0")


def build_schedule(args: argparse.Namespace, procs: list[Process]) -> Schedule:
    algo = args.algorithm
    if algo == "fcfs":
        return fcfs(procs)
    if algo == "sjf":
        return sjf(procs)
    if algo == "srtf":
        return srtf(procs)
    if algo == "rr":
        return round_robin(procs, args.quantum)
    return mlfq(procs, args.quanta, args.boost)


def format_table(summary: Summary) -> str:
    rows = [("PID", "Arrival", "Burst", "Start", "Finish", "Turnaround", "Waiting", "Response")]
    for s in summary.per_process:
        rows.append((s.pid, s.arrival, s.burst, s.first_run, s.completion,
                     s.turnaround, s.waiting, s.response))
    rows.append(("avg", "", "", "", "", f"{summary.avg_turnaround:.2f}",
                 f"{summary.avg_waiting:.2f}", f"{summary.avg_response:.2f}"))
    cells = [[str(c) for c in r] for r in rows]
    widths = [max(len(r[i]) for r in cells) for i in range(len(cells[0]))]
    lines = ["  ".join(c.rjust(w) for c, w in zip(r, widths)) for r in cells]
    lines.insert(1, "  ".join("-" * w for w in widths))
    lines.insert(-1, lines[1])
    return "\n".join(lines)


def format_footer(summary: Summary) -> str:
    return (f"makespan={summary.makespan}  CPU utilization={summary.utilization:.1%}  "
            f"throughput={summary.throughput:.3f}/unit  context switches={summary.context_switches}")


def cmd_run(args: argparse.Namespace) -> int:
    procs = load_workload(args.workload)
    sched = build_schedule(args, procs)
    summary = summarize(sched)
    print(f"== {sched.algorithm} ==\n")
    print(ascii_gantt(sched, scale=args.scale, show_levels=args.algorithm == "mlfq"))
    print()
    print(format_table(summary))
    print()
    print(format_footer(summary))
    if args.svg:
        Path(args.svg).write_text(svg_gantt(sched), encoding="utf-8")
        print(f"\nwrote {args.svg}")
    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    procs = load_workload(args.workload)
    schedules = [fcfs(procs), sjf(procs), srtf(procs),
                 round_robin(procs, args.quantum), mlfq(procs, args.quanta, args.boost)]
    rows = [("Algorithm", "Avg turnaround", "Avg waiting", "Avg response", "Switches", "Makespan")]
    for sched in schedules:
        s = summarize(sched)
        rows.append((s.algorithm, f"{s.avg_turnaround:.2f}", f"{s.avg_waiting:.2f}",
                     f"{s.avg_response:.2f}", str(s.context_switches), str(s.makespan)))
    widths = [max(len(r[i]) for r in rows) for i in range(len(rows[0]))]
    for i, r in enumerate(rows):
        print("  ".join(r[0].ljust(widths[0]) if j == 0 else c.rjust(widths[j])
                        for j, c in enumerate(r)))
        if i == 0:
            print("  ".join("-" * w for w in widths))
    if args.gantt:
        for sched in schedules:
            print(f"\n{sched.algorithm}")
            print(ascii_gantt(sched, scale=args.scale))
    return 0


def cmd_random(args: argparse.Namespace) -> int:
    print("pid,arrival,burst")
    for p in random_workload(args.n, seed=args.seed):
        print(f"{p.pid},{p.arrival},{p.burst}")
    return 0


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cpusched", description="CPU scheduling simulator")
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p: argparse.ArgumentParser) -> None:
        p.add_argument("workload", help="CSV file of pid,arrival,burst")
        p.add_argument("-q", "--quantum", type=int, default=2, help="Round Robin quantum (default 2)")
        p.add_argument("--quanta", type=_parse_quanta, default=(2, 4, None),
                       help="MLFQ allotments per level, 0 = unlimited (default 2,4,0)")
        p.add_argument("--boost", type=int, default=None, help="MLFQ priority-boost period")
        p.add_argument("--scale", type=int, default=2, help="ASCII columns per time unit")

    run = sub.add_parser("run", help="simulate one algorithm")
    common(run)
    run.add_argument("-a", "--algorithm", choices=["fcfs", "sjf", "srtf", "rr", "mlfq"], default="fcfs")
    run.add_argument("--svg", help="also write an SVG Gantt chart to this file")
    run.set_defaults(func=cmd_run)

    cmp_ = sub.add_parser("compare", help="compare all algorithms on one workload")
    common(cmp_)
    cmp_.add_argument("--gantt", action="store_true", help="print each algorithm's Gantt chart too")
    cmp_.set_defaults(func=cmd_compare)

    rnd = sub.add_parser("random", help="print a random workload")
    rnd.add_argument("n", type=int)
    rnd.add_argument("--seed", type=int, default=None)
    rnd.set_defaults(func=cmd_random)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = make_parser().parse_args(argv)
    try:
        return args.func(args)
    except (OSError, ValueError) as exc:
        print(f"cpusched: error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
