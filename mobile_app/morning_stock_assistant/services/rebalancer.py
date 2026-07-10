class Rebalancer:

    def __init__(self, portfolio_engine):
        self.engine = portfolio_engine

    def run_monthly(self, stock_list, months):

        history = []

        for month in months:

            portfolio = self.engine.build_portfolio(
                stock_list,
                year=month["year"],
                report_code="11011"
            )

            history.append({
                "month": month["label"],
                "portfolio": portfolio
            })

        return history