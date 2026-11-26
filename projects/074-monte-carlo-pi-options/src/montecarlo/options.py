"""Pricing European options by simulating geometric Brownian motion.

Under the risk-neutral measure a stock follows dS = r S dt + sigma S dW, so
its price at maturity T is

    S_T = S_0 * exp((r - sigma^2 / 2) T + sigma sqrt(T) Z),   Z ~ N(0, 1).

The fair price of an option paying f(S_T) is exp(-rT) * E[f(S_T)], which we
estimate with a sample mean. Because European options also have the
closed-form Black-Scholes price, we can check the simulation exactly.

Two classic variance-reduction techniques are implemented:

* Antithetic variates - pair every Z with -Z. The two payoffs are negatively
  correlated, so their average has lower variance than two independent draws.
* Control variates - the discounted terminal price exp(-rT) S_T has known
  mean S_0. Its correlation with the payoff lets us subtract out noise:
  Y_cv = Y - beta (C - S_0), with beta = Cov(Y, C) / Var(C).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import erf, exp, log, sqrt

import numpy as np

from .stats import Estimate, estimate_from_samples


class OptionKind(str, Enum):
    CALL = "call"
    PUT = "put"


class Method(str, Enum):
    CRUDE = "crude"
    ANTITHETIC = "antithetic"
    CONTROL = "control"


@dataclass(frozen=True)
class OptionSpec:
    """A European option on a non-dividend-paying stock."""

    spot: float        # S_0, current stock price
    strike: float      # K
    rate: float        # r, continuously compounded risk-free rate
    vol: float         # sigma, annualised volatility
    maturity: float    # T, in years
    kind: OptionKind = OptionKind.CALL

    def __post_init__(self) -> None:
        if self.spot <= 0 or self.strike <= 0:
            raise ValueError("spot and strike must be positive")
        if self.vol <= 0 or self.maturity <= 0:
            raise ValueError("vol and maturity must be positive")
        object.__setattr__(self, "kind", OptionKind(self.kind))

    def payoff(self, terminal: np.ndarray) -> np.ndarray:
        if self.kind is OptionKind.CALL:
            return np.maximum(terminal - self.strike, 0.0)
        return np.maximum(self.strike - terminal, 0.0)

    @property
    def discount(self) -> float:
        return exp(-self.rate * self.maturity)


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + erf(x / sqrt(2.0)))


def black_scholes_price(spec: OptionSpec) -> float:
    """Closed-form Black-Scholes price, used as ground truth."""
    s, k, r, v, t = spec.spot, spec.strike, spec.rate, spec.vol, spec.maturity
    d1 = (log(s / k) + (r + 0.5 * v * v) * t) / (v * sqrt(t))
    d2 = d1 - v * sqrt(t)
    if spec.kind is OptionKind.CALL:
        return s * _norm_cdf(d1) - k * exp(-r * t) * _norm_cdf(d2)
    return k * exp(-r * t) * _norm_cdf(-d2) - s * _norm_cdf(-d1)


def simulate_terminal_prices(spec: OptionSpec, z: np.ndarray) -> np.ndarray:
    """Map standard Normal draws ``z`` to terminal stock prices S_T."""
    drift = (spec.rate - 0.5 * spec.vol ** 2) * spec.maturity
    diffusion = spec.vol * sqrt(spec.maturity)
    return spec.spot * np.exp(drift + diffusion * z)


def mc_price(spec: OptionSpec, samples: int, method: Method | str = Method.CRUDE,
             seed: int | np.random.Generator | None = None,
             confidence: float = 0.95) -> Estimate:
    """Monte Carlo price of ``spec`` using ``samples`` Normal draws.

    For a fair comparison every method consumes the same number of random
    normals; antithetic pairs therefore yield ``samples // 2`` i.i.d. values.
    """
    method = Method(method)
    if samples < 4:
        raise ValueError("samples must be >= 4")
    rng = seed if isinstance(seed, np.random.Generator) else np.random.default_rng(seed)

    if method is Method.ANTITHETIC:
        z = rng.standard_normal(samples // 2)
        up = spec.payoff(simulate_terminal_prices(spec, z))
        down = spec.payoff(simulate_terminal_prices(spec, -z))
        # Each pair average is one i.i.d. observation.
        return estimate_from_samples(spec.discount * 0.5 * (up + down), confidence)

    z = rng.standard_normal(samples)
    terminal = simulate_terminal_prices(spec, z)
    y = spec.discount * spec.payoff(terminal)

    if method is Method.CRUDE:
        return estimate_from_samples(y, confidence)

    # Control variate: C = discounted S_T, with exact mean S_0 (martingale).
    c = spec.discount * terminal
    cov = np.cov(y, c, ddof=1)
    beta = cov[0, 1] / cov[1, 1]
    adjusted = y - beta * (c - spec.spot)
    return estimate_from_samples(adjusted, confidence)


__all__ = ["OptionKind", "Method", "OptionSpec", "black_scholes_price",
           "simulate_terminal_prices", "mc_price"]
