"""
Stock Service

- KRX + DART 통합 데이터 레이어
- 단일 종목 기준 전체 정보 제공
- AI / GUI 입력용 데이터 생성
"""

from dataclasses import dataclass
from pathlib import Path
import time

from morning_stock_assistant.ai.market_benchmark import MarketBenchmark

from morning_stock_assistant.collectors.krx.collector import KRXCollector
from morning_stock_assistant.collectors.dart.collector import DartCollector
from morning_stock_assistant.collectors.price.yahoo_collector import YahooPriceCollector
from morning_stock_assistant.services.industry_mapper import IndustryMapper
from morning_stock_assistant.collectors.news.collector import NewsCollector


@dataclass
class StockInfo:
    code: str
    name: str = None
    market: str = None
    asset_type: str = "STOCK"
    is_etf: bool = False

    # DART 재무
    sales: int = 0
    operating_profit: int = 0
    net_income: int = 0
    assets: int = 0
    liabilities: int = 0
    equity: int = 0

    # 지표
    roe: float = 0.0
    debt_ratio: float = 0.0

    price: float = 0.0
    change_rate: float = 0.0
    currency: str = "KRW"
    price_date: str = ""

    eps: float = 0.0
    bps: float = 0.0
    per: float = 0.0
    pbr: float = 0.0
    psr: float = 0.0
    pcr: float = 0.0
    market_cap: float = 0.0
    relative_per: float = 0.0
    relative_pbr: float = 0.0
    price_history: any = None
    industry: str = "OTHER"

    # -----------------------------
    # 성장성
    # -----------------------------
    sales_growth: float = 0.0
    op_growth: float = 0.0
    eps_growth: float = 0.0
    bps_growth: float = 0.0

    # -----------------------------
    # 수익성
    # -----------------------------
    roa: float = 0.0
    operating_margin: float = 0.0
    net_margin: float = 0.0

    # -----------------------------
    # 현금흐름
    # -----------------------------
    free_cash_flow: int = 0
    operating_cash_flow: int = 0
    capex: int = 0
    cash: int = 0
    total_debt: int = 0
    roic: float = 0.0
    fcf_yield: float = 0.0
    sales_cagr_3y: float = 0.0
    op_cagr_3y: float = 0.0
    net_income_cagr_3y: float = 0.0

    # -----------------------------
    # 배당
    # -----------------------------
    dividend_yield: float = 0.0

    # -----------------------------
    # 안정성
    # -----------------------------
    current_ratio: float = 0.0

    # -----------------------------
    # 기술적 지표
    # -----------------------------
    ma20: float = 0.0
    ma60: float = 0.0
    ma120: float = 0.0

    high52: float = 0.0
    low52: float = 0.0

    volume_ratio: float = 0.0
    news_score: int = 0
    short_ratio: float = 0.0
    short_volume: float = 0.0
    short_value: float = 0.0
    foreign_net_buy: float = 0.0
    institution_net_buy: float = 0.0
    individual_net_buy: float = 0.0
    institutional_ownership: float = 0.0
    analyst_target_mean: float = 0.0
    analyst_target_high: float = 0.0
    analyst_target_low: float = 0.0
    analyst_count: float = 0.0
    analyst_recommendation: str = ""


class StockService:
    """
    통합 주식 데이터 서비스
    """

    def __init__(
        self,
        api_key: str,
        cache_dir: Path,
    ):

        self.industry = IndustryMapper()
        self.benchmark = MarketBenchmark()

        try:
            self.krx = KRXCollector(cache_dir)
        except Exception:
            self.krx = None

        if api_key:
            try:
                self.dart = DartCollector(api_key, cache_dir)
            except Exception:
                self.dart = None
        else:
            self.dart = None

        self.price = YahooPriceCollector(
            market_lookup=self.krx.get if self.krx else None
        )
        self.analysis_cache = {}
        self.stock_cache = {}
        self.price_summary_cache = {}
        self.stock_cache_ttl = 300
        self.price_summary_cache_ttl = 60
        self.news = NewsCollector()

    @staticmethod
    def _cache_get(cache, key, ttl):

        cached = cache.get(key)

        if not cached:
            return None

        created_at, value = cached

        if time.time() - created_at <= ttl:
            return value

        cache.pop(key, None)
        return None

    @staticmethod
    def _cache_set(cache, key, value):

        cache[key] = (time.time(), value)

    @staticmethod
    def _safe_number(value, default=0):

        if value is None:
            return default

        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    # --------------------------------------------------
    # 단일 종목 전체 정보
    # --------------------------------------------------
    def get_stock(self, stock_code: str, year: str, report_code: str):
        """
        종목 통합 데이터 반환
        """
        # ------------------------------------
        # 미국 주식 여부
        # ------------------------------------

        cache_key = (stock_code, year, report_code)
        cached = self._cache_get(
            self.stock_cache,
            cache_key,
            self.stock_cache_ttl
        )

        if cached is not None:
            return cached

        is_us_stock = stock_code.isalpha()

        price_data = self.price.get_price(stock_code)
        change_rate = self.price.get_change_rate(stock_code)
        price_history = self.price.get_history(stock_code)
        try:
            technical = self.price.get_technical(stock_code)
        except Exception:
            technical = {}
        fundamental = self.price.get_fundamental(stock_code)
        market_flow = self.price.get_market_flow(stock_code)

        # ------------------------------------
        # 한국 / 미국 분기
        # ------------------------------------

        if is_us_stock:

            krx_info = {
                "name": stock_code.upper(),
                "market": "US"
            }

        else:

            if not self.krx:
                return None

            krx_info = self.krx.get(stock_code)

            if not krx_info:
                return None

        # 2) DART 재무 데이터
        if is_us_stock:

            financial = {}

        elif self.dart:

            try:
                financial = self.dart.get_financial_statement(
                    stock_code,
                    year,
                    report_code
                ) or {}
            except Exception as e:
                print("DART financial load failed:", e)
                financial = {}

        else:

            financial = {}

        fallback_financial = self.price.get_financials(stock_code)

        for key, value in fallback_financial.items():
            if not financial.get(key):
                financial[key] = value
        

        if is_us_stock:

            industry = "US"

        else:

            industry = self.industry.get_industry(stock_code)

        benchmark = self.benchmark.get(industry)

        if benchmark is None:

            if is_us_stock:

                benchmark = {
                    "per": 25,
                    "pbr": 4
                }

            else:

                benchmark = {
                    "per": 15,
                    "pbr": 1.5
                }

        # ⭐ 가격 데이터 추가 (여기!)
        # ⭐ 여기 추가 (정확한 위치)
        if is_us_stock:

            eps = fundamental.get("eps", 0)
            bps = fundamental.get("bps", 0)

        else:

            eps = financial.get("eps", 0) or fundamental.get("eps", 0)
            bps = financial.get("bps", 0) or fundamental.get("bps", 0)

        price = (
            self._safe_number(price_data.get("price", 0))
            if price_data
            else 0
        )

        per = fundamental.get("per", 0) or (price / eps if eps > 0 else 0)
        pbr = fundamental.get("pbr", 0) or (price / bps if bps > 0 else 0)
        market_cap = self._safe_number(fundamental.get("market_cap", 0))
        shares = self._safe_number(fundamental.get("shares", 0))

        if not market_cap and price > 0 and shares > 0:
            market_cap = price * shares

        psr = self._safe_number(fundamental.get("psr", 0))
        pcr = self._safe_number(fundamental.get("pcr", 0))
        sales = self._safe_number(financial.get("sales", 0))
        free_cash_flow = self._safe_number(financial.get("free_cash_flow", 0))

        if not psr and market_cap > 0 and sales > 0:
            psr = market_cap / sales

        if not pcr and market_cap > 0 and free_cash_flow > 0:
            pcr = market_cap / free_cash_flow

        operating_cash_flow = self._safe_number(
            financial.get("operating_cash_flow", 0)
        )
        capex = self._safe_number(financial.get("capex", 0))
        cash = self._safe_number(financial.get("cash", 0))
        total_debt = self._safe_number(financial.get("total_debt", 0))

        if not free_cash_flow and operating_cash_flow:
            free_cash_flow = operating_cash_flow - capex
            financial["free_cash_flow"] = free_cash_flow

        invested_capital = (
            self._safe_number(financial.get("equity", 0))
            + total_debt
            - cash
        )
        roic = (
            self._safe_number(financial.get("operating_profit", 0))
            / invested_capital
            * 100
            if invested_capital > 0
            else 0
        )
        fcf_yield = (
            free_cash_flow / market_cap * 100
            if market_cap > 0
            else 0
        )

        # 시장 기준 비교용
        market_per = benchmark["per"]
        market_pbr = benchmark["pbr"]

        relative_per = per / market_per if market_per > 0 else 0
        relative_pbr = pbr / market_pbr if market_pbr > 0 else 0
        quote_type = str(fundamental.get("quote_type", "")).upper()
        asset_type = (
            "ETF"
            if quote_type == "ETF" or krx_info.get("market") == "ETF"
            else "STOCK"
        )
        is_etf = asset_type == "ETF"


        # 3) 데이터 결합
        stock = StockInfo(
            code=stock_code,
            name=krx_info.get("name"),
            market=krx_info.get("market"),
            asset_type=asset_type,
            is_etf=is_etf,

            sales=financial.get("sales", 0),
            operating_profit=financial.get("operating_profit", 0),
            net_income=financial.get("net_income", 0),
            assets=financial.get("assets", 0),
            liabilities=financial.get("liabilities", 0),
            equity=financial.get("equity", 0),
            roe=(
                fundamental.get("roe", 0) * 100
                if is_us_stock
                else financial.get("roe", 0)
            ),
            debt_ratio=financial.get("debt_ratio", 0.0),
            price=price,
            change_rate=self._safe_number(change_rate),
            currency=(
                price_data.get("currency", "KRW")
                if price_data
                else "KRW"
            ),
            price_date=(
                price_data.get("price_date", "")
                if price_data
                else ""
            ),
            price_history=price_history,

            industry=industry,

            eps=eps,
            bps=bps,
            per=per,
            pbr=pbr,
            psr=psr,
            pcr=pcr,
            market_cap=market_cap,

            relative_per=relative_per,
            relative_pbr=relative_pbr,

            sales_growth=financial.get("sales_growth", 0),
            op_growth=financial.get("op_growth", 0),
            eps_growth=financial.get("eps_growth", 0),
            bps_growth=financial.get("bps_growth", 0),

            roa=financial.get("roa", 0),
            operating_margin=financial.get("operating_margin", 0),
            net_margin=financial.get("net_margin", 0),

            free_cash_flow=financial.get("free_cash_flow", 0),
            operating_cash_flow=operating_cash_flow,
            capex=capex,
            cash=cash,
            total_debt=total_debt,
            roic=round(roic, 2),
            fcf_yield=round(fcf_yield, 2),
            sales_cagr_3y=financial.get("sales_cagr_3y", 0),
            op_cagr_3y=financial.get("op_cagr_3y", 0),
            net_income_cagr_3y=financial.get("net_income_cagr_3y", 0),

            dividend_yield=(
                (fundamental.get("dividend_yield", 0) or 0) * 100
                if is_us_stock
                else (
                    financial.get("dividend_yield", 0)
                    or fundamental.get("dividend_yield", 0)
                )
            ),

            current_ratio=financial.get("current_ratio", 0),

            ma20=technical.get("ma20", 0) if technical else 0,
            ma60=technical.get("ma60", 0) if technical else 0,
            ma120=technical.get("ma120", 0) if technical else 0,

            high52=technical.get("high52", 0) if technical else 0,
            low52=technical.get("low52", 0) if technical else 0,

            volume_ratio=technical.get("volume_ratio", 0) if technical else 0,

            news_score = 0,
            short_ratio=self._safe_number(
                market_flow.get(
                    "short_ratio",
                    fundamental.get("short_ratio", 0)
                )
            ),
            short_volume=self._safe_number(
                market_flow.get("short_volume", 0)
            ),
            short_value=self._safe_number(
                market_flow.get("short_value", 0)
            ),
            foreign_net_buy=self._safe_number(
                market_flow.get("foreign_net_buy", 0)
            ),
            institution_net_buy=self._safe_number(
                market_flow.get("institution_net_buy", 0)
            ),
            individual_net_buy=self._safe_number(
                market_flow.get("individual_net_buy", 0)
            ),
            institutional_ownership=self._safe_number(
                market_flow.get(
                    "institutional_ownership",
                    fundamental.get("institutional_ownership", 0)
                )
            ),
            analyst_target_mean=self._safe_number(
                fundamental.get("analyst_target_mean", 0)
            ),
            analyst_target_high=self._safe_number(
                fundamental.get("analyst_target_high", 0)
            ),
            analyst_target_low=self._safe_number(
                fundamental.get("analyst_target_low", 0)
            ),
            analyst_count=self._safe_number(
                fundamental.get("analyst_count", 0)
            ),
            analyst_recommendation=str(
                fundamental.get("analyst_recommendation", "") or ""
            ),

        )
        stock.news_score = self.news.get_news_score(
            stock.name
        )

        self._cache_set(
            self.stock_cache,
            cache_key,
            stock
        )

        return stock

    # --------------------------------------------------
    # 간단 요약 데이터
    # --------------------------------------------------
    def get_summary(self, stock_code: str, year: str, report_code: str):
        """
        AI 입력용 요약 데이터
        """

        stock = self.get_stock(stock_code, year, report_code)
        if not stock:
            return None

        return {
            "code": stock.code,
            "name": stock.name,
            "market": stock.market,

            "sales": stock.sales,
            "operating_profit": stock.operating_profit,
            "net_income": stock.net_income,

            "roe": stock.roe,
            "debt_ratio": stock.debt_ratio,
        }

    # --------------------------------------------------
    # 투자 점수 (기초 버전)
    # --------------------------------------------------
    def score_stock(self, stock_code: str, year: str, report_code: str):
        """
        간단 투자 점수 (0~100)
        """

        stock = self.get_stock(stock_code, year, report_code)
        if not stock:
            return None

        score = 0

        # ROE 점수 (최대 40)
        if stock.roe:
            score += min(stock.roe * 2, 40)

        # 부채비율 (낮을수록 좋음, 최대 30)
        if stock.debt_ratio:
            score += max(30 - (stock.debt_ratio / 5), 0)

        # 흑자 여부 (20)
        if stock.net_income > 0:
            score += 20

        # 매출 규모 (10)
        if stock.sales > 0:
            score += 10

        return round(min(score, 100), 2)
    
    def get_price_summary(self, stock_code):

        cached = self._cache_get(
            self.price_summary_cache,
            stock_code,
            self.price_summary_cache_ttl
        )

        if cached is not None:
            return cached

        price_data = self.price.get_price(stock_code)

        change = self.price.get_change_rate(
            stock_code,
            price_data
        )

        summary = {
            "price": (
                self._safe_number(price_data.get("price", 0))
                if price_data
                else 0
            ),
            "change": self._safe_number(change),
            "currency": (
                price_data.get("currency", "KRW")
                if price_data
                else "KRW"
            ),
            "price_date": (
                price_data.get("price_date", "")
                if price_data
                else ""
            ),
        }

        self._cache_set(
            self.price_summary_cache,
            stock_code,
            summary
        )

        return summary

    def get_briefing_metrics(self, stock_code):

        summary = self.get_price_summary(stock_code)

        return {
            "price": self._safe_number(summary.get("price", 0)),
            "change_1d": self._safe_number(summary.get("change", 0)),
            "change_1m": self._history_return(stock_code, "1mo"),
            "change_3m": self._history_return(stock_code, "3mo"),
            "currency": summary.get("currency", "KRW"),
            "price_date": summary.get("price_date", ""),
        }

    def _history_return(self, stock_code, period):

        try:
            hist = self.price.get_history(stock_code, period=period)

            if hist is None or hist.empty or "Close" not in hist:
                return 0

            close = hist["Close"].dropna()

            if len(close) < 2:
                return 0

            start = self._safe_number(close.iloc[0])
            end = self._safe_number(close.iloc[-1])

            if start <= 0:
                return 0

            return round(((end - start) / start) * 100, 2)

        except Exception:
            return 0
