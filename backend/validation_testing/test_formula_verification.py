
import pytest

from rag.financial_calculator import (
    calculate_quick_ratio,
    calculate_interest_coverage,
    calculate_free_cash_flow,
    calculate_eps,
    calculate_dividend_yield,
    calculate_growth,
    calculate_cagr,
)


# Independent formula verification tests

def test_quick_ratio_accuracy():
    result = calculate_quick_ratio(120000, 60000)
    assert result["result"] == pytest.approx(2.0)


def test_interest_coverage_accuracy():
    result = calculate_interest_coverage(500000, 100000)
    assert result["result"] == pytest.approx(5.0)


def test_free_cash_flow_accuracy():
    result = calculate_free_cash_flow(800000, 250000)
    assert result["result"] == pytest.approx(550000.0)


def test_eps_with_negative_income():
    result = calculate_eps(-2000000, 1000000)
    assert result["result"] == pytest.approx(-2.0)


def test_dividend_yield_accuracy():
    result = calculate_dividend_yield(4, 80)
    assert result["result"] == pytest.approx(5.0)


def test_growth_precision():
    result = calculate_growth(125, 100)
    assert result["result"] == pytest.approx(25.0, abs=1e-9)


def test_cagr_accuracy():
    result = calculate_cagr(100, 133.1, 3)
    assert result["result"] == pytest.approx(10.0, abs=1e-9)


# Numerical input validation tests

@pytest.mark.parametrize("invalid_value", [
    None,
    "invalid",
    float("nan"),
    float("inf"),
    float("-inf"),
])
def test_invalid_financial_input_rejected(invalid_value):
    with pytest.raises(ValueError):
        calculate_free_cash_flow(invalid_value, 100)

def test_free_cash_flow_with_negative_operating_cash_flow():
    result = calculate_free_cash_flow(-100000, 25000)
    assert result["result"] == pytest.approx(-125000.0)


def test_eps_with_small_positive_values():
    result = calculate_eps(0.01, 2)
    assert result["result"] == pytest.approx(0.005)


def test_quick_ratio_with_large_values():
    result = calculate_quick_ratio(1_000_000_000, 500_000_000)
    assert result["result"] == pytest.approx(2.0)


def test_growth_with_declining_value():
    result = calculate_growth(80, 100)
    assert result["result"] == pytest.approx(-20.0)