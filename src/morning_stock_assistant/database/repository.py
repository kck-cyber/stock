from datetime import datetime

from morning_stock_assistant.database.models import Company


class CompanyRepository:

    def __init__(self, session):
        self.session = session

    def add(self, company):
        self.session.add(company)
        self.session.commit()

    def get_all(self):
        return self.session.query(Company).all()

    def get_by_id(self, company_id):
        return (
            self.session.query(Company)
            .filter(Company.id == company_id)
            .first()
        )

    def get_by_stock_code(self, stock_code):
        return (
            self.session.query(Company)
            .filter(Company.stock_code == stock_code)
            .first()
        )

    def save_or_update(self, data):

        company = self.get_by_stock_code(data["stock_code"])

        if company is None:

            company = Company(
                company_name=data["company_name"],
                stock_code=data["stock_code"],
                market=data["market"],
            )

            self.session.add(company)

        company.current_price = data.get("current_price")
        company.market_cap = data.get("market_cap")
        company.per = data.get("per")
        company.eps = data.get("eps")
        company.book_value = data.get("book_value")
        company.currency = data.get("currency")
        company.sector = data.get("sector")
        company.industry = data.get("industry")
        company.last_collected_at = datetime.now()

        self.session.commit()

        return company

    def delete(self, company):
        self.session.delete(company)
        self.session.commit()

    def update(self):
        self.session.commit()