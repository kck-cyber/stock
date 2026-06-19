import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

SRC_DIR = PROJECT_ROOT / "src"

sys.path.insert(0, str(SRC_DIR))

from morning_stock_assistant.collectors.stock_search import StockSearch

engine = StockSearch()

result = engine.search("삼성전자")

print(result)

result = engine.search("005930")

print(result)