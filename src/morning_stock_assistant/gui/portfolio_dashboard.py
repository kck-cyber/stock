import tkinter as tk
from tkinter import ttk

from services.stock_service import StockService
from pathlib import Path

from services.portfolio_engine import PortfolioEngine
from services.backtest_engine import BacktestEngine

import matplotlib.pyplot as plt

from services.benchmark_comparator import BenchmarkComparator

from services.rebalancer import Rebalancer

from services.trading_engine import TradingEngine

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))


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


class PortfolioDashboard:

    def __init__(self, root, api_key, cache_dir):

        self.root = root
        self.service = StockService(api_key, cache_dir)
        self.backtest = BacktestEngine(self.service, self.engine)

        self.root.title("Quant Portfolio Dashboard")
        self.root.geometry("1200x700")

        self.engine = PortfolioEngine(self.service)
        self.equity = EquityCurve()
        self.comparator = BenchmarkComparator()
        self.rebalancer = Rebalancer(self.engine)
        self.trader = TradingEngine(self.engine)

        # 테이블
        self.tree = ttk.Treeview(root, columns=(
            "code", "name", "roe", "per", "pbr", "relative_per", "relative_pbr", "score"
        ), show="headings")

        for col in self.tree["columns"]:
            self.tree.heading(col, text=col)

        self.tree.pack(fill="both", expand=True)

        # 버튼
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=10)

        tk.Button(btn_frame, text="Load Portfolio", command=self.load_data).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Build Portfolio", command=self.build_portfolio).pack(side="left", padx=5)
        tk.Button(self.root, text="Run Backtest", command=self.run_backtest).pack()
        tk.Button(self.root, text="Show Equity Curve", command=self.show_curve).pack()
        tk.Button(self.root, text="Compare vs Market", command=self.compare_market).pack()
        tk.Button(self.root, text="Monthly Rebalance", command=self.run_rebalance).pack()
        tk.Button(self.root, text="Run Trading Simulation", command=self.run_trade).pack()

    # -----------------------------
    # 데이터 로딩
    # -----------------------------
    def load_data(self):

        stock_list = ["005930", "000660", "035420", "051910"]

        self.tree.delete(*self.tree.get_children())

        for code in stock_list:

            stock = self.service.get_stock(
                code,
                "2024",
                "11011"
            )

            if not stock:
                continue

            score = self.service.score_stock(
                code,
                "2024",
                "11011"
            )

            self.tree.insert("", "end", values=(
                stock.code,
                stock.name,
                round(stock.roe, 2),
                round(stock.per, 2),
                round(stock.pbr, 2),
                round(stock.relative_per, 2),
                score
            ))

    def build_portfolio(self):

        stock_list = ["005930", "000660", "035420", "051910"]

        portfolio = self.engine.build_portfolio(stock_list)

        self.tree.delete(*self.tree.get_children())

        for code, data in portfolio.items():

            stock = self.service.get_stock(code, "2024", "11011")

            if not stock:
                continue

            self.tree.insert("", "end", values=(
                code,
                data["name"],
                round(stock.roe, 2),
                round(stock.per, 2),
                round(stock.pbr, 2),
                round(stock.relative_per, 2),
                round(stock.relative_pbr, 2),
                data["score"]
            ))

    def run_backtest(self):

        stock_list = ["005930", "000660", "035420", "051910"]

        results = self.backtest.run_backtest(stock_list, [2020, 2021, 2022, 2023])

        self.tree.delete(*self.tree.get_children())

        for r in results:

            self.tree.insert("", "end", values=(
                r["year"],
                "",
                "",
                "",
                "",
                "",
                r["return"]
            ))

    def show_curve(self):

        stock_list = ["005930", "000660", "035420", "051910"]

        results = self.backtest.run_backtest(
            stock_list,
            [2020, 2021, 2022, 2023]
        )

        years, values = self.equity.build_curve(results)

        plt.figure()

        plt.plot(years, values)

        plt.title("Quant Portfolio Equity Curve")
        plt.xlabel("Year")
        plt.ylabel("Portfolio Value")

        plt.show()

    def compare_market(self):

        stock_list = ["005930", "000660", "035420", "051910"]

        strategy = self.backtest.run_backtest(
            stock_list,
            [2020, 2021, 2022, 2023]
        )

        market = [
            {"year": 2020, "return": 8.1},
            {"year": 2021, "return": 10.2},
            {"year": 2022, "return": -5.0},
            {"year": 2023, "return": 9.3}
        ]

        result = self.comparator.compare(strategy, market)

        self.tree.delete(*self.tree.get_children())

        for r in result:

            self.tree.insert("", "end", values=(
                r["year"],
                "",
                "",
                "",
                "",
                "",
                r["strategy"]
            ))

    def run_rebalance(self):

        stock_list = ["005930", "000660", "035420", "051910"]

        months = [
            {"label": "2024-01", "year": "2024"},
            {"label": "2024-02", "year": "2024"},
            {"label": "2024-03", "year": "2024"},
        ]

        history = self.rebalancer.run_monthly(stock_list, months)

        self.tree.delete(*self.tree.get_children())

        for h in history:

            top = list(h["portfolio"].values())[0]

            self.tree.insert("", "end", values=(
                h["month"],
                top["name"],
                "",
                "",
                "",
                "",
                top["score"]
            ))

    def run_trade(self):

        stock_list = ["005930", "000660", "035420", "051910"]

        signals = self.trader.generate_signals(stock_list)

        price_map = {}

        for code in stock_list:
            stock = self.service.get_stock(code, "2024", "11011")
            price_map[code] = stock.price

        self.trader.execute_trades(signals, price_map)

        self.tree.delete(*self.tree.get_children())

        for code, pos in self.trader.positions.items():

            self.tree.insert("", "end", values=(
                code,
                "",
                "",
                "",
                "",
                "",
                pos["qty"]
            ))