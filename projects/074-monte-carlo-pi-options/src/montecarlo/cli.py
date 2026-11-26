"""Command-line interface: ``montecarlo pi | option | convergence``."""

from __future__ import annotations

import argparse
import time
from math import pi as PI

from .options import Method, OptionKind, OptionSpec, black_scholes_price, mc_price
from .pi import estimate_pi, estimate_pi_stratified


def _cmd_pi(args: argparse.Namespace) -> int:
    start = time.perf_counter()
    fn = estimate_pi_stratified if args.stratified else estimate_pi
    est = fn(args.samples, seed=args.seed, confidence=args.confidence)
    elapsed = time.perf_counter() - start
    label = "stratified" if args.stratified else "crude"
    print(f"pi ({label})  ≈ {est}")
    print(f"true pi        = {PI:.6f}")
    print(f"abs error      = {abs(est.value - PI):.6f}  "
          f"({'inside' if est.contains(PI) else 'OUTSIDE'} the CI)")
    print(f"time           = {elapsed:.3f}s")
    return 0


def _cmd_option(args: argparse.Namespace) -> int:
    spec = OptionSpec(args.spot, args.strike, args.rate, args.vol, args.maturity, args.kind)
    exact = black_scholes_price(spec)
    print(f"European {spec.kind.value}: S0={spec.spot} K={spec.strike} r={spec.rate} "
          f"sigma={spec.vol} T={spec.maturity}")
    print(f"Black-Scholes  = {exact:.6f}")
    crude_se = None
    for method in Method:
        est = mc_price(spec, args.samples, method, seed=args.seed, confidence=args.confidence)
        if method is Method.CRUDE:
            crude_se = est.std_error
        speedup = (crude_se / est.std_error) ** 2 if est.std_error > 0 else float("inf")
        print(f"{method.value:<11}    = {est}  variance reduction x{speedup:.1f}")
    return 0


def _cmd_convergence(args: argparse.Namespace) -> int:
    """Show the 1/sqrt(n) error law: each 100x more samples ~ 10x smaller SE."""
    print(f"{'n':>12} {'pi estimate':>12} {'std error':>12} {'SE*sqrt(n)':>12}")
    n = 100
    while n <= args.max_samples:
        est = estimate_pi(n, seed=args.seed)
        print(f"{n:>12,} {est.value:>12.6f} {est.std_error:>12.6f} {est.std_error * n ** 0.5:>12.4f}")
        n *= 10
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="montecarlo",
                                     description="Monte Carlo estimates of pi and option prices.")
    sub = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--seed", type=int, default=None, help="RNG seed for reproducibility")
    common.add_argument("--confidence", type=float, default=0.95, choices=[0.90, 0.95, 0.99])

    p = sub.add_parser("pi", parents=[common], help="estimate pi with random darts")
    p.add_argument("--samples", "-n", type=int, default=1_000_000)
    p.add_argument("--stratified", action="store_true", help="use stratified sampling")
    p.set_defaults(func=_cmd_pi)

    o = sub.add_parser("option", parents=[common], help="price a European option")
    o.add_argument("--spot", type=float, default=100.0)
    o.add_argument("--strike", type=float, default=100.0)
    o.add_argument("--rate", type=float, default=0.05)
    o.add_argument("--vol", type=float, default=0.2)
    o.add_argument("--maturity", type=float, default=1.0)
    o.add_argument("--kind", choices=[k.value for k in OptionKind], default="call")
    o.add_argument("--samples", "-n", type=int, default=200_000)
    o.set_defaults(func=_cmd_option)

    c = sub.add_parser("convergence", parents=[common], help="demonstrate the 1/sqrt(n) law")
    c.add_argument("--max-samples", type=int, default=10_000_000)
    c.set_defaults(func=_cmd_convergence)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)
