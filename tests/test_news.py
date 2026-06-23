from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

sys.path.insert(0, str(SRC_DIR))

from morning_stock_assistant.collectors.naver.news import NaverNewsCollector


collector = NaverNewsCollector()

news = collector.collect("삼성전자")

for item in news:

    print("-" * 50)

    print(item["title"])

    print(item["date"])

    print(item["url"])