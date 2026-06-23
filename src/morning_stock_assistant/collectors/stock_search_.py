"""
Stock Search Engine

회사명 또는 종목코드를 표준 티커(Symbol)로 변환한다.
"""

from dataclasses import dataclass


@dataclass
class SearchResult:

    company_name: str

    ticker: str

    market: str


class StockSearch:

    """
    종목 검색 엔진

    현재는 내부 테이블을 사용하며,
    추후 KRX API와 연동될 예정이다.
    """

    STOCK_TABLE = {

        "005930": ("삼성전자", "005930.KS"),

        "삼성전자": ("삼성전자", "005930.KS"),

        "000660": ("SK하이닉스", "000660.KS"),

        "SK하이닉스": ("SK하이닉스", "000660.KS"),

    }

    def search(self, keyword: str):

        result = self.STOCK_TABLE.get(keyword)

        if result is None:

            return None

        return SearchResult(

            company_name=result[0],

            ticker=result[1],

            market="KOSPI",

        )