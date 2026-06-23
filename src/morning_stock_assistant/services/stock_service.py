"""
Stock Service

- KRX + DART 통합 데이터 레이어
- 단일 종목 기준 전체 정보 제공
- AI / GUI 입력용 데이터 생성
"""

from dataclasses import dataclass
from pathlib import Path

from collectors.krx.collector import KRXCollector
from collectors.dart.collector import DartCollector

from collectors.price.yahoo_collector import YahooPriceCollector
from morning_stock_assistant.ai.market_benchmark import MarketBenchmark

from collectors.industry_mapper import IndustryMapper


@dataclass
class StockInfo:
    code: str
    name: str = None
    market: str = None

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

    eps: float = 0.0
    bps: float = 0.0
    per: float = 0.0
    pbr: float = 0.0
    relative_per: float = 0.0
    relative_pbr: float = 0.0
    price_history: any = None
    industry: str = "OTHER"


class StockService:
    """
    통합 주식 데이터 서비스
    """

    def __init__(self, api_key: str, cache_dir: Path):

        self.industry = IndustryMapper()
        self.benchmark = MarketBenchmark()

        self.krx = KRXCollector(cache_dir)
        self.dart = DartCollector(api_key, cache_dir)

        self.price = YahooPriceCollector()

    # --------------------------------------------------
    # 단일 종목 전체 정보
    # --------------------------------------------------
    def get_stock(self, stock_code: str, year: str, report_code: str):
        """
        종목 통합 데이터 반환
        """

        price_data = self.price.get_price(stock_code)
        change_rate = self.price.get_change_rate(stock_code)
        price_history = self.price.get_history(stock_code)

        # 1) KRX 기본 정보
        krx_info = self.krx.get(stock_code)
        if not krx_info:
            return None

        # 2) DART 재무 데이터
        financial = self.dart.get_financial_statement(stock_code, year, report_code)
        if not financial:
            financial = {}
        

        industry = self.industry.get_industry(stock_code)
        benchmark = self.benchmark.get(industry)

        if not benchmark:
            benchmark = {"per": 15, "pbr": 1.5}

        # ⭐ 가격 데이터 추가 (여기!)
        # ⭐ 여기 추가 (정확한 위치)
        eps = financial.get("eps", 0)
        bps = financial.get("bps", 0)

        price = price_data.get("price", 0) if price_data else 0

        per = price / eps if eps > 0 else 0
        pbr = price / bps if bps > 0 else 0

        # 시장 기준 비교용
        market_per = benchmark["per"]
        market_pbr = benchmark["pbr"]

        relative_per = per / market_per if market_per > 0 else 0
        relative_pbr = pbr / market_pbr if market_pbr > 0 else 0


        # 3) 데이터 결합
        stock = StockInfo(
            code=stock_code,
            name=krx_info.get("name"),
            market=krx_info.get("market"),

            sales=financial.get("sales", 0),
            operating_profit=financial.get("operating_profit", 0),
            net_income=financial.get("net_income", 0),
            assets=financial.get("assets", 0),
            liabilities=financial.get("liabilities", 0),
            equity=financial.get("equity", 0),
            roe=financial.get("roe", 0.0),
            debt_ratio=financial.get("debt_ratio", 0.0),
            price=price_data.get("price", 0) if price_data else 0,
            change_rate=change_rate or 0,
            price_history=price_history,

            industry=industry,

            eps=eps,
            bps=bps,
            per=per,
            pbr=pbr,

            relative_per=relative_per,
            relative_pbr=relative_pbr,
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