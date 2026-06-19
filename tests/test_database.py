import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"

sys.path.insert(0, str(SRC_DIR))

from morning_stock_assistant.services.stock_service import StockService

service = StockService()

service.search("삼성전자")

print("DB 저장 완료")