"""
Industry Mapper (Simple version)

- 종목 → 업종 분류 (간단 버전)
"""

class IndustryMapper:

    def __init__(self):
        self.map = {
            "005930": "IT",
            "000660": "IT",
            "035420": "IT",
            "051910": "CHEM",
            "207940": "BIO",
            "068270": "BIO",
        }

    def get_industry(self, stock_code: str):
        return self.map.get(stock_code, "OTHER")