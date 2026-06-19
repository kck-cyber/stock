import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"

sys.path.insert(0, str(SRC_DIR))

from morning_stock_assistant.database.database import DatabaseManager
from morning_stock_assistant.database.repository import CompanyRepository

db = DatabaseManager(PROJECT_ROOT)
session = db.get_session()

repo = CompanyRepository(session)

companies = repo.get_all()

print("=" * 60)

for company in companies:

    print(f"회사명      : {company.company_name}")
    print(f"종목코드    : {company.stock_code}")
    print(f"시장        : {company.market}")
    print(f"현재가      : {company.current_price}")
    print(f"PER         : {company.per}")
    print(f"EPS         : {company.eps}")
    print(f"섹터        : {company.sector}")
    print(f"업종        : {company.industry}")
    print("-" * 60)

print("=" * 60)