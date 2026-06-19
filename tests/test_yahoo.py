import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"

sys.path.insert(0, str(SRC_DIR))

from morning_stock_assistant.collectors.yahoo import YahooCollector

collector = YahooCollector()

data = collector.collect("005930.KS")

print("=" * 60)

for key, value in data.items():
    print(f"{key:20}: {value}")

print("=" * 60)