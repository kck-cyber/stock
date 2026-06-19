"""
Stock Service

주식 데이터 수집 및 저장 서비스
"""

from pathlib import Path

from morning_stock_assistant.collectors.stock_search import StockSearch
from morning_stock_assistant.collectors.yahoo import YahooCollector

from morning_stock_assistant.database.database import DatabaseManager
from morning_stock_assistant.database.repository import CompanyRepository


class StockService:

    def __init__(self, project_root):

        self.database = DatabaseManager(project_root)

        self.search_engine = StockSearch()

        self.yahoo = YahooCollector()

        self.database.create_tables()

        self.session = self.database.get_session()

        self.repository = CompanyRepository(self.session)

    def search(self, keyword: str):

        result = self.search_engine.search(keyword)

        if result is None:

            return None

        data = self.yahoo.collect(result.ticker)

        data["stock_code"] = result.ticker.replace(".KS", "")

        self.repository.save_or_update(data)

        return data