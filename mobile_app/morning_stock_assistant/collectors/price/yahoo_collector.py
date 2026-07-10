"""
Yahoo Finance Price Collector

Supports US tickers and Korean six-digit tickers.
"""

from datetime import datetime, timedelta
from io import StringIO

import pandas as pd
import requests
import yfinance as yf

from morning_stock_assistant.collectors.krx.collector import ensure_pkg_resources_stub


class YahooPriceCollector:
    """
    Price data collector backed by Yahoo Finance.
    """

    def __init__(self, market_lookup=None):

        self.market_lookup = market_lookup

    def _to_ticker_candidates(self, stock_code: str):

        stock_code = stock_code.strip().upper()

        if stock_code.isalpha():
            return [stock_code]

        if stock_code.isdigit() and len(stock_code) == 6:
            market = self._get_market(stock_code)

            if market in ("코스닥", "KOSDAQ"):
                return [stock_code + ".KQ", stock_code + ".KS"]

            if market in ("유가", "KOSPI"):
                return [stock_code + ".KS", stock_code + ".KQ"]

            return [stock_code + ".KS", stock_code + ".KQ"]

        return [stock_code]

    def _to_ticker(self, stock_code: str):

        return self._to_ticker_candidates(stock_code)[0]

    def _get_market(self, stock_code: str):

        if not self.market_lookup:
            return ""

        try:
            item = self.market_lookup(stock_code)
            return item.get("market", "") if item else ""
        except Exception:
            return ""

    def is_us_stock(self, stock_code: str):

        return stock_code.isalpha()

    def is_korean_stock(self, stock_code: str):

        return stock_code.isdigit() and len(stock_code) == 6

    def get_price(self, stock_code: str):

        if self.is_korean_stock(stock_code):
            krx_price = self._get_krx_price(stock_code)

            if krx_price:
                return krx_price

        for ticker in self._to_ticker_candidates(stock_code):
            try:
                data = yf.Ticker(ticker)
                info = data.fast_info
                price = info.get("last_price")

                if price is None:
                    history_price = self._get_yahoo_history_price(ticker)

                    if history_price:
                        return history_price

                    continue

                return {
                    "price": price,
                    "prev_close": info.get("previous_close"),
                    "currency": info.get("currency"),
                    "ticker": ticker,
                    "price_date": self._get_yahoo_last_price_date(ticker),
                }

            except Exception:
                continue

        return None

    def _get_yahoo_history_price(self, ticker: str):

        try:
            hist = yf.Ticker(ticker).history(period="5d")

            if hist.empty:
                return None

            close = hist["Close"].dropna()

            if close.empty:
                return None

            price = float(close.iloc[-1])
            prev_close = (
                float(close.iloc[-2])
                if len(close) >= 2
                else price
            )

            return {
                "price": price,
                "prev_close": prev_close,
                "currency": "USD",
                "ticker": ticker,
                "price_date": self._format_index_date(close.index[-1]),
            }

        except Exception:
            return None

    def _get_yahoo_last_price_date(self, ticker: str):

        try:
            hist = yf.Ticker(ticker).history(period="5d")

            if hist.empty or "Close" not in hist:
                return ""

            close = hist["Close"].dropna()

            if close.empty:
                return ""

            return self._format_index_date(close.index[-1])

        except Exception:
            return ""

    @staticmethod
    def _format_index_date(value):

        try:
            if hasattr(value, "to_pydatetime"):
                value = value.to_pydatetime()

            return value.strftime("%Y-%m-%d")
        except Exception:
            return str(value)[:10] if value is not None else ""

    def _get_krx_price(self, stock_code: str):

        try:
            ensure_pkg_resources_stub()

            from pykrx import stock

            end = datetime.today()
            start = end - timedelta(days=14)

            df = stock.get_market_ohlcv_by_date(
                start.strftime("%Y%m%d"),
                end.strftime("%Y%m%d"),
                stock_code,
            )

            if df.empty:
                return None

            close = df["종가"].dropna()

            if close.empty:
                return None

            price = float(close.iloc[-1])
            prev_close = (
                float(close.iloc[-2])
                if len(close) >= 2
                else price
            )

            return {
                "price": price,
                "prev_close": prev_close,
                "currency": "KRW",
                "ticker": stock_code,
                "price_date": self._format_index_date(close.index[-1]),
            }

        except Exception as e:
            print("KRX price load failed:", e)
            return None

    def get_fundamental(self, stock_code):

        result = {}

        if self.is_korean_stock(stock_code):
            krx_fundamental = self._get_krx_fundamental(stock_code)

            if krx_fundamental:
                result.update(krx_fundamental)

            naver_fundamental = self._get_naver_financials(stock_code)

            for key, value in naver_fundamental.items():
                if not result.get(key) and value:
                    result[key] = value

        for ticker in self._to_ticker_candidates(stock_code):
            try:
                info = yf.Ticker(ticker).info

                if not info:
                    continue

                yahoo_result = {
                    "eps": info.get("trailingEps", 0),
                    "bps": info.get("bookValue", 0),
                    "per": info.get("trailingPE", 0),
                    "forward_per": info.get("forwardPE", 0),
                    "psr": info.get("priceToSalesTrailing12Months", 0),
                    "pcr": info.get("priceToCashflow", 0),
                    "roe": info.get("returnOnEquity", 0),
                    "market_cap": info.get("marketCap", 0),
                    "shares": info.get("sharesOutstanding", 0),
                    "dividend_yield": info.get("dividendYield", 0),
                    "sector": info.get("sector", ""),
                    "industry": info.get("industry", ""),
                    "quote_type": info.get("quoteType", ""),
                    "short_ratio": info.get("shortPercentOfFloat", 0),
                    "institutional_ownership": info.get(
                        "heldPercentInstitutions",
                        0
                    ),
                    "analyst_target_mean": info.get("targetMeanPrice", 0),
                    "analyst_target_high": info.get("targetHighPrice", 0),
                    "analyst_target_low": info.get("targetLowPrice", 0),
                    "analyst_count": info.get("numberOfAnalystOpinions", 0),
                    "analyst_recommendation": (
                        info.get("recommendationKey")
                        or info.get("recommendationMean")
                        or ""
                    ),
                }

                for key, value in yahoo_result.items():
                    if not result.get(key) and value:
                        result[key] = value

                if result:
                    return result

            except Exception:
                continue

        return result

    def get_market_flow(self, stock_code):

        result = {
            "short_ratio": 0,
            "short_volume": 0,
            "short_value": 0,
            "foreign_net_buy": 0,
            "institution_net_buy": 0,
            "individual_net_buy": 0,
            "institutional_ownership": 0,
        }

        if self.is_korean_stock(stock_code):
            krx_flow = self._get_krx_market_flow(stock_code)

            if krx_flow:
                result.update(krx_flow)

            return result

        for ticker in self._to_ticker_candidates(stock_code):
            try:
                info = yf.Ticker(ticker).info

                short_ratio = info.get("shortPercentOfFloat", 0) or 0
                institutional_ownership = (
                    info.get("heldPercentInstitutions", 0)
                    or 0
                )

                result.update({
                    "short_ratio": (
                        float(short_ratio) * 100
                        if short_ratio <= 1
                        else float(short_ratio)
                    ),
                    "institutional_ownership": (
                        float(institutional_ownership) * 100
                        if institutional_ownership <= 1
                        else float(institutional_ownership)
                    ),
                })
                return result
            except Exception:
                continue

        return result

    def _get_krx_market_flow(self, stock_code):

        try:
            ensure_pkg_resources_stub()

            from pykrx import stock

            end = datetime.today()
            start = end - timedelta(days=14)
            start_text = start.strftime("%Y%m%d")
            end_text = end.strftime("%Y%m%d")
            result = {}

            try:
                short_df = stock.get_shorting_volume_by_date(
                    start_text,
                    end_text,
                    stock_code
                )

                if short_df is not None and not short_df.empty:
                    row = short_df.dropna(how="all").iloc[-1]
                    result["short_volume"] = self._safe_float(
                        self._find_series_value(row, ("공매도", "short"))
                    )
                    result["short_ratio"] = self._safe_float(
                        self._find_series_value(row, ("비중", "ratio"))
                    )
            except Exception:
                pass

            try:
                investor_df = stock.get_market_trading_value_by_date(
                    start_text,
                    end_text,
                    stock_code
                )

                if investor_df is not None and not investor_df.empty:
                    totals = investor_df.sum(numeric_only=True)
                    result["foreign_net_buy"] = self._safe_float(
                        self._find_series_value(
                            totals,
                            ("외국인합계", "외국인", "foreigner")
                        )
                    )
                    result["institution_net_buy"] = self._safe_float(
                        self._find_series_value(
                            totals,
                            ("기관합계", "기관", "institution")
                        )
                    )
                    result["individual_net_buy"] = self._safe_float(
                        self._find_series_value(
                            totals,
                            ("개인", "individual")
                        )
                    )
            except Exception:
                pass

            return result

        except Exception:
            return {}

    @staticmethod
    def _find_series_value(series, candidates):

        if series is None:
            return 0

        normalized = {
            str(key).replace(" ", "").lower(): key
            for key in series.index
        }

        for candidate in candidates:
            candidate = str(candidate).replace(" ", "").lower()

            for key, original_key in normalized.items():
                if candidate in key:
                    return series.get(original_key, 0)

        return 0

    def _get_naver_financials(self, stock_code):

        try:
            url = (
                "https://finance.naver.com/item/main.naver?"
                f"code={stock_code}"
            )

            response = requests.get(
                url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0 Safari/537.36"
                    )
                },
                timeout=10,
            )
            response.raise_for_status()
            response.encoding = (
                response.apparent_encoding
                or response.encoding
                or "utf-8"
            )

            tables = pd.read_html(StringIO(response.text))

            target = None

            for table in tables:
                first_col = table.iloc[:, 0].astype(str)

                if first_col.str.contains("매출액", na=False).any():
                    target = table
                    break

            if target is None:
                return {}

            flat_columns = [
                " ".join(str(part) for part in column if str(part) != "nan")
                if isinstance(column, tuple)
                else str(column)
                for column in target.columns
            ]

            target = target.copy()
            target.columns = flat_columns
            label_column = target.columns[0]

            def row_value(label, annual=True):
                values = row_values(label, annual)
                return values[-1] if values else 0

            def row_values(label, annual=True):
                rows = target[
                    target[label_column]
                    .astype(str)
                    .str.contains(label, na=False, regex=False)
                ]

                if rows.empty:
                    return []

                row = rows.iloc[0]

                columns = target.columns[1:]

                if annual:
                    annual_columns = [
                        column
                        for column in columns
                        if "최근 연간" in column and "(E)" not in column
                    ]

                    if annual_columns:
                        columns = annual_columns

                values = []

                for column in columns:
                    value = self._safe_float(row.get(column, 0))

                    if value:
                        values.append(value)

                return values

            def cagr(label):
                values = row_values(label)

                if len(values) < 2:
                    return 0

                latest = values[-1]
                oldest_index = max(0, len(values) - 3)
                oldest = values[oldest_index]
                period = len(values) - 1 - oldest_index

                if latest <= 0 or oldest <= 0 or period <= 0:
                    return 0

                return round(((latest / oldest) ** (1 / period) - 1) * 100, 2)

            def won_from_eok(value):
                return value * 100_000_000 if value else 0

            def listed_shares():
                for table in tables:
                    first_col = table.iloc[:, 0].astype(str)

                    if not first_col.str.contains("상장주식수", na=False).any():
                        continue

                    row = table[
                        first_col.str.contains("상장주식수", na=False)
                    ].iloc[0]

                    return self._safe_float(
                        str(row.iloc[1]).replace(",", "")
                    )

                return 0

            eps = row_value("EPS")
            bps = row_value("BPS")
            per = row_value("PER")
            pbr = row_value("PBR")
            debt_ratio = row_value("부채비율")
            shares = listed_shares()
            equity = bps * shares if bps and shares else 0
            liabilities = (
                equity * debt_ratio / 100
                if equity and debt_ratio
                else 0
            )
            assets = equity + liabilities if equity else 0

            return {
                "sales": won_from_eok(row_value("매출액")),
                "operating_profit": won_from_eok(row_value("영업이익")),
                "net_income": won_from_eok(row_value("당기순이익")),
                "assets": assets,
                "liabilities": liabilities,
                "equity": equity,
                "roe": row_value("ROE"),
                "roa": row_value("ROA"),
                "debt_ratio": debt_ratio,
                "current_ratio": row_value("유동비율") or row_value("당좌비율"),
                "operating_margin": row_value("영업이익률"),
                "net_margin": row_value("순이익률"),
                "sales_growth": row_value("매출액증가율"),
                "op_growth": row_value("영업이익증가율"),
                "eps_growth": row_value("EPS증가율"),
                "sales_cagr_3y": cagr("매출액"),
                "op_cagr_3y": cagr("영업이익"),
                "net_income_cagr_3y": cagr("당기순이익"),
                "eps": eps,
                "bps": bps,
                "per": per,
                "pbr": pbr,
                "dividend_yield": (
                    row_value("배당수익률")
                    or row_value("시가배당률")
                ),
            }

        except Exception as e:
            print("Naver financial load failed:", e)
            return {}

    def _get_krx_fundamental(self, stock_code):

        try:
            ensure_pkg_resources_stub()

            from pykrx import stock

            end = datetime.today()
            start = end - timedelta(days=30)

            df = stock.get_market_fundamental_by_date(
                start.strftime("%Y%m%d"),
                end.strftime("%Y%m%d"),
                stock_code,
            )

            if df.empty:
                return {}

            row = df.dropna(how="all").iloc[-1]

            return {
                "eps": self._safe_float(row.get("EPS", 0)),
                "bps": self._safe_float(row.get("BPS", 0)),
                "per": self._safe_float(row.get("PER", 0)),
                "pbr": self._safe_float(row.get("PBR", 0)),
                "dividend_yield": self._safe_float(row.get("DIV", 0)),
                "dps": self._safe_float(row.get("DPS", 0)),
                "roe": 0,
            }

        except Exception as e:
            print("KRX fundamental load failed:", e)
            return {}

    def get_financials(self, stock_code):

        if self.is_korean_stock(stock_code):
            naver_financials = self._get_naver_financials(stock_code)

            if naver_financials:
                return naver_financials

        for ticker in self._to_ticker_candidates(stock_code):
            try:
                data = yf.Ticker(ticker)
                income = data.financials
                balance = data.balance_sheet
                cashflow = data.cashflow

                financial = {
                    "sales": self._first_value(
                        income,
                        ("Total Revenue", "Operating Revenue")
                    ),
                    "operating_profit": self._first_value(
                        income,
                        ("Operating Income", "EBIT")
                    ),
                    "net_income": self._first_value(
                        income,
                        ("Net Income", "Net Income Common Stockholders")
                    ),
                    "assets": self._first_value(
                        balance,
                        ("Total Assets",)
                    ),
                    "liabilities": self._first_value(
                        balance,
                        ("Total Liabilities Net Minority Interest", "Total Liab")
                    ),
                    "equity": self._first_value(
                        balance,
                        ("Stockholders Equity", "Total Equity Gross Minority Interest")
                    ),
                    "free_cash_flow": self._first_value(
                        cashflow,
                        ("Free Cash Flow",)
                    ),
                    "operating_cash_flow": self._first_value(
                        cashflow,
                        ("Operating Cash Flow", "Total Cash From Operating Activities")
                    ),
                    "capex": abs(self._first_value(
                        cashflow,
                        ("Capital Expenditure", "Capital Expenditures")
                    )),
                    "cash": self._first_value(
                        balance,
                        ("Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments")
                    ),
                    "total_debt": self._first_value(
                        balance,
                        ("Total Debt", "Long Term Debt And Capital Lease Obligation")
                    ),
                }

                sales = financial["sales"]
                operating_profit = financial["operating_profit"]
                net_income = financial["net_income"]
                assets = financial["assets"]
                liabilities = financial["liabilities"]
                equity = financial["equity"]

                financial["roe"] = (
                    round(net_income / equity * 100, 2)
                    if equity > 0
                    else 0
                )
                financial["roa"] = (
                    round(net_income / assets * 100, 2)
                    if assets > 0
                    else 0
                )
                financial["debt_ratio"] = (
                    round(liabilities / equity * 100, 2)
                    if equity > 0
                    else 0
                )
                financial["operating_margin"] = (
                    round(operating_profit / sales * 100, 2)
                    if sales > 0
                    else 0
                )
                financial["net_margin"] = (
                    round(net_income / sales * 100, 2)
                    if sales > 0
                    else 0
                )
                financial["sales_cagr_3y"] = self._cagr_from_frame(
                    income,
                    ("Total Revenue", "Operating Revenue")
                )
                financial["op_cagr_3y"] = self._cagr_from_frame(
                    income,
                    ("Operating Income", "EBIT")
                )
                financial["net_income_cagr_3y"] = self._cagr_from_frame(
                    income,
                    ("Net Income", "Net Income Common Stockholders")
                )

                if any(financial.values()):
                    return financial

            except Exception:
                continue

        return {}

    @staticmethod
    def _first_value(frame, labels):

        if frame is None or frame.empty:
            return 0

        for label in labels:
            if label in frame.index:
                series = frame.loc[label].dropna()

                if not series.empty:
                    return YahooPriceCollector._safe_float(series.iloc[0])

        return 0

    @staticmethod
    def _cagr_from_frame(frame, labels, years=3):

        if frame is None or frame.empty:
            return 0

        for label in labels:
            if label not in frame.index:
                continue

            values = [
                float(value)
                for value in frame.loc[label].dropna().tolist()
                if value
            ]

            if len(values) < 2:
                continue

            latest = values[0]
            oldest_index = min(len(values) - 1, years - 1)
            oldest = values[oldest_index]

            if latest <= 0 or oldest <= 0:
                continue

            period = max(oldest_index, 1)
            return round(((latest / oldest) ** (1 / period) - 1) * 100, 2)

        return 0

    @staticmethod
    def _safe_float(value):

        try:
            return float(value)
        except (TypeError, ValueError):
            return 0

    def get_change_rate(self, stock_code: str, price_data=None):

        try:
            if price_data is None:
                price_data = self.get_price(stock_code)

            if not price_data:
                return None

            price = price_data.get("price")
            prev = price_data.get("prev_close")

            if not price or not prev:
                return None

            return round(((price - prev) / prev) * 100, 2)

        except Exception:
            return None

    def get_history(self, stock_code: str, period="1y", interval=None):

        intraday_interval = interval in ("1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h")

        if self.is_korean_stock(stock_code) and not intraday_interval:
            krx_history = self._get_krx_history(stock_code, period)

            if krx_history is not None:
                return krx_history

        for ticker in self._to_ticker_candidates(stock_code):
            try:
                interval = interval or ("5m" if period == "1d" else "1d")
                hist = yf.Ticker(ticker).history(
                    period=period,
                    interval=interval
                )

                if hist.empty:
                    continue

                hist["MA20"] = hist["Close"].rolling(20).mean()
                hist["MA60"] = hist["Close"].rolling(60).mean()
                hist["MA120"] = hist["Close"].rolling(120).mean()

                return hist

            except Exception:
                continue

        return None

    def _get_krx_history(self, stock_code: str, period="1y"):

        try:
            ensure_pkg_resources_stub()

            from pykrx import stock

            end = datetime.today()
            days = {
                "1d": 7,
                "1mo": 45,
                "3mo": 110,
                "6mo": 210,
                "1y": 370,
            }.get(period, 370)
            start = end - timedelta(days=days)

            df = stock.get_market_ohlcv_by_date(
                start.strftime("%Y%m%d"),
                end.strftime("%Y%m%d"),
                stock_code,
            )

            if df.empty:
                return None

            hist = df.rename(columns={
                "시가": "Open",
                "고가": "High",
                "저가": "Low",
                "종가": "Close",
                "거래량": "Volume",
            })

            hist["MA20"] = hist["Close"].rolling(20).mean()
            hist["MA60"] = hist["Close"].rolling(60).mean()
            hist["MA120"] = hist["Close"].rolling(120).mean()

            return hist

        except Exception as e:
            print("KRX history load failed:", e)
            return None

    def get_technical(self, stock_code: str):

        if self.is_korean_stock(stock_code):
            hist = self._get_krx_history(stock_code)

            if hist is not None:
                return self._technical_from_history(hist)

        for ticker in self._to_ticker_candidates(stock_code):
            try:
                hist = yf.Ticker(ticker).history(period="1y")

                if hist.empty:
                    continue

                return self._technical_from_history(hist)

            except Exception:
                continue

        return None

    @staticmethod
    def _technical_from_history(hist):

        close = hist["Close"]
        volume = hist["Volume"]

        ma20 = float(close.tail(20).mean())
        ma60 = float(close.tail(60).mean())
        ma120 = float(close.tail(120).mean())
        high52 = float(close.max())
        low52 = float(close.min())

        volume_ratio = 0.0

        if len(volume) >= 21:
            avg20 = volume.tail(20).mean()
            yesterday = volume.iloc[-1]

            if avg20 > 0:
                volume_ratio = float(yesterday / avg20)

        return {
            "ma20": round(ma20, 2),
            "ma60": round(ma60, 2),
            "ma120": round(ma120, 2),
            "high52": round(high52, 2),
            "low52": round(low52, 2),
            "volume_ratio": round(volume_ratio, 2),
        }
