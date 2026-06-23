"""
Morning Stock Assistant Pro

Application Controller
"""

from pathlib import Path

from morning_stock_assistant.database.database import DatabaseManager
from morning_stock_assistant.gui.main_window import MainWindow

from morning_stock_assistant.services.stock_service import StockService
from morning_stock_assistant.ai.analyzer import StockAnalyzer
from morning_stock_assistant.config import CACHE_DIR, DART_API_KEY


class MorningStockAssistant:
    """
    프로그램 전체를 관리하는 클래스
    """

    def __init__(self, project_root: Path):

        self.project_root = project_root

        # Database Manager
        self.database = DatabaseManager(project_root)

        # SQLite 테이블 자동 생성
        self.database.create_tables()

        self.main_window = None

    def start(self):

        stock_service = StockService(
            api_key=DART_API_KEY,
            cache_dir=CACHE_DIR
        )

        analyzer = StockAnalyzer(stock_service)

        self.main_window = MainWindow(
            stock_service,
            analyzer
        )

        self.main_window.run()