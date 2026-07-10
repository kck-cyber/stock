from datetime import datetime
import pandas as pd


class BacktestEngine:

    def __init__(self, stock_service, portfolio_engine):
        self.service = stock_service
        self.engine = portfolio_engine

    # -----------------------------------
    # 단일 시점 포트폴리오 수익률
    # -----------------------------------
    def run_backtest(self, stock_list, years):

        results = []

        for year in years:

            portfolio = self.engine.build_portfolio(
                stock_list,
                year=str(year),
                report_code="11011"
            )

            total_return = 0
            count = 0

            for code, data in portfolio.items():

                stock = self.service.get_stock(
                    code,
                    str(year),
                    "11011"
                )

                if not stock:
                    continue

                # 단순 수익률 (예시)
                ret = stock.roe  # 실제론 price change 써야 함

                total_return += ret
                count += 1

            avg_return = total_return / count if count > 0 else 0

            results.append({
                "year": year,
                "return": round(avg_return, 2)
            })

        return results