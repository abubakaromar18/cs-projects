"""Monte Carlo simulation toolkit: estimate pi and price European options.

Every estimator returns an :class:`~montecarlo.stats.Estimate`, which carries
the point estimate together with its standard error and a confidence interval,
so the statistical uncertainty of a simulation is never hidden.
"""

from .stats import Estimate, estimate_from_samples
from .pi import estimate_pi, estimate_pi_stratified
from .options import (
    OptionSpec,
    black_scholes_price,
    mc_price,
    simulate_terminal_prices,
)

__all__ = [
    "Estimate",
    "estimate_from_samples",
    "estimate_pi",
    "estimate_pi_stratified",
    "OptionSpec",
    "black_scholes_price",
    "mc_price",
    "simulate_terminal_prices",
]

__version__ = "1.0.0"
