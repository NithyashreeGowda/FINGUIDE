READY = "READY"
NEEDS_INFORMATION = "NEEDS_INFORMATION"
CONFLICTING_CONTEXT = "CONFLICTING_CONTEXT"

REQUIRED_FIELDS = [
    "age", "income", "monthly_expenses", "investment_amount",
    "investment_horizon", "financial_goal", "risk_preference", "risk_capacity",
    "existing_investments", "liquidity_requirement", "liabilities",
]

# "100% complete" and "READY" now mean the same thing.
PROFILE_FIELDS = REQUIRED_FIELDS

LABELS = {
    "age": "age",
    "income": "monthly income",
    "monthly_expenses": "monthly expenses",
    "investment_amount": "investment amount",
    "investment_horizon": "investment horizon",
    "financial_goal": "financial goal",
    "risk_preference": "risk preference",
    "risk_capacity": "risk capacity",
    "existing_investments": "existing investments",
    "liquidity_requirement": "liquidity requirement",
    "liabilities": "liabilities",
}


def _blank(value) -> bool:
    return value is None or value == ""


def completeness(profile: dict) -> int:
    done = sum(1 for f in PROFILE_FIELDS if not _blank(profile.get(f)))
    return round(done / len(PROFILE_FIELDS) * 100)


def _join(items):
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def find_conflicts(p: dict) -> list:
    conflicts = []

    def add(code, fields, text):
        conflicts.append({"code": code, "fields": fields, "message": text})

    risk = p.get("risk_preference")
    capacity = p.get("risk_capacity")
    horizon = p.get("investment_horizon")
    target = p.get("target_return_percent")
    goal = p.get("financial_goal")

    if risk == "conservative" and target is not None and target >= 20:
        add("CONSERVATIVE_HIGH_RETURN", ["risk_preference", "target_return_percent"],
            f"A conservative risk preference rarely fits a {target:g}% target return.")

    if horizon is not None and horizon <= 1 and target is not None and target >= 20:
        add("SHORT_HORIZON_HIGH_RETURN", ["investment_horizon", "target_return_percent"],
            f"A {target:g}% return over {horizon:g} year(s) is unrealistic without very high risk.")

    if risk == "aggressive" and capacity == "low":
        add("PREFERENCE_EXCEEDS_CAPACITY", ["risk_preference", "risk_capacity"],
            "You prefer aggressive risk, but your capacity to absorb losses is low.")

    if goal == "capital_preservation" and risk == "aggressive":
        add("GOAL_VS_RISK", ["financial_goal", "risk_preference"],
            "Capital preservation as a goal doesn't match an aggressive risk preference.")

    income, expenses = p.get("income"), p.get("monthly_expenses")
    if income is not None and expenses is not None and expenses > income:
        add("EXPENSES_EXCEED_INCOME", ["income", "monthly_expenses"],
            "Your monthly expenses are higher than your monthly income.")

    return conflicts


def validate_context(profile) -> dict:
    profile = profile or {}

    missing = [f for f in REQUIRED_FIELDS if _blank(profile.get(f))]
    if missing:
        names = _join([LABELS[f] for f in missing])
        verb = "is" if len(missing) == 1 else "are"
        return {
            "status": NEEDS_INFORMATION,
            "missing_fields": missing,
            "conflicts": [],
            "message": f"Your {names} {verb} required before generating a personalized recommendation.",
        }

    conflicts = find_conflicts(profile)
    if conflicts:
        return {
            "status": CONFLICTING_CONTEXT,
            "missing_fields": [],
            "conflicts": conflicts,
            "message": "Some of your selected preferences may not align with your stated investment expectations.",
        }

    return {
        "status": READY,
        "missing_fields": [],
        "conflicts": [],
        "message": "Financial context complete.",
    }