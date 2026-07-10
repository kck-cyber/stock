"""
Quant Analyzer (v2)

- FactorEngine 기반 투자 판단
- 기존 Rule-based AI → Quant AI로 전환
"""

from dataclasses import dataclass, field
from morning_stock_assistant.ai.factor_engine import FactorEngine


@dataclass
class AnalysisResult:
    code: str
    name: str
    score: float
    signal: str

    value: float
    quality: float

    growth: float
    stability: float
    dividend: float

    momentum: float

    # GUI 출력용
    roe: float
    debt_ratio: float
    net_income: int

    price: float
    change_rate: float
    per: float
    pbr: float
    psr: float = 0
    pcr: float = 0
    market_cap: float = 0

    comment: str = ""
    asset_type: str = "STOCK"
    is_etf: bool = False

    news: float = 0
    currency: str = "KRW"
    price_date: str = ""

    sales: int = 0
    operating_profit: int = 0
    assets: int = 0
    liabilities: int = 0
    equity: int = 0

    eps: float = 0
    bps: float = 0
    relative_per: float = 0
    relative_pbr: float = 0

    sales_growth: float = 0
    op_growth: float = 0
    eps_growth: float = 0
    bps_growth: float = 0

    roa: float = 0
    operating_margin: float = 0
    net_margin: float = 0
    dividend_yield: float = 0
    current_ratio: float = 0
    free_cash_flow: int = 0
    operating_cash_flow: int = 0
    capex: int = 0
    cash: int = 0
    total_debt: int = 0
    roic: float = 0
    fcf_yield: float = 0
    sales_cagr_3y: float = 0
    op_cagr_3y: float = 0
    net_income_cagr_3y: float = 0

    ma20: float = 0
    ma60: float = 0
    ma120: float = 0
    high52: float = 0
    low52: float = 0
    volume_ratio: float = 0
    short_ratio: float = 0
    short_volume: float = 0
    short_value: float = 0
    foreign_net_buy: float = 0
    institution_net_buy: float = 0
    individual_net_buy: float = 0
    institutional_ownership: float = 0
    analyst_target_mean: float = 0
    analyst_target_high: float = 0
    analyst_target_low: float = 0
    analyst_count: float = 0
    analyst_recommendation: str = ""
    score_breakdown: list = field(default_factory=list)
    preset: str = "균형형"


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
    def analyze(
        self,
        stock_code: str,
        year: str,
        report_code: str,
        preset_name: str = None
    ):

        self.factor.set_preset(preset_name or self.factor.preset_name)
        preset_name = self.factor.preset_name

        cache_key = (
            stock_code,
            year,
            report_code,
            preset_name
        )

        if cache_key in self.service.analysis_cache:
            return self.service.analysis_cache[cache_key]

        stock = self.service.get_stock(
            stock_code,
            year,
            report_code
        )

        if not stock:
            print(f"[ERROR] stock not found: {stock_code}")
            return None

        value = self.factor.value_score(stock)
        quality = self.factor.quality_score(stock)

        growth = self.factor.growth_score(stock)
        stability = self.factor.stability_score(stock)
        dividend = self.factor.dividend_score(stock)

        momentum = self.factor.momentum_score(stock)

        total = self.factor.total_score(stock, preset_name)
        signal = self.factor.signal(stock, preset_name)
        score_breakdown = self.factor.score_breakdown(stock, preset_name)

        comment = self._make_comment(
            stock,
            value,
            quality,
            growth,
            stability,
            dividend,
            momentum,
            signal
        )

        result = AnalysisResult(
            code=stock.code,
            name=stock.name,
            asset_type=stock.asset_type,
            is_etf=stock.is_etf,
            growth=growth,
            stability=stability,
            dividend=dividend,

            news=stock.news_score,
            score=total,
            signal=signal,

            value=value,
            quality=quality,
            momentum=momentum,

            roe=stock.roe,
            debt_ratio=stock.debt_ratio,
            net_income=stock.net_income,

            price=stock.price,
            change_rate=stock.change_rate,
            currency=stock.currency,
            price_date=stock.price_date,
            per=stock.per,
            pbr=stock.pbr,
            psr=stock.psr,
            pcr=stock.pcr,
            market_cap=stock.market_cap,

            sales=stock.sales,
            operating_profit=stock.operating_profit,
            assets=stock.assets,
            liabilities=stock.liabilities,
            equity=stock.equity,

            eps=stock.eps,
            bps=stock.bps,
            relative_per=stock.relative_per,
            relative_pbr=stock.relative_pbr,

            sales_growth=stock.sales_growth,
            op_growth=stock.op_growth,
            eps_growth=stock.eps_growth,
            bps_growth=stock.bps_growth,

            roa=stock.roa,
            operating_margin=stock.operating_margin,
            net_margin=stock.net_margin,
            dividend_yield=stock.dividend_yield,
            current_ratio=stock.current_ratio,
            free_cash_flow=stock.free_cash_flow,
            operating_cash_flow=stock.operating_cash_flow,
            capex=stock.capex,
            cash=stock.cash,
            total_debt=stock.total_debt,
            roic=stock.roic,
            fcf_yield=stock.fcf_yield,
            sales_cagr_3y=stock.sales_cagr_3y,
            op_cagr_3y=stock.op_cagr_3y,
            net_income_cagr_3y=stock.net_income_cagr_3y,

            ma20=stock.ma20,
            ma60=stock.ma60,
            ma120=stock.ma120,
            high52=stock.high52,
            low52=stock.low52,
            volume_ratio=stock.volume_ratio,
            short_ratio=stock.short_ratio,
            short_volume=stock.short_volume,
            short_value=stock.short_value,
            foreign_net_buy=stock.foreign_net_buy,
            institution_net_buy=stock.institution_net_buy,
            individual_net_buy=stock.individual_net_buy,
            institutional_ownership=stock.institutional_ownership,
            analyst_target_mean=stock.analyst_target_mean,
            analyst_target_high=stock.analyst_target_high,
            analyst_target_low=stock.analyst_target_low,
            analyst_count=stock.analyst_count,
            analyst_recommendation=stock.analyst_recommendation,
            score_breakdown=score_breakdown,
            preset=preset_name,

            comment=comment
        )

        self.service.analysis_cache[cache_key] = result

        return result

    # --------------------------------------------------
    # 설명 생성
    # --------------------------------------------------
    def _make_comment(
        self,
        stock,
        value,
        quality,
        growth,
        stability,
        dividend,
        momentum,
        signal
    ):

        comments = []

        if growth >= 20:
            comments.append("성장성이 매우 우수합니다.")
        elif growth >= 10:
            comments.append("성장성이 양호합니다.")

        if stability >= 15:
            comments.append("재무 안정성이 우수합니다.")

        if dividend >= 5:
            comments.append("배당 매력이 있습니다.")

        if stock.news_score >= 3:
            comments.append("최근 뉴스 흐름이 긍정적입니다.")
        elif stock.news_score <= -3:
            comments.append("최근 뉴스 흐름이 부정적입니다.")

        # -------------------------
        # 종합
        # -------------------------

        comments.append(f"투자판단 : {signal}")

        weak_factors = []

        if value < 15:
            weak_factors.append("가치")

        if quality < 40:
            weak_factors.append("수익성")

        if growth < 10:
            weak_factors.append("성장성")

        if stability < 10:
            weak_factors.append("안정성")

        if momentum < 20:
            weak_factors.append("모멘텀")

        if (
            stock.news_score >= 3
            and signal in ("★ 매도", "★★ 비중 축소")
            and weak_factors
        ):
            comments.append(
                "뉴스 흐름은 긍정적이지만 "
                f"{', '.join(weak_factors[:3])} 점수가 부족해 "
                f"종합판정은 {signal}입니다."
            )

        elif (
            stock.news_score <= -3
            and signal in ("★★★ 보유", "★★★★ 매수", "★★★★★ 적극 매수")
        ):
            comments.append(
                "종합점수는 양호하지만 최근 뉴스 흐름은 부정적이므로 "
                "추가 확인이 필요합니다."
            )

        # -------------------------
        # Value
        # -------------------------

        if value >= 25:
            comments.append("저평가 구간")

        elif value >= 15:
            comments.append("적정 가치")

        else:
            comments.append("고평가 가능성")

        # -------------------------
        # Quality
        # -------------------------

        if stock.roe >= 15:
            comments.append("ROE 우수")

        elif stock.roe >= 10:
            comments.append("ROE 양호")

        else:
            comments.append("ROE 낮음")

        if stock.debt_ratio <= 100:
            comments.append("재무 안정")

        else:
            comments.append("부채비율 높음")

        # -------------------------
        # Growth
        # -------------------------

        if stock.sales_growth >= 10:
            comments.append("매출 성장")

        if stock.op_growth >= 10:
            comments.append("영업이익 성장")

        # -------------------------
        # Momentum
        # -------------------------

        if stock.price > stock.ma20 > 0:
            comments.append("20일선 상회")

        if stock.price > stock.ma60 > 0:
            comments.append("60일선 상회")

        if stock.volume_ratio >= 2:
            comments.append("거래량 급증")

        # -------------------------
        # 배당
        # -------------------------

        if stock.dividend_yield >= 3:
            comments.append("배당 매력")

        if stock.relative_per < 0.8:
            comments.append("업종 대비 PER 저평가")

        if stock.relative_pbr < 0.8:
            comments.append("업종 대비 PBR 저평가")

        if stock.sales_growth < 0:
            comments.append("매출 감소")

        if stock.op_growth < 0:
            comments.append("영업이익 감소")

        if stock.price < stock.ma20:
            comments.append("단기 추세 약세")

        if stock.price < stock.ma60:
            comments.append("중기 추세 약세")

        return " | ".join(comments)
    
AIAnalyzer = StockAnalyzer
