"""
Quant Factor Engine

- 재무 + 가격 기반 팩터 점수화
- 퀀트 전략의 핵심 모듈
"""

class FactorEngine:
    DEFAULT_PRESET = "균형형"
    FACTOR_MAX = {
        "Value": 100,
        "Quality": 130,
        "Growth": 60,
        "Stability": 20,
        "Dividend": 10,
        "Momentum": 50,
    }
    PRESET_ALIASES = {
        "Balanced": "균형형",
        "Growth": "성장형",
        "Value": "가치형",
        "Dividend": "배당형",
        "Momentum": "모멘텀형",
        "Stability": "안정형",
    }
    PRESETS = {
        "균형형": {
            "Value": 0.25,
            "Quality": 0.20,
            "Growth": 0.20,
            "Stability": 0.10,
            "Dividend": 0.05,
            "Momentum": 0.15,
            "News": 0.05,
        },
        "성장형": {
            "Value": 0.15,
            "Quality": 0.20,
            "Growth": 0.30,
            "Stability": 0.10,
            "Dividend": 0.03,
            "Momentum": 0.17,
            "News": 0.05,
        },
        "가치형": {
            "Value": 0.35,
            "Quality": 0.20,
            "Growth": 0.12,
            "Stability": 0.15,
            "Dividend": 0.08,
            "Momentum": 0.07,
            "News": 0.03,
        },
        "배당형": {
            "Value": 0.20,
            "Quality": 0.18,
            "Growth": 0.10,
            "Stability": 0.20,
            "Dividend": 0.22,
            "Momentum": 0.07,
            "News": 0.03,
        },
        "모멘텀형": {
            "Value": 0.12,
            "Quality": 0.15,
            "Growth": 0.18,
            "Stability": 0.08,
            "Dividend": 0.02,
            "Momentum": 0.40,
            "News": 0.05,
        },
        "안정형": {
            "Value": 0.20,
            "Quality": 0.25,
            "Growth": 0.10,
            "Stability": 0.25,
            "Dividend": 0.10,
            "Momentum": 0.07,
            "News": 0.03,
        },
    }

    def __init__(self, preset_name=None):

        self.preset_name = self.normalize_preset(
            preset_name or self.DEFAULT_PRESET
        )

    def preset_names(self):

        return list(self.PRESETS.keys())

    def normalize_preset(self, preset_name):

        if preset_name in self.PRESET_ALIASES:
            return self.PRESET_ALIASES[preset_name]

        if preset_name in self.PRESETS:
            return preset_name

        return self.DEFAULT_PRESET

    def set_preset(self, preset_name):

        self.preset_name = self.normalize_preset(preset_name)

    def get_weights(self, preset_name=None):

        preset_name = self.normalize_preset(
            preset_name or self.preset_name
        )
        return self.PRESETS.get(
            preset_name,
            self.PRESETS[self.DEFAULT_PRESET]
        )

    """
    퀀트 팩터 계산기
    """

    # -----------------------------
    # VALUE (저평가)
    # -----------------------------
    def value_score(self, stock):
        score = 0

        per = getattr(stock, "per", 0)
        pbr = getattr(stock, "pbr", 0)
        pcr = getattr(stock, "pcr", 0)
        psr = getattr(stock, "psr", 0)
        relative_per = getattr(stock, "relative_per", 0)
        relative_pbr = getattr(stock, "relative_pbr", 0)
        fcf_yield = getattr(stock, "fcf_yield", 0)
        fcf_yield = getattr(stock, "fcf_yield", 0)
        roe = getattr(stock, "roe", 0)
        debt_ratio = getattr(stock, "debt_ratio", 999)

        if 0 < per <= 10:
            score += 18
        elif 0 < per <= 15:
            score += 14
        elif 0 < per <= 25:
            score += 8

        if 0 < pbr <= 1:
            score += 18
        elif 0 < pbr <= 2:
            score += 12
        elif 0 < pbr <= 4:
            score += 6

        if 0 < pcr <= 8:
            score += 14
        elif 0 < pcr <= 15:
            score += 10
        elif 0 < pcr <= 25:
            score += 5

        if 0 < psr <= 2:
            score += 12
        elif 0 < psr <= 5:
            score += 8
        elif 0 < psr <= 10:
            score += 4

        if 0 < relative_per <= 0.8:
            score += 10
        elif 0 < relative_per <= 1.0:
            score += 5

        if 0 < relative_pbr <= 0.8:
            score += 8
        elif 0 < relative_pbr <= 1.0:
            score += 4

        if fcf_yield >= 8:
            score += 10
        elif fcf_yield >= 4:
            score += 7
        elif fcf_yield >= 2:
            score += 4

        if roe >= 15:
            score += 12
        elif roe >= 10:
            score += 8
        elif roe >= 5:
            score += 4

        if debt_ratio <= 50:
            score += 8
        elif debt_ratio <= 100:
            score += 4

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

        if getattr(stock, "roic", 0) >= 15:
            score += 15
        elif getattr(stock, "roic", 0) >= 8:
            score += 10
        elif getattr(stock, "roic", 0) >= 4:
            score += 5

        if getattr(stock, "free_cash_flow", 0) > 0:
            score += 10

        if getattr(stock, "operating_cash_flow", 0) > 0:
            score += 5

        return min(score, 130)

    # -----------------------------
    # MOMENTUM (가격)
    # -----------------------------
    def momentum_score(self, stock):

        score = 0

        price = getattr(stock, "price", 0)

        ma20 = getattr(stock, "ma20", 0)
        ma60 = getattr(stock, "ma60", 0)
        ma120 = getattr(stock, "ma120", 0)

        high52 = getattr(stock, "high52", 0)
        low52 = getattr(stock, "low52", 0)

        volume_ratio = getattr(stock, "volume_ratio", 0)

        # -----------------------------
        # 이동평균선
        # -----------------------------

        if price > ma20 > 0:
            score += 10

        if price > ma60 > 0:
            score += 10

        if price > ma120 > 0:
            score += 10

        # -----------------------------
        # 52주 위치
        # -----------------------------

        if high52 > low52:

            position = (
                (price - low52)
                /
                (high52 - low52)
            )

            if position >= 0.8:
                score += 10

            elif position >= 0.6:
                score += 5

        # -----------------------------
        # 거래량
        # -----------------------------

        if volume_ratio >= 2:
            score += 10

        elif volume_ratio >= 1.3:
            score += 5

        return score
    
    def news_score(self, stock):

        score = stock.news_score

        if score >= 5:
            return 10

        if score >= 2:
            return 5

        if score <= -5:
            return -10

        if score <= -2:
            return -5

        return 0

    # -----------------------------
    # TOTAL SCORE
    # -----------------------------
    def total_score(self, stock, preset_name=None):

        value = self.normalize_factor_score("Value", self.value_score(stock))
        quality = self.normalize_factor_score("Quality", self.quality_score(stock))
        growth = self.normalize_factor_score("Growth", self.growth_score(stock))
        stability = self.normalize_factor_score("Stability", self.stability_score(stock))
        dividend = self.normalize_factor_score("Dividend", self.dividend_score(stock))
        momentum = self.normalize_factor_score("Momentum", self.momentum_score(stock))
        news = self.normalize_news_score(self.news_score(stock))

        weights = self.get_weights(preset_name)

        score = (
            value * weights["Value"] +
            quality * weights["Quality"] +
            growth * weights["Growth"] +
            stability * weights["Stability"] +
            dividend * weights["Dividend"] +
            momentum * weights["Momentum"] +
            news * weights["News"]
        )

        return round(score, 2)

    def score_breakdown(self, stock, preset_name=None):

        weights = self.get_weights(preset_name)

        items = [
            ("Value", self.value_score(stock), self.value_reasons(stock)),
            ("Quality", self.quality_score(stock), self.quality_reasons(stock)),
            ("Growth", self.growth_score(stock), self.growth_reasons(stock)),
            ("Stability", self.stability_score(stock), self.stability_reasons(stock)),
            ("Dividend", self.dividend_score(stock), self.dividend_reasons(stock)),
            ("Momentum", self.momentum_score(stock), self.momentum_reasons(stock)),
            ("News", self.news_score(stock), self.news_reasons(stock)),
        ]

        breakdown = []

        for name, raw_score, reasons in items:
            normalized_score = (
                self.normalize_news_score(raw_score)
                if name == "News"
                else self.normalize_factor_score(name, raw_score)
            )
            weight = weights[name]
            contribution = round(normalized_score * weight, 2)
            breakdown.append({
                "name": name,
                "raw_score": normalized_score,
                "original_score": raw_score,
                "weight": weight,
                "contribution": contribution,
                "reasons": reasons,
            })

        return breakdown

    def normalize_factor_score(self, name, score):

        max_score = self.FACTOR_MAX.get(name, 100)

        if max_score <= 0:
            return 0

        score = max(min(score, max_score), 0)
        return round((score / max_score) * 100, 2)

    @staticmethod
    def normalize_news_score(score):

        score = max(min(score, 10), -10)
        return round(((score + 10) / 20) * 100, 2)

    def value_reasons(self, stock):

        reasons = []

        per = getattr(stock, "per", 0)
        pbr = getattr(stock, "pbr", 0)
        pcr = getattr(stock, "pcr", 0)
        psr = getattr(stock, "psr", 0)
        relative_per = getattr(stock, "relative_per", 0)
        relative_pbr = getattr(stock, "relative_pbr", 0)
        fcf_yield = getattr(stock, "fcf_yield", 0)

        if 0 < per <= 10:
            reasons.append(f"PER {per:.2f} <= 10: +18")
        elif 0 < per <= 15:
            reasons.append(f"PER {per:.2f} <= 15: +14")
        elif 0 < per <= 25:
            reasons.append(f"PER {per:.2f} <= 25: +8")
        else:
            reasons.append(f"PER {per:.2f}: +0")

        if 0 < pbr <= 1:
            reasons.append(f"PBR {pbr:.2f} <= 1: +18")
        elif 0 < pbr <= 2:
            reasons.append(f"PBR {pbr:.2f} <= 2: +12")
        elif 0 < pbr <= 4:
            reasons.append(f"PBR {pbr:.2f} <= 4: +6")
        else:
            reasons.append(f"PBR {pbr:.2f}: +0")

        if 0 < pcr <= 8:
            reasons.append(f"PCR {pcr:.2f} <= 8: +14")
        elif 0 < pcr <= 15:
            reasons.append(f"PCR {pcr:.2f} <= 15: +10")
        elif 0 < pcr <= 25:
            reasons.append(f"PCR {pcr:.2f} <= 25: +5")
        else:
            reasons.append(f"PCR {pcr:.2f}: +0")

        if 0 < psr <= 2:
            reasons.append(f"PSR {psr:.2f} <= 2: +12")
        elif 0 < psr <= 5:
            reasons.append(f"PSR {psr:.2f} <= 5: +8")
        elif 0 < psr <= 10:
            reasons.append(f"PSR {psr:.2f} <= 10: +4")
        else:
            reasons.append(f"PSR {psr:.2f}: +0")

        if 0 < relative_per <= 0.8:
            reasons.append(f"업종대비 PER {relative_per:.2f} <= 0.8: +10")
        elif 0 < relative_per <= 1.0:
            reasons.append(f"업종대비 PER {relative_per:.2f} <= 1.0: +5")
        else:
            reasons.append(f"업종대비 PER {relative_per:.2f}: +0")

        if 0 < relative_pbr <= 0.8:
            reasons.append(f"업종대비 PBR {relative_pbr:.2f} <= 0.8: +8")
        elif 0 < relative_pbr <= 1.0:
            reasons.append(f"업종대비 PBR {relative_pbr:.2f} <= 1.0: +4")
        else:
            reasons.append(f"업종대비 PBR {relative_pbr:.2f}: +0")

        if fcf_yield >= 8:
            reasons.append(f"FCF Yield {fcf_yield:.2f}% >= 8%: +10")
        elif fcf_yield >= 4:
            reasons.append(f"FCF Yield {fcf_yield:.2f}% >= 4%: +7")
        elif fcf_yield >= 2:
            reasons.append(f"FCF Yield {fcf_yield:.2f}% >= 2%: +4")
        else:
            reasons.append(f"FCF Yield {fcf_yield:.2f}% < 2%: +0")

        if stock.roe >= 15:
            reasons.append(f"ROE {stock.roe:.2f}% >= 15%: +12")
        elif stock.roe >= 10:
            reasons.append(f"ROE {stock.roe:.2f}% >= 10%: +8")
        elif stock.roe >= 5:
            reasons.append(f"ROE {stock.roe:.2f}% >= 5%: +4")
        else:
            reasons.append(f"ROE {stock.roe:.2f}% < 5%: +0")

        if stock.debt_ratio <= 50:
            reasons.append(f"부채비율 {stock.debt_ratio:.2f}% <= 50%: +8")
        elif stock.debt_ratio <= 100:
            reasons.append(f"부채비율 {stock.debt_ratio:.2f}% <= 100%: +4")
        else:
            reasons.append(f"부채비율 {stock.debt_ratio:.2f}% > 100%: +0")

        return reasons

    def quality_reasons(self, stock):

        reasons = []
        reasons.append(
            f"순이익 {'흑자' if stock.net_income > 0 else '비흑자'}: "
            f"+{40 if stock.net_income > 0 else 0}"
        )
        reasons.append(
            f"영업이익 {'흑자' if stock.operating_profit > 0 else '비흑자'}: "
            f"+{30 if stock.operating_profit > 0 else 0}"
        )
        reasons.append(
            f"ROE {stock.roe:.2f}% {'>= 10%' if stock.roe >= 10 else '< 10%'}: "
            f"+{30 if stock.roe >= 10 else 0}"
        )
        roic = getattr(stock, "roic", 0)
        if roic >= 15:
            reasons.append(f"ROIC {roic:.2f}% >= 15%: +15")
        elif roic >= 8:
            reasons.append(f"ROIC {roic:.2f}% >= 8%: +10")
        elif roic >= 4:
            reasons.append(f"ROIC {roic:.2f}% >= 4%: +5")
        else:
            reasons.append(f"ROIC {roic:.2f}% < 4%: +0")
        reasons.append(
            f"잉여현금흐름 {'양수' if getattr(stock, 'free_cash_flow', 0) > 0 else '비양수'}: "
            f"+{10 if getattr(stock, 'free_cash_flow', 0) > 0 else 0}"
        )
        reasons.append(
            f"영업현금흐름 {'양수' if getattr(stock, 'operating_cash_flow', 0) > 0 else '비양수'}: "
            f"+{5 if getattr(stock, 'operating_cash_flow', 0) > 0 else 0}"
        )

        return reasons

    def growth_reasons(self, stock):

        return [
            self._growth_reason("매출성장률", stock.sales_growth),
            self._growth_reason("영업이익성장률", stock.op_growth),
            self._growth_reason("EPS성장률", stock.eps_growth),
            self._growth_reason("3년 매출 CAGR", getattr(stock, "sales_cagr_3y", 0)),
            self._growth_reason("3년 영업이익 CAGR", getattr(stock, "op_cagr_3y", 0)),
            self._growth_reason("3년 순이익 CAGR", getattr(stock, "net_income_cagr_3y", 0)),
        ]

    @staticmethod
    def _growth_reason(label, value):

        if value >= 15:
            return f"{label} {value:.2f}% >= 15%: +10"

        if value >= 5:
            return f"{label} {value:.2f}% >= 5%: +5"

        return f"{label} {value:.2f}% < 5%: +0"

    def stability_reasons(self, stock):

        reasons = []

        if stock.debt_ratio <= 50:
            reasons.append(f"부채비율 {stock.debt_ratio:.2f}% <= 50%: +10")
        elif stock.debt_ratio <= 100:
            reasons.append(f"부채비율 {stock.debt_ratio:.2f}% <= 100%: +5")
        else:
            reasons.append(f"부채비율 {stock.debt_ratio:.2f}% > 100%: +0")

        if stock.current_ratio >= 150:
            reasons.append(f"유동/당좌비율 {stock.current_ratio:.2f}% >= 150%: +10")
        elif stock.current_ratio >= 100:
            reasons.append(f"유동/당좌비율 {stock.current_ratio:.2f}% >= 100%: +5")
        else:
            reasons.append(f"유동/당좌비율 {stock.current_ratio:.2f}% < 100%: +0")

        return reasons

    def dividend_reasons(self, stock):

        if stock.dividend_yield >= 5:
            return [f"배당수익률 {stock.dividend_yield:.2f}% >= 5%: +10"]

        if stock.dividend_yield >= 2:
            return [f"배당수익률 {stock.dividend_yield:.2f}% >= 2%: +5"]

        return [f"배당수익률 {stock.dividend_yield:.2f}% < 2%: +0"]

    def momentum_reasons(self, stock):

        reasons = []

        price = getattr(stock, "price", 0)
        ma20 = getattr(stock, "ma20", 0)
        ma60 = getattr(stock, "ma60", 0)
        ma120 = getattr(stock, "ma120", 0)
        high52 = getattr(stock, "high52", 0)
        low52 = getattr(stock, "low52", 0)
        volume_ratio = getattr(stock, "volume_ratio", 0)

        reasons.append(f"현재가 > MA20: +{10 if price > ma20 > 0 else 0}")
        reasons.append(f"현재가 > MA60: +{10 if price > ma60 > 0 else 0}")
        reasons.append(f"현재가 > MA120: +{10 if price > ma120 > 0 else 0}")

        if high52 > low52:
            position = (price - low52) / (high52 - low52)

            if position >= 0.8:
                reasons.append(f"52주 위치 {position * 100:.1f}% >= 80%: +10")
            elif position >= 0.6:
                reasons.append(f"52주 위치 {position * 100:.1f}% >= 60%: +5")
            else:
                reasons.append(f"52주 위치 {position * 100:.1f}% < 60%: +0")
        else:
            reasons.append("52주 고저 데이터 부족: +0")

        if volume_ratio >= 2:
            reasons.append(f"거래량 비율 {volume_ratio:.2f}x >= 2.0x: +10")
        elif volume_ratio >= 1.3:
            reasons.append(f"거래량 비율 {volume_ratio:.2f}x >= 1.3x: +5")
        else:
            reasons.append(f"거래량 비율 {volume_ratio:.2f}x < 1.3x: +0")

        return reasons

    def news_reasons(self, stock):

        raw = getattr(stock, "news_score", 0)
        score = self.news_score(stock)

        if raw >= 5:
            mood = "긍정 뉴스 흐름"
        elif raw >= 2:
            mood = "약한 긍정 뉴스 흐름"
        elif raw <= -5:
            mood = "부정 뉴스 흐름"
        elif raw <= -2:
            mood = "약한 부정 뉴스 흐름"
        else:
            mood = "중립 뉴스 흐름"

        return [f"{mood}: 감성 원점수 {raw}, 팩터 점수 {score}"]

    # -----------------------------
    # SIGNAL
    # -----------------------------
    def signal(self, stock, preset_name=None):

        score = self.total_score(stock, preset_name)

        if score >= 85:
            return "★★★★★ 적극 매수"

        if score >= 75:
            return "★★★★ 매수"

        if score >= 60:
            return "★★★ 보유"

        if score >= 45:
            return "★★ 비중 축소"

        return "★ 매도"
        
    
    # ------------------------------------------
    # 성장성
    # ------------------------------------------

    def growth_score(self, stock):

        score = 0

        try:

            if getattr(stock, "sales_growth", 0) >= 10:
                score += 10

            elif getattr(stock, "sales_growth", 0) >= 5:
                score += 5

            if getattr(stock, "op_growth", 0) >= 10:
                score += 10

            elif getattr(stock, "op_growth", 0) >= 5:
                score += 5

            if getattr(stock, "eps_growth", 0) >= 10:
                score += 10

            elif getattr(stock, "eps_growth", 0) >= 5:
                score += 5

            if getattr(stock, "sales_cagr_3y", 0) >= 10:
                score += 10

            elif getattr(stock, "sales_cagr_3y", 0) >= 5:
                score += 5

            if getattr(stock, "op_cagr_3y", 0) >= 10:
                score += 10

            elif getattr(stock, "op_cagr_3y", 0) >= 5:
                score += 5

            if getattr(stock, "net_income_cagr_3y", 0) >= 10:
                score += 10

            elif getattr(stock, "net_income_cagr_3y", 0) >= 5:
                score += 5

        except Exception:
            pass

        return score

    # ------------------------------------------
    # 배당
    # ------------------------------------------

    def dividend_score(self, stock):

        score = 0

        dividend = getattr(stock, "dividend_yield", 0)

        if dividend >= 5:
            score = 10

        elif dividend >= 3:
            score = 7

        elif dividend >= 1:
            score = 5

        return score

    # ------------------------------------------
    # 재무안정성
    # ------------------------------------------

    def stability_score(self, stock):

        score = 0

        debt = getattr(stock, "debt_ratio", 999)

        current = getattr(stock, "current_ratio", 0)

        if debt < 100:
            score += 10

        elif debt < 150:
            score += 5

        if current > 150:
            score += 10

        elif current > 100:
            score += 5

        return score
    
    def growth_score(self, stock):

        score = 0

        for name in (
            "sales_growth",
            "op_growth",
            "eps_growth",
            "sales_cagr_3y",
            "op_cagr_3y",
            "net_income_cagr_3y",
        ):
            value = getattr(stock, name, 0)

            if value >= 15:
                score += 10
            elif value >= 5:
                score += 5

        return score
    
    def stability_score(self, stock):

        score = 0

        if stock.debt_ratio <= 50:
            score += 10
        elif stock.debt_ratio <= 100:
            score += 5

        if stock.current_ratio >= 150:
            score += 10
        elif stock.current_ratio >= 100:
            score += 5

        return score
    
    def dividend_score(self, stock):

        score = 0

        if stock.dividend_yield >= 5:
            score += 10
        elif stock.dividend_yield >= 2:
            score += 5

        return score
    
