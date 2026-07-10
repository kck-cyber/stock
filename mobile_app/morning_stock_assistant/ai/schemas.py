"""
AI Response Schema

Morning Stock Assistant Pro
"""

from dataclasses import dataclass, field


# --------------------------------------------------------
# AI 분석 결과
# --------------------------------------------------------

@dataclass
class AnalysisResult:

    score: int = 0

    opinion: str = ""

    confidence: int = 0

    fair_price: float = 0

    target_price: float = 0

    summary: str = ""

    investment_points: list[str] = field(default_factory=list)

    risk_factors: list[str] = field(default_factory=list)


# --------------------------------------------------------
# 뉴스
# --------------------------------------------------------

@dataclass
class NewsItem:

    title: str = ""

    press: str = ""

    date: str = ""

    sentiment: str = "중립"

    url: str = ""


# --------------------------------------------------------
# 회사 정보
# --------------------------------------------------------

@dataclass
class CompanyData:

    company_name: str = ""

    stock_code: str = ""

    market: str = ""

    current_price: float = 0

    market_cap: float = 0

    per: float = 0

    eps: float = 0

    book_value: float = 0

    sector: str = ""

    industry: str = ""

    currency: str = ""