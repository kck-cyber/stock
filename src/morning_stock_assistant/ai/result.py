from dataclasses import dataclass


@dataclass
class AIResult:

    company_name: str

    current_price: float

    fair_price: float

    target_price: float

    buy_score: float

    confidence: float

    opinion: str

    investment_point: str

    risk_factor: str