from dataclasses import dataclass


@dataclass
class AIResult:

    company_name: str

    fair_price: float

    target_price: float

    buy_score: int

    confidence: int

    opinion: str

    investment_point: str

    risk_factor: str