# Monte Carlo Pi & Options

A small, polished NumPy toolkit that uses random simulation to estimate **π** and to price
**European options**, and checks every answer against the exact one. Every estimate comes
with its standard error and a confidence interval, so you can see how much to trust it.

## What it does

- **π by darts**: throws uniform points at the unit square and counts how many land in the
  quarter circle (probability π/4). Includes a **stratified-sampling** version that is about
  18× more precise for the same number of points.
- **Option pricing**: simulates geometric Brownian motion to price European calls and puts,
  compared with the closed-form **Black-Scholes** price. Three estimators:
  crude, **antithetic variates** and **control variates**.
- **Convergence demo**: shows the 1/√n error law in a table.

## CS & math concepts

| Concept | Where |
|---|---|
| Law of Large Numbers, Central Limit Theorem, confidence intervals | `stats.py` |
| Bernoulli estimators, batched vectorised simulation (bounded memory) | `pi.py` |
| Stratified sampling (variance reduction) | `pi.py` |
| Geometric Brownian motion, risk-neutral pricing, Black-Scholes | `options.py` |
| Antithetic & control variates, regression-optimal β | `options.py` |
| Reproducible RNG streams (`numpy.random.Generator`) | everywhere |

## Layout

```
src/montecarlo/
  stats.py     Estimate dataclass, standard errors, z-scores
  pi.py        crude + stratified π estimators
  options.py   OptionSpec, GBM simulation, Black-Scholes, MC pricer
  cli.py       argparse front end (pi / option / convergence)
tests/         pytest suite (21 tests)
```

## Build, run, test

Requires Python 3.10+ and NumPy.

```bash
make install        # pip install -e ".[dev]"
make test           # python -m pytest
make demo           # runs the three CLI commands below

montecarlo pi --samples 1000000 --seed 42 [--stratified]
montecarlo option --spot 100 --strike 105 --rate 0.05 --vol 0.2 --maturity 1 --kind call
montecarlo convergence --max-samples 10000000
```

Without installing: `PYTHONPATH=src python -m montecarlo pi`.

Library use:

```python
from montecarlo import OptionSpec, mc_price, black_scholes_price, estimate_pi

print(estimate_pi(1_000_000, seed=1))
spec = OptionSpec(spot=100, strike=100, rate=0.05, vol=0.2, maturity=1.0, kind="call")
print(black_scholes_price(spec), mc_price(spec, 200_000, "control", seed=1))
```

## Example output

```
$ montecarlo pi --samples 1000000 --seed 42
pi (crude)  ≈ 3.142980 ± 0.003217 (95% CI [3.139763, 3.146197], n=1,000,000)
true pi        = 3.141593
abs error      = 0.001387  (inside the CI)

$ montecarlo pi --samples 1000000 --seed 42 --stratified
pi (stratified)  ≈ 3.141568 ± 0.000181 (95% CI [3.141387, 3.141749], n=1,000,000)

$ montecarlo option --spot 100 --strike 105 --seed 42
European call: S0=100.0 K=105.0 r=0.05 sigma=0.2 T=1.0
Black-Scholes  = 8.021352
crude          = 8.039778 ± 0.058235 (95% CI [7.981543, 8.098013], n=200,000)  variance reduction x1.0
antithetic     = 8.046100 ± 0.046285 (95% CI [7.999815, 8.092385], n=100,000)  variance reduction x1.6
control        = 8.041266 ± 0.026404 (95% CI [8.014861, 8.067670], n=200,000)  variance reduction x4.9

$ montecarlo convergence --seed 7
           n  pi estimate    std error   SE*sqrt(n)
         100     3.080000     0.169181       1.6918
      10,000     3.164400     0.016262       1.6262
   1,000,000     3.143496     0.001641       1.6409
  10,000,000     3.141603     0.000519       1.6422
```

The constant `SE*sqrt(n)` column is the 1/√n law: 100× more samples buys one more digit.
"Variance reduction ×k" means the estimator matches crude Monte Carlo run with k× more samples.

## Tests

`pytest` checks: the CI covers π about 95% of the time over 400 repeated runs; SE shrinks
about 10× per 100× samples; stratified beats crude; Black-Scholes matches Hull's textbook
value 10.4506 and satisfies put-call parity; every MC method lands within 4 SE of the exact
price; variance reduction lowers SE; and the CLI commands run.

## Possible extensions

- Quasi-Monte Carlo (Sobol / Halton sequences) for close to 1/n convergence
- Path-dependent options (Asian, barrier, lookback) via multi-step GBM paths
- Greeks via pathwise derivatives or likelihood-ratio estimators
- Importance sampling for deep out-of-the-money options
- Parallel simulation with `multiprocessing` and independent `SeedSequence.spawn` streams
- Matplotlib plots of dart throws and the convergence curve
