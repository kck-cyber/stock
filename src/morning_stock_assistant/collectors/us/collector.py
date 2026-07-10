"""
US Stock Collector

NASDAQ
NYSE
AMEX
"""

from pathlib import Path
import pandas as pd


class USCollector:

    def __init__(self):

        self.data = {}

        self.csv = (
            Path(__file__).resolve().parents[4]
            / "storage"
            / "us_stocks.csv"
        )

    # ------------------------
    # Load
    # ------------------------
    def load(self):

        if not self.csv.exists():
            return

        df = pd.read_csv(self.csv)

        self.data.clear()

        for _, row in df.iterrows():

            symbol = str(row["symbol"]).upper()

            self.data[symbol] = {
                "code": symbol,
                "name": row["name"],
                "exchange": row["exchange"],
                "country": "USA",
                "currency": "USD"
            }

    # ------------------------
    # Search
    # ------------------------
    def search(self, keyword):

        keyword = keyword.lower()

        result = []

        for stock in self.data.values():

            if (
                keyword in stock["code"].lower()
                or
                keyword in stock["name"].lower()
            ):
                result.append(stock)

        return result

    # ------------------------
    # Code
    # ------------------------
    def find_by_code(self, code):

        return self.data.get(code.upper())

    # ------------------------
    # Name
    # ------------------------
    def find_by_name(self, name):

        name = name.lower()

        for stock in self.data.values():

            if stock["name"].lower() == name:

                return stock

        return None

    # ------------------------
    # All
    # ------------------------
    def all(self):

        return list(self.data.values())