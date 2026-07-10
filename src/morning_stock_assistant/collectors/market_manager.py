"""
Market Manager

한국 / 미국 / ETF 통합 검색
"""

from typing import List


class MarketManager:

    def __init__(self):

        self.collectors = []

    # -------------------------
    # Collector 등록
    # -------------------------
    def register(self, collector):

        self.collectors.append(collector)

    # -------------------------
    # 전체 검색
    # -------------------------
    def search(self, keyword: str):

        keyword = keyword.strip().lower()

        if not keyword:
            return []

        results = []

        for collector in self.collectors:

            try:

                results.extend(
                    collector.search(keyword)
                )

            except Exception as e:

                print(e)

        return results

    # -------------------------
    # 코드 검색
    # -------------------------
    def find_by_code(self, code: str):

        code = code.upper()

        for collector in self.collectors:

            stock = collector.find_by_code(code)

            if stock:

                return stock

        return None

    # -------------------------
    # 이름 검색
    # -------------------------
    def find_by_name(self, name: str):

        name = name.lower()

        for collector in self.collectors:

            stock = collector.find_by_name(name)

            if stock:

                return stock

        return None

    # -------------------------
    # 전체 종목
    # -------------------------
    def all(self):

        stocks = []

        for collector in self.collectors:

            stocks.extend(
                collector.all()
            )

        return stocks