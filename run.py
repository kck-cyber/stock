import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"

sys.path.insert(0, str(SRC_DIR))

from morning_stock_assistant.app import MorningStockAssistant


def main():

    app = QApplication(sys.argv)

    msa = MorningStockAssistant(PROJECT_ROOT)

    msa.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()