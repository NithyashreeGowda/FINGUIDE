import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from context_validator import validate_context, completeness, NEEDS_INFORMATION, CONFLICTING_CONTEXT, READY

def full(**over):
    p = dict(age=30, income=50000, monthly_expenses=20000, investment_amount=100000,
             investment_horizon=5, financial_goal="wealth_creation", risk_preference="moderate",
             risk_capacity="medium", existing_investments=0, liquidity_requirement="low",
             liabilities=0, target_return_percent=12)
    p.update(over)
    return p

def test_ready():
    assert validate_context(full())["status"] == READY

def test_missing_horizon():
    r = validate_context(full(investment_horizon=None))
    assert r["status"] == NEEDS_INFORMATION and r["missing_fields"] == ["investment_horizon"]

def test_empty_profile():
    assert validate_context(None)["status"] == NEEDS_INFORMATION

def test_zero_is_not_missing():
    assert validate_context(full(liabilities=0, existing_investments=0))["status"] == READY

def test_conservative_30_percent_1_year():
    r = validate_context(full(risk_preference="conservative", target_return_percent=30, investment_horizon=1))
    codes = {c["code"] for c in r["conflicts"]}
    assert r["status"] == CONFLICTING_CONTEXT
    assert {"CONSERVATIVE_HIGH_RETURN", "SHORT_HORIZON_HIGH_RETURN"} <= codes

def test_aggressive_low_capacity():
    r = validate_context(full(risk_preference="aggressive", risk_capacity="low"))
    assert r["conflicts"][0]["code"] == "PREFERENCE_EXCEEDS_CAPACITY"

def test_capital_preservation_vs_aggressive():
    r = validate_context(full(financial_goal="capital_preservation", risk_preference="aggressive"))
    assert any(c["code"] == "GOAL_VS_RISK" for c in r["conflicts"])

def test_expenses_exceed_income():
    r = validate_context(full(income=20000, monthly_expenses=30000))
    assert any(c["code"] == "EXPENSES_EXCEED_INCOME" for c in r["conflicts"])

def test_completeness():
    assert completeness(full()) == 100
    assert completeness(full(age=None)) < 100