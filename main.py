from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"

sys.path.insert(0, str(SRC_DIR))

from morning_stock_assistant.app import MorningStockAssistant


def main():
    app = MorningStockAssistant(PROJECT_ROOT)
    app.start()


if __name__ == "__main__":
    main()