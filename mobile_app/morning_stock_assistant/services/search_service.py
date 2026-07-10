"""
통합 종목 검색 서비스

KRX + US Market
"""

from morning_stock_assistant.collectors.market.us_market import USMarket


class SearchService:

    def __init__(self, krx_collector):

        self.krx = krx_collector
        self.us = USMarket()

    # --------------------------------------------------

    def search(self, keyword):

        keyword = keyword.strip()

        result = []

        # -------------------------
        # 한국
        # -------------------------

        krx_result = self.krx.search(keyword)

        if krx_result:

            result.extend(krx_result)

        # -------------------------
        # 미국
        # -------------------------

        us_result = self.us.search(keyword)

        if us_result:

            result.extend(us_result)

        return result