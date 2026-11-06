from __future__ import annotations

import math
from typing import Any


def _coerce_float(value: Any, field_name: str) -> float:
    if value is None:
        raise ValueError(f"{field_name} is required.")
    try:
        numeric_value = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be numeric.") from exc
    if math.isnan(numeric_value) or math.isinf(numeric_value):
        raise ValueError(f"{field_name} must be a finite number.")
    return numeric_value


def _result_payload(metric: str, formula: str, inputs: dict[str, Any], result: float, unit: str | None = None) -> dict[str, Any]:
    return {
        "metric": metric,
        "formula": formula,
        "inputs": inputs,
        "result": result,
        "unit": unit,
        "status": "ok",
    }


def calculate_growth(current_value: Any, previous_value: Any, *, periods: int = 1) -> dict[str, Any]:
    current = _coerce_float(current_value, "current_value")
    previous = _coerce_float(previous_value, "previous_value")
    if periods <= 0:
        raise ValueError("periods must be greater than zero.")
    if previous == 0:
        raise ValueError("previous_value cannot be zero when calculating growth.")
    growth_pct = ((current - previous) / abs(previous)) * 100.0
    return _result_payload(
        "growth",
        "((current - previous) / abs(previous)) * 100",
        {"current_value": current, "previous_value": previous, "periods": periods},
        growth_pct,
        unit="%",
    )


def calculate_margin(profit_value: Any, revenue_value: Any) -> dict[str, Any]:
    profit = _coerce_float(profit_value, "profit_value")
    revenue = _coerce_float(revenue_value, "revenue_value")
    if revenue == 0:
        raise ValueError("revenue_value cannot be zero when calculating margin.")
    margin_pct = (profit / revenue) * 100.0
    return _result_payload(
        "margin",
        "(profit / revenue) * 100",
        {"profit_value": profit, "revenue_value": revenue},
        margin_pct,
        unit="%",
    )


def calculate_cagr(start_value: Any, end_value: Any, years: Any) -> dict[str, Any]:
    start = _coerce_float(start_value, "start_value")
    end = _coerce_float(end_value, "end_value")
    periods = _coerce_float(years, "years")
    if start == 0:
        raise ValueError("start_value cannot be zero when calculating CAGR.")
    if periods <= 0:
        raise ValueError("years must be greater than zero.")
    cagr = ((end / start) ** (1.0 / periods) - 1.0) * 100.0
    return _result_payload(
        "CAGR",
        "((end / start) ** (1 / years) - 1) * 100",
        {"start_value": start, "end_value": end, "years": periods},
        cagr,
        unit="%",
    )


def calculate_current_ratio(current_assets: Any, current_liabilities: Any) -> dict[str, Any]:
    assets = _coerce_float(current_assets, "current_assets")
    liabilities = _coerce_float(current_liabilities, "current_liabilities")
    if liabilities == 0:
        raise ValueError("current_liabilities cannot be zero.")
    ratio = assets / liabilities
    return _result_payload(
        "current_ratio",
        "current_assets / current_liabilities",
        {"current_assets": assets, "current_liabilities": liabilities},
        ratio,
        unit="x",
    )


def calculate_quick_ratio(quick_assets: Any, current_liabilities: Any) -> dict[str, Any]:
    quick = _coerce_float(quick_assets, "quick_assets")
    liabilities = _coerce_float(current_liabilities, "current_liabilities")
    if liabilities == 0:
        raise ValueError("current_liabilities cannot be zero.")
    ratio = quick / liabilities
    return _result_payload(
        "quick_ratio",
        "quick_assets / current_liabilities",
        {"quick_assets": quick, "current_liabilities": liabilities},
        ratio,
        unit="x",
    )


def calculate_debt_to_equity(total_debt: Any, total_equity: Any) -> dict[str, Any]:
    debt = _coerce_float(total_debt, "total_debt")
    equity = _coerce_float(total_equity, "total_equity")
    if equity == 0:
        raise ValueError("total_equity cannot be zero.")
    ratio = debt / equity
    return _result_payload(
        "debt_to_equity",
        "total_debt / total_equity",
        {"total_debt": debt, "total_equity": equity},
        ratio,
        unit="x",
    )


def calculate_interest_coverage(ebit: Any, interest_expense: Any) -> dict[str, Any]:
    ebit = _coerce_float(ebit, "ebit")
    interest = _coerce_float(interest_expense, "interest_expense")
    if interest == 0:
        raise ValueError("interest_expense cannot be zero.")
    coverage = ebit / interest
    return _result_payload(
        "interest_coverage",
        "EBIT / interest_expense",
        {"ebit": ebit, "interest_expense": interest},
        coverage,
        unit="x",
    )


def calculate_free_cash_flow(operating_cash_flow: Any, capex: Any) -> dict[str, Any]:
    ocf = _coerce_float(operating_cash_flow, "operating_cash_flow")
    capex_value = _coerce_float(capex, "capex")
    free_cash_flow = ocf - capex_value
    return _result_payload(
        "free_cash_flow",
        "operating_cash_flow - capex",
        {"operating_cash_flow": ocf, "capex": capex_value},
        free_cash_flow,
        unit="currency",
    )


def calculate_eps(net_income: Any, shares_outstanding: Any) -> dict[str, Any]:
    income = _coerce_float(net_income, "net_income")
    shares = _coerce_float(shares_outstanding, "shares_outstanding")
    if shares == 0:
        raise ValueError("shares_outstanding cannot be zero.")
    eps = income / shares
    return _result_payload(
        "eps",
        "net_income / shares_outstanding",
        {"net_income": income, "shares_outstanding": shares},
        eps,
        unit="per share",
    )


def calculate_dividend_yield(dividend_per_share: Any, share_price: Any) -> dict[str, Any]:
    dividend = _coerce_float(dividend_per_share, "dividend_per_share")
    price = _coerce_float(share_price, "share_price")
    if price == 0:
        raise ValueError("share_price cannot be zero.")
    yield_pct = (dividend / price) * 100.0
    return _result_payload(
        "dividend_yield",
        "(dividend_per_share / share_price) * 100",
        {"dividend_per_share": dividend, "share_price": price},
        yield_pct,
        unit="%",
    )


def calculate_metric(metric: str, **kwargs: Any) -> dict[str, Any]:
    normalized = metric.strip().lower().replace(" ", "_")
    handlers = {
        "growth": calculate_growth,
        "revenue_growth": calculate_growth,
        "net_profit_growth": calculate_growth,
        "operating_profit_growth": calculate_growth,
        "margin": calculate_margin,
        "gross_profit_margin": calculate_margin,
        "operating_profit_margin": calculate_margin,
        "ebitda_margin": calculate_margin,
        "net_profit_margin": calculate_margin,
        "cagr": calculate_cagr,
        "current_ratio": calculate_current_ratio,
        "quick_ratio": calculate_quick_ratio,
        "debt_to_equity": calculate_debt_to_equity,
        "interest_coverage": calculate_interest_coverage,
        "free_cash_flow": calculate_free_cash_flow,
        "eps": calculate_eps,
        "dividend_yield": calculate_dividend_yield,
    }

    if normalized not in handlers:
        raise ValueError(f"Unsupported financial metric: {metric}")

    return handlers[normalized](**kwargs)
