import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"

sys.path.insert(0, str(SRC_DIR))

from morning_stock_assistant.services.stock_service import StockService


service = StockService()

data = service.search("005930.KS")

print()

for key, value in data.items():

    print(f"{key}: {value}")