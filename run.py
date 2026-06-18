"""
=========================================================
Morning Stock Assistant Pro
run.py

프로그램 시작 파일

Author : kck-cyber
Version : v0.2
=========================================================
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"

sys.path.insert(0, str(SRC_DIR))

from PySide6.QtWidgets import QApplication

from morning_stock_assistant.app import MorningStockAssistant

def main() -> int:
    """
    프로그램 시작
    """

    # 프로젝트 루트
    project_root = Path(__file__).resolve().parent

    # QApplication 생성
    app = QApplication(sys.argv)

    # 메인 프로그램
    program = MorningStockAssistant(project_root)

    program.start()

    # 이벤트 루프
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())