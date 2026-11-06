from rag.financial_calculator import (
    calculate_cagr,
    calculate_current_ratio,
    calculate_debt_to_equity,
    calculate_growth,
    calculate_margin,
)


def test_growth_calculation():
    result = calculate_growth(120, 100)
    assert result["status"] == "ok"
    assert abs(result["result"] - 20.0) < 1e-9


def test_margin_calculation():
    result = calculate_margin(25, 100)
    assert abs(result["result"] - 25.0) < 1e-9


def test_cagr_calculation():
    result = calculate_cagr(100, 121, 2)
    assert abs(result["result"] - 10.0) < 1e-9


def test_current_ratio_calculation():
    result = calculate_current_ratio(120, 60)
    assert abs(result["result"] - 2.0) < 1e-9


def test_debt_to_equity_calculation():
    result = calculate_debt_to_equity(60, 30)
    assert abs(result["result"] - 2.0) < 1e-9


def test_zero_denominator_rejected():
    try:
        calculate_margin(25, 0)
    except ValueError:
        return
    raise AssertionError("Expected ValueError for zero denominator in margin calculation")
