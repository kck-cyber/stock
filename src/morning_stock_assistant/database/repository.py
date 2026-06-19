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

    def delete(self, company):

        self.session.delete(company)

        self.session.commit()

    def update(self):

        self.session.commit()