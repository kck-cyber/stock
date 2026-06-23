"""
Quant Analyzer (v2)

- FactorEngine 기반 투자 판단
- 기존 Rule-based AI → Quant AI로 전환
"""

from dataclasses import dataclass
from morning_stock_assistant.ai.factor_engine import FactorEngine


@dataclass
class AnalysisResult:
    code: str
    name: str
    score: float
    signal: str

    value: float
    quality: float
    momentum: float

    # GUI 출력용
    roe: float
    debt_ratio: float
    net_income: int

    comment: str


class StockAnalyzer:
    """
    Quant 기반 분석 엔진
    """

    def __init__(self, stock_service):
        self.service = stock_service
        self.factor = FactorEngine()

    # --------------------------------------------------
    # 메인 분석
    # --------------------------------------------------
    def analyze(self, stock_code: str, year: str, report_code: str):

        stock = self.service.get_stock(stock_code, year, report_code)
        if not stock:
            return None

        # -----------------------------
        # 팩터 계산
        # -----------------------------
        value = self.factor.value_score(stock)
        quality = self.factor.quality_score(stock)
        momentum = self.factor.momentum_score(stock)

        total = self.factor.total_score(stock)
        signal = self.factor.signal(stock)

        comment = self._make_comment(stock, value, quality, momentum, signal)

        return AnalysisResult(
            code=stock.code,
            name=stock.name,
            score=total,
            signal=signal,

            value=value,
            quality=quality,
            momentum=momentum,

            roe=stock.roe,
            debt_ratio=stock.debt_ratio,
            net_income=stock.net_income,

            comment=comment
        )

    # --------------------------------------------------
    # 설명 생성
    # --------------------------------------------------
    def _make_comment(self, stock, v, q, m, signal):

        comments = []

        comments.append(f"Value Score: {v}")
        comments.append(f"Quality Score: {q}")
        comments.append(f"Momentum Score: {m}")

        comments.append(f"ROE: {stock.roe:.2f}%")
        comments.append(f"부채비율: {stock.debt_ratio:.2f}%")

        if signal in ["STRONG BUY", "BUY"]:
            comments.append("퀀트 기준에서 매수 구간")
        elif signal == "HOLD":
            comments.append("중립 구간")
        else:
            comments.append("보수적 접근 필요")

        return " | ".join(comments)
    
AIAnalyzer = StockAnalyzer