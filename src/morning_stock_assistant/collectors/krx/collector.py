from pathlib import Path

import pandas as pd
from pykrx import stock


class KRXCollector:

    def __init__(self, project_root: Path):

        self.project_root = project_root

        self.output_file = (
            project_root /
            "config" /
            "stock_master.csv"
        )

    def collect(self):

        tickers = stock.get_market_ticker_list()

        rows = []

        for ticker in tickers:

            try:

                name = stock.get_market_ticker_name(ticker)

                rows.append({
                    "company_name": name,
                    "stock_code": ticker,
                    "ticker": f"{ticker}.KS",
                    "market": "KOSPI/KOSDAQ"
                })

            except Exception:

                continue

        df = pd.DataFrame(rows)

        df.to_csv(
            self.output_file,
            index=False,
            encoding="utf-8-sig"
        )

        return df