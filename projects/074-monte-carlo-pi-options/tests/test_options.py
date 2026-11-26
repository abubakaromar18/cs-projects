import pytest

from montecarlo import OptionSpec, black_scholes_price, mc_price
from montecarlo.options import Method

ATM_CALL = OptionSpec(100, 100, 0.05, 0.2, 1.0, "call")
OTM_PUT = OptionSpec(100, 90, 0.03, 0.3, 0.5, "put")


def test_black_scholes_reference_value():
    # Textbook value (Hull): S=100, K=100, r=5%, sigma=20%, T=1 -> 10.4506
    assert black_scholes_price(ATM_CALL) == pytest.approx(10.450584, abs=1e-5)


def test_put_call_parity():
    put = OptionSpec(100, 100, 0.05, 0.2, 1.0, "put")
    lhs = black_scholes_price(ATM_CALL) - black_scholes_price(put)
    rhs = 100 - 100 * ATM_CALL.discount
    assert lhs == pytest.approx(rhs, abs=1e-10)


@pytest.mark.parametrize("method", list(Method))
@pytest.mark.parametrize("spec", [ATM_CALL, OTM_PUT])
def test_mc_matches_black_scholes(spec, method):
    est = mc_price(spec, 200_000, method, seed=42)
    exact = black_scholes_price(spec)
    assert abs(est.value - exact) < 4 * est.std_error
    assert abs(est.value - exact) / exact < 0.02


def test_variance_reduction_lowers_standard_error():
    crude = mc_price(ATM_CALL, 100_000, "crude", seed=7)
    anti = mc_price(ATM_CALL, 100_000, "antithetic", seed=7)
    ctrl = mc_price(ATM_CALL, 100_000, "control", seed=7)
    assert anti.std_error < crude.std_error
    assert ctrl.std_error < crude.std_error / 2  # strong correlation for a call


def test_reproducible_and_validates_inputs():
    assert mc_price(ATM_CALL, 1_000, seed=1) == mc_price(ATM_CALL, 1_000, seed=1)
    with pytest.raises(ValueError):
        OptionSpec(-1, 100, 0.05, 0.2, 1.0)
    with pytest.raises(ValueError):
        OptionSpec(100, 100, 0.05, 0.0, 1.0)
    with pytest.raises(ValueError):
        mc_price(ATM_CALL, 2)
    with pytest.raises(ValueError):
        mc_price(ATM_CALL, 1_000, "bogus")
