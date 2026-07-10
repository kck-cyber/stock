"""
Yahoo Finance Collector
"""

from typing import Dict

import yfinance as yf

from ..base import BaseCollector


class YahooCollector(BaseCollector):
    """
    Yahoo Finance 데이터 수집기
    """

    def collect(self, ticker: str) -> Dict:

        stock = yf.Ticker(ticker)

        info = stock.info

        return {

            "company_name": info.get("longName"),

            "symbol": info.get("symbol"),

            "market": info.get("exchange"),

            "currency": info.get("currency"),

            "current_price": info.get("currentPrice"),

            "market_cap": info.get("marketCap"),

            "per": info.get("trailingPE"),

            "eps": info.get("trailingEps"),

            "book_value": info.get("bookValue"),

            "dividend_yield": info.get("dividendYield"),

            "sector": info.get("sector"),

            "industry": info.get("industry"),

        }