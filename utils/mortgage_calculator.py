
from typing import Tuple

STANDARD_RATE = 0.045  # 4.5% annual
MAX_TENURE_YEARS = 25
UPFRONT_COST_RATE = 0.07  # 7%
MAX_LTV = 0.8  # 80% LTV

def calculate_emi(principal: float, annual_rate: float = STANDARD_RATE, tenure_years: int = MAX_TENURE_YEARS) -> float:
    """
    Deterministic EMI calculation.
    """
    if tenure_years <= 0:
        raise ValueError("tenure_years must be > 0")
    r = annual_rate / 12.0
    n = tenure_years * 12
    if r == 0:
        return round(principal / n, 2)
    emi = principal * r * (1 + r) ** n / ((1 + r) ** n - 1)
    return round(emi, 2)

def affordability(property_price: float) -> dict:
    """Return downpayment, loan amount (using MAX_LTV), upfront costs."""
    downpayment = round(property_price * (1 - MAX_LTV), 2)  # 20%
    loan = round(property_price * MAX_LTV, 2)
    upfront = round(property_price * UPFRONT_COST_RATE, 2)
    return {"property_price": property_price, "downpayment": downpayment, "loan": loan, "upfront_costs": upfront}

def buy_vs_rent(property_price: float, monthly_rent: float | None, years_stay: int) -> dict:
    """
    Heuristic Buy vs Rent. Returns computed facts and textual recommendation.
    """
    facts = affordability(property_price)
    loan = facts["loan"]
    emi = calculate_emi(loan)
    monthly_mortgage_interest_plus = emi  # we keep simple: EMI covers interest+principal (maintenance omitted)
    recommendation = ""
    reasoning = {}

    if years_stay < 3:
        recommendation = "Rent"
        reasoning["why"] = "Short stay (<3 years): transaction + upfront costs make buying expensive."
    elif years_stay > 5:
        recommendation = "Buy"
        reasoning["why"] = "Long stay (>5 years): equity buildup usually outweighs rent."
    else:
        # for 3-5 years: compare EMI vs rent
        if monthly_rent is None:
            recommendation = "Neutral"
            reasoning["why"] = "You didn't provide current rent — cannot fully compare."
        else:
            if monthly_mortgage_interest_plus < monthly_rent * 1.0:
                recommendation = "Buy"
                reasoning["why"] = "Monthly mortgage is comparable/less than your rent over the horizon."
            else:
                recommendation = "Rent"
                reasoning["why"] = "Monthly mortgage is higher than rent; renting may be cheaper short-term."

    reasoning.update({
        "emi_monthly": emi,
        "loan_amount": loan,
        "downpayment": facts["downpayment"],
        "upfront_costs": facts["upfront_costs"]
    })

    return {"recommendation": recommendation, "reasoning": reasoning}
