import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"

sys.path.insert(0, str(SRC_DIR))

from morning_stock_assistant.collectors.krx.collector import KRXCollector

collector = KRXCollector(PROJECT_ROOT)

df = collector.collect()

print(df.head())

print()

print("총 종목 수 :", len(df))