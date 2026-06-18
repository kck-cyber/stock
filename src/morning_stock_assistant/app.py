"""
Morning Stock Assistant Pro

Application Controller
"""

from pathlib import Path

from morning_stock_assistant.gui.main_window import MainWindow


class MorningStockAssistant:
    """
    프로그램 전체를 관리하는 클래스
    """

    def __init__(self, project_root: Path):

        self.project_root = project_root

        self.main_window = None

    def start(self):
        """
        프로그램 시작
        """

        self.main_window = MainWindow()

        self.main_window.show()