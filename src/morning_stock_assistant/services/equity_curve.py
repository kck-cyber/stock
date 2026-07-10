import matplotlib.pyplot as plt


class EquityCurve:

    def build_curve(self, backtest_results):

        years = []
        values = []

        base = 100  # 초기 자본

        for r in backtest_results:

            years.append(r["year"])

            base = base * (1 + r["return"] / 100)

            values.append(base)

        return years, values