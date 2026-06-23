"""
Quant Factor Engine

- 재무 + 가격 기반 팩터 점수화
- 퀀트 전략의 핵심 모듈
"""

class FactorEngine:
    """
    퀀트 팩터 계산기
    """

    # -----------------------------
    # VALUE (저평가)
    # -----------------------------
    def value_score(self, stock):
        score = 0

        # ROE
        if stock.roe >= 15:
            score += 40
        elif stock.roe >= 10:
            score += 25
        elif stock.roe >= 5:
            score += 10

        # 부채비율
        if stock.debt_ratio <= 50:
            score += 30
        elif stock.debt_ratio <= 100:
            score += 15

        return min(score, 100)

    # -----------------------------
    # QUALITY (수익성)
    # -----------------------------
    def quality_score(self, stock):
        score = 0

        if stock.net_income > 0:
            score += 40

        if stock.operating_profit > 0:
            score += 30

        if stock.roe >= 10:
            score += 30

        return min(score, 100)

    # -----------------------------
    # MOMENTUM (가격)
    # -----------------------------
    def momentum_score(self, stock):
        """
        실제 가격 기반 모멘텀
        """

        score = 0

        try:
            if hasattr(stock, "price_history") and stock.price_history is not None:

                prices = stock.price_history["Close"]

                if len(prices) < 2:
                    return 0

                start = prices.iloc[0]
                end = prices.iloc[-1]

                return_rate = ((end - start) / start) * 100

                if return_rate > 20:
                    score = 100
                elif return_rate > 10:
                    score = 70
                elif return_rate > 0:
                    score = 40
                else:
                    score = 10

        except Exception:
            return 0

        return score

    # -----------------------------
    # TOTAL SCORE
    # -----------------------------
    def total_score(self, stock):
        v = self.value_score(stock)
        q = self.quality_score(stock)
        m = self.momentum_score(stock)

        return round(
            (v * 0.4) +
            (q * 0.4) +
            (m * 0.2),
            2
        )

    # -----------------------------
    # SIGNAL
    # -----------------------------
    def signal(self, stock):
        score = self.total_score(stock)

        if score >= 75:
            return "STRONG BUY"
        elif score >= 55:
            return "BUY"
        elif score >= 40:
            return "HOLD"
        else:
            return "SELL"